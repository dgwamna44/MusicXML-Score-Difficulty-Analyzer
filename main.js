// main.js — Electron entry point for eXeMpLify
"use strict";

const { app, BrowserWindow, dialog, shell, ipcMain } = require("electron");
const path  = require("path");
const { spawn } = require("child_process");
const http  = require("http");
const fs    = require("fs");


// ─────────────────────────────────────────────────────────────
// Config
// ─────────────────────────────────────────────────────────────

const FLASK_PORT = 5000;
const FLASK_HOST = "127.0.0.1";

const FLASK_STARTUP_TIMEOUT_MS = 15000;
const FLASK_POLL_INTERVAL_MS   = 250;
const MIN_SPLASH_TIME_MS  =      8000;


// ─────────────────────────────────────────────────────────────
// State
// ─────────────────────────────────────────────────────────────

let flaskProcess = null;
let flaskStopped = false;
let flaskReady   = false;

let splashWindow = null;
let mainWindow   = null;
let splashStartTime = Date.now();


// ─────────────────────────────────────────────────────────────
// Path helpers
// ─────────────────────────────────────────────────────────────

function rootDir() {

  return app.isPackaged
    ? path.join(process.resourcesPath, "app")
    : __dirname;

}

function exists(p) {

  try {
    return p && fs.existsSync(p);
  } catch {
    return false;
  }

}

function findProjectRoot() {

  const candidates = [

    process.env.EXEMPLIFY_ROOT,
    rootDir(),
    app.getAppPath?.(),
    process.cwd(),

  ].filter(Boolean);

  for (const root of candidates) {

    if (exists(path.join(root, "flask_app.py")) ||
        exists(path.join(root, "html", "index.html"))) {

      return root;

    }

  }

  return rootDir();

}

function findHtmlIndex() {

  const root = findProjectRoot();

  const index = path.join(root, "html", "index.html");

  return exists(index) ? index : null;

}

function findSplashHtml() {

  const root = findProjectRoot();

  const splash = path.join(root, "html", "splash.html");

  return exists(splash) ? splash : null;

}

function findFlaskScript() {

  const root = findProjectRoot();

  const script = path.join(root, "flask_app.py");

  return exists(script) ? script : null;

}

function preloadPath() {

  const p = path.join(findProjectRoot(), "preload.js");

  return exists(p) ? p : undefined;

}


// ─────────────────────────────────────────────────────────────
// Python resolver
// ─────────────────────────────────────────────────────────────

function pythonExecutable() {

  if (app.isPackaged) {

    return process.platform === "win32"
      ? path.join(process.resourcesPath, "python", "python.exe")
      : path.join(process.resourcesPath, "python", "bin", "python3");

  }

  const root = findProjectRoot();

  const venvWin  = path.join(root, ".venv", "Scripts", "python.exe");
  const venvUnix = path.join(root, ".venv", "bin", "python3");

  if (process.platform === "win32" && exists(venvWin))
    return venvWin;

  if (process.platform !== "win32" && exists(venvUnix))
    return venvUnix;

  return process.platform === "win32" ? "python" : "python3";

}


// ─────────────────────────────────────────────────────────────
// Splash window
// ─────────────────────────────────────────────────────────────

function createSplash() {

  const splashHtml = findSplashHtml();

  splashWindow = new BrowserWindow({
  
    width: 720,
    height: 560,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    center: true,
    show: true,

  });

  if (splashHtml)
    splashWindow.loadFile(splashHtml);

  splashWindow.on("closed", () => {
    splashWindow = null;
  });

}

process.env.EXEMPLIFY_ROOT = app.isPackaged
  ? process.resourcesPath
  : app.getAppPath();


// ─────────────────────────────────────────────────────────────
// Main window
// ─────────────────────────────────────────────────────────────

function createMainWindow() {

  mainWindow = new BrowserWindow({

    width: 1400,
    height: 900,

    minWidth: 900,
    minHeight: 600,

    show: false,

    title: "eXeMpLify",

    backgroundColor: "#141416",

    titleBarStyle:
      process.platform === "darwin"
        ? "hiddenInset"
        : "hidden",

    frame:
      process.platform === "darwin",

    webPreferences: {

      preload: preloadPath(),

      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: true,

    }

  });


  const index = findHtmlIndex();

  if (index) {

    mainWindow.loadFile(index);

  }
  else if (flaskReady) {

    mainWindow.loadURL(
      `http://${FLASK_HOST}:${FLASK_PORT}/`
    );

  }
  else {

    mainWindow.loadURL(
      "data:text/plain,eXeMpLify failed to load UI."
    );

  }


  mainWindow.webContents.setWindowOpenHandler(({ url }) => {

    if (url.startsWith("http"))
      shell.openExternal(url);

    return { action: "deny" };

  });


mainWindow.once("ready-to-show", () => {

  const elapsed = Date.now() - splashStartTime;

  const remaining =
    Math.max(0, MIN_SPLASH_TIME_MS - elapsed);

  setTimeout(() => {

    if (splashWindow && !splashWindow.isDestroyed()) {

      splashWindow.close();
      splashWindow = null;

    }

    mainWindow.show();

  }, remaining);

});


  mainWindow.on("closed", () => {
    mainWindow = null;
  });


  if (!app.isPackaged)
    mainWindow.webContents.openDevTools();

}


// ─────────────────────────────────────────────────────────────
// Flask lifecycle
// ─────────────────────────────────────────────────────────────

function startFlask() {

  return new Promise((resolve, reject) => {

    const python = pythonExecutable();
    const script = findFlaskScript();

    if (!script) {

      console.warn("Flask script not found.");
      resolve(false);
      return;

    }

    flaskProcess = spawn(python, [script], {

      cwd: findProjectRoot(),

      env: {

        ...process.env,

        FLASK_ENV: "production",
        FLASK_PORT: String(FLASK_PORT),
        FLASK_HOST,

        PYTHONUNBUFFERED: "1",

      },

      windowsHide: true,

    });


    flaskProcess.stdout.on("data", d =>
      console.log("[Flask]", d.toString())
    );


    flaskProcess.stderr.on("data", d =>
      console.log("[Flask]", d.toString())
    );


    flaskProcess.on("exit", code => {

      flaskProcess = null;

      if (!flaskStopped && mainWindow) {

        dialog.showErrorBox(
          "Backend stopped",
          `Flask exited with code ${code}`
        );

      }

    });


    const deadline =
      Date.now() + FLASK_STARTUP_TIMEOUT_MS;


    function poll() {

      const req = http.get(

        `http://${FLASK_HOST}:${FLASK_PORT}/api/health`,

        res => {

          if (res.statusCode < 500) {

            flaskReady = true;
            resolve(true);

          }
          else retry();

        }

      );

      req.on("error", retry);

    }


    function retry() {

      if (Date.now() > deadline) {

        reject(
          new Error("Flask startup timeout")
        );

        return;

      }

      setTimeout(
        poll,
        FLASK_POLL_INTERVAL_MS
      );

    }


    setTimeout(poll, 500);

  });

}


function stopFlask() {

  if (!flaskProcess) return;

  flaskStopped = true;

  try {

    http.get(
      `http://${FLASK_HOST}:${FLASK_PORT}/api/shutdown`
    );

  } catch {}

  setTimeout(() => {

    flaskProcess?.kill();
    flaskProcess = null;

  }, 1500);

}


// ─────────────────────────────────────────────────────────────
// IPC
// ─────────────────────────────────────────────────────────────

function registerIPC() {

  ipcMain.on("window:minimize",
    () => mainWindow?.minimize());

  ipcMain.on("window:maximize", () => {

    if (!mainWindow) return;

    mainWindow.isMaximized()
      ? mainWindow.unmaximize()
      : mainWindow.maximize();

  });

  ipcMain.on("window:close",
    () => mainWindow?.close());

  ipcMain.handle("app:version",
    () => app.getVersion());

}


// ─────────────────────────────────────────────────────────────
// App lifecycle
// ─────────────────────────────────────────────────────────────

app.whenReady().then(async () => {

  registerIPC();

  createSplash();

  try {

    await startFlask();

  }
  catch (err) {

    console.error(err);

  }

  createMainWindow();

});


app.on("activate", () => {

  if (BrowserWindow.getAllWindows().length === 0)
    createMainWindow();

});


app.on("window-all-closed", () => {

  if (process.platform !== "darwin")
    app.quit();

});


app.on("before-quit", stopFlask);
app.on("will-quit",   stopFlask);


app.on("web-contents-created", (_, contents) => {

  contents.on("will-navigate",
    (event, url) => {

      if (!url.startsWith("file://")) {

        event.preventDefault();
        shell.openExternal(url);

      }

    });

});

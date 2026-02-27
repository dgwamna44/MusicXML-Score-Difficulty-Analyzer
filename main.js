// main.js — Electron entry point for eXeMpLify
"use strict";

process.env.EXEMPLIFY_ROOT = "C:\\Users\\dgwam\\ScoreAnalyzer";

const { app, BrowserWindow, dialog, shell, ipcMain } = require("electron");
const path       = require("path");
const { spawn }  = require("child_process");
const http       = require("http");
const fs         = require("fs");

// ─── Config ───────────────────────────────────────────────────────────────────

const FLASK_PORT               = 5000;
const FLASK_HOST               = "127.0.0.1";
const FLASK_STARTUP_TIMEOUT_MS = 15_000;
const FLASK_POLL_INTERVAL_MS   = 250;

// ─── State ────────────────────────────────────────────────────────────────────

let flaskProcess = null;
let mainWindow   = null;
let flaskStopped = false; // guard: prevents double-stop warning dialog
let flaskReady   = false;

// ─── Path helpers ─────────────────────────────────────────────────────────────

/**
 * Canonical project root in both dev and packaged modes.
 *
 *   Dev:      folder containing main.js  (__dirname)
 *   Packaged: <install>/resources/app/
 *
 * Always use rootDir() instead of bare __dirname so packaged builds
 * resolve correctly and Electron Fiddle / temp-dir launches don't break.
 */
function rootDir() {
  return app.isPackaged
    ? path.join(process.resourcesPath, "app")
    : __dirname;
}

function existingPath(p) {
  try {
    return p && fs.existsSync(p) ? p : null;
  } catch {
    return null;
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
    const flask = path.join(root, "flask_app.py");
    const htmlIndex = path.join(root, "html", "index.html");
    if (existingPath(flask) || existingPath(htmlIndex)) return root;
  }
  return rootDir();
}

function findHtmlIndex() {
  const candidates = [
    process.env.EXEMPLIFY_ROOT,
    rootDir(),
    app.getAppPath?.(),
    process.cwd(),
  ].filter(Boolean);

  for (const root of candidates) {
    const index = path.join(root, "html", "index.html");
    if (existingPath(index)) return index;
  }
  return null;
}

function findFlaskScript() {
  const candidates = [
    process.env.EXEMPLIFY_ROOT,
    rootDir(),
    app.getAppPath?.(),
    process.cwd(),
  ].filter(Boolean);

  for (const root of candidates) {
    const flask = path.join(root, "flask_app.py");
    if (existingPath(flask)) return flask;
  }
  return null;
}

function pythonExecutable() {
  if (app.isPackaged) {
    return process.platform === "win32"
      ? path.join(process.resourcesPath, "python", "python.exe")
      : path.join(process.resourcesPath, "python", "bin", "python3");
  }
  // Dev: prefer a local venv, fall back to system Python
  const projectRoot = findProjectRoot();
  const venvWin  = path.join(projectRoot, ".venv", "Scripts", "python.exe");
  const venvUnix = path.join(projectRoot, ".venv", "bin",     "python3");
  if (process.platform === "win32"  && fs.existsSync(venvWin))  return venvWin;
  if (process.platform !== "win32"  && fs.existsSync(venvUnix)) return venvUnix;
  return process.platform === "win32" ? "python" : "python3";
}

const flaskAppPath = () => findFlaskScript();
const htmlDir      = () => {
  const index = findHtmlIndex();
  return index ? path.dirname(index) : path.join(findProjectRoot(), "html");
};
const preloadPath  = () => path.join(findProjectRoot(), "preload.js");

// ─── Flask lifecycle ──────────────────────────────────────────────────────────

function startFlask() {
  return new Promise((resolve, reject) => {
    const python = pythonExecutable();
    const script = flaskAppPath();

    if (!script) {
      console.warn("[Flask] flask_app.py not found; skipping backend startup.");
      resolve(false);
      return;
    }

    console.log(`[Flask] Starting: ${python} ${script}`);

    flaskProcess = spawn(python, [script], {
      cwd: findProjectRoot(),
      env: {
        ...process.env,
        FLASK_ENV:        "production",
        FLASK_PORT:       String(FLASK_PORT),
        FLASK_HOST,
        PYTHONUNBUFFERED: "1",
      },
      windowsHide: true,
    });

    flaskProcess.stdout.on("data", (d) =>
      console.log(`[Flask stdout] ${d.toString().trimEnd()}`));

    flaskProcess.stderr.on("data", (d) =>
      // Flask logs to stderr by default — this is normal, not an error
      console.log(`[Flask stderr] ${d.toString().trimEnd()}`));

    flaskProcess.on("error", (err) => {
      console.error("[Flask] Failed to spawn:", err.message);
      reject(err);
    });

    flaskProcess.on("exit", (code, signal) => {
      console.log(`[Flask] Process exited — code: ${code}, signal: ${signal}`);
      flaskProcess = null;
      // Only warn the user if Flask died on its own (not because we stopped it)
      if (!flaskStopped && mainWindow && !mainWindow.isDestroyed()) {
        dialog.showMessageBox(mainWindow, {
          type:    "warning",
          title:   "Backend stopped",
          message: "The analysis backend has stopped unexpectedly.",
          detail:  `Exit code: ${code ?? "—"}\n\nYou may need to restart the app.`,
          buttons: ["OK"],
        });
      }
    });

    // Poll /api/health until Flask is accepting connections
    const deadline = Date.now() + FLASK_STARTUP_TIMEOUT_MS;

    function poll() {
      const req = http.get(
        `http://${FLASK_HOST}:${FLASK_PORT}/api/health`,
        (res) => {
          if (res.statusCode < 500) {
            console.log("[Flask] Ready ✓");
            resolve(true);
          } else {
            retry();
          }
          res.resume(); // drain so the socket is freed
        }
      );
      req.on("error", retry);
      req.setTimeout(200, () => { req.destroy(); retry(); });
    }

    function retry() {
      if (Date.now() > deadline) {
        reject(new Error(`Flask did not respond within ${FLASK_STARTUP_TIMEOUT_MS}ms`));
        return;
      }
      setTimeout(poll, FLASK_POLL_INTERVAL_MS);
    }

    setTimeout(poll, 500); // brief pause before first ping
  });
}

function stopFlask() {
  if (!flaskProcess || flaskStopped) return;
  flaskStopped = true;
  console.log("[Flask] Shutting down...");
  // Ask Flask to exit gracefully via its own endpoint
  http.get(`http://${FLASK_HOST}:${FLASK_PORT}/api/shutdown`).on("error", () => {});
  // Hard-kill if still alive after 1.5 s
  setTimeout(() => {
    if (flaskProcess) { flaskProcess.kill("SIGTERM"); flaskProcess = null; }
  }, 1500);
}

// ─── IPC handlers ─────────────────────────────────────────────────────────────
// These match the window control sends in preload.js

function registerIpcHandlers() {
  ipcMain.on("window:minimize", () => mainWindow?.minimize());
  ipcMain.on("window:maximize", () => {
    if (!mainWindow) return;
    mainWindow.isMaximized() ? mainWindow.unmaximize() : mainWindow.maximize();
  });
  ipcMain.on("window:close", () => mainWindow?.close());

  ipcMain.handle("app:version", () => app.getVersion());
}

// ─── Window creation ──────────────────────────────────────────────────────────

function createWindow() {
  const preloadFile = preloadPath();
  const preloadExists = existingPath(preloadFile);

  mainWindow = new BrowserWindow({
    width:     1400,
    height:    900,
    minWidth:  900,
    minHeight: 600,
    title:     "eXeMpLify",

    // macOS keeps its native traffic lights; Win/Linux uses our custom titlebar
    titleBarStyle: process.platform === "darwin" ? "hiddenInset" : "hidden",
    frame:         process.platform === "darwin",

    backgroundColor: "#141416", // matches dark-theme bg, stops white flash on load

    webPreferences: {
      preload:          preloadExists || undefined,
      contextIsolation: true,
      nodeIntegration:  false,
      webSecurity:      true,
    },
  });

  const indexPath = findHtmlIndex();
  if (indexPath) {
    mainWindow.loadFile(indexPath);
  } else if (flaskReady) {
    const fallbackUrl = `http://${FLASK_HOST}:${FLASK_PORT}/`;
    console.warn(`[UI] html/index.html not found, loading ${fallbackUrl}`);
    mainWindow.loadURL(fallbackUrl);
  } else {
    const msg = [
      "eXeMpLify could not find html/index.html or start the backend.",
      "",
      "Fixes:",
      "• Ensure html/ and flask_app.py are included in your Electron bundle.",
      "• Or set EXEMPLIFY_ROOT to the project folder.",
      "",
      "Then restart the app.",
    ].join("\\n");
    mainWindow.loadURL(`data:text/plain,${encodeURIComponent(msg)}`);
  }

  // Open http(s) links in the system browser, not inside Electron
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("http")) shell.openExternal(url);
    return { action: "deny" };
  });

  mainWindow.on("closed", () => { mainWindow = null; });

  // Uncomment to open DevTools on launch during development:
  if (!app.isPackaged) mainWindow.webContents.openDevTools();
}

// ─── App lifecycle ────────────────────────────────────────────────────────────

app.whenReady().then(async () => {
  registerIpcHandlers();

  try {
    flaskReady = await startFlask();
  } catch (err) {
    console.error("[Flask] Startup failed:", err.message);
    const choice = dialog.showMessageBoxSync({
      type:      "error",
      title:     "Backend failed to start",
      message:   "The analysis backend could not start.",
      detail:    `${err.message}\n\nThe app will open but analysis will not work.\nCheck that Python and all dependencies are installed.`,
      buttons:   ["Open Anyway", "Quit"],
      defaultId: 1,
    });
    if (choice === 1) { app.quit(); return; }
  }

  createWindow();

  // macOS: re-create the window when clicking the dock icon
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

// Quit when all windows are closed (except on macOS)
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

// Always clean up Flask on any exit path
app.on("before-quit", stopFlask);
app.on("will-quit",   stopFlask);

// ─── Security: keep navigation inside local files ─────────────────────────────

app.on("web-contents-created", (_, contents) => {
  contents.on("will-navigate", (evt, url) => {
    if (!url.startsWith("file://")) {
      evt.preventDefault();
      shell.openExternal(url);
    }
  });
});

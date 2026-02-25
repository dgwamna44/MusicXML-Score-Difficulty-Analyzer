// main.js — Electron entry point for eXeMpLify
const { app, BrowserWindow, dialog, shell } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const http = require("http");
const fs = require("fs");

// ─── Config ───────────────────────────────────────────────────────────────────

const FLASK_PORT = 5000;
const FLASK_HOST = "127.0.0.1";
const FLASK_STARTUP_TIMEOUT_MS = 15000; // how long to wait for Flask before giving up
const FLASK_POLL_INTERVAL_MS = 250;     // how often to ping Flask while waiting

// ─── State ────────────────────────────────────────────────────────────────────

let flaskProcess = null;
let mainWindow = null;

// ─── Helpers: resolve paths correctly in dev vs packaged app ──────────────────

function isPackaged() {
  return app.isPackaged;
}

/**
 * In dev:       root of your repo  (where package.json lives)
 * In packaged:  resources/app/     (where electron-builder puts your files)
 */
function rootDir() {
  return isPackaged()
    ? path.join(process.resourcesPath, "app")
    : path.join(__dirname);
}

function pythonExecutable() {
  if (isPackaged()) {
    // When packaged, point at the bundled Python (e.g. via PyInstaller or
    // a vendored venv). Adjust this path to match how you bundle Python.
    const win  = path.join(process.resourcesPath, "python", "python.exe");
    const unix = path.join(process.resourcesPath, "python", "bin", "python3");
    if (process.platform === "win32") return win;
    return unix;
  }

  // Dev: use whatever python3/python is on PATH, or a local venv if present.
  const venvWin  = path.join(rootDir(), ".venv", "Scripts", "python.exe");
  const venvUnix = path.join(rootDir(), ".venv", "bin", "python3");
  if (process.platform === "win32" && fs.existsSync(venvWin)) return venvWin;
  if (process.platform !== "win32" && fs.existsSync(venvUnix)) return venvUnix;
  return process.platform === "win32" ? "python" : "python3";
}

function flaskAppPath() {
  return path.join(rootDir(), "flask_app.py");
}

function htmlDir() {
  return path.join(rootDir(), "html");
}

// ─── Flask lifecycle ──────────────────────────────────────────────────────────

function startFlask() {
  return new Promise((resolve, reject) => {
    const python = pythonExecutable();
    const script = flaskAppPath();

    console.log(`[Flask] Starting: ${python} ${script}`);

    flaskProcess = spawn(python, [script], {
      cwd: rootDir(),
      env: {
        ...process.env,
        FLASK_ENV: "production",
        FLASK_PORT: String(FLASK_PORT),
        FLASK_HOST: FLASK_HOST,
        // Prevent Python from buffering stdout/stderr so we see logs immediately
        PYTHONUNBUFFERED: "1",
      },
      // On Windows, CREATE_NO_WINDOW prevents a console flash
      windowsHide: true,
    });

    flaskProcess.stdout.on("data", (data) => {
      console.log(`[Flask stdout] ${data.toString().trim()}`);
    });

    flaskProcess.stderr.on("data", (data) => {
      // Flask logs to stderr by default — this is normal, not an error
      console.log(`[Flask stderr] ${data.toString().trim()}`);
    });

    flaskProcess.on("error", (err) => {
      console.error("[Flask] Failed to start process:", err.message);
      reject(err);
    });

    flaskProcess.on("exit", (code, signal) => {
      console.log(`[Flask] Process exited — code: ${code}, signal: ${signal}`);
      flaskProcess = null;
      // If the main window is still open and Flask dies unexpectedly, warn the user
      if (mainWindow && !mainWindow.isDestroyed()) {
        dialog.showMessageBox(mainWindow, {
          type: "warning",
          title: "Backend stopped",
          message: "The analysis backend has stopped unexpectedly.",
          detail: `Exit code: ${code ?? "—"}\n\nYou may need to restart the app.`,
          buttons: ["OK"],
        });
      }
    });

    // Poll until Flask is accepting connections
    const deadline = Date.now() + FLASK_STARTUP_TIMEOUT_MS;
    const poll = () => {
      const req = http.get(
        `http://${FLASK_HOST}:${FLASK_PORT}/api/health`,
        (res) => {
          // Any response at all means Flask is up
          if (res.statusCode < 500) {
            console.log("[Flask] Ready ✓");
            resolve();
          } else {
            retry();
          }
        }
      );
      req.on("error", retry);
      req.setTimeout(200, () => { req.destroy(); retry(); });
    };

    const retry = () => {
      if (Date.now() > deadline) {
        reject(new Error(`Flask did not start within ${FLASK_STARTUP_TIMEOUT_MS}ms`));
        return;
      }
      setTimeout(poll, FLASK_POLL_INTERVAL_MS);
    };

    // Give Flask a moment to start the process before first poll
    setTimeout(poll, 500);
  });
}

function stopFlask() {
  if (!flaskProcess) return;
  console.log("[Flask] Sending shutdown signal...");
  try {
    // Graceful: ask Flask to shut down via its own endpoint first
    http.get(`http://${FLASK_HOST}:${FLASK_PORT}/api/shutdown`).on("error", () => {});
  } catch (_) {}
  // Hard kill after a short grace period
  setTimeout(() => {
    if (flaskProcess) {
      flaskProcess.kill("SIGTERM");
      flaskProcess = null;
    }
  }, 1500);
}

// ─── Window creation ──────────────────────────────────────────────────────────

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    title: "eXeMpLify",

    // Remove the native titlebar so our custom one shows
    titleBarStyle: process.platform === "darwin" ? "hiddenInset" : "hidden",
    // On Windows/Linux use a frameless window with our own controls
    frame: process.platform === "darwin",

    backgroundColor: "#141416", // match your dark theme bg, prevents white flash on load

    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,   // ← security best practice
      nodeIntegration: false,   // ← keep renderer sandboxed
      webSecurity: true,
    },
  });

  // Load the existing HTML frontend
  mainWindow.loadFile(path.join(htmlDir(), "index.html"));

  // Open external links in the system browser, not Electron
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("http")) shell.openExternal(url);
    return { action: "deny" };
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  // Uncomment during development to auto-open DevTools:
  // mainWindow.webContents.openDevTools();
}

// ─── App lifecycle ────────────────────────────────────────────────────────────

app.whenReady().then(async () => {
  try {
    await startFlask();
  } catch (err) {
    console.error("[Flask] Startup failed:", err.message);
    const choice = dialog.showMessageBoxSync({
      type: "error",
      title: "Backend failed to start",
      message: "The analysis backend could not start.",
      detail: `${err.message}\n\nThe app will open but analysis will not work.\nCheck that Python and all dependencies are installed.`,
      buttons: ["Open Anyway", "Quit"],
      defaultId: 1,
    });
    if (choice === 1) {
      app.quit();
      return;
    }
  }

  createWindow();

  // macOS: re-create window when clicking dock icon with no windows open
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

// Quit when all windows are closed (except on macOS)
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

// Always clean up Flask on exit
app.on("before-quit", () => stopFlask());
app.on("will-quit", () => stopFlask());

// ─── Security: block navigation away from local files ─────────────────────────
app.on("web-contents-created", (_, contents) => {
  contents.on("will-navigate", (evt, url) => {
    if (!url.startsWith("file://")) {
      evt.preventDefault();
      shell.openExternal(url);
    }
  });
});
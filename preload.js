const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  // ── Window controls (used by custom titlebar) ──────────────────────────────
  minimizeWindow: () => ipcRenderer.send("window:minimize"),
  maximizeWindow: () => ipcRenderer.send("window:maximize"),
  closeWindow:    () => ipcRenderer.send("window:close"),

  // ── Platform info (lets your UI adapt: e.g. hide traffic lights on Windows) ─
  platform: process.platform,   // "darwin" | "win32" | "linux"

  // ── App version (for display in settings/about) ───────────────────────────
  appVersion: () => ipcRenderer.invoke("app:version"),
});
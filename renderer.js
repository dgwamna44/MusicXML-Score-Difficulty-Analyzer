/**
 * This file is loaded via the <script> tag in the index.html file and will
 * be executed in the renderer process for that window. No Node.js APIs are
 * available in this process because `nodeIntegration` is turned off and
 * `contextIsolation` is turned on. Use the contextBridge API in `preload.js`
 * to expose Node.js functionality from the main process.
 */
/**
 * renderer.js
 *
 * Runs in the renderer process. Connects window-control buttons and
 * platform/version info exposed by preload.js via contextBridge.
 *
 * NOTE: script.js (type="module") handles all application logic.
 * This file handles only Electron shell integration.
 */

(function () {
  "use strict";

  const api = window.electronAPI;
  if (!api) {
    // Running in a plain browser (dev mode without Electron) — skip silently.
    return;
  }

  // ── Platform class ─────────────────────────────────────────────────────────
  // Add e.g. "platform-win32" / "platform-darwin" / "platform-linux" to <html>
  // so CSS can hide/show traffic lights or custom titlebar controls per OS.
  if (api.platform) {
    document.documentElement.classList.add(`platform-${api.platform}`);
  }

  // ── Custom titlebar window controls ───────────────────────────────────────
  // Wire up any elements with data-window-action="minimize|maximize|close".
  // Add those attributes to your titlebar buttons in index.html.
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-window-action]");
    if (!btn) return;
    switch (btn.dataset.windowAction) {
      case "minimize": api.minimizeWindow(); break;
      case "maximize": api.maximizeWindow(); break;
      case "close":    api.closeWindow();    break;
    }
  });

  // ── App version display ────────────────────────────────────────────────────
  // If you have an element like <span id="appVersion"></span>, fill it in.
  const versionEl = document.getElementById("appVersion");
  if (versionEl && typeof api.appVersion === "function") {
    api.appVersion().then((v) => {
      versionEl.textContent = v ? `v${v}` : "";
    }).catch(() => {});
  }

})();
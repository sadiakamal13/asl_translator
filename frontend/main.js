const { app, BrowserWindow, ipcMain } = require("electron");
const path   = require("path");
const { spawn } = require("child_process");
const readline = require("readline");

let mainWindow;
let detectorProcess;
let llmProcess;

// ── Spawn Python processes ────────────────────────────────────────────────────
function spawnBackend() {
  const pythonCmd = process.platform === "win32" ? "python" : "python3";
  const backendDir = path.join(__dirname, "../backend");

  // 1. ASL detector
  detectorProcess = spawn(pythonCmd, [
    path.join(backendDir, "asl_detector.py"),
  ]);

  // 2. LLM bridge (reads from its own stdin)
  llmProcess = spawn(pythonCmd, [
    path.join(backendDir, "llm_bridge.py"),
  ]);

  // ── Detector stdout → renderer + LLM bridge stdin ────────────────────────
  const detectorRL = readline.createInterface({ input: detectorProcess.stdout });
  detectorRL.on("line", (line) => {
    try {
      const event = JSON.parse(line);

      // Forward all events to renderer
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send("backend-event", event);
      }

      // Forward translate_request to LLM bridge
      if (event.type === "translate_request") {
        llmProcess.stdin.write(line + "\n");
      }
    } catch (_) { /* ignore malformed lines */ }
  });

  // ── LLM bridge stdout → renderer ─────────────────────────────────────────
  const llmRL = readline.createInterface({ input: llmProcess.stdout });
  llmRL.on("line", (line) => {
    try {
      const event = JSON.parse(line);
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send("backend-event", event);
      }
    } catch (_) {}
  });

  // ── Stderr logging ────────────────────────────────────────────────────────
  detectorProcess.stderr.on("data", (d) => {
    const msg = d.toString().trim();
    if (msg) console.error("[detector]", msg);
  });

  llmProcess.stderr.on("data", (d) => {
    const msg = d.toString().trim();
    if (msg) console.error("[llm]", msg);
  });

  detectorProcess.on("exit", (code) => {
    console.log("[detector] exited", code);
  });
  llmProcess.on("exit", (code) => {
    console.log("[llm] exited", code);
  });
}

// ── Create window ─────────────────────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width:  1200,
    height: 820,
    minWidth: 900,
    minHeight: 680,
    backgroundColor: "#0a0a0f",
    titleBarStyle: "hidden",
    trafficLightPosition: { x: 18, y: 18 },
    webPreferences: {
      preload:          path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration:  false,
    },
    icon: path.join(__dirname, "../frontend/assets/icon.png"),
  });

  mainWindow.loadFile(path.join(__dirname, "../frontend/index.html"));

  mainWindow.on("closed", () => {
    mainWindow = null;
    if (detectorProcess) detectorProcess.kill();
    if (llmProcess)      llmProcess.kill();
  });
}

// ── IPC: renderer requests ────────────────────────────────────────────────────
ipcMain.on("clear-sequence", () => {
  // Optionally notify detector to reset (for future extension)
});

// ── App lifecycle ─────────────────────────────────────────────────────────────
app.whenReady().then(() => {
  createWindow();
  spawnBackend();
});

app.on("window-all-closed", () => {
  if (detectorProcess) detectorProcess.kill();
  if (llmProcess)      llmProcess.kill();
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

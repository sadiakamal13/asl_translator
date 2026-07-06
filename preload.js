const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("asl", {
  onBackendEvent: (cb) => ipcRenderer.on("backend-event", (_e, data) => cb(data)),
  clearSequence:  ()   => ipcRenderer.send("clear-sequence"),
});

import { app, BrowserWindow, ipcMain, dialog } from 'electron';
import path from 'path';
import { spawn, ChildProcess } from 'child_process';
import http from 'http';

let mainWindow: BrowserWindow | null = null;
let pythonProcess: ChildProcess | null = null;
const BACKEND_PORT = process.env.NOVA_PORT || '8000';
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;

function findPythonExecutable(): string {
  if (process.env.PYTHON_PATH) {
    return process.env.PYTHON_PATH;
  }
  // Check known conda environment paths first (prefer 'lcd' or 'api' env with PyTorch)
  const userHome = process.env.USERPROFILE || process.env.HOME || '';
  const possiblePaths = [
    path.join(userHome, 'miniconda3', 'envs', 'lcd', 'python.exe'),
    path.join(userHome, 'anaconda3', 'envs', 'lcd', 'python.exe'),
    path.join(userHome, 'miniconda3', 'envs', 'api', 'python.exe'),
    path.join(userHome, 'anaconda3', 'envs', 'api', 'python.exe'),
    path.join(userHome, 'miniconda3', 'python.exe'),
    path.join(userHome, 'anaconda3', 'python.exe'),
    'python',
    'python3',
  ];

  for (const p of possiblePaths) {
    try {
      if (p.includes(path.sep)) {
        const fs = require('fs');
        if (fs.existsSync(p)) {
          return p;
        }
      } else {
        return p;
      }
    } catch {
      // ignore
    }
  }
  return 'python';
}

function startBackendServer(): void {
  const pythonPath = findPythonExecutable();
  const repoRoot = path.resolve(__dirname, '../../../');

  console.log(`[Electron] Starting Python backend with executable: ${pythonPath}`);
  console.log(`[Electron] Backend working directory: ${repoRoot}`);

  pythonProcess = spawn(
    pythonPath,
    ['-m', 'backend.app.main', '--port', BACKEND_PORT, '--host', '127.0.0.1'],
    {
      cwd: repoRoot,
      env: {
        ...process.env,
        PYTHONUNBUFFERED: '1',
      },
      stdio: ['pipe', 'pipe', 'pipe'],
    }
  );

  pythonProcess.stdout?.on('data', (data) => {
    console.log(`[Backend stdout] ${data.toString().trim()}`);
  });

  pythonProcess.stderr?.on('data', (data) => {
    console.error(`[Backend stderr] ${data.toString().trim()}`);
  });

  pythonProcess.on('error', (err) => {
    console.error('[Backend error]', err);
  });

  pythonProcess.on('exit', (code, signal) => {
    console.log(`[Backend exit] Exited with code ${code}, signal ${signal}`);
  });
}

function stopBackendServer(): void {
  if (pythonProcess && pythonProcess.pid) {
    console.log(`[Electron] Terminating backend process PID: ${pythonProcess.pid}`);
    try {
      if (process.platform === 'win32') {
        spawn('taskkill', ['/pid', pythonProcess.pid.toString(), '/f', '/t']);
      } else {
        pythonProcess.kill('SIGTERM');
      }
    } catch (e) {
      console.error('[Electron] Error killing backend process:', e);
    }
    pythonProcess = null;
  }
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1100,
    minHeight: 700,
    backgroundColor: '#0f172a',
    title: 'NOVA AI Trainer',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
      webSecurity: true,
    },
  });

  // Remove default menu bar for clean modern desktop look
  mainWindow.setMenuBarVisibility(false);

  // In development, load from Vite dev server or built dist
  const devServerUrl = process.env.VITE_DEV_SERVER_URL;
  if (devServerUrl) {
    mainWindow.loadURL(devServerUrl);
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// IPC Handlers
ipcMain.handle('app:getBackendUrl', () => BACKEND_URL);
ipcMain.handle('app:getVersion', () => app.getVersion());

ipcMain.handle('dialog:selectDirectory', async (_, defaultPath?: string) => {
  if (!mainWindow) return null;
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory', 'createDirectory'],
    defaultPath: defaultPath,
    title: 'Select Directory',
  });
  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }
  return result.filePaths[0];
});

app.whenReady().then(() => {
  // Start backend unless explicitly disabled (e.g. running standalone backend in another terminal)
  if (process.env.NOVA_NO_SPAWN_BACKEND !== '1') {
    startBackendServer();
  }
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('will-quit', () => {
  stopBackendServer();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

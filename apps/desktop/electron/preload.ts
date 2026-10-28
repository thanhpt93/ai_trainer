import { contextBridge, ipcRenderer } from 'electron';

export interface ElectronAPI {
  getBackendUrl: () => Promise<string>;
  selectDirectory: (defaultPath?: string) => Promise<string | null>;
  getAppVersion: () => Promise<string>;
  isElectron: boolean;
}

const electronAPI: ElectronAPI = {
  getBackendUrl: () => ipcRenderer.invoke('app:getBackendUrl'),
  selectDirectory: (defaultPath?: string) => ipcRenderer.invoke('dialog:selectDirectory', defaultPath),
  getAppVersion: () => ipcRenderer.invoke('app:getVersion'),
  isElectron: true,
};

contextBridge.exposeInMainWorld('electronAPI', electronAPI);

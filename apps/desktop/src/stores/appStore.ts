import { create } from 'zustand';
import { HealthStatus, SystemInfo } from '../types';
import { api } from '../services/api';

interface AppState {
  backendConnected: boolean;
  backendChecking: boolean;
  backendError: string | null;
  health: HealthStatus | null;
  systemInfo: SystemInfo | null;
  lastPingTimeMs: number;
  
  checkBackendStatus: () => Promise<void>;
  fetchSystemInfo: () => Promise<void>;
}

export const useAppStore = create<AppState>((set) => ({
  backendConnected: false,
  backendChecking: false,
  backendError: null,
  health: null,
  systemInfo: null,
  lastPingTimeMs: 0,

  checkBackendStatus: async () => {
    set({ backendChecking: true });
    const startTime = performance.now();
    try {
      const health = await api.checkHealth();
      const latency = Math.round(performance.now() - startTime);
      set({
        backendConnected: health.status === 'healthy',
        backendError: health.status === 'healthy' ? null : 'Backend in degraded state',
        health,
        lastPingTimeMs: latency,
        backendChecking: false,
      });
    } catch (err: any) {
      set({
        backendConnected: false,
        backendError: err.message || 'Unable to reach backend server',
        health: null,
        backendChecking: false,
      });
    }
  },

  fetchSystemInfo: async () => {
    try {
      const info = await api.getSystemInfo();
      set({ systemInfo: info });
    } catch (err) {
      console.error('Failed to fetch system info:', err);
    }
  },
}));

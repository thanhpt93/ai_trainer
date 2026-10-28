import React, { useEffect } from 'react';
import {
  Settings as SettingsIcon,
  HardDrive,
  Cpu,
  Server,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Database,
  Terminal,
} from 'lucide-react';
import { useAppStore } from '../stores/appStore';

export const SettingsPage: React.FC = () => {
  const {
    backendConnected,
    backendChecking,
    backendError,
    health,
    systemInfo,
    lastPingTimeMs,
    checkBackendStatus,
    fetchSystemInfo,
  } = useAppStore();

  useEffect(() => {
    checkBackendStatus();
    fetchSystemInfo();
  }, []);

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between pb-2">
        <div>
          <h1 className="text-xl font-bold text-white">Application Settings & System Environment</h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Hardware runtime capabilities, local storage configuration, and desktop backend status.
          </p>
        </div>
        <button
          onClick={() => {
            checkBackendStatus();
            fetchSystemInfo();
          }}
          disabled={backendChecking}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${backendChecking ? 'animate-spin' : ''}`} />
          <span>Refresh Environment</span>
        </button>
      </div>

      {/* Backend Connectivity Status Card */}
      <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center">
              <Server className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white">Local Python Backend Service</h2>
              <p className="text-xs text-slate-400">FastAPI process running strictly on loopback (127.0.0.1)</p>
            </div>
          </div>
          <div>
            {backendConnected ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-semibold">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Healthy ({lastPingTimeMs}ms)</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 text-xs font-semibold">
                <XCircle className="w-3.5 h-3.5" />
                <span>Disconnected</span>
              </span>
            )}
          </div>
        </div>

        {backendError && (
          <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs rounded-lg">
            {backendError}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 text-xs">
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
            <span className="text-slate-400 block text-[11px]">API Host & Port</span>
            <span className="text-slate-200 font-mono">127.0.0.1:8000</span>
          </div>
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
            <span className="text-slate-400 block text-[11px]">API Specification</span>
            <span className="text-slate-200 font-mono">FastAPI v0.162 (OpenAPI v1)</span>
          </div>
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
            <span className="text-slate-400 block text-[11px]">Database Engine</span>
            <span className="text-slate-200 font-mono">SQLite (WAL Mode + FK)</span>
          </div>
        </div>
      </div>

      {/* Hardware & System Environment Card */}
      <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400 flex items-center justify-center">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white">Hardware & Acceleration Capabilities</h2>
            <p className="text-xs text-slate-400">Host platform details and CUDA acceleration availability</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
          <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800">
            <span className="text-slate-400 block text-[11px]">Operating System</span>
            <span className="text-slate-200 font-mono">{systemInfo?.os || 'Loading...'}</span>
          </div>
          <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800">
            <span className="text-slate-400 block text-[11px]">Python Version</span>
            <span className="text-slate-200 font-mono">{systemInfo?.python_version || 'Loading...'}</span>
          </div>
          <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800">
            <span className="text-slate-400 block text-[11px]">CPU Cores</span>
            <span className="text-slate-200 font-mono">{systemInfo?.cpu_count || 1} Logical Cores</span>
          </div>
          <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800">
            <span className="text-slate-400 block text-[11px]">System RAM</span>
            <span className="text-slate-200 font-mono">
              {systemInfo?.memory_available_gb} GB / {systemInfo?.memory_total_gb} GB Free
            </span>
          </div>
        </div>

        {/* CUDA Hardware Card */}
        <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between text-xs">
          <div>
            <span className="font-semibold text-slate-200 block">NVIDIA CUDA Acceleration</span>
            <span className="text-slate-400 text-[11px]">
              {systemInfo?.cuda_available
                ? `Active: ${systemInfo.cuda_device_name || 'NVIDIA GPU'}`
                : 'No CUDA GPU detected or PyTorch CUDA runtime not initialized.'}
            </span>
          </div>
          <div>
            {systemInfo?.cuda_available ? (
              <span className="px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono font-semibold">
                CUDA Enabled
              </span>
            ) : (
              <span className="px-2.5 py-1 rounded bg-slate-800 text-slate-400 border border-slate-700 font-mono">
                CPU Only
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Storage & Application Paths Card */}
      <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center">
            <HardDrive className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white">Storage Locations & File Hierarchy</h2>
            <p className="text-xs text-slate-400">Documented application metadata and user data directories</p>
          </div>
        </div>

        <div className="space-y-2.5 text-xs font-mono">
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <span className="text-slate-400 block text-[10px] font-sans">Application Metadata Directory</span>
              <span className="text-slate-200 truncate">{systemInfo?.app_data_dir || 'Default OS directory'}</span>
            </div>
            <span className="text-[10px] text-slate-400 font-sans">Metadata & Settings</span>
          </div>

          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <span className="text-slate-400 block text-[10px] font-sans">SQLite Database File</span>
              <span className="text-slate-200 truncate">{systemInfo?.database_path || 'nova_trainer.db'}</span>
            </div>
            <span className="text-[10px] text-slate-400 font-sans">Indexed Records</span>
          </div>
        </div>
      </div>
    </div>
  );
};

import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Activity, Plus, Database, RefreshCw, AlertCircle, CheckCircle2 } from 'lucide-react';
import { useAppStore } from '../stores/appStore';

interface NavbarProps {
  onOpenCreateProject?: () => void;
  onOpenImportDataset?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  onOpenCreateProject,
  onOpenImportDataset,
}) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { backendConnected, backendChecking, backendError, lastPingTimeMs, checkBackendStatus } = useAppStore();

  const getPageTitle = () => {
    const path = location.pathname;
    if (path === '/') return 'Dashboard';
    if (path.startsWith('/projects/')) return 'Project Details';
    if (path === '/projects') return 'Projects';
    if (path.startsWith('/datasets/')) return 'Dataset Details';
    if (path === '/datasets') return 'Datasets';
    if (path === '/annotation') return 'Annotation Studio';
    if (path === '/training') return 'Models & Training';
    if (path === '/experiments') return 'Experiments';
    if (path === '/evaluation') return 'Evaluation';
    if (path === '/models') return 'Model Registry';
    if (path === '/settings') return 'Settings';
    return 'NOVA AI Trainer';
  };

  return (
    <header className="h-16 bg-slate-900/90 backdrop-blur border-b border-slate-800 flex items-center justify-between px-6 z-10 select-none">
      <div className="flex items-center gap-3">
        <h2 className="text-lg font-bold text-slate-100">{getPageTitle()}</h2>
      </div>

      <div className="flex items-center gap-4">
        {/* Backend Connectivity Status Badge */}
        <div className="flex items-center gap-2">
          {backendConnected ? (
            <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>Backend Online</span>
              <span className="text-[10px] text-emerald-400 font-mono">({lastPingTimeMs}ms)</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-medium">
              <span className="w-2 h-2 rounded-full bg-rose-400" />
              <span>{backendChecking ? 'Connecting...' : 'Backend Offline'}</span>
              <button
                onClick={() => checkBackendStatus()}
                className="hover:text-rose-300 ml-1"
                title="Retry connection"
              >
                <RefreshCw className={`w-3 h-3 ${backendChecking ? 'animate-spin' : ''}`} />
              </button>
            </div>
          )}
        </div>

        {/* Global Quick Action Buttons */}
        <div className="flex items-center gap-2 border-l border-slate-800 pl-4">
          <button
            onClick={() => {
              if (onOpenCreateProject) onOpenCreateProject();
              else navigate('/projects?create=true');
            }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/20 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Project</span>
          </button>
          <button
            onClick={() => {
              if (onOpenImportDataset) onOpenImportDataset();
              else navigate('/datasets?import=true');
            }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition-colors"
          >
            <Database className="w-3.5 h-3.5" />
            <span>Import Dataset</span>
          </button>
        </div>
      </div>
    </header>
  );
};

import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FolderKanban,
  Database,
  Images,
  Activity,
  Plus,
  ArrowRight,
  PenTool,
  Cpu,
  Clock,
  AlertCircle,
} from 'lucide-react';
import { api } from '../services/api';
import { DashboardStats } from '../types';
import { useAppStore } from '../stores/appStore';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { backendConnected } = useAppStore();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getDashboardStats();
      setStats(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard metrics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, [backendConnected]);

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Top Banner / Welcome */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-xl bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">NOVA AI Trainer Workspace</h1>
          <p className="text-sm text-slate-400 mt-1">
            Central hub for managing computer vision datasets, project workflows, and training configurations.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/projects?create=true')}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold shadow-lg shadow-indigo-600/30 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Create Project</span>
          </button>
          <button
            onClick={() => navigate('/datasets?import=true')}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-sm font-medium transition-all"
          >
            <Database className="w-4 h-4" />
            <span>Import Dataset</span>
          </button>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
          <button
            onClick={fetchStats}
            className="px-3 py-1 bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 rounded text-xs font-medium"
          >
            Retry
          </button>
        </div>
      )}

      {/* Key Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Projects */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Total Projects</span>
            <div className="w-9 h-9 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <FolderKanban className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-extrabold text-white">
              {loading ? '-' : stats?.total_projects ?? 0}
            </span>
            <span className="text-xs text-slate-400 ml-2">projects created</span>
          </div>
        </div>

        {/* Total Datasets */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Total Datasets</span>
            <div className="w-9 h-9 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
              <Database className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-extrabold text-white">
              {loading ? '-' : stats?.total_datasets ?? 0}
            </span>
            <span className="text-xs text-slate-400 ml-2">managed datasets</span>
          </div>
        </div>

        {/* Total Indexed Images */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Indexed Images</span>
            <div className="w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <Images className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-extrabold text-white">
              {loading ? '-' : stats?.total_indexed_images.toLocaleString() ?? 0}
            </span>
            <span className="text-xs text-slate-400 ml-2">images verified</span>
          </div>
        </div>

        {/* Running Training Jobs */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Active Jobs</span>
            <div className="w-9 h-9 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
              <Activity className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-3xl font-extrabold text-white">
              {loading ? '-' : stats?.running_training_jobs ?? 0}
            </span>
            <span className="text-xs text-slate-400 ml-2">jobs running</span>
          </div>
        </div>
      </div>

      {/* Grid: Recent Projects & Quick Action Shortcuts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Recent Projects */}
        <div className="lg:col-span-2 p-6 rounded-xl bg-slate-900 border border-slate-800 flex flex-col">
          <div className="flex items-center justify-between pb-4 border-b border-slate-800">
            <div>
              <h2 className="text-base font-bold text-white">Recent Projects</h2>
              <p className="text-xs text-slate-400 mt-0.5">Projects created and active in your workspace</p>
            </div>
            <button
              onClick={() => navigate('/projects')}
              className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 font-medium"
            >
              <span>View all</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="mt-4 flex-1">
            {loading ? (
              <div className="py-12 flex justify-center text-slate-400 text-sm">
                <span>Loading projects...</span>
              </div>
            ) : !stats?.recent_projects || stats.recent_projects.length === 0 ? (
              <div className="py-12 flex flex-col items-center justify-center text-center">
                <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center text-slate-400 mb-3">
                  <FolderKanban className="w-6 h-6" />
                </div>
                <h3 className="text-sm font-semibold text-slate-300">No projects yet</h3>
                <p className="text-xs text-slate-400 max-w-sm mt-1">
                  Create your first computer vision project to begin importing datasets and configuring models.
                </p>
                <button
                  onClick={() => navigate('/projects?create=true')}
                  className="mt-4 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium"
                >
                  Create Project
                </button>
              </div>
            ) : (
              <div className="divide-y divide-slate-800/60">
                {stats.recent_projects.map((project) => (
                  <div
                    key={project.id}
                    onClick={() => navigate(`/projects/${project.id}`)}
                    className="py-3 px-2 flex items-center justify-between hover:bg-slate-800/40 rounded-lg cursor-pointer transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 font-semibold text-xs">
                        {project.name.slice(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-white hover:text-indigo-400 transition-colors">
                          {project.name}
                        </h4>
                        <div className="flex items-center gap-2 mt-0.5 text-[11px] text-slate-400">
                          <span className="px-1.5 py-0.2 rounded bg-indigo-950 text-indigo-300 border border-indigo-800/60">
                            {project.task_type}
                          </span>
                          <span>•</span>
                          <span className="font-mono">{project.dataset_count || 0} datasets</span>
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-[11px] text-slate-400 flex items-center gap-1 font-mono">
                        <Clock className="w-3 h-3" />
                        {new Date(project.updated_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right 1 Col: Quick Actions & Future Phase Preview */}
        <div className="space-y-4">
          <div className="p-6 rounded-xl bg-slate-900 border border-slate-800">
            <h2 className="text-base font-bold text-white mb-1">Quick Actions</h2>
            <p className="text-xs text-slate-400 mb-4">Direct workflow shortcuts</p>

            <div className="space-y-2.5">
              <button
                onClick={() => navigate('/projects?create=true')}
                className="w-full flex items-center justify-between p-3 rounded-lg bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 text-left transition-colors group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
                    <FolderKanban className="w-4 h-4" />
                  </div>
                  <div>
                    <span className="text-xs font-semibold text-slate-200 block group-hover:text-indigo-400">
                      Create Project
                    </span>
                    <span className="text-[11px] text-slate-400">Set up metadata & task type</span>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-slate-200" />
              </button>

              <button
                onClick={() => navigate('/datasets?import=true')}
                className="w-full flex items-center justify-between p-3 rounded-lg bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 text-left transition-colors group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-sky-500/10 text-sky-400 flex items-center justify-center">
                    <Database className="w-4 h-4" />
                  </div>
                  <div>
                    <span className="text-xs font-semibold text-slate-200 block group-hover:text-sky-400">
                      Import Dataset
                    </span>
                    <span className="text-[11px] text-slate-400">Scan & index local image folders</span>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-slate-200" />
              </button>

              <button
                onClick={() => navigate('/annotation')}
                className="w-full flex items-center justify-between p-3 rounded-lg bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 text-left transition-colors group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
                    <PenTool className="w-4 h-4" />
                  </div>
                  <div>
                    <span className="text-xs font-semibold text-slate-200 block group-hover:text-emerald-400">
                      Annotation Studio
                    </span>
                    <span className="text-[11px] text-slate-400">Label images & draw bounding boxes</span>
                  </div>
                </div>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                  Ready
                </span>
              </button>

              <button
                onClick={() => navigate('/training')}
                className="w-full flex items-center justify-between p-3 rounded-lg bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 text-left transition-colors group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center">
                    <Cpu className="w-4 h-4" />
                  </div>
                  <div>
                    <span className="text-xs font-semibold text-slate-200 block group-hover:text-purple-400">
                      Start Training
                    </span>
                    <span className="text-[11px] text-slate-400">Configure & launch training worker</span>
                  </div>
                </div>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-700 text-slate-300 font-mono">
                  Phase 3
                </span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

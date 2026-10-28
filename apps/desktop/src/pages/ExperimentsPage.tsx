import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FlaskConical,
  RefreshCw,
  Activity,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ExternalLink,
  ChevronRight,
  Sliders,
} from 'lucide-react';
import { api } from '../services/api';
import { TrainingJob } from '../types';

export const ExperimentsPage: React.FC = () => {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<TrainingJob[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedJobIds, setSelectedJobIds] = useState<string[]>([]);

  const loadJobs = async () => {
    setLoading(true);
    try {
      const data = await api.getTrainingJobs();
      setJobs(data);
    } catch (err) {
      console.error('Failed to load experiment jobs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
  }, []);

  const toggleSelect = (id: string) => {
    setSelectedJobIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const selectedJobs = jobs.filter((j) => selectedJobIds.includes(j.id));

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950 overflow-y-auto select-none">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/60 backdrop-blur px-8 py-5 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
              Experiment Hub
            </span>
            <h1 className="text-xl font-bold text-white tracking-tight">Experiment Tracking & Comparison</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Compare model hyperparameter configurations, validation trajectories, and benchmarks across training runs.
          </p>
        </div>

        <button
          onClick={loadJobs}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-200 rounded-lg text-xs font-semibold transition"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      <div className="p-8 space-y-6 max-w-7xl">
        {/* Comparison Section (if 2 or more selected) */}
        {selectedJobs.length >= 2 && (
          <div className="bg-slate-900 border border-indigo-500/40 rounded-xl p-5 shadow-lg shadow-indigo-500/5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Sliders className="w-4 h-4 text-indigo-400" />
                <h2 className="text-sm font-semibold text-white">
                  Comparing {selectedJobs.length} Selected Experiments
                </h2>
              </div>
              <button
                onClick={() => setSelectedJobIds([])}
                className="text-xs text-slate-400 hover:text-white"
              >
                Clear Selection
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400">
                    <th className="py-2 px-3">Run Name</th>
                    <th className="py-2 px-3">Backbone</th>
                    <th className="py-2 px-3">Status</th>
                    <th className="py-2 px-3">Epochs</th>
                    <th className="py-2 px-3">Best Val Accuracy</th>
                    <th className="py-2 px-3">Device</th>
                    <th className="py-2 px-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                  {selectedJobs.map((j) => (
                    <tr key={j.id} className="hover:bg-slate-800/30">
                      <td className="py-2 px-3 font-semibold text-white font-sans">{j.name || j.id.slice(0, 8)}</td>
                      <td className="py-2 px-3 text-indigo-400">{j.model_architecture}</td>
                      <td className="py-2 px-3 font-sans text-xs">
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                          {j.status}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-slate-300">{j.current_epoch} / {j.total_epochs}</td>
                      <td className="py-2 px-3 text-emerald-400 font-semibold font-sans">
                        {j.best_metric_value !== null && j.best_metric_value !== undefined
                          ? `${(j.best_metric_value * 100).toFixed(1)}%`
                          : '—'}
                      </td>
                      <td className="py-2 px-3 uppercase text-slate-400">{j.device || 'cpu'}</td>
                      <td className="py-2 px-3 text-right font-sans">
                        <button
                          onClick={() => navigate(`/training/${j.id}`)}
                          className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-[11px] transition"
                        >
                          View Telemetry
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Full Experiments Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">All Experiment Runs ({jobs.length})</h2>
            <span className="text-[11px] text-slate-500">
              Select multiple runs with checkboxes to trigger side-by-side comparison.
            </span>
          </div>

          {loading ? (
            <div className="p-12 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
              Loading experiment records...
            </div>
          ) : jobs.length === 0 ? (
            <div className="p-12 text-center text-slate-500 text-xs">
              No training runs executed yet. Go to <button onClick={() => navigate('/training')} className="text-indigo-400 underline">Training Engine</button> to launch an experiment.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-950/40 text-slate-400">
                    <th className="py-3 px-3 w-8"></th>
                    <th className="py-3 px-4 font-medium">Run Name</th>
                    <th className="py-3 px-4 font-medium">Model</th>
                    <th className="py-3 px-4 font-medium">Status</th>
                    <th className="py-3 px-4 font-medium">Progress</th>
                    <th className="py-3 px-4 font-medium">Best Val Accuracy</th>
                    <th className="py-3 px-4 font-medium">Device</th>
                    <th className="py-3 px-4 font-medium">Executed</th>
                    <th className="py-3 px-4 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {jobs.map((job) => {
                    const isSelected = selectedJobIds.includes(job.id);
                    return (
                      <tr key={job.id} className="hover:bg-slate-800/30 transition">
                        <td className="py-3 px-3">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleSelect(job.id)}
                            className="rounded bg-slate-950 border-slate-700 text-indigo-600 focus:ring-0 cursor-pointer"
                          />
                        </td>
                        <td className="py-3 px-4 font-semibold text-white">
                          <button
                            onClick={() => navigate(`/training/${job.id}`)}
                            className="hover:text-indigo-400 transition flex items-center gap-1.5"
                          >
                            <span>{job.name || job.id.slice(0, 8)}</span>
                            <ChevronRight className="w-3.5 h-3.5 opacity-50" />
                          </button>
                        </td>
                        <td className="py-3 px-4 font-mono text-[11px] text-slate-300">
                          {job.model_architecture || 'resnet18'}
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2 py-0.5 rounded text-[11px] font-semibold border ${
                              job.status === 'COMPLETED'
                                ? 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30'
                                : job.status === 'RUNNING'
                                ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                                : job.status === 'FAILED'
                                ? 'bg-rose-500/20 text-rose-400 border-rose-500/30'
                                : 'bg-slate-800 text-slate-400 border-slate-700'
                            }`}
                          >
                            {job.status}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-400">
                          Epoch {job.current_epoch} / {job.total_epochs}
                        </td>
                        <td className="py-3 px-4">
                          {job.best_metric_value !== null && job.best_metric_value !== undefined ? (
                            <span className="text-emerald-400 font-semibold font-mono">
                              {(job.best_metric_value * 100).toFixed(1)}%
                            </span>
                          ) : (
                            <span className="text-slate-500">—</span>
                          )}
                        </td>
                        <td className="py-3 px-4 uppercase font-mono text-[10px] text-slate-400">
                          {job.device || 'cpu'}
                        </td>
                        <td className="py-3 px-4 text-slate-400">
                          {new Date(job.created_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                            month: 'short',
                            day: 'numeric',
                          })}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              onClick={() => navigate(`/training/${job.id}`)}
                              className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs transition"
                            >
                              Monitor
                            </button>
                            {job.status === 'COMPLETED' && (
                              <button
                                onClick={() => navigate(`/evaluation?job=${job.id}`)}
                                className="px-2 py-1 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 rounded text-xs transition"
                              >
                                Eval
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

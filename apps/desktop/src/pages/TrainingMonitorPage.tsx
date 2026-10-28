import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Play,
  Pause,
  StopCircle,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Cpu,
  Terminal,
  Activity,
  LineChart,
  Boxes,
  Download,
  Clock,
  Sparkles,
} from 'lucide-react';
import { api } from '../services/api';
import {
  TrainingJob,
  EpochMetric,
  ExportModelResponse,
} from '../types';

export const TrainingMonitorPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [job, setJob] = useState<TrainingJob | null>(null);
  const [metrics, setMetrics] = useState<EpochMetric[]>([]);
  const [logs, setLogs] = useState<string[]>([]);
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const [isCancelling, setIsCancelling] = useState<boolean>(false);
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [exportResult, setExportResult] = useState<ExportModelResponse | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  const logsEndRef = useRef<HTMLDivElement>(null);

  // Poll job status, metrics, and logs
  useEffect(() => {
    if (!id) return;

    let isMounted = true;
    const fetchStatus = async () => {
      try {
        const [jobData, metricsData, logsData] = await Promise.all([
          api.getTrainingJob(id),
          api.getTrainingJobMetrics(id),
          api.getTrainingJobLogs(id, 250),
        ]);

        if (isMounted) {
          setJob(jobData);
          setMetrics(metricsData);
          setLogs(logsData.logs || []);
        }
      } catch (err: any) {
        console.error('Error polling training job:', err);
      }
    };

    fetchStatus();

    // Poll every 1.5s if job is running or preparing
    const timer = setInterval(() => {
      if (job && (job.status === 'COMPLETED' || job.status === 'CANCELLED' || job.status === 'FAILED')) {
        clearInterval(timer);
        return;
      }
      fetchStatus();
    }, 1500);

    return () => {
      isMounted = false;
      clearInterval(timer);
    };
  }, [id, job?.status]);

  // Auto-scroll logs
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const handleCancelJob = async () => {
    if (!id || !window.confirm('Are you sure you want to cancel this training job?')) return;
    setIsCancelling(true);
    try {
      const res = await api.cancelTrainingJob(id);
      setJob(res);
    } catch (err: any) {
      alert(`Cancel failed: ${err.message}`);
    } finally {
      setIsCancelling(false);
    }
  };

  const handleExportModel = async () => {
    if (!id) return;
    setIsExporting(true);
    setExportError(null);
    try {
      const resp = await api.exportTrainingJobModel(id, {
        format: 'ONNX',
        input_size: 224,
        dynamic_batch: true,
      });
      setExportResult(resp);
    } catch (err: any) {
      setExportError(err.message || 'Export failed');
    } finally {
      setIsExporting(false);
    }
  };

  if (!job) {
    return (
      <div className="flex-1 flex items-center justify-center bg-slate-950 text-slate-400 text-xs gap-2">
        <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
        Loading training monitor telemetry...
      </div>
    );
  }

  const latestMetric = metrics.length > 0 ? metrics[metrics.length - 1] : null;

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950 overflow-hidden select-none">
      {/* Top Header */}
      <div className="border-b border-slate-800 bg-slate-900/60 backdrop-blur px-6 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/training')}
            className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 transition"
            title="Back to training"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-white">
                {job.name || `Job ${job.id.slice(0, 8)}`}
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-300 border border-slate-700">
                {job.model_architecture || 'resnet18'}
              </span>
              <span
                className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                  job.status === 'RUNNING'
                    ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30 animate-pulse'
                    : job.status === 'COMPLETED'
                    ? 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30'
                    : job.status === 'CANCELLED'
                    ? 'bg-amber-500/20 text-amber-400 border-amber-500/30'
                    : job.status === 'FAILED'
                    ? 'bg-rose-500/20 text-rose-400 border-rose-500/30'
                    : 'bg-slate-800 text-slate-400 border-slate-700'
                }`}
              >
                {job.status}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Device: <span className="uppercase text-slate-300 font-mono">{job.device || 'cpu'}</span>
              {job.started_at && ` • Started: ${new Date(job.started_at).toLocaleTimeString()}`}
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          {job.status === 'RUNNING' && (
            <button
              onClick={handleCancelJob}
              disabled={isCancelling}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/40 text-rose-300 rounded-lg text-xs font-semibold transition"
            >
              <StopCircle className="w-3.5 h-3.5" />
              {isCancelling ? 'Cancelling...' : 'Cancel Job'}
            </button>
          )}

          {job.status === 'COMPLETED' && (
            <>
              <button
                onClick={() => navigate(`/evaluation?job=${job.id}`)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-indigo-600/20 transition"
              >
                <Activity className="w-3.5 h-3.5" />
                View Evaluation
              </button>

              <button
                onClick={handleExportModel}
                disabled={isExporting}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-emerald-600/20 transition"
              >
                <Download className="w-3.5 h-3.5" />
                {isExporting ? 'Exporting ONNX...' : 'Export ONNX'}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Export Success Banner */}
      {exportResult && (
        <div className="mx-6 mt-3 p-3 bg-emerald-950/30 border border-emerald-500/40 rounded-lg text-xs text-emerald-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span>
              Model exported to ONNX: <strong>{exportResult.onnx_file_path}</strong> (
              {(exportResult.file_size_bytes / (1024 * 1024)).toFixed(2)} MB, Verified with smoke inference)
            </span>
          </div>
          <button
            onClick={() => navigate('/models')}
            className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded font-medium text-[11px]"
          >
            View in Registry
          </button>
        </div>
      )}

      {exportError && (
        <div className="mx-6 mt-3 p-3 bg-rose-950/30 border border-rose-500/40 rounded-lg text-xs text-rose-200 flex items-center gap-2">
          <XCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
          <span>{exportError}</span>
        </div>
      )}

      {/* KPI Stats Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 px-6 py-4 border-b border-slate-800 bg-slate-900/30">
        <div className="bg-slate-900/80 border border-slate-800 p-3 rounded-xl">
          <span className="text-[10px] text-slate-400 uppercase font-semibold">Progress</span>
          <div className="text-lg font-bold text-white mt-0.5">
            Epoch {job.current_epoch} <span className="text-xs text-slate-500 font-normal">/ {job.total_epochs}</span>
          </div>
          <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
            <div
              className="bg-indigo-500 h-full rounded-full transition-all duration-500"
              style={{
                width: `${Math.min(100, (job.current_epoch / Math.max(1, job.total_epochs)) * 100)}%`,
              }}
            />
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 p-3 rounded-xl">
          <span className="text-[10px] text-slate-400 uppercase font-semibold">Best Val Accuracy</span>
          <div className="text-lg font-bold text-emerald-400 mt-0.5">
            {job.best_metric_value !== null && job.best_metric_value !== undefined ? (
              `${(job.best_metric_value * 100).toFixed(1)}%`
            ) : (
              '—'
            )}
          </div>
          <span className="text-[10px] text-slate-500">Highest validation score</span>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 p-3 rounded-xl">
          <span className="text-[10px] text-slate-400 uppercase font-semibold">Latest Train Loss</span>
          <div className="text-lg font-bold text-white mt-0.5 font-mono">
            {latestMetric ? latestMetric.train_loss.toFixed(4) : '—'}
          </div>
          <span className="text-[10px] text-slate-500">
            {latestMetric ? `Train Acc: ${(latestMetric.train_accuracy * 100).toFixed(1)}%` : 'Awaiting 1st epoch'}
          </span>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 p-3 rounded-xl">
          <span className="text-[10px] text-slate-400 uppercase font-semibold">Learning Rate</span>
          <div className="text-lg font-bold text-white mt-0.5 font-mono">
            {latestMetric ? latestMetric.learning_rate.toExponential(2) : '—'}
          </div>
          <span className="text-[10px] text-slate-500">
            {latestMetric ? `Epoch Time: ${latestMetric.duration_seconds}s` : 'Active worker'}
          </span>
        </div>
      </div>

      {/* Main Grid: Curves & Terminal Logs */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-4 p-6 overflow-hidden">
        {/* Left Column: Visual Charts / Telemetry */}
        <div className="flex flex-col bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
          <div className="p-3 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-semibold text-white">
              <LineChart className="w-4 h-4 text-indigo-400" />
              <span>Training Telemetry Curves</span>
            </div>
            <span className="text-[10px] text-slate-500">
              {metrics.length} Epoch{metrics.length !== 1 ? 's' : ''} Recorded
            </span>
          </div>

          <div className="flex-1 p-4 overflow-y-auto space-y-4">
            {/* Accuracy Table / Curve Preview */}
            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/80">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-300 mb-2">
                <span>Validation Accuracy Progression</span>
                <span className="text-emerald-400 text-[11px]">
                  Target: 100%
                </span>
              </div>

              {metrics.length === 0 ? (
                <div className="py-8 text-center text-slate-600 text-xs">
                  Awaiting first epoch completion to plot metric curves...
                </div>
              ) : (
                <div className="space-y-1.5">
                  {metrics.map((m) => (
                    <div key={m.epoch} className="flex items-center gap-3 text-xs">
                      <span className="w-12 text-slate-500 font-mono text-[11px]">
                        Ep {m.epoch}
                      </span>
                      <div className="flex-1 bg-slate-900 h-3 rounded overflow-hidden flex">
                        <div
                          className="bg-indigo-500 h-full rounded transition-all"
                          style={{ width: `${(m.val_accuracy || 0) * 100}%` }}
                        />
                      </div>
                      <span className="w-14 text-right font-mono text-[11px] text-slate-300 font-semibold">
                        {m.val_accuracy !== null && m.val_accuracy !== undefined
                          ? `${(m.val_accuracy * 100).toFixed(1)}%`
                          : '—'}
                      </span>
                      <span className="w-14 text-right font-mono text-[10px] text-slate-500">
                        {m.duration_seconds}s
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Epoch Metrics History Table */}
            <div className="bg-slate-950 rounded-lg border border-slate-800/80 overflow-hidden">
              <div className="px-3 py-2 border-b border-slate-800 text-[11px] font-semibold text-slate-400">
                Detailed Epoch Telemetry
              </div>
              <div className="max-h-48 overflow-y-auto">
                <table className="w-full text-left border-collapse text-[11px]">
                  <thead>
                    <tr className="border-b border-slate-800 bg-slate-900/40 text-slate-400 font-mono">
                      <th className="py-1.5 px-3">Ep</th>
                      <th className="py-1.5 px-3">Train Loss</th>
                      <th className="py-1.5 px-3">Train Acc</th>
                      <th className="py-1.5 px-3">Val Loss</th>
                      <th className="py-1.5 px-3">Val Acc</th>
                      <th className="py-1.5 px-3">Val F1</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/40 font-mono">
                    {metrics.map((m) => (
                      <tr key={m.epoch} className="hover:bg-slate-900/30">
                        <td className="py-1.5 px-3 text-slate-300">{m.epoch}</td>
                        <td className="py-1.5 px-3 text-slate-400">{m.train_loss.toFixed(4)}</td>
                        <td className="py-1.5 px-3 text-slate-300">{(m.train_accuracy * 100).toFixed(1)}%</td>
                        <td className="py-1.5 px-3 text-slate-400">
                          {m.val_loss !== null && m.val_loss !== undefined ? m.val_loss.toFixed(4) : '—'}
                        </td>
                        <td className="py-1.5 px-3 text-emerald-400 font-semibold">
                          {m.val_accuracy !== null && m.val_accuracy !== undefined
                            ? `${(m.val_accuracy * 100).toFixed(1)}%`
                            : '—'}
                        </td>
                        <td className="py-1.5 px-3 text-indigo-400">
                          {m.val_f1 !== null && m.val_f1 !== undefined ? m.val_f1.toFixed(4) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Real-Time Worker Console Logs */}
        <div className="flex flex-col bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
          <div className="p-3 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-semibold text-white">
              <Terminal className="w-4 h-4 text-emerald-400" />
              <span>Training Worker Output Logs</span>
            </div>
            <label className="flex items-center gap-1.5 text-[11px] text-slate-400 cursor-pointer">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="rounded bg-slate-950 border-slate-700 text-indigo-600 focus:ring-0"
              />
              <span>Auto-scroll</span>
            </label>
          </div>

          <div className="flex-1 p-4 bg-slate-950 font-mono text-[11px] text-slate-300 overflow-y-auto space-y-1">
            {logs.length === 0 ? (
              <div className="text-slate-600 italic">No output logs captured yet...</div>
            ) : (
              logs.map((line, idx) => {
                let color = 'text-slate-300';
                if (line.includes('[ERROR]') || line.includes('FATAL') || line.includes('Error')) {
                  color = 'text-rose-400 font-semibold';
                } else if (line.includes('[WARNING]') || line.includes('warning')) {
                  color = 'text-amber-400';
                } else if (line.includes('Best model') || line.includes('SUCCESS') || line.includes('COMPLETED')) {
                  color = 'text-emerald-400 font-semibold';
                }

                return (
                  <div key={idx} className={`${color} leading-relaxed break-all`}>
                    {line}
                  </div>
                );
              })
            )}
            <div ref={logsEndRef} />
          </div>
        </div>
      </div>
    </div>
  );
};

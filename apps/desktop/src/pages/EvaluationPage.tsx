import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Activity,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  LineChart,
  ArrowRight,
  Eye,
  FileQuestion,
  Sparkles,
} from 'lucide-react';
import { api } from '../services/api';
import { TrainingJob, EvaluationReport } from '../types';

export const EvaluationPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [jobs, setJobs] = useState<TrainingJob[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string>('');
  const [evaluation, setEvaluation] = useState<EvaluationReport | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  // 1. Load Completed Jobs
  useEffect(() => {
    const loadJobs = async () => {
      try {
        const allJobs = await api.getTrainingJobs();
        const completed = allJobs.filter((j) => j.status === 'COMPLETED');
        setJobs(completed);

        const paramJob = searchParams.get('job');
        const activeJob = paramJob || (completed.length > 0 ? completed[0].id : '');
        if (activeJob) {
          setSelectedJobId(activeJob);
        }
      } catch (err) {
        console.error('Failed to load training jobs:', err);
      }
    };
    loadJobs();
  }, []);

  // 2. Load Evaluation Report when job changes
  useEffect(() => {
    if (!selectedJobId) {
      setEvaluation(null);
      return;
    }

    const loadEval = async () => {
      setLoading(true);
      try {
        const data = await api.getTrainingJobEvaluations(selectedJobId);
        if (data && data.accuracy !== undefined) {
          setEvaluation(data as EvaluationReport);
        } else {
          setEvaluation(null);
        }
      } catch (err) {
        console.error('Failed to load evaluation:', err);
        setEvaluation(null);
      } finally {
        setLoading(false);
      }
    };

    loadEval();
  }, [selectedJobId]);

  const activeJob = jobs.find((j) => j.id === selectedJobId);

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950 overflow-y-auto select-none">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/60 backdrop-blur px-8 py-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
              Evaluation Studio
            </span>
            <h1 className="text-xl font-bold text-white tracking-tight">Model Evaluation & Benchmark</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Examine confusion matrices, per-class metrics, and inspect misclassified test samples.
          </p>
        </div>

        {/* Job Selector Dropdown */}
        <div className="flex items-center gap-3">
          <label className="text-xs text-slate-400 font-medium">Evaluation Job:</label>
          <select
            value={selectedJobId}
            onChange={(e) => {
              setSelectedJobId(e.target.value);
              setSearchParams({ job: e.target.value });
            }}
            disabled={jobs.length === 0}
            className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500 disabled:opacity-50 min-w-[220px]"
          >
            {jobs.length === 0 && <option value="">No completed jobs found</option>}
            {jobs.map((j) => (
              <option key={j.id} value={j.id}>
                {j.name || j.id.slice(0, 8)} ({j.model_architecture})
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center p-12 text-slate-400 text-xs gap-2">
          <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
          Loading evaluation report...
        </div>
      ) : !evaluation ? (
        <div className="p-16 text-center text-slate-500 text-xs">
          {jobs.length === 0
            ? 'No completed classification jobs available for evaluation. Train a model first.'
            : 'Select a completed training job from the dropdown above to view benchmark results.'}
        </div>
      ) : (
        <div className="p-8 space-y-6 max-w-6xl">
          {/* Top KPI Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl shadow-sm">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Overall Accuracy</span>
              <div className="text-2xl font-bold text-emerald-400 mt-1">
                {(evaluation.accuracy * 100).toFixed(1)}%
              </div>
              <span className="text-[10px] text-slate-500">
                {evaluation.total_samples} samples evaluated
              </span>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl shadow-sm">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Macro Precision</span>
              <div className="text-2xl font-bold text-white mt-1">
                {(evaluation.precision_macro * 100).toFixed(1)}%
              </div>
              <span className="text-[10px] text-slate-500">Unweighted class average</span>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl shadow-sm">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Macro Recall</span>
              <div className="text-2xl font-bold text-white mt-1">
                {(evaluation.recall_macro * 100).toFixed(1)}%
              </div>
              <span className="text-[10px] text-slate-500">True positive detection rate</span>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl shadow-sm">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Macro F1 Score</span>
              <div className="text-2xl font-bold text-indigo-400 mt-1">
                {(evaluation.f1_macro * 100).toFixed(1)}%
              </div>
              <span className="text-[10px] text-slate-500">Harmonic mean balance</span>
            </div>
          </div>

          {/* Section: Confusion Matrix & Per-Class Metrics */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Confusion Matrix */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-indigo-400" />
                  <h2 className="text-sm font-semibold text-white">Confusion Matrix</h2>
                </div>
                <span className="text-[11px] text-slate-400">Rows: Actual • Cols: Predicted</span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-center border-collapse text-xs">
                  <thead>
                    <tr>
                      <th className="p-2 text-slate-500 text-left font-normal text-[11px]">Actual \ Pred</th>
                      {evaluation.confusion_matrix.labels.map((lbl, idx) => (
                        <th key={idx} className="p-2 font-semibold text-slate-300 font-mono text-[11px]">
                          {lbl}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {evaluation.confusion_matrix.labels.map((actualLabel, rowIdx) => (
                      <tr key={rowIdx}>
                        <td className="p-2 text-left font-semibold text-slate-300 font-mono text-[11px]">
                          {actualLabel}
                        </td>
                        {evaluation.confusion_matrix.matrix[rowIdx].map((val, colIdx) => {
                          const isDiagonal = rowIdx === colIdx;
                          return (
                            <td
                              key={colIdx}
                              className={`p-2.5 font-mono text-xs font-semibold rounded-lg ${
                                isDiagonal
                                  ? val > 0
                                    ? 'bg-emerald-600/30 text-emerald-300 border border-emerald-500/30'
                                    : 'bg-slate-950 text-slate-500'
                                  : val > 0
                                  ? 'bg-rose-600/30 text-rose-300 border border-rose-500/30'
                                  : 'bg-slate-950/60 text-slate-600'
                              }`}
                            >
                              {val}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Per-Class Metrics Breakdown */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <LineChart className="w-4 h-4 text-indigo-400" />
                  <h2 className="text-sm font-semibold text-white">Class-Specific Performance</h2>
                </div>
                <span className="text-[11px] text-slate-400">
                  {evaluation.per_class_metrics.length} Classes
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 font-medium">
                      <th className="py-2 px-3">Class</th>
                      <th className="py-2 px-3">Precision</th>
                      <th className="py-2 px-3">Recall</th>
                      <th className="py-2 px-3">F1 Score</th>
                      <th className="py-2 px-3 text-right">Support</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                    {evaluation.per_class_metrics.map((pcm) => (
                      <tr key={pcm.class_name} className="hover:bg-slate-800/30">
                        <td className="py-2.5 px-3 font-semibold text-white">{pcm.class_name}</td>
                        <td className="py-2.5 px-3 text-slate-300">{(pcm.precision * 100).toFixed(1)}%</td>
                        <td className="py-2.5 px-3 text-slate-300">{(pcm.recall * 100).toFixed(1)}%</td>
                        <td className="py-2.5 px-3 text-indigo-400 font-semibold">
                          {(pcm.f1_score * 100).toFixed(1)}%
                        </td>
                        <td className="py-2.5 px-3 text-right text-slate-400">{pcm.support}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Section: Misclassified Image Gallery */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <FileQuestion className="w-4 h-4 text-rose-400" />
                <h2 className="text-sm font-semibold text-white">
                  Misclassified Samples ({evaluation.misclassified_samples.length})
                </h2>
              </div>
              <span className="text-[11px] text-slate-500">
                Ground-truth vs Predicted discrepancies
              </span>
            </div>

            {evaluation.misclassified_samples.length === 0 ? (
              <div className="py-8 text-center text-emerald-400 text-xs flex items-center justify-center gap-2">
                <CheckCircle2 className="w-4 h-4" />
                <span>Zero misclassifications detected! Model achieved 100% accuracy on evaluated split.</span>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                {evaluation.misclassified_samples.map((item, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-slate-950 rounded-lg border border-slate-800 flex flex-col justify-between text-xs space-y-2"
                  >
                    <div className="font-mono text-[11px] text-slate-300 truncate" title={item.relative_path}>
                      {item.relative_path}
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
                      <div>
                        <span className="text-[10px] text-slate-500 block">Actual</span>
                        <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-semibold text-[11px]">
                          {item.ground_truth}
                        </span>
                      </div>

                      <ArrowRight className="w-3.5 h-3.5 text-slate-600" />

                      <div className="text-right">
                        <span className="text-[10px] text-slate-500 block">Predicted</span>
                        <span className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 font-semibold text-[11px]">
                          {item.predicted} ({(item.confidence * 100).toFixed(0)}%)
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

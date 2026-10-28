import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Boxes,
  RefreshCw,
  Download,
  Trash2,
  FileCheck,
  CheckCircle2,
  ExternalLink,
  Layers,
  Cpu,
  Info,
} from 'lucide-react';
import { api } from '../services/api';
import { ModelArtifact, Project } from '../types';

export const ModelRegistryPage: React.FC = () => {
  const navigate = useNavigate();
  const [artifacts, setArtifacts] = useState<ModelArtifact[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const [modelsData, projData] = await Promise.all([
        api.getRegisteredModels(selectedProjectId || undefined),
        api.getProjects(),
      ]);
      setArtifacts(modelsData);
      setProjects(projData.items);
    } catch (err) {
      console.error('Failed to load model registry:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedProjectId]);

  const handleDelete = async (id: string) => {
    if (!window.confirm('Delete this registered model artifact record?')) return;
    try {
      await api.deleteRegisteredModel(id);
      loadData();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950 overflow-y-auto select-none">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/60 backdrop-blur px-8 py-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
              Deployment Ready
            </span>
            <h1 className="text-xl font-bold text-white tracking-tight">Model Registry & Export Hub</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Catalog of trained, validated, and exported ONNX model packages with verified inference benchmarks.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedProjectId}
            onChange={(e) => setSelectedProjectId(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
          >
            <option value="">All Projects</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>

          <button
            onClick={loadData}
            className="p-1.5 rounded-lg bg-slate-900 border border-slate-700 text-slate-400 hover:text-white transition"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="p-8 space-y-6 max-w-7xl">
        {loading ? (
          <div className="p-16 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
            <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
            Loading model registry...
          </div>
        ) : artifacts.length === 0 ? (
          <div className="p-16 text-center text-slate-500 text-xs bg-slate-900 border border-slate-800 rounded-xl space-y-3">
            <Boxes className="w-10 h-10 mx-auto text-slate-700" />
            <h3 className="text-sm font-semibold text-slate-300">No Exported Models In Registry</h3>
            <p className="max-w-md mx-auto text-slate-400">
              Once you complete a model training run in the Training Engine, export it to ONNX to register it here for deployment.
            </p>
            <button
              onClick={() => navigate('/training')}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow-md transition"
            >
              Go to Training Engine
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {artifacts.map((art) => (
              <div
                key={art.id}
                className="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-xl p-5 shadow-sm flex flex-col justify-between transition space-y-4"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold font-mono">
                      {art.export_format} v{art.version}
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">
                      {(art.file_size_bytes / (1024 * 1024)).toFixed(2)} MB
                    </span>
                  </div>

                  <h3 className="text-sm font-bold text-white truncate" title={art.name}>
                    {art.name}
                  </h3>
                  <p className="text-xs text-indigo-400 font-mono mt-0.5">
                    {art.model_architecture || 'resnet18'} • {art.task_type}
                  </p>

                  <div className="mt-3 p-2.5 bg-slate-950 rounded-lg border border-slate-800/80 space-y-1.5 text-[11px]">
                    <div className="flex items-center justify-between text-slate-400">
                      <span>Framework:</span>
                      <span className="text-white font-medium">{art.framework}</span>
                    </div>
                    <div className="flex items-center justify-between text-slate-400">
                      <span>Checksum (SHA-256):</span>
                      <span className="text-slate-300 font-mono text-[10px] truncate max-w-[140px]" title={art.checksum_sha256 || ''}>
                        {art.checksum_sha256 ? `${art.checksum_sha256.slice(0, 12)}...` : '—'}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-500 truncate pt-1 border-t border-slate-800/60" title={art.artifact_path}>
                      {art.artifact_path}
                    </div>
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
                  <span className="text-[10px] text-slate-500">
                    {new Date(art.created_at).toLocaleDateString()}
                  </span>

                  <div className="flex items-center gap-2">
                    {art.training_job_id && (
                      <button
                        onClick={() => navigate(`/evaluation?job=${art.training_job_id}`)}
                        className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-[11px] transition"
                        title="View Evaluation"
                      >
                        Eval
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(art.id)}
                      className="p-1.5 text-slate-500 hover:text-rose-400 rounded hover:bg-rose-500/10 transition"
                      title="Delete from registry"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

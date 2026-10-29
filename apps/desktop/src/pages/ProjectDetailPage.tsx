import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  FolderOpen,
  Calendar,
  Database,
  Plus,
  Trash2,
  RefreshCw,
  ExternalLink,
  AlertCircle,
  X,
  PenTool,
} from 'lucide-react';
import { api } from '../services/api';
import { Project, Dataset, DatasetCreate, DatasetFormat } from '../types';

export const ProjectDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [project, setProject] = useState<Project | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Import Dataset Modal
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [importForm, setImportForm] = useState<DatasetCreate>({
    name: '',
    description: '',
    root_path: '',
    format: 'folder_images',
    scan_immediately: true,
  });
  const [importSubmitting, setImportSubmitting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);

  // Scanning dataset progress state
  const [scanningDatasetId, setScanningDatasetId] = useState<string | null>(null);

  const loadData = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const proj = await api.getProject(id);
      setProject(proj);
      const ds = await api.getProjectDatasets(id);
      setDatasets(ds.items);
    } catch (err: any) {
      setError(err.message || 'Failed to load project details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  const handleSelectDirectory = async () => {
    if (window.electronAPI?.selectDirectory) {
      try {
        const selected = await window.electronAPI.selectDirectory();
        if (selected) {
          setImportForm((prev) => ({
            ...prev,
            root_path: selected,
            name: prev.name || selected.split(/[\\/]/).pop() || '',
          }));
        }
      } catch (err) {
        console.error('Failed to select directory via Electron dialog:', err);
      }
    }
  };

  const handleImportSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !importForm.name.trim() || !importForm.root_path.trim()) {
      setImportError('Dataset name and source directory are required.');
      return;
    }
    setImportSubmitting(true);
    setImportError(null);
    try {
      await api.createDataset(id, {
        name: importForm.name.trim(),
        description: importForm.description?.trim() || undefined,
        root_path: importForm.root_path.trim(),
        format: importForm.format,
        scan_immediately: importForm.scan_immediately,
      });
      setIsImportOpen(false);
      setImportForm({
        name: '',
        description: '',
        root_path: '',
        format: 'folder_images',
        scan_immediately: true,
      });
      await loadData();
    } catch (err: any) {
      setImportError(err.message || 'Failed to import dataset');
    } finally {
      setImportSubmitting(false);
    }
  };

  const handleScanDataset = async (datasetId: string) => {
    setScanningDatasetId(datasetId);
    try {
      const res = await api.scanDataset(datasetId);
      alert(res.message);
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Error scanning dataset');
    } finally {
      setScanningDatasetId(null);
    }
  };

  const handleDeleteDataset = async (datasetId: string, datasetName: string) => {
    if (!window.confirm(`Delete dataset "${datasetName}"? Metadata will be removed; files on disk are preserved.`)) {
      return;
    }
    try {
      await api.deleteDataset(datasetId);
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to delete dataset');
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center text-slate-400 text-sm">
        <span>Loading project details...</span>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="max-w-4xl mx-auto p-6 rounded-xl bg-slate-900 border border-slate-800 text-center space-y-4">
        <AlertCircle className="w-8 h-8 text-rose-400 mx-auto" />
        <h3 className="text-base font-bold text-white">Project Not Found</h3>
        <p className="text-xs text-slate-400">{error || 'Unable to locate the requested project.'}</p>
        <button
          onClick={() => navigate('/projects')}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold"
        >
          Back to Projects
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Back button and title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/projects')}
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-white">{project.name}</h1>
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-indigo-950 text-indigo-400 border border-indigo-800/80">
                {project.task_type}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              {project.description || 'No description provided.'}
            </p>
          </div>
        </div>

        <button
          onClick={() => {
            const firstDs = datasets.length > 0 ? `&dataset=${datasets[0].id}` : '';
            navigate(`/annotation?project=${project.id}${firstDs}`);
          }}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg shadow-emerald-600/20 transition-all self-start sm:self-auto"
        >
          <PenTool className="w-4 h-4" />
          <span>Open Annotation Studio</span>
        </button>
      </div>

      {/* Overview Metadata Card */}
      <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
        <div className="space-y-1">
          <span className="text-slate-400">Root Storage Path</span>
          <div className="flex items-center gap-2 font-mono text-slate-300 truncate" title={project.root_path}>
            <FolderOpen className="w-4 h-4 text-slate-400 flex-shrink-0" />
            <span className="truncate">{project.root_path}</span>
          </div>
        </div>

        <div className="space-y-1">
          <span className="text-slate-400">Created / Updated</span>
          <div className="flex items-center gap-2 font-mono text-slate-300">
            <Calendar className="w-4 h-4 text-slate-400" />
            <span>
              {new Date(project.created_at).toLocaleDateString()} (Updated {new Date(project.updated_at).toLocaleDateString()})
            </span>
          </div>
        </div>

        <div className="space-y-1">
          <span className="text-slate-400">Datasets Linked</span>
          <div className="flex items-center gap-2 font-mono text-slate-300">
            <Database className="w-4 h-4 text-indigo-400" />
            <span>{datasets.length} Active Dataset{datasets.length === 1 ? '' : 's'}</span>
          </div>
        </div>
      </div>

      {/* Datasets Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-white">Project Datasets</h2>
            <p className="text-xs text-slate-400">Manage image directories associated with this project</p>
          </div>
          <button
            onClick={() => setIsImportOpen(true)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/20"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Import Dataset</span>
          </button>
        </div>

        {datasets.length === 0 ? (
          <div className="py-16 text-center p-8 rounded-xl bg-slate-900 border border-slate-800">
            <Database className="w-10 h-10 text-slate-400 mx-auto mb-3" />
            <h3 className="text-sm font-semibold text-slate-200">No datasets imported</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1">
              Import or link a local folder containing images (JPEG, PNG, BMP, TIFF) to this project.
            </p>
            <button
              onClick={() => setIsImportOpen(true)}
              className="mt-4 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold"
            >
              Import Dataset Now
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {datasets.map((dataset) => (
              <div
                key={dataset.id}
                className="p-5 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between">
                    <div>
                      <h4
                        onClick={() => navigate(`/datasets/${dataset.id}`)}
                        className="text-base font-bold text-white hover:text-indigo-400 cursor-pointer transition-colors"
                      >
                        {dataset.name}
                      </h4>
                      <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">
                        {dataset.description || 'No description.'}
                      </p>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleScanDataset(dataset.id)}
                        disabled={scanningDatasetId === dataset.id}
                        title="Re-scan image folder"
                        className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-400 hover:bg-slate-800 disabled:opacity-50"
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${scanningDatasetId === dataset.id ? 'animate-spin' : ''}`} />
                      </button>
                      <button
                        onClick={() => handleDeleteDataset(dataset.id, dataset.name)}
                        title="Delete dataset"
                        className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-950/40"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  <div className="mt-3 p-3 rounded-lg bg-slate-950 border border-slate-800/80 font-mono text-[11px] text-slate-400 truncate" title={dataset.root_path}>
                    <span className="text-slate-400 select-none">Source: </span>
                    {dataset.root_path}
                  </div>

                  {/* Stat badges */}
                  <div className="mt-4 grid grid-cols-3 gap-2 text-center">
                    <div className="p-2 rounded-lg bg-slate-800/50 border border-slate-800">
                      <span className="block text-sm font-bold text-emerald-400">{dataset.valid_image_count}</span>
                      <span className="text-[10px] text-slate-400">Valid Images</span>
                    </div>
                    <div className="p-2 rounded-lg bg-slate-800/50 border border-slate-800">
                      <span className="block text-sm font-bold text-rose-400">{dataset.corrupted_image_count}</span>
                      <span className="text-[10px] text-slate-400">Corrupted</span>
                    </div>
                    <div className="p-2 rounded-lg bg-slate-800/50 border border-slate-800">
                      <span className="block text-sm font-bold text-amber-400">{dataset.unsupported_file_count}</span>
                      <span className="text-[10px] text-slate-400">Unsupported</span>
                    </div>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-xs">
                  <span className="text-[11px] text-slate-400 font-mono">
                    Scanned: {dataset.last_scanned_at ? new Date(dataset.last_scanned_at).toLocaleTimeString() : 'Never'}
                  </span>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => navigate(`/annotation?project=${project.id}&dataset=${dataset.id}`)}
                      className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400 hover:text-emerald-300"
                    >
                      <PenTool className="w-3.5 h-3.5" />
                      <span>Annotate</span>
                    </button>
                    <button
                      onClick={() => navigate(`/datasets/${dataset.id}`)}
                      className="flex items-center gap-1.5 text-xs font-semibold text-indigo-400 hover:text-indigo-300"
                    >
                      <span>View Images</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* IMPORT DATASET MODAL */}
      {isImportOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl p-6 select-none animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h3 className="text-base font-bold text-white">Import Dataset to {project.name}</h3>
              <button
                onClick={() => setIsImportOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {importError && (
              <div className="mt-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
                <span>{importError}</span>
              </div>
            )}

            <form onSubmit={handleImportSubmit} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Dataset Name <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={importForm.name}
                  onChange={(e) => setImportForm({ ...importForm, name: e.target.value })}
                  placeholder="e.g. Batch 01 Inspection"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Source Image Directory <span className="text-rose-400">*</span>
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    required
                    value={importForm.root_path}
                    onChange={(e) => setImportForm({ ...importForm, root_path: e.target.value })}
                    placeholder="Absolute directory path containing images"
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white font-mono placeholder-slate-400 focus:outline-none focus:border-indigo-500"
                  />
                  <button
                    type="button"
                    onClick={handleSelectDirectory}
                    className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-medium"
                  >
                    Browse...
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Format</label>
                <select
                  value={importForm.format}
                  onChange={(e) => setImportForm({ ...importForm, format: e.target.value as DatasetFormat })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="folder_images">Folder of Images (Recursive Scan)</option>
                  <option value="coco">COCO Format</option>
                  <option value="yolo">YOLO Format</option>
                  <option value="pascal_voc">Pascal VOC Format</option>
                </select>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="scanImmediately"
                  checked={importForm.scan_immediately}
                  onChange={(e) => setImportForm({ ...importForm, scan_immediately: e.target.checked })}
                  className="rounded border-slate-800 text-indigo-600 focus:ring-0"
                />
                <label htmlFor="scanImmediately" className="text-xs text-slate-300 cursor-pointer">
                  Scan and index images immediately upon import
                </label>
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsImportOpen(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={importSubmitting}
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold disabled:opacity-50"
                >
                  {importSubmitting ? 'Scanning & Importing...' : 'Import Dataset'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

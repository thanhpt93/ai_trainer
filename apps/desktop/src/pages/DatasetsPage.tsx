import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Database,
  Search,
  Plus,
  RefreshCw,
  FolderOpen,
  Calendar,
  AlertCircle,
  ExternalLink,
  Trash2,
  FolderKanban,
  CheckCircle2,
  XCircle,
  X,
} from 'lucide-react';
import { api } from '../services/api';
import { Dataset, Project, DatasetCreate, DatasetFormat, PathValidationResult } from '../types';

export const DatasetsPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  // Import Modal
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [importForm, setImportForm] = useState<DatasetCreate>({
    name: '',
    description: '',
    root_path: '',
    format: 'folder_images',
    scan_immediately: true,
  });
  const [pathInspection, setPathInspection] = useState<PathValidationResult | null>(null);
  const [inspectingPath, setInspectingPath] = useState(false);
  const [importSubmitting, setImportSubmitting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);

  // Re-scanning state
  const [scanningId, setScanningId] = useState<string | null>(null);

  useEffect(() => {
    if (searchParams.get('import') === 'true') {
      setIsImportOpen(true);
      setSearchParams({});
    }
  }, [searchParams]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [dsRes, projRes] = await Promise.all([
        api.getAllDatasets(),
        api.getProjects(),
      ]);
      setDatasets(dsRes.items);
      setProjects(projRes.items);
      if (projRes.items.length > 0 && !selectedProjectId) {
        setSelectedProjectId(projRes.items[0].id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch datasets');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

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
          inspectPath(selected);
        }
      } catch (err) {
        console.error('Failed to select directory via Electron dialog:', err);
      }
    }
  };

  const inspectPath = async (dirPath: string) => {
    if (!dirPath || dirPath.length < 3) {
      setPathInspection(null);
      return;
    }
    setInspectingPath(true);
    try {
      const res = await api.validatePath(dirPath);
      setPathInspection(res);
    } catch {
      setPathInspection(null);
    } finally {
      setInspectingPath(false);
    }
  };

  const handleImportSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProjectId) {
      setImportError('Please select or create a project first.');
      return;
    }
    if (!importForm.name.trim() || !importForm.root_path.trim()) {
      setImportError('Dataset name and source directory path are required.');
      return;
    }
    setImportSubmitting(true);
    setImportError(null);
    try {
      await api.createDataset(selectedProjectId, {
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
      setPathInspection(null);
      await loadData();
    } catch (err: any) {
      setImportError(err.message || 'Failed to import dataset');
    } finally {
      setImportSubmitting(false);
    }
  };

  const handleScanDataset = async (datasetId: string) => {
    setScanningId(datasetId);
    try {
      const res = await api.scanDataset(datasetId);
      alert(res.message);
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Error scanning dataset');
    } finally {
      setScanningId(null);
    }
  };

  const handleDeleteDataset = async (datasetId: string, name: string) => {
    if (!window.confirm(`Delete dataset "${name}"? Files on disk will remain untouched.`)) return;
    try {
      await api.deleteDataset(datasetId);
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to delete dataset');
    }
  };

  const filteredDatasets = datasets.filter(
    (d) =>
      d.name.toLowerCase().includes(search.toLowerCase()) ||
      d.root_path.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Top Header and Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white">Datasets Management</h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Indexed image folders, source paths, formats, and dataset health across all projects.
          </p>
        </div>
        <button
          onClick={() => setIsImportOpen(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>Import Dataset</span>
        </button>
      </div>

      {/* Search Bar */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search datasets by name or storage path..."
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-xs text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400" />
            <span>{error}</span>
          </div>
          <button onClick={loadData} className="underline hover:text-rose-200">
            Retry
          </button>
        </div>
      )}

      {/* Dataset Cards List */}
      {loading ? (
        <div className="py-20 text-center text-slate-400 text-sm">
          <span>Loading datasets...</span>
        </div>
      ) : filteredDatasets.length === 0 ? (
        <div className="py-20 flex flex-col items-center justify-center text-center p-8 rounded-xl bg-slate-900 border border-slate-800">
          <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center text-slate-400 mb-3">
            <Database className="w-6 h-6" />
          </div>
          <h3 className="text-base font-semibold text-slate-200">No datasets found</h3>
          <p className="text-xs text-slate-400 max-w-sm mt-1">
            {search
              ? 'No datasets match your search term.'
              : 'Import your first image folder to begin indexing vision datasets.'}
          </p>
          {!search && (
            <button
              onClick={() => setIsImportOpen(true)}
              className="mt-4 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold"
            >
              Import Dataset
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredDatasets.map((dataset) => {
            const parentProject = projects.find((p) => p.id === dataset.project_id);
            return (
              <div
                key={dataset.id}
                className="p-5 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between">
                    <div>
                      {parentProject && (
                        <span
                          onClick={() => navigate(`/projects/${parentProject.id}`)}
                          className="text-[10px] font-semibold text-indigo-400 hover:underline cursor-pointer flex items-center gap-1 mb-1"
                        >
                          <FolderKanban className="w-3 h-3" />
                          <span>{parentProject.name}</span>
                        </span>
                      )}
                      <h3
                        onClick={() => navigate(`/datasets/${dataset.id}`)}
                        className="text-base font-bold text-white hover:text-indigo-400 cursor-pointer transition-colors"
                      >
                        {dataset.name}
                      </h3>
                      <p className="text-xs text-slate-400 mt-1 line-clamp-2 min-h-[32px]">
                        {dataset.description || 'No description provided.'}
                      </p>
                    </div>

                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleScanDataset(dataset.id)}
                        disabled={scanningId === dataset.id}
                        title="Re-scan directory"
                        className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-400 hover:bg-slate-800"
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${scanningId === dataset.id ? 'animate-spin' : ''}`} />
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

                  <div className="mt-3 p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 font-mono text-[11px] text-slate-400 truncate" title={dataset.root_path}>
                    <span className="text-slate-400">Path: </span>
                    {dataset.root_path}
                  </div>

                  {/* Summary counts */}
                  <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
                    <div className="p-2 rounded bg-slate-800/40 border border-slate-800">
                      <span className="block font-bold text-emerald-400 text-sm">{dataset.valid_image_count}</span>
                      <span className="text-[10px] text-slate-400">Valid</span>
                    </div>
                    <div className="p-2 rounded bg-slate-800/40 border border-slate-800">
                      <span className="block font-bold text-rose-400 text-sm">{dataset.corrupted_image_count}</span>
                      <span className="text-[10px] text-slate-400">Corrupted</span>
                    </div>
                    <div className="p-2 rounded bg-slate-800/40 border border-slate-800">
                      <span className="block font-bold text-amber-400 text-sm">{dataset.unsupported_file_count}</span>
                      <span className="text-[10px] text-slate-400">Unsupported</span>
                    </div>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-xs">
                  <span className="text-[11px] text-slate-400 font-mono">
                    {dataset.last_scanned_at ? new Date(dataset.last_scanned_at).toLocaleDateString() : 'Never scanned'}
                  </span>
                  <button
                    onClick={() => navigate(`/datasets/${dataset.id}`)}
                    className="flex items-center gap-1.5 text-xs font-semibold text-indigo-400 hover:text-indigo-300"
                  >
                    <span>View Images</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* GLOBAL IMPORT DATASET MODAL */}
      {isImportOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl p-6 select-none animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h3 className="text-base font-bold text-white">Import Image Dataset</h3>
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
                  Target Project <span className="text-rose-400">*</span>
                </label>
                {projects.length === 0 ? (
                  <div className="p-3 bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs rounded-lg flex items-center justify-between">
                    <span>No projects available. Please create a project first.</span>
                    <button
                      type="button"
                      onClick={() => navigate('/projects?create=true')}
                      className="underline font-bold"
                    >
                      New Project
                    </button>
                  </div>
                ) : (
                  <select
                    value={selectedProjectId}
                    onChange={(e) => setSelectedProjectId(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    {projects.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} ({p.task_type})
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Dataset Name <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={importForm.name}
                  onChange={(e) => setImportForm({ ...importForm, name: e.target.value })}
                  placeholder="e.g. Surface Inspection Batch 1"
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
                    onChange={(e) => {
                      const val = e.target.value;
                      setImportForm({ ...importForm, root_path: val });
                      inspectPath(val);
                    }}
                    placeholder="e.g. C:/Datasets/PCB_Images"
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

                {/* Directory Inspection Live Feedback */}
                {pathInspection && (
                  <div className="mt-2 p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-[11px] space-y-1">
                    {pathInspection.is_valid ? (
                      <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Valid directory: ~{pathInspection.estimated_image_count} top-level images found</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1.5 text-rose-400 font-medium">
                        <XCircle className="w-3.5 h-3.5" />
                        <span>{pathInspection.error_message || 'Directory invalid or unreadable'}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Format</label>
                <select
                  value={importForm.format}
                  onChange={(e) => setImportForm({ ...importForm, format: e.target.value as DatasetFormat })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="folder_images">Folder of Images (Recursive Scan)</option>
                  <option value="coco">COCO Format (Annotations in Phase 2)</option>
                  <option value="yolo">YOLO Format (Annotations in Phase 2)</option>
                  <option value="pascal_voc">Pascal VOC Format (Annotations in Phase 2)</option>
                </select>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="scanImmediatelyGlobal"
                  checked={importForm.scan_immediately}
                  onChange={(e) => setImportForm({ ...importForm, scan_immediately: e.target.checked })}
                  className="rounded border-slate-800 text-indigo-600 focus:ring-0"
                />
                <label htmlFor="scanImmediatelyGlobal" className="text-xs text-slate-300 cursor-pointer">
                  Scan and index images recursively immediately
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
                  disabled={importSubmitting || projects.length === 0}
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

import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  FolderKanban,
  Search,
  Plus,
  Filter,
  Trash2,
  Edit2,
  ExternalLink,
  FolderOpen,
  Calendar,
  AlertCircle,
  Database,
  X,
} from 'lucide-react';
import { api } from '../services/api';
import { Project, ProjectCreate, TASK_TYPES, TaskType } from '../types';

export const ProjectsPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState('');
  const [selectedTaskType, setSelectedTaskType] = useState<string>('');

  // Create Project Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState<ProjectCreate>({
    name: '',
    description: '',
    task_type: 'Image Classification',
    root_path: '',
  });
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Rename Modal State
  const [renameProject, setRenameProject] = useState<Project | null>(null);
  const [renameName, setRenameName] = useState('');
  const [renameSubmitting, setRenameSubmitting] = useState(false);

  // Delete Modal State
  const [deleteProject, setDeleteProject] = useState<Project | null>(null);
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);

  // Open modal if ?create=true in URL
  useEffect(() => {
    if (searchParams.get('create') === 'true') {
      setIsCreateOpen(true);
      setSearchParams({});
    }
  }, [searchParams]);

  const loadProjects = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getProjects(search || undefined, selectedTaskType || undefined);
      setProjects(data.items);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch projects');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, [search, selectedTaskType]);

  const handleSelectDirectory = async () => {
    if (window.electronAPI?.selectDirectory) {
      try {
        const selected = await window.electronAPI.selectDirectory();
        if (selected) {
          setCreateForm((prev) => ({ ...prev, root_path: selected }));
        }
      } catch (err) {
        console.error('Failed to select directory via Electron dialog:', err);
      }
    }
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createForm.name.trim()) {
      setCreateError('Project name is required.');
      return;
    }
    setCreateSubmitting(true);
    setCreateError(null);
    try {
      const newProj = await api.createProject({
        name: createForm.name.trim(),
        description: createForm.description?.trim() || undefined,
        task_type: createForm.task_type,
        root_path: createForm.root_path?.trim() || undefined,
      });
      setIsCreateOpen(false);
      setCreateForm({
        name: '',
        description: '',
        task_type: 'Image Classification',
        root_path: '',
      });
      navigate(`/projects/${newProj.id}`);
    } catch (err: any) {
      setCreateError(err.message || 'Error creating project');
    } finally {
      setCreateSubmitting(false);
    }
  };

  const handleRenameSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!renameProject || !renameName.trim()) return;
    setRenameSubmitting(true);
    try {
      await api.updateProject(renameProject.id, { name: renameName.trim() });
      setRenameProject(null);
      await loadProjects();
    } catch (err: any) {
      alert(err.message || 'Failed to rename project');
    } finally {
      setRenameSubmitting(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deleteProject) return;
    setDeleteSubmitting(true);
    try {
      await api.deleteProject(deleteProject.id);
      setDeleteProject(null);
      await loadProjects();
    } catch (err: any) {
      alert(err.message || 'Failed to delete project');
    } finally {
      setDeleteSubmitting(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header and Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white">Vision Projects</h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Organize and manage computer vision datasets and model architectures.
          </p>
        </div>
        <button
          onClick={() => setIsCreateOpen(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>Create Project</span>
        </button>
      </div>

      {/* Search and Filters Bar */}
      <div className="flex flex-col sm:flex-row items-center gap-3 p-4 rounded-xl bg-slate-900 border border-slate-800">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search projects by name or description..."
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-xs text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500 transition-colors"
          />
        </div>
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Filter className="w-4 h-4 text-slate-400 flex-shrink-0" />
          <select
            value={selectedTaskType}
            onChange={(e) => setSelectedTaskType(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="">All Task Types</option>
            {TASK_TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400" />
            <span>{error}</span>
          </div>
          <button onClick={loadProjects} className="underline hover:text-rose-200">
            Retry
          </button>
        </div>
      )}

      {/* Projects List / Grid */}
      {loading ? (
        <div className="py-20 text-center text-slate-400 text-sm">
          <span>Loading projects...</span>
        </div>
      ) : projects.length === 0 ? (
        <div className="py-20 flex flex-col items-center justify-center text-center p-8 rounded-xl bg-slate-900 border border-slate-800">
          <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center text-slate-400 mb-3">
            <FolderKanban className="w-6 h-6" />
          </div>
          <h3 className="text-base font-semibold text-slate-200">No projects found</h3>
          <p className="text-xs text-slate-400 max-w-sm mt-1">
            {search || selectedTaskType
              ? 'No projects match your search query or filter criteria.'
              : 'Get started by creating your first computer vision project.'}
          </p>
          {!search && !selectedTaskType && (
            <button
              onClick={() => setIsCreateOpen(true)}
              className="mt-4 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold"
            >
              Create Project
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {projects.map((project) => (
            <div
              key={project.id}
              className="p-5 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-indigo-950 text-indigo-400 border border-indigo-800/80">
                      {project.task_type}
                    </span>
                    <h3
                      onClick={() => navigate(`/projects/${project.id}`)}
                      className="text-base font-bold text-white mt-2 group-hover:text-indigo-400 cursor-pointer transition-colors"
                    >
                      {project.name}
                    </h3>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => {
                        setRenameProject(project);
                        setRenameName(project.name);
                      }}
                      title="Rename Project"
                      className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => setDeleteProject(project)}
                      title="Delete Project"
                      className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-950/40"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                <p className="text-xs text-slate-400 mt-2 line-clamp-2 min-h-[32px]">
                  {project.description || 'No description provided.'}
                </p>

                <div className="mt-4 space-y-2 text-[11px] text-slate-400 border-t border-slate-800/80 pt-3">
                  <div className="flex items-center gap-2 truncate" title={project.root_path}>
                    <FolderOpen className="w-3.5 h-3.5 flex-shrink-0 text-slate-400" />
                    <span className="font-mono truncate">{project.root_path}</span>
                  </div>
                  <div className="flex items-center justify-between text-slate-400">
                    <div className="flex items-center gap-1.5">
                      <Database className="w-3.5 h-3.5" />
                      <span>{project.dataset_count || 0} Datasets</span>
                    </div>
                    <div className="flex items-center gap-1 font-mono">
                      <Calendar className="w-3.5 h-3.5" />
                      <span>{new Date(project.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/80">
                <button
                  onClick={() => navigate(`/projects/${project.id}`)}
                  className="w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-slate-800 hover:bg-indigo-600 text-slate-200 hover:text-white text-xs font-semibold transition-colors"
                >
                  <span>Open Project</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* CREATE PROJECT MODAL */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl p-6 select-none animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h3 className="text-base font-bold text-white">Create New Project</h3>
              <button
                onClick={() => setIsCreateOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {createError && (
              <div className="mt-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
                <span>{createError}</span>
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Project Name <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={createForm.name}
                  onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                  placeholder="e.g. PCB Defect Inspection"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Task Type</label>
                <select
                  value={createForm.task_type}
                  onChange={(e) => setCreateForm({ ...createForm, task_type: e.target.value as TaskType })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  {TASK_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Description</label>
                <textarea
                  rows={2}
                  value={createForm.description}
                  onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                  placeholder="Optional brief description of the vision task..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-semibold text-slate-300">
                    Storage Location <span className="text-[11px] text-slate-400 font-normal">(Optional)</span>
                  </label>
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={createForm.root_path}
                    onChange={(e) => setCreateForm({ ...createForm, root_path: e.target.value })}
                    placeholder="Leave blank for default application storage"
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

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createSubmitting}
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold disabled:opacity-50"
                >
                  {createSubmitting ? 'Creating...' : 'Create Project'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* RENAME MODAL */}
      {renameProject && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-2xl">
            <h3 className="text-base font-bold text-white mb-4">Rename Project</h3>
            <form onSubmit={handleRenameSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">New Project Name</label>
                <input
                  type="text"
                  required
                  value={renameName}
                  onChange={(e) => setRenameName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div className="flex items-center justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setRenameProject(null)}
                  className="px-4 py-2 bg-slate-800 text-slate-300 rounded-lg text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={renameSubmitting}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold"
                >
                  {renameSubmitting ? 'Saving...' : 'Save'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* DELETE CONFIRMATION MODAL */}
      {deleteProject && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-2xl">
            <div className="flex items-center gap-3 text-rose-400 mb-3">
              <AlertCircle className="w-6 h-6 flex-shrink-0" />
              <h3 className="text-base font-bold text-white">Delete Project</h3>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Are you sure you want to delete <strong className="text-white">"{deleteProject.name}"</strong>?
              This will remove all indexed dataset metadata from the database. Original raw image files on disk will NOT be touched.
            </p>
            <div className="flex items-center justify-end gap-3 mt-6">
              <button
                type="button"
                onClick={() => setDeleteProject(null)}
                className="px-4 py-2 bg-slate-800 text-slate-300 rounded-lg text-xs"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteConfirm}
                disabled={deleteSubmitting}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold disabled:opacity-50"
              >
                {deleteSubmitting ? 'Deleting...' : 'Delete Project'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

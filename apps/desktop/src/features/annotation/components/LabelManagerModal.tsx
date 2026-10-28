import React, { useState } from 'react';
import { X, Plus, Trash2, Edit2, Tag, AlertCircle, Check } from 'lucide-react';
import { ProjectLabel, LabelCreate } from '../../../types';
import { api } from '../../../services/api';

interface LabelManagerModalProps {
  projectId: string;
  labels: ProjectLabel[];
  onClose: () => void;
  onLabelsUpdated: () => void;
}

const PRESET_COLORS = [
  '#ef4444', // Red
  '#f97316', // Orange
  '#f59e0b', // Amber
  '#10b981', // Emerald
  '#06b6d4', // Cyan
  '#3b82f6', // Blue
  '#6366f1', // Indigo
  '#8b5cf6', // Violet
  '#ec4899', // Pink
  '#14b8a6', // Teal
];

export const LabelManagerModal: React.FC<LabelManagerModalProps> = ({
  projectId,
  labels,
  onClose,
  onLabelsUpdated,
}) => {
  const [newLabelName, setNewLabelName] = useState('');
  const [newLabelColor, setNewLabelColor] = useState('#6366f1');
  const [newLabelDesc, setNewLabelDesc] = useState('');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Edit State
  const [editingLabelId, setEditingLabelId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editColor, setEditColor] = useState('');
  const [savingEdit, setSavingEdit] = useState(false);

  const handleCreateLabel = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newLabelName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      await api.createProjectLabel(projectId, {
        name: newLabelName.trim(),
        color: newLabelColor,
        description: newLabelDesc.trim() || undefined,
      });
      setNewLabelName('');
      setNewLabelDesc('');
      onLabelsUpdated();
    } catch (err: any) {
      setError(err.message || 'Failed to create label');
    } finally {
      setCreating(false);
    }
  };

  const handleStartEdit = (label: ProjectLabel) => {
    setEditingLabelId(label.id);
    setEditName(label.name);
    setEditColor(label.color);
  };

  const handleSaveEdit = async (labelId: string) => {
    if (!editName.trim()) return;
    setSavingEdit(true);
    try {
      await api.updateProjectLabel(labelId, {
        name: editName.trim(),
        color: editColor,
      });
      setEditingLabelId(null);
      onLabelsUpdated();
    } catch (err: any) {
      alert(err.message || 'Failed to update label');
    } finally {
      setSavingEdit(false);
    }
  };

  const handleDeleteLabel = async (label: ProjectLabel) => {
    if (!window.confirm(`Delete label "${label.name}"?`)) return;
    try {
      await api.deleteProjectLabel(label.id);
      onLabelsUpdated();
    } catch (err: any) {
      alert(err.message || 'Cannot delete label');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 select-none">
      <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-600/20 text-indigo-400 flex items-center justify-center">
              <Tag className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Project Labels Management</h3>
              <p className="text-xs text-slate-400">Manage categories, bounding box colors, and descriptions</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Create New Label Bar */}
        <form onSubmit={handleCreateLabel} className="mt-4 p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
          <span className="text-xs font-semibold text-slate-300 block">Add New Class Label</span>
          <div className="flex flex-col sm:flex-row gap-2">
            <input
              type="text"
              required
              value={newLabelName}
              onChange={(e) => setNewLabelName(e.target.value)}
              placeholder="Class name (e.g. Scratch, Defect, Component)"
              className="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
            <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-900 border border-slate-800 rounded-lg">
              <input
                type="color"
                value={newLabelColor}
                onChange={(e) => setNewLabelColor(e.target.value)}
                className="w-5 h-5 rounded cursor-pointer bg-transparent border-0"
              />
              <span className="text-[11px] font-mono text-slate-400">{newLabelColor}</span>
            </div>
            <button
              type="submit"
              disabled={creating || !newLabelName.trim()}
              className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>{creating ? 'Adding...' : 'Add Label'}</span>
            </button>
          </div>

          {/* Quick preset color swatches */}
          <div className="flex items-center gap-1.5 pt-1">
            <span className="text-[10px] text-slate-500 mr-1">Presets:</span>
            {PRESET_COLORS.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setNewLabelColor(c)}
                style={{ backgroundColor: c }}
                className={`w-4 h-4 rounded-full transition-transform ${newLabelColor === c ? 'scale-125 ring-2 ring-white' : 'opacity-80 hover:opacity-100'}`}
              />
            ))}
          </div>
        </form>

        {/* Existing Labels List */}
        <div className="mt-4 flex-1 overflow-y-auto space-y-2 pr-1">
          <span className="text-xs font-semibold text-slate-400 block mb-1">
            Existing Labels ({labels.length})
          </span>

          {labels.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-xs">
              No labels defined for this project yet. Add your first label above.
            </div>
          ) : (
            labels.map((label) => (
              <div
                key={label.id}
                className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between gap-3"
              >
                {editingLabelId === label.id ? (
                  <div className="flex items-center gap-2 flex-1">
                    <input
                      type="color"
                      value={editColor}
                      onChange={(e) => setEditColor(e.target.value)}
                      className="w-5 h-5 rounded cursor-pointer bg-transparent"
                    />
                    <input
                      type="text"
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-white"
                    />
                    <button
                      onClick={() => handleSaveEdit(label.id)}
                      disabled={savingEdit}
                      className="p-1 text-emerald-400 hover:bg-slate-800 rounded"
                    >
                      <Check className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setEditingLabelId(null)}
                      className="p-1 text-slate-400 hover:bg-slate-800 rounded"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center gap-2.5">
                      <span
                        className="w-3.5 h-3.5 rounded-full flex-shrink-0"
                        style={{ backgroundColor: label.color }}
                      />
                      <div>
                        <span className="text-xs font-semibold text-white block">{label.name}</span>
                        {label.description && (
                          <span className="text-[11px] text-slate-500 block">{label.description}</span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                        {label.annotation_count || 0} referenced
                      </span>
                      <button
                        onClick={() => handleStartEdit(label)}
                        className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800"
                        title="Edit label"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDeleteLabel(label)}
                        className="p-1 text-slate-400 hover:text-rose-400 rounded hover:bg-rose-950/40"
                        title="Delete label (protected if referenced)"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="mt-4 pt-3 border-t border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};

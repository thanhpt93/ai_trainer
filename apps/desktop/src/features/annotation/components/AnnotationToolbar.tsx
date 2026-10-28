import React, { useState } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  RotateCcw,
  RotateCw,
  ZoomIn,
  ZoomOut,
  Maximize2,
  MousePointer,
  Square,
  Hand,
  Tag,
  Download,
  HelpCircle,
  CheckCircle2,
  AlertCircle,
  Loader2,
  X,
} from 'lucide-react';
import { Project, Dataset, AnnotationTool } from '../../../types';

interface AnnotationToolbarProps {
  projects: Project[];
  datasets: Dataset[];
  selectedProjectId: string;
  selectedDatasetId: string;
  taskType: string;
  currentIndex: number;
  totalImages: number;
  currentTool: AnnotationTool;
  zoom: number;
  saveStatus: 'saved' | 'saving' | 'dirty' | 'error';
  canUndo: boolean;
  canRedo: boolean;
  onProjectChange: (id: string) => void;
  onDatasetChange: (id: string) => void;
  onPrevImage: () => void;
  onNextImage: () => void;
  onToolChange: (tool: AnnotationTool) => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFitView: () => void;
  onResetZoom: () => void;
  onUndo: () => void;
  onRedo: () => void;
  onSave: () => void;
  onOpenLabelManager: () => void;
  onOpenExportModal: () => void;
}

export const AnnotationToolbar: React.FC<AnnotationToolbarProps> = ({
  projects,
  datasets,
  selectedProjectId,
  selectedDatasetId,
  taskType,
  currentIndex,
  totalImages,
  currentTool,
  zoom,
  saveStatus,
  canUndo,
  canRedo,
  onProjectChange,
  onDatasetChange,
  onPrevImage,
  onNextImage,
  onToolChange,
  onZoomIn,
  onZoomOut,
  onFitView,
  onResetZoom,
  onUndo,
  onRedo,
  onSave,
  onOpenLabelManager,
  onOpenExportModal,
}) => {
  const [showShortcuts, setShowShortcuts] = useState(false);
  const isObjectDetection = taskType.includes('Detection') || taskType.includes('Object');

  return (
    <div className="h-14 bg-slate-900 border-b border-slate-800 px-4 flex items-center justify-between gap-4 select-none flex-shrink-0 z-20">
      {/* Left: Project & Dataset Selectors & Nav */}
      <div className="flex items-center gap-3">
        {/* Project Selector */}
        <select
          value={selectedProjectId}
          onChange={(e) => onProjectChange(e.target.value)}
          className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-medium focus:outline-none focus:border-indigo-500 max-w-[160px] truncate"
          title="Select Project"
        >
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>

        {/* Dataset Selector */}
        <select
          value={selectedDatasetId}
          onChange={(e) => onDatasetChange(e.target.value)}
          className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-medium focus:outline-none focus:border-indigo-500 max-w-[180px] truncate"
          title="Select Dataset"
        >
          {datasets.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>

        <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-indigo-950 text-indigo-400 border border-indigo-800/80 hidden md:inline-block">
          {taskType}
        </span>

        {/* Previous / Next Navigator */}
        <div className="flex items-center gap-1 border-l border-slate-800 pl-3">
          <button
            onClick={onPrevImage}
            disabled={currentIndex <= 0}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40 transition-colors"
            title="Previous image (A)"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-xs font-mono text-slate-300 px-1 min-w-[50px] text-center">
            {totalImages > 0 ? `${currentIndex + 1} / ${totalImages}` : '0 / 0'}
          </span>
          <button
            onClick={onNextImage}
            disabled={currentIndex >= totalImages - 1}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40 transition-colors"
            title="Next image (D)"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Center: Tools & Undo/Redo */}
      <div className="flex items-center gap-2">
        {/* Tool Mode: Select vs Draw Box vs Pan */}
        {isObjectDetection ? (
          <div className="flex items-center bg-slate-950 p-0.5 rounded-lg border border-slate-800">
            <button
              onClick={() => onToolChange('select')}
              className={`p-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 transition-colors ${
                currentTool === 'select'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Select / Move Box tool (V)"
            >
              <MousePointer className="w-3.5 h-3.5" />
              <span className="text-[11px] hidden lg:inline">Select (V)</span>
            </button>
            <button
              onClick={() => onToolChange('draw')}
              className={`p-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 transition-colors ${
                currentTool === 'draw'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Draw Bounding Box (B)"
            >
              <Square className="w-3.5 h-3.5" />
              <span className="text-[11px] hidden lg:inline">Draw Box (B)</span>
            </button>
            <button
              onClick={() => onToolChange('pan')}
              className={`p-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 transition-colors ${
                currentTool === 'pan'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Pan / Move Canvas (H or Space+Drag)"
            >
              <Hand className="w-3.5 h-3.5" />
              <span className="text-[11px] hidden lg:inline">Pan (H)</span>
            </button>
          </div>
        ) : (
          <div className="flex items-center bg-slate-950 p-0.5 rounded-lg border border-slate-800">
            <button
              onClick={() => onToolChange('pan')}
              className="p-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 bg-indigo-600 text-white shadow-sm"
              title="Pan / Move Image (Left click and drag anywhere)"
            >
              <Hand className="w-3.5 h-3.5" />
              <span className="text-[11px]">Pan Mode (Drag to Move)</span>
            </button>
          </div>
        )}

        {/* Undo / Redo */}
        <div className="flex items-center gap-1 border-l border-slate-800 pl-2">
          <button
            onClick={onUndo}
            disabled={!canUndo}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 disabled:opacity-30 transition-colors"
            title="Undo (Ctrl+Z)"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onRedo}
            disabled={!canRedo}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 disabled:opacity-30 transition-colors"
            title="Redo (Ctrl+Y)"
          >
            <RotateCw className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Zoom Controls */}
        <div className="flex items-center gap-1 border-l border-slate-800 pl-2">
          <button
            onClick={onZoomOut}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onResetZoom}
            className="text-[11px] font-mono text-slate-300 hover:text-indigo-400 px-1.5 py-1 rounded bg-slate-950 border border-slate-800"
            title="Reset to 100%"
          >
            {Math.round(zoom * 100)}%
          </button>
          <button
            onClick={onZoomIn}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onFitView}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            title="Fit to Screen"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Right: Save Status, Label Manager, Export, Help */}
      <div className="flex items-center gap-2.5">
        {/* Save Status & Action */}
        <button
          onClick={onSave}
          disabled={saveStatus === 'saving'}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
            saveStatus === 'dirty'
              ? 'bg-amber-600 hover:bg-amber-500 text-white shadow-lg shadow-amber-600/20'
              : saveStatus === 'saving'
              ? 'bg-slate-800 text-slate-300 cursor-wait'
              : saveStatus === 'error'
              ? 'bg-rose-600 hover:bg-rose-500 text-white'
              : 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-600/30'
          }`}
          title="Save annotations (Ctrl+S)"
        >
          {saveStatus === 'saving' ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : saveStatus === 'dirty' ? (
            <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
          ) : saveStatus === 'error' ? (
            <AlertCircle className="w-3.5 h-3.5 text-white" />
          ) : (
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          )}
          <span>
            {saveStatus === 'saving'
              ? 'Saving...'
              : saveStatus === 'dirty'
              ? 'Save (Ctrl+S)*'
              : saveStatus === 'error'
              ? 'Save Failed'
              : 'Saved'}
          </span>
        </button>

        {/* Label Manager Button */}
        <button
          onClick={onOpenLabelManager}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition-colors"
          title="Manage Class Labels"
        >
          <Tag className="w-3.5 h-3.5 text-indigo-400" />
          <span className="hidden xl:inline">Labels</span>
        </button>

        {/* Export Button */}
        <button
          onClick={onOpenExportModal}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition-colors"
          title="Export Annotations"
        >
          <Download className="w-3.5 h-3.5 text-emerald-400" />
          <span className="hidden xl:inline">Export</span>
        </button>

        {/* Help / Shortcuts Button */}
        <button
          onClick={() => setShowShortcuts(!showShortcuts)}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800"
          title="Keyboard shortcuts (?)"
        >
          <HelpCircle className="w-4 h-4" />
        </button>
      </div>

      {/* Shortcuts Guide Modal */}
      {showShortcuts && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <HelpCircle className="w-4 h-4 text-indigo-400" />
                <span>Keyboard Shortcuts</span>
              </h3>
              <button
                onClick={() => setShowShortcuts(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="mt-4 space-y-2.5 text-xs text-slate-300">
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span>Save annotation</span>
                <kbd className="px-1.5 py-0.5 rounded bg-slate-800 font-mono text-slate-300">Ctrl + S</kbd>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span>Undo action</span>
                <kbd className="px-1.5 py-0.5 rounded bg-slate-800 font-mono text-slate-300">Ctrl + Z</kbd>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span>Redo action</span>
                <kbd className="px-1.5 py-0.5 rounded bg-slate-800 font-mono text-slate-300">Ctrl + Y</kbd>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span>Previous Image</span>
                <kbd className="px-1.5 py-0.5 rounded bg-slate-800 font-mono text-slate-300">A</kbd>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span>Next Image</span>
                <kbd className="px-1.5 py-0.5 rounded bg-slate-800 font-mono text-slate-300">D</kbd>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span>Select / Move Box tool</span>
                <kbd className="px-1.5 py-0.5 rounded bg-slate-800 font-mono text-slate-300">V</kbd>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span>Draw Bounding Box tool</span>
                <kbd className="px-1.5 py-0.5 rounded bg-slate-800 font-mono text-slate-300">B</kbd>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span>Pan / Move Canvas</span>
                <kbd className="px-1.5 py-0.5 rounded bg-slate-800 font-mono text-slate-300">H or Space+Drag</kbd>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span>Delete selected box</span>
                <kbd className="px-1.5 py-0.5 rounded bg-slate-800 font-mono text-slate-300">Delete</kbd>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/60">
                <span>Quick class select</span>
                <kbd className="px-1.5 py-0.5 rounded bg-slate-800 font-mono text-slate-300">1 - 9</kbd>
              </div>
              <div className="flex justify-between py-1">
                <span>Cancel / Deselect</span>
                <kbd className="px-1.5 py-0.5 rounded bg-slate-800 font-mono text-slate-300">Esc</kbd>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

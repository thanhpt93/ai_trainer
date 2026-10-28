import React from 'react';
import {
  Tag,
  Square,
  Trash2,
  Ban,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Info,
  Layers,
  FileText,
  Plus,
} from 'lucide-react';
import {
  ProjectLabel,
  BoundingBox,
  ImageRecord,
  AnnotationStatus,
} from '../../../types';

interface AnnotationPropertiesPanelProps {
  taskType: string;
  isMultiLabel: boolean;
  labels: ProjectLabel[];
  selectedLabelIds: string[];
  boxes: BoundingBox[];
  activeLabelId: string | null;
  selectedBoxId: string | null;
  isNegative: boolean;
  isReview: boolean;
  notes: string;
  imageInfo: ImageRecord | null;
  onSelectBox: (id: string | null) => void;
  onSetActiveLabel: (id: string) => void;
  onToggleClassificationLabel: (id: string) => void;
  onChangeBoxLabel: (boxId: string, newLabelId: string) => void;
  onDeleteBox: (boxId: string) => void;
  onClearAllBoxes: () => void;
  onToggleNegative: () => void;
  onToggleReview: () => void;
  onNotesChange: (notes: string) => void;
  onOpenLabelManager: () => void;
}

export const AnnotationPropertiesPanel: React.FC<AnnotationPropertiesPanelProps> = ({
  taskType,
  isMultiLabel,
  labels,
  selectedLabelIds,
  boxes,
  activeLabelId,
  selectedBoxId,
  isNegative,
  isReview,
  notes,
  imageInfo,
  onSelectBox,
  onSetActiveLabel,
  onToggleClassificationLabel,
  onChangeBoxLabel,
  onDeleteBox,
  onClearAllBoxes,
  onToggleNegative,
  onToggleReview,
  onNotesChange,
  onOpenLabelManager,
}) => {
  const isClassification = taskType.includes('Classification');
  const isObjectDetection = taskType.includes('Detection') || taskType.includes('Object');

  return (
    <div className="w-80 bg-slate-900 border-l border-slate-800 flex flex-col h-full select-none flex-shrink-0">
      {/* Header */}
      <div className="p-3.5 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-indigo-400" />
          <h3 className="text-xs font-bold text-white uppercase tracking-wider">Properties</h3>
        </div>
        <button
          onClick={onOpenLabelManager}
          className="text-[11px] text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1"
        >
          <Plus className="w-3 h-3" />
          <span>Edit Classes</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3.5 space-y-4">
        {/* CLASSIFICATION PANEL */}
        {isClassification && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-300">
                Classification Labels {isMultiLabel ? '(Multi-label)' : '(Single-label)'}
              </span>
              <span className="text-[10px] text-slate-400 font-mono">1-9 keys</span>
            </div>

            {labels.length === 0 ? (
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-center text-xs text-slate-500">
                No classes defined yet. Click "Edit Classes" to add labels.
              </div>
            ) : (
              <div className="space-y-1.5">
                {labels.map((lbl, idx) => {
                  const isChecked = selectedLabelIds.includes(lbl.id);
                  return (
                    <button
                      key={lbl.id}
                      type="button"
                      onClick={() => onToggleClassificationLabel(lbl.id)}
                      className={`w-full p-2 rounded-lg border text-left flex items-center justify-between transition-colors ${
                        isChecked
                          ? 'bg-indigo-600/20 border-indigo-500/50 text-white font-semibold'
                          : 'bg-slate-950 border-slate-800/80 text-slate-300 hover:bg-slate-800/60'
                      }`}
                    >
                      <div className="flex items-center gap-2.5 min-w-0 truncate">
                        <span
                          className="w-3 h-3 rounded-full flex-shrink-0"
                          style={{ backgroundColor: lbl.color }}
                        />
                        <span className="text-xs truncate">{lbl.name}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        {idx < 9 && (
                          <span className="text-[10px] font-mono text-slate-400 px-1 rounded bg-slate-900 border border-slate-800">
                            {idx + 1}
                          </span>
                        )}
                        {isChecked && <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" />}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* OBJECT DETECTION PANEL */}
        {isObjectDetection && (
          <div className="space-y-4">
            {/* Active Class Selector for New Boxes */}
            <div className="space-y-2">
              <span className="text-xs font-semibold text-slate-300 block">
                Active Draw Class
              </span>
              <div className="grid grid-cols-2 gap-1.5">
                {labels.map((lbl) => {
                  const isActive = lbl.id === activeLabelId;
                  return (
                    <button
                      key={lbl.id}
                      type="button"
                      onClick={() => onSetActiveLabel(lbl.id)}
                      className={`p-1.5 rounded-lg border text-left flex items-center gap-2 text-xs truncate transition-colors ${
                        isActive
                          ? 'bg-indigo-600/20 border-indigo-500 text-white font-semibold'
                          : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'
                      }`}
                    >
                      <span
                        className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                        style={{ backgroundColor: lbl.color }}
                      />
                      <span className="truncate">{lbl.name}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Detected Objects List */}
            <div className="space-y-2 pt-2 border-t border-slate-800">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-300">
                  Objects on Image ({boxes.length})
                </span>
                {boxes.length > 0 && (
                  <button
                    onClick={onClearAllBoxes}
                    className="text-[10px] text-rose-400 hover:text-rose-300 font-medium"
                  >
                    Clear All
                  </button>
                )}
              </div>

              {boxes.length === 0 ? (
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-center text-xs text-slate-500">
                  No objects drawn. Use the Draw tool (B) to create bounding boxes.
                </div>
              ) : (
                <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                  {boxes.map((box, idx) => {
                    const isSelected = box.id === selectedBoxId;
                    return (
                      <div
                        key={box.id}
                        onClick={() => onSelectBox(box.id)}
                        className={`p-2.5 rounded-lg border text-xs cursor-pointer transition-colors ${
                          isSelected
                            ? 'bg-indigo-600/20 border-indigo-500 text-white'
                            : 'bg-slate-950 border-slate-800/80 text-slate-300 hover:bg-slate-800/50'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 min-w-0">
                            <span
                              className="w-2.5 h-2.5 rounded-sm flex-shrink-0"
                              style={{ backgroundColor: box.label_color }}
                            />
                            <span className="font-semibold text-xs truncate">
                              #{idx + 1} {box.label_name}
                            </span>
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onDeleteBox(box.id);
                            }}
                            className="p-1 text-slate-500 hover:text-rose-400 rounded"
                            title="Delete box"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>

                        {/* Coordinates Chip */}
                        <div className="mt-1 font-mono text-[10px] text-slate-400 flex items-center justify-between">
                          <span>
                            [{box.x_min.toFixed(2)}, {box.y_min.toFixed(2)}] → [{box.x_max.toFixed(2)}, {box.y_max.toFixed(2)}]
                          </span>
                        </div>

                        {/* Quick Class Switcher Dropdown */}
                        <select
                          value={box.label_id}
                          onChange={(e) => {
                            e.stopPropagation();
                            onChangeBoxLabel(box.id, e.target.value);
                          }}
                          onClick={(e) => e.stopPropagation()}
                          className="mt-1.5 w-full bg-slate-900 border border-slate-800 rounded px-2 py-0.5 text-[11px] text-slate-300 focus:outline-none focus:border-indigo-500"
                        >
                          {labels.map((lbl) => (
                            <option key={lbl.id} value={lbl.id}>
                              {lbl.name}
                            </option>
                          ))}
                        </select>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {/* UNIVERSAL ACTIONS */}
        <div className="pt-3 border-t border-slate-800 space-y-2.5">
          <span className="text-xs font-semibold text-slate-300 block">Actions & Flags</span>

          {/* Mark Negative Toggle */}
          <button
            type="button"
            onClick={onToggleNegative}
            className={`w-full py-2 px-3 rounded-lg border text-xs font-semibold flex items-center justify-center gap-2 transition-colors ${
              isNegative
                ? 'bg-sky-600 text-white border-sky-500'
                : 'bg-slate-950 text-slate-300 border-slate-800 hover:bg-slate-800'
            }`}
          >
            <Ban className="w-3.5 h-3.5" />
            <span>{isNegative ? 'Negative Image (Confirmed)' : 'Mark as Negative Image'}</span>
          </button>

          {/* Review Flag Toggle */}
          <button
            type="button"
            onClick={onToggleReview}
            className={`w-full py-2 px-3 rounded-lg border text-xs font-semibold flex items-center justify-center gap-2 transition-colors ${
              isReview
                ? 'bg-amber-600 text-white border-amber-500'
                : 'bg-slate-950 text-slate-300 border-slate-800 hover:bg-slate-800'
            }`}
          >
            <AlertCircle className="w-3.5 h-3.5" />
            <span>{isReview ? 'Flagged for Review' : 'Mark for Review'}</span>
          </button>
        </div>

        {/* NOTES SECTION */}
        <div className="pt-3 border-t border-slate-800 space-y-1.5">
          <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5 text-slate-400" />
            <span>Annotation Notes</span>
          </label>
          <textarea
            rows={2}
            value={notes}
            onChange={(e) => onNotesChange(e.target.value)}
            placeholder="Add comments or edge case notes..."
            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        {/* IMAGE METADATA */}
        {imageInfo && (
          <div className="pt-3 border-t border-slate-800 space-y-2 text-[11px] font-mono text-slate-400">
            <span className="font-sans font-semibold text-slate-300 block text-xs">
              Image Info
            </span>
            <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
              <div className="flex justify-between">
                <span>Resolution:</span>
                <span className="text-slate-300">
                  {imageInfo.width && imageInfo.height ? `${imageInfo.width} × ${imageInfo.height} px` : 'N/A'}
                </span>
              </div>
              <div className="flex justify-between">
                <span>File Size:</span>
                <span className="text-slate-300">
                  {(imageInfo.file_size_bytes / 1024).toFixed(1)} KB
                </span>
              </div>
              <div className="flex justify-between">
                <span>Format / Ch:</span>
                <span className="text-slate-300">
                  {imageInfo.format || 'Image'} ({imageInfo.channels || 3} ch)
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

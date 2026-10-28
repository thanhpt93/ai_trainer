import React, { useState } from 'react';
import { X, Download, FolderOpen, CheckCircle2, AlertCircle } from 'lucide-react';
import { ExportFormat, ExportResponse } from '../../../types';
import { api } from '../../../services/api';

interface ExportModalProps {
  datasetId: string;
  datasetName: string;
  taskType: string;
  onClose: () => void;
}

export const ExportModal: React.FC<ExportModalProps> = ({
  datasetId,
  datasetName,
  taskType,
  onClose,
}) => {
  const isClassification = taskType.includes('Classification');
  const [format, setFormat] = useState<ExportFormat>(isClassification ? 'csv' : 'yolo');
  const [outputDir, setOutputDir] = useState('');
  const [includeUnannotated, setIncludeUnannotated] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [result, setResult] = useState<ExportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSelectDirectory = async () => {
    if (window.electronAPI?.selectDirectory) {
      try {
        const selected = await window.electronAPI.selectDirectory();
        if (selected) {
          setOutputDir(selected);
        }
      } catch (err) {
        console.error('Failed to select export directory:', err);
      }
    }
  };

  const handleExport = async (e: React.FormEvent) => {
    e.preventDefault();
    setExporting(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.exportDataset(datasetId, {
        format,
        output_dir: outputDir.trim() || undefined,
        include_unannotated: includeUnannotated,
      });
      setResult(res);
    } catch (err: any) {
      setError(err.message || 'Export failed');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 select-none">
      <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-600/20 text-indigo-400 flex items-center justify-center">
              <Download className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Export Dataset Annotations</h3>
              <p className="text-xs text-slate-400">{datasetName} • {taskType}</p>
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

        {result ? (
          <div className="mt-4 space-y-4">
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs space-y-2">
              <div className="flex items-center gap-2 font-bold text-sm">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <span>Export Successful!</span>
              </div>
              <p>{result.message}</p>
              <div className="p-2.5 bg-slate-950 rounded border border-slate-800 font-mono text-[11px] break-all text-slate-300">
                <span className="text-slate-500 block text-[10px]">Destination:</span>
                {result.export_path}
              </div>
            </div>
            <div className="flex justify-end pt-2">
              <button
                onClick={onClose}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleExport} className="mt-4 space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Target Export Format <span className="text-rose-400">*</span>
              </label>
              <select
                value={format}
                onChange={(e) => setFormat(e.target.value as ExportFormat)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              >
                {isClassification ? (
                  <>
                    <option value="csv">CSV (image_path, label)</option>
                    <option value="json">JSON (Mapping Dictionary)</option>
                  </>
                ) : (
                  <>
                    <option value="yolo">YOLO Format (labels/*.txt + data.yaml)</option>
                    <option value="coco">COCO Format (annotations.json)</option>
                    <option value="pascal_voc">Pascal VOC Format (Annotations/*.xml)</option>
                    <option value="csv">CSV Summary</option>
                    <option value="json">JSON Generic</option>
                  </>
                )}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Destination Folder <span className="text-[11px] text-slate-500 font-normal">(Optional)</span>
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={outputDir}
                  onChange={(e) => setOutputDir(e.target.value)}
                  placeholder="Default: AppData/exports"
                  className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white font-mono placeholder-slate-500 focus:outline-none focus:border-indigo-500"
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

            <div className="flex items-center gap-2 pt-1">
              <input
                type="checkbox"
                id="includeUnannotated"
                checked={includeUnannotated}
                onChange={(e) => setIncludeUnannotated(e.target.checked)}
                className="rounded border-slate-800 text-indigo-600 focus:ring-0"
              />
              <label htmlFor="includeUnannotated" className="text-xs text-slate-300 cursor-pointer">
                Include unannotated / blank images in export output
              </label>
            </div>

            <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={exporting}
                className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold disabled:opacity-50 flex items-center gap-1.5"
              >
                <Download className="w-3.5 h-3.5" />
                <span>{exporting ? 'Exporting...' : 'Export Now'}</span>
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

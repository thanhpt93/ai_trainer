import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  RefreshCw,
  FolderOpen,
  AlertCircle,
  CheckCircle2,
  XCircle,
  FileQuestion,
  ChevronLeft,
  ChevronRight,
  Eye,
  X,
  FileImage,
  PenTool,
} from 'lucide-react';
import { api } from '../services/api';
import { Dataset, ImageRecord, PaginatedImages } from '../types';

export const DatasetDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [paginated, setPaginated] = useState<PaginatedImages | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter & Pagination State
  const [page, setPage] = useState(1);
  const [validFilter, setValidFilter] = useState<'all' | 'valid' | 'corrupt'>('all');
  const [scanning, setScanning] = useState(false);

  // Selected image preview modal
  const [selectedImage, setSelectedImage] = useState<ImageRecord | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);

  const loadDataset = async () => {
    if (!id) return;
    try {
      const data = await api.getDataset(id);
      setDataset(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load dataset');
    }
  };

  const loadImages = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const isValidParam = validFilter === 'all' ? undefined : validFilter === 'valid';
      const data = await api.getDatasetImages(id, isValidParam, page, 50);
      setPaginated(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load dataset images');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDataset();
  }, [id]);

  useEffect(() => {
    loadImages();
  }, [id, page, validFilter]);

  const handleRescan = async () => {
    if (!id) return;
    setScanning(true);
    try {
      const res = await api.scanDataset(id);
      alert(res.message);
      await loadDataset();
      await loadImages();
    } catch (err: any) {
      alert(err.message || 'Error re-scanning directory');
    } finally {
      setScanning(false);
    }
  };

  const handleOpenPreview = async (img: ImageRecord) => {
    if (!id) return;
    setSelectedImage(img);
    if (img.is_valid) {
      const url = await api.getImageFileUrl(id, img.id);
      setImagePreviewUrl(url);
    } else {
      setImagePreviewUrl(null);
    }
  };

  if (!dataset && loading) {
    return (
      <div className="py-24 text-center text-slate-400 text-sm">
        <span>Loading dataset details...</span>
      </div>
    );
  }

  if (error || !dataset) {
    return (
      <div className="max-w-4xl mx-auto p-6 rounded-xl bg-slate-900 border border-slate-800 text-center space-y-4">
        <AlertCircle className="w-8 h-8 text-rose-400 mx-auto" />
        <h3 className="text-base font-bold text-white">Dataset Not Found</h3>
        <p className="text-xs text-slate-400">{error || 'Unable to locate dataset.'}</p>
        <button
          onClick={() => navigate('/datasets')}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold"
        >
          Back to Datasets
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header and Back button */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="text-xl font-bold text-white">{dataset.name}</h1>
            <p className="text-xs text-slate-400 mt-0.5">
              {dataset.description || 'No dataset description.'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(`/annotation?project=${dataset.project_id}&dataset=${dataset.id}`)}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md shadow-emerald-600/20 transition-colors"
          >
            <PenTool className="w-3.5 h-3.5" />
            <span>Annotate Dataset</span>
          </button>
          <button
            onClick={handleRescan}
            disabled={scanning}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${scanning ? 'animate-spin' : ''}`} />
            <span>{scanning ? 'Scanning Folder...' : 'Re-scan Directory'}</span>
          </button>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Total Images</span>
          <div className="mt-2 text-2xl font-extrabold text-white">{dataset.image_count}</div>
          <span className="text-[11px] text-slate-400">indexed files</span>
        </div>

        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
          <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400">Valid Images</span>
          <div className="mt-2 text-2xl font-extrabold text-emerald-400">{dataset.valid_image_count}</div>
          <span className="text-[11px] text-slate-400">headers verified</span>
        </div>

        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
          <span className="text-xs font-semibold uppercase tracking-wider text-rose-400">Corrupted Files</span>
          <div className="mt-2 text-2xl font-extrabold text-rose-400">{dataset.corrupted_image_count}</div>
          <span className="text-[11px] text-slate-400">unreadable images</span>
        </div>

        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
          <span className="text-xs font-semibold uppercase tracking-wider text-amber-400">Unsupported Files</span>
          <div className="mt-2 text-2xl font-extrabold text-amber-400">{dataset.unsupported_file_count}</div>
          <span className="text-[11px] text-slate-400">non-image files</span>
        </div>
      </div>

      {/* Source Location Path Bar */}
      <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2 truncate font-mono text-slate-300" title={dataset.root_path}>
          <FolderOpen className="w-4 h-4 text-slate-400 flex-shrink-0" />
          <span className="text-slate-400">Storage Root:</span>
          <span className="truncate">{dataset.root_path}</span>
        </div>
        <span className="text-[11px] text-slate-400 font-mono flex-shrink-0 pl-4">
          Last scanned: {dataset.last_scanned_at ? new Date(dataset.last_scanned_at).toLocaleString() : 'Never'}
        </span>
      </div>

      {/* Filter and Image List Table */}
      <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-white">Scanned Image Records</h2>

          {/* Filter Pills */}
          <div className="flex items-center gap-2 p-1 bg-slate-950 border border-slate-800 rounded-lg text-xs">
            <button
              onClick={() => { setValidFilter('all'); setPage(1); }}
              className={`px-3 py-1 rounded-md transition-colors ${validFilter === 'all' ? 'bg-indigo-600 text-white font-medium' : 'text-slate-400 hover:text-white'}`}
            >
              All ({dataset.image_count})
            </button>
            <button
              onClick={() => { setValidFilter('valid'); setPage(1); }}
              className={`px-3 py-1 rounded-md transition-colors ${validFilter === 'valid' ? 'bg-indigo-600 text-white font-medium' : 'text-slate-400 hover:text-white'}`}
            >
              Valid Only ({dataset.valid_image_count})
            </button>
            <button
              onClick={() => { setValidFilter('corrupt'); setPage(1); }}
              className={`px-3 py-1 rounded-md transition-colors ${validFilter === 'corrupt' ? 'bg-indigo-600 text-white font-medium' : 'text-slate-400 hover:text-white'}`}
            >
              Corrupted ({dataset.corrupted_image_count})
            </button>
          </div>
        </div>

        {/* Image Table */}
        {loading ? (
          <div className="py-16 text-center text-slate-400 text-xs">
            <span>Loading image records...</span>
          </div>
        ) : !paginated || paginated.items.length === 0 ? (
          <div className="py-16 text-center text-slate-400 text-xs">
            <FileQuestion className="w-8 h-8 mx-auto mb-2 text-slate-400" />
            <span>No images match the current filter.</span>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[10px]">
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Relative Path</th>
                  <th className="py-2.5 px-3">Resolution</th>
                  <th className="py-2.5 px-3">Format</th>
                  <th className="py-2.5 px-3">Channels</th>
                  <th className="py-2.5 px-3">Size</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {paginated.items.map((img) => (
                  <tr key={img.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-2.5 px-3">
                      {img.is_valid ? (
                        <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-sans">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Valid</span>
                        </span>
                      ) : (
                        <span
                          className="inline-flex items-center gap-1 text-[11px] text-rose-400 font-sans"
                          title={img.error_reason || 'Unreadable file'}
                        >
                          <XCircle className="w-3.5 h-3.5" />
                          <span>Corrupt</span>
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 max-w-xs truncate text-slate-200" title={img.relative_path}>
                      {img.relative_path}
                    </td>
                    <td className="py-2.5 px-3 text-slate-400">
                      {img.width && img.height ? `${img.width} × ${img.height}` : '-'}
                    </td>
                    <td className="py-2.5 px-3 text-slate-400">{img.format || '-'}</td>
                    <td className="py-2.5 px-3 text-slate-400">{img.channels ? `${img.channels} ch` : '-'}</td>
                    <td className="py-2.5 px-3 text-slate-400">
                      {Math.round(img.file_size_bytes / 1024)} KB
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <button
                        onClick={() => handleOpenPreview(img)}
                        className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 font-sans text-xs inline-flex items-center gap-1"
                      >
                        <Eye className="w-3 h-3" />
                        <span>Inspect</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Controls */}
        {paginated && paginated.total_pages > 1 && (
          <div className="flex items-center justify-between pt-3 border-t border-slate-800 text-xs">
            <span className="text-slate-400">
              Showing Page {paginated.page} of {paginated.total_pages} ({paginated.total} total items)
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 disabled:opacity-40"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="px-2 font-mono">{page}</span>
              <button
                onClick={() => setPage((p) => Math.min(paginated.total_pages, p + 1))}
                disabled={page >= paginated.total_pages}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 disabled:opacity-40"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* INSPECT IMAGE MODAL */}
      {selectedImage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-2xl rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-2xl select-none">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <FileImage className="w-4 h-4 text-indigo-400" />
                <h3 className="text-sm font-bold text-white truncate max-w-md">
                  {selectedImage.relative_path}
                </h3>
              </div>
              <button
                onClick={() => setSelectedImage(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="mt-4 flex flex-col md:flex-row gap-4 items-center justify-center">
              {imagePreviewUrl ? (
                <div className="max-h-72 max-w-full rounded-lg overflow-hidden border border-slate-800 bg-slate-950 flex items-center justify-center">
                  <img
                    src={imagePreviewUrl}
                    alt={selectedImage.relative_path}
                    className="max-h-72 object-contain"
                  />
                </div>
              ) : (
                <div className="h-48 w-full rounded-lg bg-rose-950/20 border border-rose-900/30 flex flex-col items-center justify-center text-rose-400 p-4 text-center">
                  <AlertCircle className="w-8 h-8 mb-2" />
                  <span className="text-xs font-semibold">Image Preview Unavailable</span>
                  <span className="text-[11px] text-rose-300 mt-1">
                    {selectedImage.error_reason || 'File header corrupted or unreadable'}
                  </span>
                </div>
              )}

              <div className="w-full md:w-64 space-y-2 text-xs font-mono text-slate-300 bg-slate-950 p-3 rounded-lg border border-slate-800">
                <div>
                  <span className="text-slate-400 font-sans block text-[10px]">Status</span>
                  <span className={selectedImage.is_valid ? 'text-emerald-400' : 'text-rose-400'}>
                    {selectedImage.is_valid ? 'Valid Image Header' : 'Corrupted / Invalid'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 font-sans block text-[10px]">Dimensions</span>
                  <span>{selectedImage.width ? `${selectedImage.width} × ${selectedImage.height} px` : 'N/A'}</span>
                </div>
                <div>
                  <span className="text-slate-400 font-sans block text-[10px]">Channels & Format</span>
                  <span>{selectedImage.format || 'Unknown'} ({selectedImage.channels || 0} channels)</span>
                </div>
                <div>
                  <span className="text-slate-400 font-sans block text-[10px]">File Size</span>
                  <span>{(selectedImage.file_size_bytes / 1024).toFixed(1)} KB</span>
                </div>
                <div>
                  <span className="text-slate-400 font-sans block text-[10px]">Absolute Path</span>
                  <span className="break-all text-[10px] text-slate-400">{selectedImage.absolute_path}</span>
                </div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-800 flex justify-end">
              <button
                onClick={() => setSelectedImage(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded-lg font-medium"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

import React, { useState } from 'react';
import {
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Clock,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  FileQuestion,
  Image as ImageIcon,
} from 'lucide-react';
import {
  AnnotatedImageItem,
  DatasetAnnotationSummary,
  AnnotationStatus,
} from '../../../types';

interface DatasetImageListProps {
  summary: DatasetAnnotationSummary | null;
  images: AnnotatedImageItem[];
  selectedImageId: string | null;
  datasetId: string;
  totalImages: number;
  currentPage: number;
  totalPages: number;
  statusFilter: string;
  search: string;
  loading: boolean;
  onSelectImage: (id: string) => void;
  onFilterChange: (status: string) => void;
  onSearchChange: (query: string) => void;
  onPageChange: (page: number) => void;
  onJumpToNextUnannotated: () => void;
  getImageThumbnailUrl: (imgId: string) => string;
}

export const DatasetImageList: React.FC<DatasetImageListProps> = ({
  summary,
  images,
  selectedImageId,
  datasetId,
  totalImages,
  currentPage,
  totalPages,
  statusFilter,
  search,
  loading,
  onSelectImage,
  onFilterChange,
  onSearchChange,
  onPageChange,
  onJumpToNextUnannotated,
  getImageThumbnailUrl,
}) => {
  const getStatusBadge = (status: AnnotationStatus, isNegative: boolean) => {
    if (isNegative) {
      return (
        <span className="text-[10px] px-1.5 py-0.2 rounded bg-sky-950 text-sky-400 border border-sky-800/60 font-medium">
          Negative
        </span>
      );
    }
    switch (status) {
      case 'ANNOTATED':
        return (
          <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-950 text-emerald-400 border border-emerald-800/60 font-medium">
            Annotated
          </span>
        );
      case 'NEEDS_REVIEW':
        return (
          <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-950 text-amber-400 border border-amber-800/60 font-medium">
            Review
          </span>
        );
      case 'INVALID':
        return (
          <span className="text-[10px] px-1.5 py-0.2 rounded bg-rose-950 text-rose-400 border border-rose-800/60 font-medium">
            Invalid
          </span>
        );
      default:
        return (
          <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 border border-slate-700 font-medium">
            Unannotated
          </span>
        );
    }
  };

  return (
    <div className="w-80 bg-slate-900 border-r border-slate-800 flex flex-col h-full select-none flex-shrink-0">
      {/* Dataset Progress Section */}
      <div className="p-3 border-b border-slate-800 bg-slate-950/40 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-slate-300">Dataset Progress</span>
          <span className="font-mono text-indigo-400 font-bold">
            {summary?.completion_percentage ?? 0}%
          </span>
        </div>

        {/* Progress bar */}
        <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden flex">
          <div
            className="bg-emerald-500 h-1.5 transition-all duration-300"
            style={{ width: `${summary?.completion_percentage ?? 0}%` }}
          />
        </div>

        {/* Counts breakdown */}
        <div className="grid grid-cols-3 gap-1 text-[11px] text-center pt-1">
          <div className="bg-slate-900/80 p-1.5 rounded border border-slate-800/80">
            <span className="block text-emerald-400 font-bold">{summary?.annotated_images ?? 0}</span>
            <span className="text-[10px] text-slate-400">Done</span>
          </div>
          <div className="bg-slate-900/80 p-1.5 rounded border border-slate-800/80">
            <span className="block text-slate-300 font-bold">{summary?.unannotated_images ?? 0}</span>
            <span className="text-[10px] text-slate-400">Todo</span>
          </div>
          <div className="bg-slate-900/80 p-1.5 rounded border border-slate-800/80">
            <span className="block text-amber-400 font-bold">{summary?.needs_review_images ?? 0}</span>
            <span className="text-[10px] text-slate-400">Review</span>
          </div>
        </div>

        {/* Jump to next unannotated */}
        {(summary?.unannotated_images ?? 0) > 0 && (
          <button
            onClick={onJumpToNextUnannotated}
            className="w-full mt-1 py-1 rounded bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 text-[11px] font-semibold flex items-center justify-center gap-1.5 transition-colors"
          >
            <Sparkles className="w-3 h-3 text-indigo-400" />
            <span>Next Unannotated</span>
          </button>
        )}
      </div>

      {/* Filter Tabs */}
      <div className="p-2 border-b border-slate-800 flex items-center gap-1 overflow-x-auto text-[11px]">
        {['ALL', 'UNANNOTATED', 'ANNOTATED', 'NEEDS_REVIEW', 'INVALID'].map((f) => (
          <button
            key={f}
            onClick={() => onFilterChange(f)}
            className={`px-2 py-1 rounded whitespace-nowrap font-medium transition-colors ${
              statusFilter === f
                ? 'bg-indigo-600 text-white'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            {f === 'ALL'
              ? 'All'
              : f === 'UNANNOTATED'
              ? 'Todo'
              : f === 'ANNOTATED'
              ? 'Done'
              : f === 'NEEDS_REVIEW'
              ? 'Review'
              : 'Invalid'}
          </button>
        ))}
      </div>

      {/* Search Input */}
      <div className="p-2.5 border-b border-slate-800">
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search images by name..."
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Scrollable Image List */}
      <div className="flex-1 overflow-y-auto divide-y divide-slate-800/60 p-1">
        {loading ? (
          <div className="py-16 text-center text-slate-500 text-xs">
            <span>Loading image list...</span>
          </div>
        ) : images.length === 0 ? (
          <div className="py-16 text-center text-slate-500 text-xs flex flex-col items-center">
            <FileQuestion className="w-8 h-8 mb-2 text-slate-600" />
            <span>No images match filter</span>
          </div>
        ) : (
          images.map((item) => {
            const isSelected = item.id === selectedImageId;
            return (
              <div
                key={item.id}
                onClick={() => onSelectImage(item.id)}
                className={`p-2 rounded-lg flex items-center gap-2.5 cursor-pointer transition-colors ${
                  isSelected
                    ? 'bg-indigo-600/20 border border-indigo-500/40 text-white'
                    : 'hover:bg-slate-800/60 text-slate-300'
                }`}
              >
                {/* Thumbnail Preview */}
                <div className="w-12 h-12 rounded bg-slate-950 border border-slate-800 overflow-hidden flex-shrink-0 flex items-center justify-center">
                  <img
                    src={getImageThumbnailUrl(item.id)}
                    alt={item.relative_path}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      (e.currentTarget as HTMLElement).style.display = 'none';
                    }}
                  />
                  <ImageIcon className="w-4 h-4 text-slate-600 -z-10" />
                </div>

                {/* Details */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-1">
                    <span className="text-xs font-semibold truncate" title={item.relative_path}>
                      {item.relative_path.split(/[\\/]/).pop()}
                    </span>
                    {getStatusBadge(item.status, item.is_negative)}
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-slate-400 mt-1">
                    <span className="font-mono">
                      {item.width && item.height ? `${item.width}×${item.height}` : 'Image'}
                    </span>
                    {item.annotation_count > 0 && (
                      <span className="font-mono text-indigo-400">
                        {item.annotation_count} obj
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Pagination Footer */}
      {totalPages > 1 && (
        <div className="p-2 border-t border-slate-800 flex items-center justify-between text-xs bg-slate-950/60">
          <span className="text-slate-400 text-[11px]">
            {currentPage} / {totalPages}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => onPageChange(currentPage - 1)}
              disabled={currentPage <= 1}
              className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-30"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => onPageChange(currentPage + 1)}
              disabled={currentPage >= totalPages}
              className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-30"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

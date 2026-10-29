import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Project,
  Dataset,
  ProjectLabel,
  BoundingBox,
  ImageRecord,
  AnnotatedImageItem,
  DatasetAnnotationSummary,
  ImageAnnotationSaveRequest,
  AnnotationTool,
} from '../../../types';
import { api } from '../../../services/api';
import { AnnotationToolbar } from './AnnotationToolbar';
import { DatasetImageList } from './DatasetImageList';
import { AnnotationCanvas } from './AnnotationCanvas';
import { AnnotationPropertiesPanel } from './AnnotationPropertiesPanel';
import { LabelManagerModal } from './LabelManagerModal';
import { ExportModal } from './ExportModal';
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts';
import { FolderKanban } from 'lucide-react';

interface HistoryState {
  boxes: BoundingBox[];
  selectedLabelIds: string[];
  isNegative: boolean;
  isReview: boolean;
  notes: string;
}

export const AnnotationWorkspace: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  // Project & Dataset Selection
  const [projects, setProjects] = useState<Project[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('');

  // Labels for active project
  const [labels, setLabels] = useState<ProjectLabel[]>([]);
  const [activeLabelId, setActiveLabelId] = useState<string | null>(null);

  // Images list (Left panel)
  const [images, setImages] = useState<AnnotatedImageItem[]>([]);
  const [totalImages, setTotalImages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [summary, setSummary] = useState<DatasetAnnotationSummary | null>(null);
  const [loadingImages, setLoadingImages] = useState(false);

  // Current Active Image
  const [selectedImageId, setSelectedImageId] = useState<string | null>(null);
  const [currentImageRecord, setCurrentImageRecord] = useState<ImageRecord | null>(null);
  const [currentImageUrl, setCurrentImageUrl] = useState<string>('');

  // Active Annotation Working State
  const [boxes, setBoxes] = useState<BoundingBox[]>([]);
  const [selectedBoxId, setSelectedBoxId] = useState<string | null>(null);
  const [selectedLabelIds, setSelectedLabelIds] = useState<string[]>([]);
  const [isNegative, setIsNegative] = useState<boolean>(false);
  const [isReview, setIsReview] = useState<boolean>(false);
  const [notes, setNotes] = useState<string>('');

  // Undo / Redo History
  const [history, setHistory] = useState<HistoryState[]>([]);
  const [historyIndex, setHistoryIndex] = useState<number>(-1);

  // Tools & Canvas State
  const [currentTool, setCurrentTool] = useState<AnnotationTool>('draw');
  const [zoom, setZoom] = useState<number>(1.0);
  const [saveStatus, setSaveStatus] = useState<'saved' | 'saving' | 'dirty' | 'error'>('saved');

  // Modals
  const [isLabelManagerOpen, setIsLabelManagerOpen] = useState(false);
  const [isExportModalOpen, setIsExportModalOpen] = useState(false);
  const [, setGlobalError] = useState<string | null>(null);

  const autosaveTimerRef = useRef<NodeJS.Timeout | null>(null);

  // 1. Initial Load: Projects & URL params
  useEffect(() => {
    const init = async () => {
      try {
        const projRes = await api.getProjects();
        setProjects(projRes.items);

        const paramProj = searchParams.get('project');
        const paramDs = searchParams.get('dataset');

        const activeProjId = paramProj || (projRes.items.length > 0 ? projRes.items[0].id : '');
        setSelectedProjectId(activeProjId);

        if (activeProjId) {
          const dsRes = await api.getProjectDatasets(activeProjId);
          setDatasets(dsRes.items);
          const activeDsId = paramDs || (dsRes.items.length > 0 ? dsRes.items[0].id : '');
          setSelectedDatasetId(activeDsId);
        }
      } catch (err: any) {
        setGlobalError(err.message || 'Failed to initialize annotation workspace');
      }
    };
    init();
  }, []);

  // Synchronize URL search params with state
  useEffect(() => {
    const paramProj = searchParams.get('project');
    const paramDs = searchParams.get('dataset');
    if (paramProj && paramProj !== selectedProjectId) {
      setSelectedProjectId(paramProj);
    }
    if (paramDs && paramDs !== selectedDatasetId) {
      setSelectedDatasetId(paramDs);
    }
  }, [searchParams]);

  // 2. When Project Changes: Load datasets & labels
  useEffect(() => {
    if (!selectedProjectId) {
      setDatasets([]);
      setLabels([]);
      setSelectedDatasetId('');
      setImages([]);
      setCurrentImageUrl('');
      return;
    }
    const loadProjectData = async () => {
      try {
        const [dsRes, lblRes] = await Promise.all([
          api.getProjectDatasets(selectedProjectId),
          api.getProjectLabels(selectedProjectId),
        ]);
        setDatasets(dsRes.items);
        setLabels(lblRes.items);
        if (lblRes.items.length > 0) {
          if (!activeLabelId || !lblRes.items.some((l) => l.id === activeLabelId)) {
            setActiveLabelId(lblRes.items[0].id);
          }
        } else {
          setActiveLabelId(null);
        }

        const paramDs = searchParams.get('dataset');
        if (paramDs && dsRes.items.some((d) => d.id === paramDs)) {
          setSelectedDatasetId(paramDs);
        } else if (dsRes.items.length > 0) {
          if (!dsRes.items.some((d) => d.id === selectedDatasetId)) {
            setSelectedDatasetId(dsRes.items[0].id);
          }
        } else {
          setSelectedDatasetId('');
          setImages([]);
          setCurrentImageUrl('');
        }
      } catch (err: any) {
        setGlobalError(err.message || 'Error loading project data');
      }
    };
    loadProjectData();
  }, [selectedProjectId, searchParams]);

  // Set default tool depending on project task type
  const activeProject = projects.find((p) => p.id === selectedProjectId);
  const activeDataset = datasets.find((d) => d.id === selectedDatasetId);
  const taskType = activeProject?.task_type || 'Object Detection';
  const isMultiLabel = activeProject?.is_multi_label || false;

  useEffect(() => {
    if (taskType.includes('Classification')) {
      setCurrentTool('pan');
    } else {
      setCurrentTool('draw');
    }
  }, [taskType]);

  // 3. When Dataset Changes: Load summary & images
  const loadDatasetImages = useCallback(async () => {
    if (!selectedDatasetId) return;
    setLoadingImages(true);
    try {
      const [sumRes, imgRes] = await Promise.all([
        api.getDatasetAnnotationSummary(selectedDatasetId),
        api.getAnnotatedImages(
          selectedDatasetId,
          statusFilter,
          searchQuery,
          currentPage,
          50
        ),
      ]);
      setSummary(sumRes);
      setImages(imgRes.items);
      setTotalImages(imgRes.total);
      setTotalPages(imgRes.total_pages);

      // Select first image if none selected or current not in list
      if (imgRes.items.length > 0) {
        if (!selectedImageId || !imgRes.items.some((i) => i.id === selectedImageId)) {
          setSelectedImageId(imgRes.items[0].id);
        }
      } else {
        setSelectedImageId(null);
      }
    } catch (err: any) {
      setGlobalError(err.message || 'Failed to load dataset images');
    } finally {
      setLoadingImages(false);
    }
  }, [selectedDatasetId, statusFilter, searchQuery, currentPage, selectedImageId]);

  useEffect(() => {
    loadDatasetImages();
  }, [selectedDatasetId, statusFilter, searchQuery, currentPage]);

  // 4. When Active Image Changes: Load its annotation
  useEffect(() => {
    if (!selectedDatasetId || !selectedImageId) {
      setCurrentImageUrl('');
      setBoxes([]);
      setSelectedLabelIds([]);
      setHistory([]);
      setHistoryIndex(-1);
      return;
    }

    const loadImageData = async () => {
      try {
        const url = api.getImageFileUrlSync(selectedDatasetId, selectedImageId);
        const ann = await api.getImageAnnotation(selectedImageId);
        setCurrentImageUrl(url);
        setBoxes(ann.objects || []);
        setSelectedLabelIds(ann.label_ids || []);
        setIsNegative(ann.is_negative || false);
        setIsReview(ann.status === 'NEEDS_REVIEW');
        setNotes(ann.notes || '');
        setSelectedBoxId(null);
        setSaveStatus('saved');

        // Initialize history
        const initialHistory: HistoryState = {
          boxes: ann.objects || [],
          selectedLabelIds: ann.label_ids || [],
          isNegative: ann.is_negative || false,
          isReview: ann.status === 'NEEDS_REVIEW',
          notes: ann.notes || '',
        };
        setHistory([initialHistory]);
        setHistoryIndex(0);

        // Fetch image record metadata
        const activeImg = images.find((i) => i.id === selectedImageId);
        if (activeImg) {
          setCurrentImageRecord({
            id: activeImg.id,
            dataset_id: selectedDatasetId,
            relative_path: activeImg.relative_path,
            absolute_path: '',
            file_size_bytes: activeImg.file_size_bytes,
            width: activeImg.width,
            height: activeImg.height,
            channels: 3,
            format: activeImg.relative_path.split('.').pop()?.toUpperCase() || 'IMG',
            is_valid: activeImg.is_valid,
            error_reason: null,
            created_at: '',
          });
        }
      } catch (err: any) {
        console.error('Failed to load image annotation:', err);
      }
    };
    loadImageData();
  }, [selectedImageId, selectedDatasetId]);

  // Push new state to History Stack
  const pushHistory = useCallback(
    (newState: Partial<HistoryState>) => {
      const currentState: HistoryState = {
        boxes,
        selectedLabelIds,
        isNegative,
        isReview,
        notes,
        ...newState,
      };

      setHistory((prev) => {
        const newHist = prev.slice(0, historyIndex + 1);
        return [...newHist, currentState];
      });
      setHistoryIndex((prev) => prev + 1);
      setSaveStatus('dirty');
    },
    [boxes, selectedLabelIds, isNegative, isReview, notes, historyIndex]
  );

  // Undo / Redo handlers
  const handleUndo = useCallback(() => {
    if (historyIndex > 0) {
      const nextIndex = historyIndex - 1;
      const targetState = history[nextIndex];
      setBoxes(targetState.boxes);
      setSelectedLabelIds(targetState.selectedLabelIds);
      setIsNegative(targetState.isNegative);
      setIsReview(targetState.isReview);
      setNotes(targetState.notes);
      setHistoryIndex(nextIndex);
      setSaveStatus('dirty');
    }
  }, [historyIndex, history]);

  const handleRedo = useCallback(() => {
    if (historyIndex < history.length - 1) {
      const nextIndex = historyIndex + 1;
      const targetState = history[nextIndex];
      setBoxes(targetState.boxes);
      setSelectedLabelIds(targetState.selectedLabelIds);
      setIsNegative(targetState.isNegative);
      setIsReview(targetState.isReview);
      setNotes(targetState.notes);
      setHistoryIndex(nextIndex);
      setSaveStatus('dirty');
    }
  }, [historyIndex, history]);

  // SAVE FUNCTIONALITY
  const handleSave = useCallback(async () => {
    if (!selectedImageId || !activeProject) return;
    setSaveStatus('saving');
    try {
      const savePayload: ImageAnnotationSaveRequest = {
        task_type: activeProject.task_type,
        is_negative: isNegative,
        status: isReview ? 'NEEDS_REVIEW' : undefined,
        label_ids: selectedLabelIds,
        objects: boxes.map((b) => ({
          label_id: b.label_id,
          x_min: b.x_min,
          y_min: b.y_min,
          x_max: b.x_max,
          y_max: b.y_max,
          confidence: b.confidence,
        })),
        notes: notes || undefined,
      };

      await api.saveImageAnnotation(selectedImageId, savePayload);
      setSaveStatus('saved');

      // Refresh left panel summary and image status
      if (selectedDatasetId) {
        const updatedSum = await api.getDatasetAnnotationSummary(selectedDatasetId);
        setSummary(updatedSum);
      }
      setImages((prev) =>
        prev.map((img) =>
          img.id === selectedImageId
            ? {
                ...img,
                status: isReview
                  ? 'NEEDS_REVIEW'
                  : isNegative || boxes.length > 0 || selectedLabelIds.length > 0
                  ? 'ANNOTATED'
                  : 'UNANNOTATED',
                is_negative: isNegative,
                annotation_count: boxes.length || selectedLabelIds.length,
              }
            : img
        )
      );
    } catch (err) {
      console.error('Save failed:', err);
      setSaveStatus('error');
    }
  }, [selectedImageId, activeProject, isNegative, isReview, selectedLabelIds, boxes, notes, selectedDatasetId]);

  // Autosave Debounce (1.5s idle)
  useEffect(() => {
    if (saveStatus !== 'dirty') return;
    if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current);

    autosaveTimerRef.current = setTimeout(() => {
      handleSave();
    }, 1500);

    return () => {
      if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current);
    };
  }, [saveStatus, handleSave]);

  // Image Navigation: Prev / Next
  const currentIndex = images.findIndex((i) => i.id === selectedImageId);

  const handlePrevImage = useCallback(() => {
    if (currentIndex > 0) {
      if (saveStatus === 'dirty') handleSave();
      setSelectedImageId(images[currentIndex - 1].id);
    }
  }, [currentIndex, images, saveStatus, handleSave]);

  const handleNextImage = useCallback(() => {
    if (currentIndex < images.length - 1) {
      if (saveStatus === 'dirty') handleSave();
      setSelectedImageId(images[currentIndex + 1].id);
    }
  }, [currentIndex, images, saveStatus, handleSave]);

  const handleJumpToNextUnannotated = useCallback(async () => {
    if (!selectedDatasetId) return;
    try {
      const res = await api.getAnnotatedImages(selectedDatasetId, 'UNANNOTATED', undefined, 1, 1);
      if (res.items.length > 0) {
        if (saveStatus === 'dirty') handleSave();
        setSelectedImageId(res.items[0].id);
      } else {
        alert('All images in this dataset have been annotated!');
      }
    } catch (err: any) {
      console.error(err);
    }
  }, [selectedDatasetId, saveStatus, handleSave]);

  // Box Manipulation Handlers
  const handleBoxChange = useCallback(
    (updatedBoxes: BoundingBox[], commitHistory: boolean = true) => {
      setBoxes(updatedBoxes);
      if (commitHistory) {
        pushHistory({ boxes: updatedBoxes });
      }
    },
    [pushHistory]
  );

  const handleBoxCreated = useCallback(
    (newBox: BoundingBox) => {
      const updated = [...boxes, newBox];
      setBoxes(updated);
      pushHistory({ boxes: updated });
    },
    [boxes, pushHistory]
  );

  const handleDeleteSelectedBox = useCallback(() => {
    if (selectedBoxId) {
      const updated = boxes.filter((b) => b.id !== selectedBoxId);
      setBoxes(updated);
      setSelectedBoxId(null);
      pushHistory({ boxes: updated });
    }
  }, [selectedBoxId, boxes, pushHistory]);

  const handleClearAllBoxes = useCallback(() => {
    if (!window.confirm('Delete all bounding boxes on this image?')) return;
    setBoxes([]);
    setSelectedBoxId(null);
    pushHistory({ boxes: [] });
  }, [pushHistory]);

  const handleChangeBoxLabel = useCallback(
    (boxId: string, newLabelId: string) => {
      const targetLabel = labels.find((l) => l.id === newLabelId);
      if (!targetLabel) return;
      const updated = boxes.map((b) =>
        b.id === boxId
          ? {
              ...b,
              label_id: targetLabel.id,
              label_name: targetLabel.name,
              label_color: targetLabel.color,
            }
          : b
      );
      setBoxes(updated);
      pushHistory({ boxes: updated });
    },
    [boxes, labels, pushHistory]
  );

  // Classification Toggle Handlers
  const handleToggleClassificationLabel = useCallback(
    (labelId: string) => {
      let updated: string[];
      if (isMultiLabel) {
        updated = selectedLabelIds.includes(labelId)
          ? selectedLabelIds.filter((id) => id !== labelId)
          : [...selectedLabelIds, labelId];
      } else {
        updated = selectedLabelIds.includes(labelId) ? [] : [labelId];
      }
      setSelectedLabelIds(updated);
      pushHistory({ selectedLabelIds: updated });
    },
    [isMultiLabel, selectedLabelIds, pushHistory]
  );

  // Universal Flags
  const handleToggleNegative = useCallback(() => {
    const nextVal = !isNegative;
    setIsNegative(nextVal);
    if (nextVal) {
      setBoxes([]);
    }
    pushHistory({ isNegative: nextVal, boxes: nextVal ? [] : boxes });
  }, [isNegative, boxes, pushHistory]);

  const handleToggleReview = useCallback(() => {
    const nextVal = !isReview;
    setIsReview(nextVal);
    pushHistory({ isReview: nextVal });
  }, [isReview, pushHistory]);

  // Keyboard Shortcuts Registration
  useKeyboardShortcuts({
    onSave: handleSave,
    onUndo: handleUndo,
    onRedo: handleRedo,
    onPrevImage: handlePrevImage,
    onNextImage: handleNextImage,
    onDeleteSelected: handleDeleteSelectedBox,
    onEscape: () => setSelectedBoxId(null),
    onSelectTool: () => setCurrentTool('select'),
    onDrawTool: () => setCurrentTool('draw'),
    onPanTool: () => setCurrentTool('pan'),
    onQuickClass: (index) => {
      if (index < labels.length) {
        const lbl = labels[index];
        if (taskType.includes('Classification')) {
          handleToggleClassificationLabel(lbl.id);
        } else {
          setActiveLabelId(lbl.id);
        }
      }
    },
  }, !isLabelManagerOpen && !isExportModalOpen);

  return (
    <div className="flex flex-col h-full w-full overflow-hidden bg-slate-950 select-none">
      {/* Top Studio Toolbar */}
      <AnnotationToolbar
        projects={projects}
        datasets={datasets}
        selectedProjectId={selectedProjectId}
        selectedDatasetId={selectedDatasetId}
        taskType={taskType}
        currentIndex={currentIndex}
        totalImages={totalImages}
        currentTool={currentTool}
        zoom={zoom}
        saveStatus={saveStatus}
        canUndo={historyIndex > 0}
        canRedo={historyIndex < history.length - 1}
        onProjectChange={(id) => {
          setSelectedProjectId(id);
          setSearchParams({ project: id });
        }}
        onDatasetChange={(id) => {
          setSelectedDatasetId(id);
          setSearchParams({ project: selectedProjectId, dataset: id });
        }}
        onPrevImage={handlePrevImage}
        onNextImage={handleNextImage}
        onToolChange={setCurrentTool}
        onZoomIn={() => setZoom((z) => Math.min(5.0, z * 1.2))}
        onZoomOut={() => setZoom((z) => Math.max(0.2, z * 0.8))}
        onFitView={() => setZoom(1.0)}
        onResetZoom={() => setZoom(1.0)}
        onUndo={handleUndo}
        onRedo={handleRedo}
        onSave={handleSave}
        onOpenLabelManager={() => setIsLabelManagerOpen(true)}
        onOpenExportModal={() => setIsExportModalOpen(true)}
      />

      {/* Main Workspace Body */}
      {projects.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center p-6 space-y-4">
          <FolderKanban className="w-12 h-12 text-slate-600" />
          <h2 className="text-base font-bold text-white">No Projects Available</h2>
          <p className="text-xs text-slate-400 max-w-sm">
            Create a computer vision project and import a dataset before using the Annotation Studio.
          </p>
          <button
            onClick={() => navigate('/projects?create=true')}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold"
          >
            Create Project
          </button>
        </div>
      ) : datasets.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center p-6 space-y-4">
          <FolderKanban className="w-12 h-12 text-slate-600" />
          <h2 className="text-base font-bold text-white">No Datasets In Project</h2>
          <p className="text-xs text-slate-400 max-w-sm">
            Import an image directory to begin labeling dataset items.
          </p>
          <button
            onClick={() => navigate('/datasets?import=true')}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold"
          >
            Import Dataset
          </button>
        </div>
      ) : (
        <div className="flex-1 flex overflow-hidden">
          {/* Left Panel: Image Browser */}
          <DatasetImageList
            summary={summary}
            images={images}
            selectedImageId={selectedImageId}
            datasetId={selectedDatasetId}
            totalImages={totalImages}
            currentPage={currentPage}
            totalPages={totalPages}
            statusFilter={statusFilter}
            search={searchQuery}
            loading={loadingImages}
            onSelectImage={(id) => {
              if (saveStatus === 'dirty') handleSave();
              setSelectedImageId(id);
            }}
            onFilterChange={(f) => {
              setStatusFilter(f);
              setCurrentPage(1);
            }}
            onSearchChange={setSearchQuery}
            onPageChange={setCurrentPage}
            onJumpToNextUnannotated={handleJumpToNextUnannotated}
            getImageThumbnailUrl={(id) => api.getImageFileUrlSync(selectedDatasetId, id)}
          />

          {/* Center Panel: Interactive Canvas */}
          {currentImageUrl ? (
            <AnnotationCanvas
              imageUrl={currentImageUrl}
              isNegative={isNegative}
              boxes={boxes}
              labels={labels}
              activeLabelId={activeLabelId}
              selectedBoxId={selectedBoxId}
              currentTool={currentTool}
              zoom={zoom}
              isObjectDetection={taskType.includes('Detection') || taskType.includes('Object')}
              onSelectBox={setSelectedBoxId}
              onBoxChange={handleBoxChange}
              onBoxCreated={handleBoxCreated}
              onZoomChange={setZoom}
            />
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-500 text-xs">
              Select an image from the left panel to begin annotating.
            </div>
          )}

          {/* Right Panel: Task Properties */}
          <AnnotationPropertiesPanel
            taskType={taskType}
            isMultiLabel={isMultiLabel}
            labels={labels}
            selectedLabelIds={selectedLabelIds}
            boxes={boxes}
            activeLabelId={activeLabelId}
            selectedBoxId={selectedBoxId}
            isNegative={isNegative}
            isReview={isReview}
            notes={notes}
            imageInfo={currentImageRecord}
            onSelectBox={setSelectedBoxId}
            onSetActiveLabel={setActiveLabelId}
            onToggleClassificationLabel={handleToggleClassificationLabel}
            onChangeBoxLabel={handleChangeBoxLabel}
            onDeleteBox={(id) => {
              const updated = boxes.filter((b) => b.id !== id);
              setBoxes(updated);
              if (selectedBoxId === id) setSelectedBoxId(null);
              pushHistory({ boxes: updated });
            }}
            onClearAllBoxes={handleClearAllBoxes}
            onToggleNegative={handleToggleNegative}
            onToggleReview={handleToggleReview}
            onNotesChange={(n) => {
              setNotes(n);
              setSaveStatus('dirty');
            }}
            onOpenLabelManager={() => setIsLabelManagerOpen(true)}
          />
        </div>
      )}

      {/* Label Manager Modal */}
      {isLabelManagerOpen && selectedProjectId && (
        <LabelManagerModal
          projectId={selectedProjectId}
          labels={labels}
          onClose={() => setIsLabelManagerOpen(false)}
          onLabelsUpdated={async () => {
            const res = await api.getProjectLabels(selectedProjectId);
            setLabels(res.items);
          }}
        />
      )}

      {/* Export Modal */}
      {isExportModalOpen && selectedDatasetId && (
        <ExportModal
          datasetId={selectedDatasetId}
          datasetName={activeDataset?.name || 'Dataset'}
          taskType={taskType}
          onClose={() => setIsExportModalOpen(false)}
        />
      )}
    </div>
  );
};

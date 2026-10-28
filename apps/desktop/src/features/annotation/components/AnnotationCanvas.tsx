import React, { useRef, useState, useEffect, useCallback } from 'react';
import { BoundingBox, ProjectLabel, AnnotationTool } from '../../../types';
import { Ban } from 'lucide-react';

interface AnnotationCanvasProps {
  imageUrl: string;
  isNegative: boolean;
  boxes: BoundingBox[];
  labels: ProjectLabel[];
  activeLabelId: string | null;
  selectedBoxId: string | null;
  currentTool: AnnotationTool;
  zoom: number;
  isObjectDetection: boolean;
  onSelectBox: (id: string | null) => void;
  onBoxChange: (updatedBoxes: BoundingBox[], commitHistory?: boolean) => void;
  onBoxCreated: (newBox: BoundingBox) => void;
  onZoomChange: (zoom: number) => void;
}

type ResizeHandle = 'nw' | 'n' | 'ne' | 'e' | 'se' | 's' | 'sw' | 'w';

export const AnnotationCanvas: React.FC<AnnotationCanvasProps> = ({
  imageUrl,
  isNegative,
  boxes,
  labels,
  activeLabelId,
  selectedBoxId,
  currentTool,
  zoom,
  isObjectDetection,
  onSelectBox,
  onBoxChange,
  onBoxCreated,
  onZoomChange,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const boxesRef = useRef<BoundingBox[]>(boxes);
  boxesRef.current = boxes;

  // Pan offsets (in screen pixels)
  const [panOffset, setPanOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [startPan, setStartPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isSpacePressed, setIsSpacePressed] = useState(false);

  // Natural image dimensions
  const [imageSize, setImageSize] = useState<{ width: number; height: number }>({ width: 0, height: 0 });
  const [displayedRect, setDisplayedRect] = useState<{ x: number; y: number; width: number; height: number }>({
    x: 0,
    y: 0,
    width: 0,
    height: 0,
  });

  // Drawing state
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawStart, setDrawStart] = useState<{ x: number; y: number } | null>(null);
  const [drawCurrent, setDrawCurrent] = useState<{ x: number; y: number } | null>(null);

  // Dragging/moving existing box state
  const [isMoving, setIsMoving] = useState(false);
  const [moveStart, setMoveStart] = useState<{ x: number; y: number } | null>(null);
  const [originalBoxCoords, setOriginalBoxCoords] = useState<{
    x_min: number;
    y_min: number;
    x_max: number;
    y_max: number;
  } | null>(null);

  // Resizing box state
  const [activeHandle, setActiveHandle] = useState<ResizeHandle | null>(null);
  const [resizeStart, setResizeStart] = useState<{ x: number; y: number } | null>(null);

  // Spacebar panning listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === 'Space' && !['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement)?.tagName)) {
        setIsSpacePressed(true);
      }
    };
    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.code === 'Space') {
        setIsSpacePressed(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, []);

  // Update displayed image rect inside the container
  const updateDisplayedRect = useCallback(() => {
    if (!containerRef.current || !imageSize.width || !imageSize.height) return;

    const containerWidth = containerRef.current.clientWidth;
    const containerHeight = containerRef.current.clientHeight;

    // Calculate aspect-ratio fit base dimensions
    const scale = Math.min(
      (containerWidth * 0.95) / imageSize.width,
      (containerHeight * 0.95) / imageSize.height
    );

    const baseWidth = imageSize.width * scale;
    const baseHeight = imageSize.height * scale;

    const currentWidth = baseWidth * zoom;
    const currentHeight = baseHeight * zoom;

    const x = (containerWidth - currentWidth) / 2 + panOffset.x;
    const y = (containerHeight - currentHeight) / 2 + panOffset.y;

    setDisplayedRect({ x, y, width: currentWidth, height: currentHeight });
  }, [imageSize, zoom, panOffset]);

  useEffect(() => {
    updateDisplayedRect();
  }, [updateDisplayedRect]);

  const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    setImageSize({ width: img.naturalWidth, height: img.naturalHeight });
    setPanOffset({ x: 0, y: 0 });
  };

  // Check if screen coordinates fall within the displayed image rectangle
  const isInsideImage = useCallback(
    (screenX: number, screenY: number): boolean => {
      return (
        displayedRect.width > 0 &&
        displayedRect.height > 0 &&
        screenX >= displayedRect.x &&
        screenX <= displayedRect.x + displayedRect.width &&
        screenY >= displayedRect.y &&
        screenY <= displayedRect.y + displayedRect.height
      );
    },
    [displayedRect]
  );

  // Convert Screen coordinates to Normalized Image coordinates [0, 1]
  const screenToNorm = useCallback(
    (screenX: number, screenY: number): { x: number; y: number } => {
      if (!displayedRect.width || !displayedRect.height) return { x: 0, y: 0 };
      const relX = screenX - displayedRect.x;
      const relY = screenY - displayedRect.y;

      const normX = Math.max(0, Math.min(1, relX / displayedRect.width));
      const normY = Math.max(0, Math.min(1, relY / displayedRect.height));
      return { x: normX, y: normY };
    },
    [displayedRect]
  );

  // Convert Normalized Image coordinates [0, 1] to Screen coordinates
  const normToScreen = useCallback(
    (normX: number, normY: number): { x: number; y: number } => {
      return {
        x: displayedRect.x + normX * displayedRect.width,
        y: displayedRect.y + normY * displayedRect.height,
      };
    },
    [displayedRect]
  );

  // Mouse wheel zoom
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
    const newZoom = Math.max(0.2, Math.min(5.0, zoom * zoomFactor));
    onZoomChange(newZoom);
  };

  // Pointer Down (Draw, Move, Resize, or Pan)
  const handleMouseDown = (e: React.MouseEvent) => {
    // Middle click or Space key down => Always Pan
    if (e.button === 1 || isSpacePressed) {
      setIsPanning(true);
      setStartPan({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y });
      return;
    }

    if (e.button !== 0) return; // Left click only

    const container = containerRef.current;
    if (!container) return;
    const rect = container.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const norm = screenToNorm(clickX, clickY);

    // 1. In Classification mode OR Pan Tool mode: Left click ALWAYS pans
    if (!isObjectDetection || currentTool === 'pan') {
      setIsPanning(true);
      setStartPan({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y });
      return;
    }

    // 2. In Select Tool mode: Clicking on empty area deselects and pans
    if (currentTool === 'select') {
      if (!activeHandle && !isMoving) {
        onSelectBox(null);
        setIsPanning(true);
        setStartPan({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y });
      }
      return;
    }

    // 3. In Draw Tool mode:
    if (currentTool === 'draw') {
      // If clicked outside the image area, pan the canvas
      if (!isInsideImage(clickX, clickY)) {
        setIsPanning(true);
        setStartPan({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y });
        return;
      }

      // If clicked inside the image, begin drawing a new box
      if (!isNegative) {
        setIsDrawing(true);
        setDrawStart(norm);
        setDrawCurrent(norm);
        onSelectBox(null);
      }
    }
  };

  // Box Mouse Down (Click to Select and Move)
  const handleBoxMouseDown = (e: React.MouseEvent, box: BoundingBox) => {
    if (e.button !== 0) return; // Left click only
    e.stopPropagation();

    // If Space key or Pan tool is active, pan canvas instead of moving box
    if (isSpacePressed || currentTool === 'pan') {
      setIsPanning(true);
      setStartPan({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y });
      return;
    }

    // Select this box
    onSelectBox(box.id);

    // Immediately initiate moving mode (works in both 'draw' and 'select' tools!)
    const container = containerRef.current;
    if (!container) return;
    const rect = container.getBoundingClientRect();
    const norm = screenToNorm(e.clientX - rect.left, e.clientY - rect.top);

    setIsMoving(true);
    setMoveStart(norm);
    setOriginalBoxCoords({
      x_min: box.x_min,
      y_min: box.y_min,
      x_max: box.x_max,
      y_max: box.y_max,
    });
  };

  // Resize Handle Mouse Down
  const handleResizeHandleDown = (
    e: React.MouseEvent,
    handle: ResizeHandle,
    box: BoundingBox
  ) => {
    if (e.button !== 0) return;
    e.stopPropagation();

    const container = containerRef.current;
    if (!container) return;
    const rect = container.getBoundingClientRect();
    const norm = screenToNorm(e.clientX - rect.left, e.clientY - rect.top);

    setActiveHandle(handle);
    setResizeStart(norm);
    setOriginalBoxCoords({
      x_min: box.x_min,
      y_min: box.y_min,
      x_max: box.x_max,
      y_max: box.y_max,
    });
  };

  // Unified Mouse Move Handler (supports window capture)
  const processMouseMove = useCallback(
    (clientX: number, clientY: number) => {
      const container = containerRef.current;
      if (!container) return;
      const rect = container.getBoundingClientRect();
      const mouseX = clientX - rect.left;
      const mouseY = clientY - rect.top;

      if (isPanning) {
        setPanOffset({
          x: clientX - startPan.x,
          y: clientY - startPan.y,
        });
        return;
      }

      const norm = screenToNorm(mouseX, mouseY);

      if (isDrawing && drawStart) {
        setDrawCurrent(norm);
      } else if (isMoving && moveStart && originalBoxCoords && selectedBoxId) {
        const dx = norm.x - moveStart.x;
        const dy = norm.y - moveStart.y;

        const boxWidth = originalBoxCoords.x_max - originalBoxCoords.x_min;
        const boxHeight = originalBoxCoords.y_max - originalBoxCoords.y_min;

        let newXmin = originalBoxCoords.x_min + dx;
        let newYmin = originalBoxCoords.y_min + dy;

        // Clamp within [0, 1] bounds
        newXmin = Math.max(0, Math.min(1 - boxWidth, newXmin));
        newYmin = Math.max(0, Math.min(1 - boxHeight, newYmin));

        const updated = boxesRef.current.map((b) =>
          b.id === selectedBoxId
            ? {
                ...b,
                x_min: round6(newXmin),
                y_min: round6(newYmin),
                x_max: round6(newXmin + boxWidth),
                y_max: round6(newYmin + boxHeight),
              }
            : b
        );
        onBoxChange(updated, false); // Live update, no history spam
      } else if (activeHandle && resizeStart && originalBoxCoords && selectedBoxId) {
        const dx = norm.x - resizeStart.x;
        const dy = norm.y - resizeStart.y;

        let { x_min, y_min, x_max, y_max } = originalBoxCoords;

        if (activeHandle.includes('w')) x_min = Math.max(0, Math.min(x_max - 0.01, x_min + dx));
        if (activeHandle.includes('e')) x_max = Math.min(1, Math.max(x_min + 0.01, x_max + dx));
        if (activeHandle.includes('n')) y_min = Math.max(0, Math.min(y_max - 0.01, y_min + dy));
        if (activeHandle.includes('s')) y_max = Math.min(1, Math.max(y_min + 0.01, y_max + dy));

        const updated = boxesRef.current.map((b) =>
          b.id === selectedBoxId
            ? {
                ...b,
                x_min: round6(x_min),
                y_min: round6(y_min),
                x_max: round6(x_max),
                y_max: round6(y_max),
              }
            : b
        );
        onBoxChange(updated, false); // Live update
      }
    },
    [
      isPanning,
      startPan,
      isDrawing,
      drawStart,
      isMoving,
      moveStart,
      originalBoxCoords,
      selectedBoxId,
      activeHandle,
      resizeStart,
      screenToNorm,
      onBoxChange,
    ]
  );

  // Unified Mouse Up Handler
  const processMouseUp = useCallback(() => {
    if (isPanning) {
      setIsPanning(false);
    }

    if (isDrawing && drawStart && drawCurrent) {
      setIsDrawing(false);
      const x_min = Math.min(drawStart.x, drawCurrent.x);
      const y_min = Math.min(drawStart.y, drawCurrent.y);
      const x_max = Math.max(drawStart.x, drawCurrent.x);
      const y_max = Math.max(drawStart.y, drawCurrent.y);

      const width = x_max - x_min;
      const height = y_max - y_min;

      // Reject zero-area or tiny accidental clicks
      if (width > 0.005 && height > 0.005) {
        // Resolve active label or default to first label
        const targetLabel =
          labels.find((l) => l.id === activeLabelId) || labels[0];
        if (targetLabel) {
          const newBox: BoundingBox = {
            id: 'box_' + Math.random().toString(36).substring(2, 9),
            label_id: targetLabel.id,
            label_name: targetLabel.name,
            label_color: targetLabel.color,
            x_min: round6(x_min),
            y_min: round6(y_min),
            x_max: round6(x_max),
            y_max: round6(y_max),
            confidence: 1.0,
          };
          onBoxCreated(newBox);
          onSelectBox(newBox.id);
        }
      }
      setDrawStart(null);
      setDrawCurrent(null);
    }

    if (isMoving) {
      setIsMoving(false);
      setMoveStart(null);
      setOriginalBoxCoords(null);
      // Commit final position to history once move completes
      onBoxChange(boxesRef.current, true);
    }

    if (activeHandle) {
      setActiveHandle(null);
      setResizeStart(null);
      setOriginalBoxCoords(null);
      // Commit final resized coordinates to history
      onBoxChange(boxesRef.current, true);
    }
  }, [
    isPanning,
    isDrawing,
    drawStart,
    drawCurrent,
    isMoving,
    activeHandle,
    labels,
    activeLabelId,
    onBoxCreated,
    onSelectBox,
    onBoxChange,
  ]);

  // Global mousemove and mouseup listeners during active drag/pan
  useEffect(() => {
    if (!isPanning && !isMoving && !isDrawing && !activeHandle) return;

    const onWindowMouseMove = (e: MouseEvent) => {
      processMouseMove(e.clientX, e.clientY);
    };

    const onWindowMouseUp = () => {
      processMouseUp();
    };

    window.addEventListener('mousemove', onWindowMouseMove);
    window.addEventListener('mouseup', onWindowMouseUp);

    return () => {
      window.removeEventListener('mousemove', onWindowMouseMove);
      window.removeEventListener('mouseup', onWindowMouseUp);
    };
  }, [isPanning, isMoving, isDrawing, activeHandle, processMouseMove, processMouseUp]);

  return (
    <div
      ref={containerRef}
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      className={`flex-1 relative bg-slate-950 overflow-hidden select-none flex items-center justify-center ${
        isPanning
          ? 'cursor-grabbing'
          : isSpacePressed || currentTool === 'pan' || !isObjectDetection
          ? 'cursor-grab'
          : currentTool === 'draw'
          ? 'cursor-crosshair'
          : 'cursor-default'
      }`}
    >
      {/* Target Image Element */}
      <img
        ref={imageRef}
        src={imageUrl}
        alt="Annotation Subject"
        onLoad={handleImageLoad}
        style={{
          position: 'absolute',
          left: `${displayedRect.x}px`,
          top: `${displayedRect.y}px`,
          width: `${displayedRect.width}px`,
          height: `${displayedRect.height}px`,
          pointerEvents: 'none',
        }}
        className="object-contain shadow-2xl"
      />

      {/* Negative Image Overlay Badge */}
      {isNegative && (
        <div className="absolute inset-0 bg-slate-950/70 backdrop-blur-xs flex items-center justify-center pointer-events-none z-10">
          <div className="px-5 py-3 rounded-2xl bg-sky-950/80 border border-sky-500/40 text-sky-300 flex items-center gap-3 shadow-2xl">
            <Ban className="w-6 h-6 text-sky-400" />
            <div>
              <span className="font-bold text-sm block">Confirmed Negative Image</span>
              <span className="text-[11px] text-sky-400">Zero target objects present</span>
            </div>
          </div>
        </div>
      )}

      {/* Bounding Box Overlays */}
      {isObjectDetection &&
        displayedRect.width > 0 &&
        boxes.map((box) => {
          const isSelected = box.id === selectedBoxId;
          const topLeft = normToScreen(box.x_min, box.y_min);
          const bottomRight = normToScreen(box.x_max, box.y_max);
          const width = bottomRight.x - topLeft.x;
          const height = bottomRight.y - topLeft.y;

          return (
            <div
              key={box.id}
              onMouseDown={(e) => handleBoxMouseDown(e, box)}
              style={{
                position: 'absolute',
                left: `${topLeft.x}px`,
                top: `${topLeft.y}px`,
                width: `${width}px`,
                height: `${height}px`,
                borderColor: box.label_color || '#6366f1',
                backgroundColor: isSelected
                  ? `${box.label_color || '#6366f1'}33`
                  : `${box.label_color || '#6366f1'}15`,
              }}
              className={`border-2 transition-colors ${
                isSelected
                  ? 'ring-2 ring-white/70 z-20 cursor-move'
                  : 'z-10 hover:border-white cursor-pointer'
              }`}
            >
              {/* Box Class Tag Header */}
              <div
                style={{ backgroundColor: box.label_color || '#6366f1' }}
                className="absolute -top-5 left-0 px-1.5 py-0.5 rounded-t text-[10px] font-bold text-white whitespace-nowrap shadow-sm pointer-events-none flex items-center gap-1"
              >
                <span>{box.label_name}</span>
              </div>

              {/* 8 Resize Handles (always rendered and draggable when selected!) */}
              {isSelected && (
                <>
                  <div
                    onMouseDown={(e) => handleResizeHandleDown(e, 'nw', box)}
                    className="absolute -top-1.5 -left-1.5 w-3 h-3 bg-white border border-slate-900 rounded-sm cursor-nw-resize z-30"
                  />
                  <div
                    onMouseDown={(e) => handleResizeHandleDown(e, 'n', box)}
                    className="absolute -top-1.5 left-1/2 -translate-x-1/2 w-3 h-3 bg-white border border-slate-900 rounded-sm cursor-n-resize z-30"
                  />
                  <div
                    onMouseDown={(e) => handleResizeHandleDown(e, 'ne', box)}
                    className="absolute -top-1.5 -right-1.5 w-3 h-3 bg-white border border-slate-900 rounded-sm cursor-ne-resize z-30"
                  />
                  <div
                    onMouseDown={(e) => handleResizeHandleDown(e, 'e', box)}
                    className="absolute top-1/2 -translate-y-1/2 -right-1.5 w-3 h-3 bg-white border border-slate-900 rounded-sm cursor-e-resize z-30"
                  />
                  <div
                    onMouseDown={(e) => handleResizeHandleDown(e, 'se', box)}
                    className="absolute -bottom-1.5 -right-1.5 w-3 h-3 bg-white border border-slate-900 rounded-sm cursor-se-resize z-30"
                  />
                  <div
                    onMouseDown={(e) => handleResizeHandleDown(e, 's', box)}
                    className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-3 h-3 bg-white border border-slate-900 rounded-sm cursor-s-resize z-30"
                  />
                  <div
                    onMouseDown={(e) => handleResizeHandleDown(e, 'sw', box)}
                    className="absolute -bottom-1.5 -left-1.5 w-3 h-3 bg-white border border-slate-900 rounded-sm cursor-sw-resize z-30"
                  />
                  <div
                    onMouseDown={(e) => handleResizeHandleDown(e, 'w', box)}
                    className="absolute top-1/2 -translate-y-1/2 -left-1.5 w-3 h-3 bg-white border border-slate-900 rounded-sm cursor-w-resize z-30"
                  />
                </>
              )}
            </div>
          );
        })}

      {/* Live Drawing Preview Box */}
      {isDrawing && drawStart && drawCurrent && (
        <div
          style={{
            position: 'absolute',
            left: `${Math.min(normToScreen(drawStart.x, drawStart.y).x, normToScreen(drawCurrent.x, drawCurrent.y).x)}px`,
            top: `${Math.min(normToScreen(drawStart.y, drawStart.y).y, normToScreen(drawCurrent.y, drawCurrent.y).y)}px`,
            width: `${Math.abs(normToScreen(drawCurrent.x, drawCurrent.y).x - normToScreen(drawStart.x, drawStart.y).x)}px`,
            height: `${Math.abs(normToScreen(drawCurrent.y, drawCurrent.y).y - normToScreen(drawStart.y, drawStart.y).y)}px`,
            borderColor: labels.find((l) => l.id === activeLabelId)?.color || '#6366f1',
          }}
          className="border-2 border-dashed bg-indigo-500/20 z-30 pointer-events-none"
        />
      )}
    </div>
  );
};

function round6(val: number): number {
  return Math.round(val * 1000000) / 1000000;
}

import { useEffect } from 'react';

interface ShortcutHandlers {
  onSave?: () => void;
  onUndo?: () => void;
  onRedo?: () => void;
  onPrevImage?: () => void;
  onNextImage?: () => void;
  onDeleteSelected?: () => void;
  onEscape?: () => void;
  onSelectTool?: () => void;
  onDrawTool?: () => void;
  onPanTool?: () => void;
  onQuickClass?: (index: number) => void;
}

export function useKeyboardShortcuts(handlers: ShortcutHandlers, enabled: boolean = true) {
  useEffect(() => {
    if (!enabled) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in text inputs or textareas
      const target = e.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        return;
      }

      const isCtrlOrCmd = e.ctrlKey || e.metaKey;

      // Save: Ctrl + S
      if (isCtrlOrCmd && (e.key === 's' || e.key === 'S')) {
        e.preventDefault();
        handlers.onSave?.();
        return;
      }

      // Undo: Ctrl + Z
      if (isCtrlOrCmd && !e.shiftKey && (e.key === 'z' || e.key === 'Z')) {
        e.preventDefault();
        handlers.onUndo?.();
        return;
      }

      // Redo: Ctrl + Y or Ctrl + Shift + Z
      if (
        (isCtrlOrCmd && (e.key === 'y' || e.key === 'Y')) ||
        (isCtrlOrCmd && e.shiftKey && (e.key === 'z' || e.key === 'Z'))
      ) {
        e.preventDefault();
        handlers.onRedo?.();
        return;
      }

      // Escape
      if (e.key === 'Escape') {
        e.preventDefault();
        handlers.onEscape?.();
        return;
      }

      // Delete or Backspace
      if (e.key === 'Delete' || e.key === 'Backspace') {
        handlers.onDeleteSelected?.();
        return;
      }

      // Navigation: A = Prev, D = Next
      if (e.key === 'a' || e.key === 'A') {
        handlers.onPrevImage?.();
        return;
      }
      if (e.key === 'd' || e.key === 'D') {
        handlers.onNextImage?.();
        return;
      }

      // Tool Switcher: V = Select, B = Bounding Box Draw, H = Pan
      if (e.key === 'v' || e.key === 'V') {
        handlers.onSelectTool?.();
        return;
      }
      if (e.key === 'b' || e.key === 'B') {
        handlers.onDrawTool?.();
        return;
      }
      if (e.key === 'h' || e.key === 'H') {
        handlers.onPanTool?.();
        return;
      }

      // Quick numbers 1-9 for class selection
      if (!isCtrlOrCmd && e.key >= '1' && e.key <= '9') {
        const num = parseInt(e.key, 10) - 1;
        handlers.onQuickClass?.(num);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handlers, enabled]);
}

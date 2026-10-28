# NOVA AI Trainer — Architecture Specification (Phase 1)

## 1. System Overview

**NOVA AI Trainer** is a standalone, technical desktop application tailored for computer vision engineers. It enables end-to-end dataset management, image inspection, annotation, training configuration, experiment tracking, and model export for deployment into platforms such as NOVA Machine Vision Platform.

The architecture emphasizes:
- **Clean modular boundaries** between the desktop presentation tier, local API service, domain logic, worker processes, and storage.
- **Process isolation**: Training jobs, heavy preprocessing, and model inference run in isolated worker processes rather than blocking the user interface or API handlers.
- **Strict desktop security**: Sandboxed Electron renderer communicating through explicit, allowlisted IPC channels with no arbitrary node integration or shell execution.
- **Extensible adapters**: Vision tasks, annotation schemas, model backends, and export targets are governed by abstract protocols so new frameworks (e.g. PyTorch, YOLOv8/v11, ONNX Runtime) can be incorporated without refactoring the application shell.

---

## 2. Tiered Architecture & Module Boundaries

```
+------------------------------------------------------------------------+
|                     Desktop Presentation Tier                          |
|  - Electron Shell (Main Process, Preload Bridge, Native Dialogs)        |
|  - React 18 + TypeScript + Vite + Zustand + Tailwind CSS               |
|  - Route Layout: Dashboard, Projects, Datasets, Studio, Training, etc. |
+-----------------------------------+------------------------------------+
                                    | Controlled Loopback HTTP (127.0.0.1)
                                    v
+------------------------------------------------------------------------+
|                      Local Backend Service                             |
|  - FastAPI (REST API v1, Pydantic v2 validation, OpenAPI docs)         |
|  - Path Validation Service (security, symlink protection, normalization)|
|  - Project & Dataset Domain Services                                   |
|  - Dataset Stream Scanner (Pillow inspection without memory overload)  |
+-------------------+--------------------------------+-------------------+
                    |                                |
                    v                                v
+------------------------------------+  +--------------------------------+
|        Persistence Layer           |  |        Worker Tier (Future)    |
|  - SQLite (WAL Mode + FK enabled)  |  |  - Isolated Subprocess Workers |
|  - SQLAlchemy 2.0 ORM              |  |  - Telemetry & Progress Stream |
|  - Relational image & job metadata |  |  - GPU/CPU Resource Monitor    |
+------------------------------------+  +--------------------------------+
```

### Module Responsibilities

1. **Desktop Shell (`apps/desktop/electron/`)**:
   - Manages desktop window lifecycle, default 1440×900 resolution.
   - Supervises Python backend subprocess startup, readiness verification, and clean termination (`taskkill` tree termination on exit to prevent orphan processes).
   - Provides safe native folder picker dialogs (`dialog:selectDirectory`) exposed via `window.electronAPI`.
   - Security policy: `contextIsolation: true`, `nodeIntegration: false`, `sandbox: false` (to enable preload bridge), and strict Content Security Policy (CSP).

2. **Frontend UI (`apps/desktop/src/`)**:
   - Built with React 18, TypeScript, Tailwind CSS, and Lucide icons.
   - Client-side navigation powered by React Router DOM.
   - Global application state managed by Zustand (`useAppStore`).
   - Clean empty states, loading indicators, and error banners.

3. **Backend Service (`backend/app/`)**:
   - Versioned REST API under `/api/v1`.
   - Binds strictly to loopback (`127.0.0.1`) on a dynamic or configured port.
   - Fast startup and structured exception handling.

4. **Domain Services & Repositories (`backend/app/services/`, `backend/app/domain/`)**:
   - `PathValidator`: Guard against unauthorized directory traversal or selecting system root paths.
   - `DatasetScanner`: Chunked stream scanning of image files (`.jpg`, `.jpeg`, `.png`, `.bmp`, `.tiff`, `.webp`). Validates headers with Pillow without loading full image arrays into memory.
   - `ProjectService` & `DatasetService`: Transactional CRUD with conflict resolution.

5. **Extensible Adapters (`backend/app/adapters/base.py`)**:
   - Abstract interfaces for `BaseTaskAdapter`, `BaseDatasetAdapter`, `BaseModelAdapter`, `BaseTrainingEngine`, and `BaseExportAdapter`.

6. **Worker Subsystem (`backend/app/workers/base.py`)**:
   - `WorkerProcessManager` protocol defining `start_worker`, `stop_worker`, `get_status`, and `get_resources`.

---

## 3. Communication & Desktop Security Protocol

- **Loopback binding**: The backend binds exclusively to `127.0.0.1`.
- **Preload Isolation**: The Electron renderer interacts only with allowlisted methods exposed through `contextBridge`:
  ```ts
  window.electronAPI.selectDirectory()
  window.electronAPI.getBackendUrl()
  window.electronAPI.getAppVersion()
  ```
- **Filesystem Security**: No arbitrary file reads/writes from the UI. File streaming is validated server-side by ensuring requested files reside strictly inside the dataset's validated root path.
- **Graceful Lifecycle**: When Electron emits `will-quit`, the Python process tree is terminated immediately to avoid lingering background daemons.

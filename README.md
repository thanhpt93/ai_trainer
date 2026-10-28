# NOVA AI Trainer (Phase 2: Annotation Studio)

> **Phase 2: NOVA AI Trainer Annotation Studio**  
> Standalone desktop application for computer vision dataset management, interactive image annotation, classification, bounding box labeling, multi-format dataset export, and future training pipeline integration.

---\n## 1. Overview & Architecture

NOVA AI Trainer is structured with strict separation of concerns across presentation, local API services, domain logic, worker processes, and storage:

```
ai_trainer/
├── apps/
│   └── desktop/               # Electron + React 18 + TypeScript + Vite + Zustand + Tailwind CSS
│       ├── electron/          # Main process, preload bridge, backend lifecycle, IPC
│       └── src/               # React UI, pages, components, layout, features, services
│           └── features/
│               └── annotation/ # Annotation Studio: Canvas, Toolbar, Properties, ImageList, Modals
├── backend/                   # Python FastAPI Backend
│   ├── app/
│   │   ├── api/v1/            # REST endpoints (health, projects, datasets, labels, annotations)
│   │   ├── core/              # Config, loopback binding, paths
│   │   ├── db/                # SQLite session, WAL mode, foreign keys, Base
│   │   ├── domain/            # Models: Project, Dataset, ImageRecord, ProjectLabel, ImageAnnotation, ...
│   │   ├── schemas/           # Pydantic v2 schemas: Project, Dataset, Label, Annotation, Export
│   │   ├── services/          # ProjectService, DatasetService, LabelService, AnnotationService, ExportService
│   │   ├── workers/           # Subprocess worker contracts for future isolated training
│   │   └── adapters/          # Extensible task, dataset, model, and export interfaces
│   └── tests/                 # Automated pytest test suite (15 unit & integration tests)
├── docs/                      # Architecture, domain models, API, and roadmap documentation
├── scripts/                   # Convenient Windows launcher scripts
└── data/                      # User data workspace
```

---

## 2. Phase 2 Features: Annotation Studio

The Annotation Studio provides a professional, desktop-first computer vision labeling environment:

1. **Four-Panel Workspace Layout**:
   - **Left Panel (Dataset & Image List):** Real-time progress bar, completion percentage, jump to next unannotated image, quick status filter tabs (`All`, `Unannotated`, `Annotated`, `Needs Review`, `Invalid`), image search, and paginated thumbnail grid.
   - **Center Panel (Interactive Canvas):** Hardware-accelerated zoom (20% to 500%), pan (middle click or Spacebar drag), aspect-ratio fit, live coordinates mapping between screen pixels and normalized image coordinates `[0, 1]`, and smooth bounding box drawing.
   - **Right Panel (Properties Panel):**
     - *Classification:* Single-label or multi-label modes with radio/checkbox toggles and active label assignment.
     - *Object Detection:* Object count, per-box coordinate displays, label assignment dropdown, deletion, and clear all.
     - *Image State:* Negative image toggle (confirmed target-absent background), quality control review flag, and annotator notes.
   - **Top Toolbar:** Project and dataset contextual breadcrumbs, task type indicator, previous/next image navigation, tool switcher (Select `V` vs Draw `B`), Undo / Redo history, live save status, Label Manager modal, and Dataset Export modal.

2. **Productivity Keyboard Shortcuts**:
   - `Ctrl+S` / `Cmd+S`: Save annotations
   - `Ctrl+Z`: Undo annotation action
   - `Ctrl+Y` / `Ctrl+Shift+Z`: Redo annotation action
   - `A` / `D` or `ArrowLeft` / `ArrowRight`: Navigate to previous / next image
   - `Delete` / `Backspace`: Delete selected bounding box
   - `Escape`: Cancel drawing or deselect active box
   - `V`: Switch to Select / Move tool
   - `B`: Switch to Bounding Box Draw tool
   - `1` – `9`: Quick-select class label by index
   - `Spacebar + Drag` / Middle Click: Pan canvas

3. **Label / Class Management**:
   - Create, edit, and delete classes with customizable color palettes.
   - Unique case-insensitive label names per project.
   - Referential integrity protection: prevents accidental deletion of labels currently referenced by annotations (HTTP 409 Conflict).

4. **Multi-Format Dataset Export**:
   - **YOLO Format:** Normalized bounding boxes in `labels/{name}.txt` with `data.yaml` class mapping and split configuration.
   - **COCO Format:** Standard COCO 1.0 JSON format (`images`, `categories`, `annotations`).
   - **Pascal VOC Format:** XML files (`<annotation><object><bndbox>...`) per image.
   - **CSV & JSON:** Tabular and structured annotation manifests.
   - Supports optional image copying into the export bundle.

---

## 3. Prerequisites

- **Operating System:** Windows 10/11 (or Linux / macOS)
- **Node.js:** v20+ and npm
- **Python:** 3.10+ (tested with Python 3.10 and 3.14)
- **Optional GPU:** NVIDIA GPU with CUDA drivers (automatically detected via PyTorch)

---

## 4. Installation

### 4.1 Python Backend Dependencies

Using Conda or virtual environment:

```bash
pip install fastapi uvicorn pydantic sqlalchemy aiosqlite pillow psutil pytest httpx
```

### 4.2 Desktop Frontend Dependencies

```bash
cd apps/desktop
npm install
```

---

## 5. Development & Startup

### 5.1 Running Desktop Application (Integrated Mode)

```bash
# In apps/desktop
npm run build && npm run build:electron
call node_modules\.bin\electron.cmd dist-electron\main.js
```

Or run the convenient script from repository root:

```bash
scripts\run_desktop.bat
```

### 5.2 Running Backend Standalone (for API Development)

```bash
python -m backend.app.main --port 8000 --host 127.0.0.1
```

Interactive OpenAPI documentation:
- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### 5.3 Running Frontend in Browser (Vite Dev Server)

```bash
cd apps/desktop
npm run dev
```

Visit [http://localhost:5173](http://localhost:5173).

---

## 6. Automated Tests

Run the complete test suite:

```bash
pytest backend/tests -v
```

All 15 automated tests cover:
- Health and system capability endpoints
- Project CRUD, validation, and duplicate conflict checks
- Label creation, updates, and reference protection
- Image Classification and Object Detection annotation workflows
- Negative image validation and coordinate bounds clamping
- Recursive dataset image folder scanning and corrupt image handling
- Secure image file streaming and directory path safety

---

## 7. Build Commands

```bash
cd apps/desktop
npm run build             # Compiles React SPA with TypeScript into dist/
npm run build:electron    # Compiles Electron main & preload into dist-electron/
```

---

## 8. Implementation Roadmap

- **Phase 1 (Completed):** Foundation, desktop shell, project management, dataset import.
- **Phase 2 (Completed):** Annotation data model, Annotation Studio, bounding boxes, labels, and exports.
- **Phase 3 (Next):** Image Classification training pipeline (ResNet, MobileNet, EfficientNet).
- **Phase 4:** Object Detection training pipeline (YOLOv8 / YOLOv11).
- **Phase 5:** Evaluation, experiments, model registry, and export for NOVA Machine Vision Platform.
- **Phase 6:** Segmentation, OCR, anomaly detection, keypoints, and distributed training.

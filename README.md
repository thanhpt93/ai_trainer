# NOVA AI Trainer (Phase 3: Classification Training & Evaluation Studio)

> **NOVA AI Trainer**  
> Standalone desktop application for computer vision dataset management, interactive image annotation, deep learning model training, interactive inference playground, multi-format dataset export, and ONNX deployment packaging.

---

## 1. Overview & Architecture

NOVA AI Trainer is structured with strict separation of concerns across presentation, local API services, domain logic, worker processes, and storage:

```
ai_trainer/
├── apps/
│   └── desktop/               # Electron + React 18 + TypeScript + Vite + Zustand + Tailwind CSS
│       ├── electron/          # Main process, preload bridge, backend lifecycle, IPC
│       └── src/               # React UI, pages, components, layout, features, services
│           ├── features/
│           │   └── annotation/ # Annotation Studio: Canvas, Toolbar, Properties, ImageList, Modals
│           └── pages/          # Dashboard, Projects, Datasets, Training, Monitoring, Evaluation
├── backend/                   # Python FastAPI Backend
│   ├── app/
│   │   ├── api/v1/            # REST endpoints (health, projects, datasets, labels, annotations, training, models)
│   │   ├── core/              # Config, loopback binding, paths
│   │   ├── db/                # SQLite session, WAL mode, foreign keys, Base
│   │   ├── domain/            # Models: Project, Dataset, ImageRecord, ProjectLabel, ImageAnnotation, TrainingJob, ModelArtifact
│   │   ├── schemas/           # Pydantic v2 schemas: Project, Dataset, Label, Annotation, TrainingJob, Export, Predict
│   │   ├── services/          # ProjectService, DatasetService, LabelService, AnnotationService, ExportService, TrainingManager, ModelCatalogService
│   │   ├── workers/           # Subprocess worker contracts for isolated background training
│   │   └── adapters/          # Extensible task, dataset, model, and export interfaces
│   └── tests/                 # Automated pytest test suite (21 unit & integration tests)
├── docs/                      # Architecture, domain models, API, and roadmap documentation
├── scripts/                   # Convenient Windows launcher scripts
└── data/                      # User data workspace
```

---

## 2. Core Features

### 2.1 Annotation Studio
- **Four-Panel Workspace Layout**: Dataset image thumbnails, canvas with pan/zoom/fit, properties panel with single/multi-label and bounding box controls, top toolbar with undo/redo.
- **Productivity Shortcuts**: Quick navigation, labeling hotkeys `1`–`9`, `Ctrl+S`, `Ctrl+Z`, `Spacebar` pan.
- **Multi-Format Export**: YOLO, COCO 1.0, Pascal VOC, CSV, JSON.

### 2.2 Deep Learning Training Engine (Phase 3)
- **Model Catalog**: ResNet-18, ResNet-50, MobileNetV3-Small, MobileNetV3-Large, EfficientNet-B0 with customizable classification heads.
- **Isolated Worker Processes**: Background training runs in a detached subprocess to ensure UI responsiveness.
- **Live Telemetry & Logs**: Real-time training loss, validation accuracy curves, epoch timings, and worker console streaming.
- **Cooperative Cancellation & Checkpointing**: Gracefully stops jobs and retains the best checkpoint weights.

### 2.3 Evaluation Studio & Interactive Inference Playground
- **Benchmark Evaluation**: Confusion matrix, per-class metrics (Precision, Recall, F1, Support), and misclassified sample inspector.
- **Interactive Model Inference Playground**: Test model predictions on any new input image:
  - Drag & drop or select an image file from disk (JPEG, PNG, WEBP, BMP).
  - Or input a direct filesystem path (with one-click sample shortcuts like `images/dog_01.jpg`, `images/cat_01.jpg`).
  - View real-time predictions: top class badge, confidence score, full probability distribution breakdown, and latency (ms).
- **Deployment Packaging**: Export best checkpoints to verified ONNX packages with smoke inference validation and SHA-256 manifests.

---

## 3. Prerequisites

- **Operating System:** Windows 10/11 (or Linux / macOS)
- **Node.js:** v20+ and npm
- **Python:** 3.10+ (tested with Python 3.10 and 3.14)
- **Optional GPU:** NVIDIA GPU with CUDA drivers (automatically detected via PyTorch)

---

## 4. Installation

### 4.1 Python Backend Dependencies

Using Conda (`lcd` or `ai` environment):

```bash
conda activate lcd
pip install fastapi uvicorn pydantic sqlalchemy aiosqlite pillow psutil pytest httpx onnx onnxruntime
```

### 4.2 Desktop Frontend Dependencies

```bash
cd apps/desktop
npm install
npm run build && npm run build:electron
```

---

## 5. Development & Startup

### 5.1 Running Desktop Application (Integrated Mode)

Double-click `scripts\run_desktop.bat` or run:

```bash
scripts\run_desktop.bat
```

### 5.2 Running Backend Standalone (for API Development)

```bash
scripts\run_backend.bat
# or:
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

All 21 automated tests cover:
- Health and system capability endpoints
- Project CRUD, validation, and duplicate conflict checks
- Label creation, updates, and reference protection
- Image Classification and Object Detection annotation workflows
- Hardware detection and vision model catalog
- Classification training lifecycle, worker isolation, and cooperative cancellation
- Real-time interactive model inference (`/jobs/{id}/predict` with local path & base64)
- ONNX model packaging with smoke inference verification
- Recursive dataset image folder scanning and corrupt image handling

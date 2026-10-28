# NOVA AI Trainer — Training Subsystem Architecture

## 1. System Components

```
┌────────────────────────────────────────┐
│         Electron Desktop Shell         │
│  (React 18 + TypeScript + TailwindCSS) │
└───────────────────┬────────────────────┘
                    │ HTTP REST (Loopback)
┌───────────────────▼────────────────────┐
│          FastAPI Backend Server        │
│    (Database, Adapters, Model APIs)    │
└───────────────────┬────────────────────┘
                    │ Subprocess Spawning (Popen)
┌───────────────────▼────────────────────┐
│      Isolated Training Worker          │
│   (PyTorch 2.12 + Torchvision + CUDA)  │
│  - Training Loop & Checkpointing       │
│  - Live Telemetry (metrics.json)       │
│  - Cooperative Cancellation Watcher    │
│  - ONNX Package Exporter               │
└────────────────────────────────────────┘
```

## 2. Process Lifecycle & State Transitions

Training jobs adhere to the following formal status state machine:

```
[QUEUED] ──► [PREPARING] ──► [RUNNING] ──► [COMPLETED]
                  │               │
                  ▼               ▼
               [FAILED]   [CANCEL_REQUESTED] ──► [CANCELLED]
```

* **QUEUED**: Configuration snapshot saved to database.
* **PREPARING**: Dataset scanned, annotations validated, stratified split generated.
* **RUNNING**: Worker process active. Progress streamed via polling/events.
* **COMPLETED**: Epochs finished, best model selected, evaluation generated, ONNX package staged.
* **CANCEL_REQUESTED**: Cancellation flag written to run folder.
* **CANCELLED**: Worker exited cooperatively and saved latest checkpoint.
* **FAILED**: Validation failure or unhandled exception in worker subprocess.

## 3. Concurrency Policy

To avoid memory exhaustion and GPU resource thrashing on desktop systems, NOVA AI Trainer enforces a strict concurrency policy of **maximum 1 running training worker at a time**. Subsequent jobs remain in `QUEUED` status until the active worker finishes or is cancelled.

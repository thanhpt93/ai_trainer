# NOVA AI Trainer — Hardware Compatibility & Acceleration

## 1. Supported Acceleration Platforms

| Hardware Target | Requirement | Acceleration Backend |
| :--- | :--- | :--- |
| **NVIDIA GPU** | NVIDIA Driver + CUDA-enabled PyTorch | PyTorch CUDA Runtime (`torch.cuda`) |
| **CPU (Universal)** | x86_64 / ARM64 Host | Multi-threaded CPU execution (MKL / OpenMP) |

## 2. Hardware Detection API

The desktop shell queries `GET /api/v1/system/hardware` on startup. The API returns:
* `pytorch_version`: Installed PyTorch runtime version.
* `cpu_count_logical`: Available logical processor cores.
* `system_memory_total_gb`: Total system RAM.
* `system_memory_available_gb`: Available system RAM.
* `cuda_available`: Boolean indicating valid GPU initialization.
* `gpu_devices`: List of available GPUs with VRAM capacity, free VRAM, and compute capability.
* `recommended_device`: Recommends `"cuda"` when available, else `"cpu"`.

## 3. Explicit Device Selection

The application never silently switches between GPU and CPU. Users explicitly choose between `Auto (CUDA if available)`, `NVIDIA GPU`, or `CPU Only`.

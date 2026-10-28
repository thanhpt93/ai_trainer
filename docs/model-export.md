# NOVA AI Trainer — Model Export & Deployment Package

## 1. Export Package Structure

Completed classification models are packaged into self-contained directory bundles:

```text
export_package/
├── model.onnx              # Exported ONNX graph
├── model_metadata.json     # Architecture, dimensions, tensor types
├── labels.json             # Ordered class list with stable label IDs
├── preprocessing.json      # Color space, resize rules, mean/std normalization
├── validation_report.json  # Benchmarked accuracy and confusion matrix
└── export_manifest.json    # SHA-256 integrity checksums
```

## 2. Dynamic Batch Dimensions

All classification models exported by NOVA AI Trainer configure dynamic batch axes for inputs and outputs:
```python
dynamic_axes = {
    "input": {0: "batch_size"},
    "output": {0: "batch_size"},
}
```
This enables downstream vision systems to execute batch inference or single-sample real-time inspection without graph reconfiguration.

## 3. Automated Verification via ONNX Runtime

During package generation, the system initiates an `onnxruntime.InferenceSession` on the exported `.onnx` file, performs inference on a synthetic test tensor, and compares output logits with PyTorch:
```python
np.testing.assert_allclose(onnx_logits, torch_logits, rtol=1e-3, atol=1e-4)
```
Packages are only flagged with `verified_with_inference: true` if numerical outputs agree within tolerance.

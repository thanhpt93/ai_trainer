import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.models.detection as detection_models
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor

from backend.app.schemas.model_artifact import (
    ModelCatalogItem,
    ExportModelResponse,
)

# Standard ImageNet normalization used by PyTorch vision models
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


class ModelCatalogService:
    """
    Catalog of supported vision classification and object detection models and
    adapters for building, configuring, loading weights, and exporting to deployment formats like ONNX.
    """

    CATALOG: Dict[str, Dict[str, Any]] = {
        # Classification Models
        "resnet18": {
            "id": "resnet18",
            "name": "ResNet-18",
            "architecture": "resnet18",
            "task_type": "Image Classification",
            "description": "Fast and lightweight 18-layer residual network. Highly recommended for quick iterations and edge deployment.",
            "supported_input_sizes": [128, 224, 256, 384],
            "default_input_size": 224,
            "parameters_count_million": 11.7,
            "pretrained_available": True,
            "supported_devices": ["cpu", "cuda"],
            "default_learning_rate": 0.001,
            "default_batch_size": 16,
            "export_formats": ["ONNX"],
        },
        "mobilenet_v3_small": {
            "id": "mobilenet_v3_small",
            "name": "MobileNetV3-Small",
            "architecture": "mobilenet_v3_small",
            "task_type": "Image Classification",
            "description": "Ultra-lightweight architecture optimized for mobile, CPU, and embedded devices with minimal latency.",
            "supported_input_sizes": [128, 160, 224],
            "default_input_size": 224,
            "parameters_count_million": 2.5,
            "pretrained_available": True,
            "supported_devices": ["cpu", "cuda"],
            "default_learning_rate": 0.002,
            "default_batch_size": 32,
            "export_formats": ["ONNX"],
        },
        "resnet50": {
            "id": "resnet50",
            "name": "ResNet-50",
            "architecture": "resnet50",
            "task_type": "Image Classification",
            "description": "Deeper 50-layer residual architecture providing higher accuracy for complex classification tasks.",
            "supported_input_sizes": [224, 256, 384],
            "default_input_size": 224,
            "parameters_count_million": 25.6,
            "pretrained_available": True,
            "supported_devices": ["cpu", "cuda"],
            "default_learning_rate": 0.0005,
            "default_batch_size": 16,
            "export_formats": ["ONNX"],
        },
        "mobilenet_v3_large": {
            "id": "mobilenet_v3_large",
            "name": "MobileNetV3-Large",
            "architecture": "mobilenet_v3_large",
            "task_type": "Image Classification",
            "description": "Larger MobileNet variant with superior accuracy while maintaining high frame rates.",
            "supported_input_sizes": [160, 224, 256],
            "default_input_size": 224,
            "parameters_count_million": 5.4,
            "pretrained_available": True,
            "supported_devices": ["cpu", "cuda"],
            "default_learning_rate": 0.001,
            "default_batch_size": 32,
            "export_formats": ["ONNX"],
        },
        "efficientnet_b0": {
            "id": "efficientnet_b0",
            "name": "EfficientNet-B0",
            "architecture": "efficientnet_b0",
            "task_type": "Image Classification",
            "description": "Scaled convolutional network with excellent accuracy-to-compute ratio.",
            "supported_input_sizes": [224],
            "default_input_size": 224,
            "parameters_count_million": 5.3,
            "pretrained_available": True,
            "supported_devices": ["cpu", "cuda"],
            "default_learning_rate": 0.001,
            "default_batch_size": 16,
            "export_formats": ["ONNX"],
        },
        # Object Detection Models (Phase 4)
        "fasterrcnn_resnet50_fpn": {
            "id": "fasterrcnn_resnet50_fpn",
            "name": "Faster R-CNN (ResNet-50 FPN)",
            "architecture": "fasterrcnn_resnet50_fpn",
            "task_type": "Object Detection",
            "description": "Two-stage object detector with ResNet-50 Feature Pyramid Network backbone. High localization and detection accuracy.",
            "supported_input_sizes": [600, 800, 1024],
            "default_input_size": 800,
            "parameters_count_million": 41.8,
            "pretrained_available": True,
            "supported_devices": ["cpu", "cuda"],
            "default_learning_rate": 0.0005,
            "default_batch_size": 2,
            "export_formats": ["ONNX"],
        },
        "fasterrcnn_mobilenet_v3_large_320_fpn": {
            "id": "fasterrcnn_mobilenet_v3_large_320_fpn",
            "name": "Faster R-CNN (MobileNetV3-Large 320 FPN)",
            "architecture": "fasterrcnn_mobilenet_v3_large_320_fpn",
            "task_type": "Object Detection",
            "description": "Lightweight Faster R-CNN detector with MobileNetV3 backbone optimized for fast training, lower memory footprint, and edge CPU deployment.",
            "supported_input_sizes": [320, 480, 640],
            "default_input_size": 320,
            "parameters_count_million": 19.4,
            "pretrained_available": True,
            "supported_devices": ["cpu", "cuda"],
            "default_learning_rate": 0.001,
            "default_batch_size": 4,
            "export_formats": ["ONNX"],
        },
    }

    @classmethod
    def list_models(cls, task_type: Optional[str] = None) -> List[ModelCatalogItem]:
        """Return list of supported architectures, optionally filtered by task type."""
        items = []
        for v in cls.CATALOG.values():
            if task_type:
                # Normalize matching
                query_task = task_type.lower().replace("_", " ")
                model_task = v.get("task_type", "").lower().replace("_", " ")
                if query_task not in model_task and model_task not in query_task:
                    continue
            items.append(ModelCatalogItem(**v))
        return items

    @classmethod
    def get_model_info(cls, architecture: str) -> Optional[ModelCatalogItem]:
        info = cls.CATALOG.get(architecture.lower())
        return ModelCatalogItem(**info) if info else None

    @classmethod
    def is_detection_model(cls, architecture: str) -> bool:
        info = cls.CATALOG.get(architecture.lower())
        if info:
            return "Detection" in info.get("task_type", "")
        return "rcnn" in architecture.lower() or "detection" in architecture.lower()

    @classmethod
    def build_model(
        cls,
        architecture: str,
        num_classes: int,
        pretrained: bool = True,
    ) -> nn.Module:
        """
        Instantiate model architecture and customize the final head to match
        the specified number of classes (including background class for detection models).
        """
        arch = architecture.lower()
        if arch not in cls.CATALOG:
            raise ValueError(f"Unsupported model architecture '{architecture}'. Supported: {list(cls.CATALOG.keys())}")

        weights = "DEFAULT" if pretrained else None

        # Classification models
        if arch == "resnet18":
            model = models.resnet18(weights=weights)
            in_features = model.fc.in_features
            model.fc = nn.Linear(in_features, num_classes)
        elif arch == "resnet50":
            model = models.resnet50(weights=weights)
            in_features = model.fc.in_features
            model.fc = nn.Linear(in_features, num_classes)
        elif arch == "mobilenet_v3_small":
            model = models.mobilenet_v3_small(weights=weights)
            in_features = model.classifier[-1].in_features
            model.classifier[-1] = nn.Linear(in_features, num_classes)
        elif arch == "mobilenet_v3_large":
            model = models.mobilenet_v3_large(weights=weights)
            in_features = model.classifier[-1].in_features
            model.classifier[-1] = nn.Linear(in_features, num_classes)
        elif arch == "efficientnet_b0":
            model = models.efficientnet_b0(weights=weights)
            in_features = model.classifier[-1].in_features
            model.classifier[-1] = nn.Linear(in_features, num_classes)

        # Object Detection models
        elif arch == "fasterrcnn_resnet50_fpn":
            model = detection_models.fasterrcnn_resnet50_fpn(weights=weights)
            in_features = model.roi_heads.box_predictor.cls_score.in_features
            model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
        elif arch == "fasterrcnn_mobilenet_v3_large_320_fpn":
            model = detection_models.fasterrcnn_mobilenet_v3_large_320_fpn(weights=weights)
            in_features = model.roi_heads.box_predictor.cls_score.in_features
            model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
        else:
            raise ValueError(f"Architecture '{arch}' not implemented.")

        return model

    @classmethod
    def load_checkpoint(
        cls,
        checkpoint_path: Path,
        architecture: str,
        num_classes: int,
        device: torch.device = torch.device("cpu"),
    ) -> Tuple[nn.Module, Dict[str, Any]]:
        """Load trained weights from a saved checkpoint."""
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint not found at: {checkpoint_path}")

        checkpoint = torch.load(checkpoint_path, map_location=device)
        model = cls.build_model(architecture, num_classes, pretrained=False)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.to(device)
        model.eval()
        return model, checkpoint

    @classmethod
    def export_onnx_package(
        cls,
        model: nn.Module,
        output_dir: Path,
        model_name: str,
        architecture: str,
        class_mapping: List[Dict[str, Any]],
        input_size: int = 224,
        dynamic_batch: bool = True,
        validation_report: Optional[Dict[str, Any]] = None,
    ) -> ExportModelResponse:
        """
        Dispatches export to either classification or object detection pipeline.
        """
        if cls.is_detection_model(architecture):
            return cls.export_detection_onnx_package(
                model=model,
                output_dir=output_dir,
                model_name=model_name,
                architecture=architecture,
                class_mapping=class_mapping,
                input_size=input_size,
                validation_report=validation_report,
            )

        # Classification ONNX Export
        output_dir.mkdir(parents=True, exist_ok=True)
        model.eval()
        model.cpu()

        onnx_filename = "model.onnx"
        onnx_path = output_dir / onnx_filename
        dummy_input = torch.randn(1, 3, input_size, input_size)

        dynamic_axes = (
            {"input": {0: "batch_size"}, "output": {0: "batch_size"}}
            if dynamic_batch
            else None
        )

        try:
            torch.onnx.export(
                model,
                dummy_input,
                str(onnx_path),
                input_names=["input"],
                output_names=["output"],
                dynamic_axes=dynamic_axes,
                opset_version=14,
                dynamo=False,
            )
        except Exception:
            torch.onnx.export(
                model,
                dummy_input,
                str(onnx_path),
                input_names=["input"],
                output_names=["output"],
                dynamic_axes=dynamic_axes,
                opset_version=14,
            )

        verified_inference = False
        try:
            import onnx
            import onnxruntime as ort
            import numpy as np

            onnx_model = onnx.load(str(onnx_path))
            onnx.checker.check_model(onnx_model)

            session = ort.InferenceSession(str(onnx_path))
            ort_inputs = {session.get_inputs()[0].name: dummy_input.numpy()}
            ort_out = session.run(None, ort_inputs)[0]

            with torch.no_grad():
                torch_out = model(dummy_input).numpy()

            np.testing.assert_allclose(ort_out, torch_out, rtol=1e-3, atol=1e-4)
            verified_inference = True
        except Exception:
            pass

        hasher = hashlib.sha256()
        with open(onnx_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        onnx_sha256 = hasher.hexdigest()
        onnx_size = onnx_path.stat().st_size

        labels_json_path = output_dir / "labels.json"
        with open(labels_json_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "class_count": len(class_mapping),
                    "classes": class_mapping,
                },
                f,
                indent=2,
            )

        prep_json_path = output_dir / "preprocessing.json"
        preprocessing_config = {
            "input_size": [input_size, input_size],
            "channels": 3,
            "color_space": "RGB",
            "resize_policy": "bilinear",
            "normalization": {
                "mean": IMAGENET_MEAN,
                "std": IMAGENET_STD,
            },
        }
        with open(prep_json_path, "w", encoding="utf-8") as f:
            json.dump(preprocessing_config, f, indent=2)

        val_json_path = output_dir / "validation_report.json"
        with open(val_json_path, "w", encoding="utf-8") as f:
            json.dump(validation_report or {}, f, indent=2)

        meta_json_path = output_dir / "model_metadata.json"
        metadata_config = {
            "model_name": model_name,
            "task_type": "IMAGE_CLASSIFICATION",
            "architecture": architecture,
            "framework": "PyTorch",
            "export_format": "ONNX",
            "input_tensor": {
                "name": "input",
                "shape": [-1 if dynamic_batch else 1, 3, input_size, input_size],
                "data_type": "float32",
            },
            "output_tensor": {
                "name": "output",
                "shape": [-1 if dynamic_batch else 1, len(class_mapping)],
                "data_type": "float32",
                "semantics": "logits",
            },
            "preprocessing": preprocessing_config,
            "num_classes": len(class_mapping),
            "onnx_sha256": onnx_sha256,
            "schema_version": "1.0.0",
        }
        with open(meta_json_path, "w", encoding="utf-8") as f:
            json.dump(metadata_config, f, indent=2)

        manifest_files = {}
        for p in [onnx_path, labels_json_path, prep_json_path, val_json_path, meta_json_path]:
            h = hashlib.sha256()
            with open(p, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            manifest_files[p.name] = {
                "sha256": h.hexdigest(),
                "size_bytes": p.stat().st_size,
            }

        manifest_path = output_dir / "export_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "package_name": model_name,
                    "exported_files": manifest_files,
                    "verified_with_inference": verified_inference,
                },
                f,
                indent=2,
            )

        return ExportModelResponse(
            success=True,
            artifact_id=model_name,
            model_name=model_name,
            export_dir=str(output_dir),
            onnx_file_path=str(onnx_path),
            manifest_path=str(manifest_path),
            metadata_path=str(meta_json_path),
            checksum_sha256=onnx_sha256,
            file_size_bytes=onnx_size,
            verified_with_inference=verified_inference,
        )

    @classmethod
    def export_detection_onnx_package(
        cls,
        model: nn.Module,
        output_dir: Path,
        model_name: str,
        architecture: str,
        class_mapping: List[Dict[str, Any]],
        input_size: int = 800,
        validation_report: Optional[Dict[str, Any]] = None,
    ) -> ExportModelResponse:
        """
        Exports the Faster R-CNN detection model to a validated self-contained ONNX deployment package.
        Validates package with onnx checker and performs smoke inference with onnxruntime.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        model.eval()
        model.cpu()

        onnx_filename = "model.onnx"
        onnx_path = output_dir / onnx_filename

        # Torchvision Faster R-CNN in eval mode accepts a list of images [Tensor(3, H, W)]
        dummy_tensor = torch.randn(3, input_size, input_size)

        try:
            torch.onnx.export(
                model,
                ([dummy_tensor],),
                str(onnx_path),
                input_names=["images"],
                output_names=["boxes", "labels", "scores"],
                dynamic_axes={
                    "images": {0: "channels", 1: "height", 2: "width"},
                    "boxes": {0: "num_detections"},
                    "labels": {0: "num_detections"},
                    "scores": {0: "num_detections"},
                },
                opset_version=14,
                dynamo=False,
            )
        except Exception:
            torch.onnx.export(
                model,
                ([dummy_tensor],),
                str(onnx_path),
                input_names=["images"],
                output_names=["boxes", "labels", "scores"],
                opset_version=14,
            )

        # Smoke inference verification with onnxruntime
        verified_inference = False
        try:
            import onnx
            import onnxruntime as ort
            import numpy as np

            onnx_model = onnx.load(str(onnx_path))
            onnx.checker.check_model(onnx_model)

            session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
            ort_inputs = {session.get_inputs()[0].name: dummy_tensor.numpy()}
            ort_out = session.run(None, ort_inputs)

            # ort_out contains [boxes (N, 4), labels (N,), scores (N,)]
            assert len(ort_out) == 3
            verified_inference = True
        except Exception as e:
            print(f"[DetectionExport] Smoke inference warning: {e}")

        # Checksum & file size
        hasher = hashlib.sha256()
        with open(onnx_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        onnx_sha256 = hasher.hexdigest()
        onnx_size = onnx_path.stat().st_size

        # 1. labels.json
        labels_json_path = output_dir / "labels.json"
        foreground_classes = [c for c in class_mapping if not c.get("is_background", False)]
        with open(labels_json_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "class_count": len(foreground_classes),
                    "total_classes_with_background": len(class_mapping),
                    "classes": class_mapping,
                    "background_class": {
                        "index": 0,
                        "name": "__background__",
                    },
                },
                f,
                indent=2,
            )

        # 2. preprocessing.json
        prep_json_path = output_dir / "preprocessing.json"
        preprocessing_config = {
            "input_size": [input_size, input_size],
            "channels": 3,
            "color_space": "RGB",
            "resize_policy": "bilinear",
            "normalization": {
                "mean": IMAGENET_MEAN,
                "std": IMAGENET_STD,
            },
            "coordinate_system": "pixel_xyxy",
        }
        with open(prep_json_path, "w", encoding="utf-8") as f:
            json.dump(preprocessing_config, f, indent=2)

        # 3. postprocessing.json
        post_json_path = output_dir / "postprocessing.json"
        postprocessing_config = {
            "coordinate_format": "xyxy",
            "confidence_threshold": 0.5,
            "iou_threshold": 0.5,
            "max_detections": 100,
            "background_class_index": 0,
            "output_semantics": {
                "boxes": "Predicted bounding boxes in [x1, y1, x2, y2] image coordinates",
                "labels": "Predicted class indices (1..N correspond to user labels)",
                "scores": "Prediction confidence values in range [0, 1]",
            },
        }
        with open(post_json_path, "w", encoding="utf-8") as f:
            json.dump(postprocessing_config, f, indent=2)

        # 4. validation_report.json
        val_json_path = output_dir / "validation_report.json"
        with open(val_json_path, "w", encoding="utf-8") as f:
            json.dump(validation_report or {}, f, indent=2)

        # 5. model_metadata.json
        meta_json_path = output_dir / "model_metadata.json"
        metadata_config = {
            "model_name": model_name,
            "task_type": "OBJECT_DETECTION",
            "architecture": architecture,
            "framework": "PyTorch",
            "export_format": "ONNX",
            "input_tensor": {
                "name": "images",
                "shape": [3, input_size, input_size],
                "data_type": "float32",
            },
            "output_tensors": [
                {
                    "name": "boxes",
                    "shape": [-1, 4],
                    "data_type": "float32",
                    "semantics": "bounding_boxes_xyxy",
                },
                {
                    "name": "labels",
                    "shape": [-1],
                    "data_type": "int64",
                    "semantics": "class_indices",
                },
                {
                    "name": "scores",
                    "shape": [-1],
                    "data_type": "float32",
                    "semantics": "confidence_scores",
                },
            ],
            "preprocessing": preprocessing_config,
            "postprocessing": postprocessing_config,
            "num_classes": len(class_mapping),
            "onnx_sha256": onnx_sha256,
            "schema_version": "1.0.0",
        }
        with open(meta_json_path, "w", encoding="utf-8") as f:
            json.dump(metadata_config, f, indent=2)

        # 6. export_manifest.json
        manifest_files = {}
        for p in [onnx_path, labels_json_path, prep_json_path, post_json_path, val_json_path, meta_json_path]:
            h = hashlib.sha256()
            with open(p, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            manifest_files[p.name] = {
                "sha256": h.hexdigest(),
                "size_bytes": p.stat().st_size,
            }

        manifest_path = output_dir / "export_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "package_name": model_name,
                    "task_type": "OBJECT_DETECTION",
                    "exported_files": manifest_files,
                    "verified_with_inference": verified_inference,
                },
                f,
                indent=2,
            )

        return ExportModelResponse(
            success=True,
            artifact_id=model_name,
            model_name=model_name,
            export_dir=str(output_dir),
            onnx_file_path=str(onnx_path),
            manifest_path=str(manifest_path),
            metadata_path=str(meta_json_path),
            checksum_sha256=onnx_sha256,
            file_size_bytes=onnx_size,
            verified_with_inference=verified_inference,
        )

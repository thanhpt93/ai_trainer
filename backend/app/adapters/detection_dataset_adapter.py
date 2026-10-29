import os
import random
import math
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from PIL import Image
import torch
from torch.utils.data import Dataset as TorchDataset
import torchvision.transforms.functional as TF
from sqlalchemy.orm import Session

from backend.app.domain.models import (
    Project,
    Dataset,
    ImageRecord,
    ProjectLabel,
    ImageAnnotation,
    ObjectAnnotation,
)
from backend.app.schemas.training_job import (
    SplitConfig,
    ClassItem,
    DatasetValidationResponse,
)

# Standard ImageNet normalization used by PyTorch vision models
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def clamp(val: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    return max(min_val, min(val, max_val))


def validate_and_convert_box(
    x_min: float,
    y_min: float,
    x_max: float,
    y_max: float,
    img_width: int,
    img_height: int,
    clamp_tolerance: float = 0.05,
) -> Optional[List[float]]:
    """
    Validates normalized coordinates [0, 1], checks for positive area,
    clamps small boundary overflows within tolerance, and converts to
    absolute pixel coordinates [x1, y1, x2, y2].

    Returns [x1, y1, x2, y2] in pixels if valid, or None if malformed/zero-area.
    """
    if img_width <= 0 or img_height <= 0:
        return None

    # Check for NaN or Inf
    for v in (x_min, y_min, x_max, y_max):
        if math.isnan(v) or math.isinf(v):
            return None

    # Clamp with tolerance
    if -clamp_tolerance <= x_min < 0.0:
        x_min = 0.0
    if -clamp_tolerance <= y_min < 0.0:
        y_min = 0.0
    if 1.0 < x_max <= 1.0 + clamp_tolerance:
        x_max = 1.0
    if 1.0 < y_max <= 1.0 + clamp_tolerance:
        y_max = 1.0

    x_min = clamp(x_min, 0.0, 1.0)
    y_min = clamp(y_min, 0.0, 1.0)
    x_max = clamp(x_max, 0.0, 1.0)
    y_max = clamp(y_max, 0.0, 1.0)

    # Positive area check in normalized space
    if x_max <= x_min or y_max <= y_min:
        return None

    # Convert to pixel space
    x1 = float(x_min * img_width)
    y1 = float(y_min * img_height)
    x2 = float(x_max * img_width)
    y2 = float(y_max * img_height)

    # Ensure minimum 1px dimension
    if (x2 - x1) < 0.5 or (y2 - y1) < 0.5:
        return None

    return [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)]


def transform_box_resize(
    box: List[float],
    orig_w: int,
    orig_h: int,
    new_w: int,
    new_h: int,
) -> List[float]:
    """
    Scales pixel bounding box [x1, y1, x2, y2] according to image resize (orig_w, orig_h) -> (new_w, new_h).
    """
    scale_x = float(new_w) / float(orig_w)
    scale_y = float(new_h) / float(orig_h)
    x1 = box[0] * scale_x
    y1 = box[1] * scale_y
    x2 = box[2] * scale_x
    y2 = box[3] * scale_y
    return [max(0.0, x1), max(0.0, y1), min(float(new_w), x2), min(float(new_h), y2)]


def transform_box_hflip(box: List[float], width: int) -> List[float]:
    """
    Horizontally flips pixel bounding box [x1, y1, x2, y2] for image of given width.
    """
    x1, y1, x2, y2 = box
    new_x1 = float(width) - x2
    new_x2 = float(width) - x1
    return [max(0.0, new_x1), y1, min(float(width), new_x2), y2]


def detection_collate_fn(batch):
    """Custom collator for detection batches of variable box count."""
    return tuple(zip(*batch))


class DetectionTorchDataset(TorchDataset):
    """
    PyTorch Dataset for Object Detection with Faster R-CNN target contract.
    Synchronizes image transformations and bounding box coordinate adjustments.
    """

    def __init__(
        self,
        samples: List[Dict[str, Any]],
        input_size: int = 800,
        is_train: bool = True,
        horizontal_flip: bool = True,
    ):
        self.samples = samples
        self.input_size = input_size
        self.is_train = is_train
        self.horizontal_flip = horizontal_flip and is_train

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        sample = self.samples[idx]
        img_path = sample["path"]
        orig_w = sample.get("width", 800)
        orig_h = sample.get("height", 600)

        # 1. Load image in RGB
        img = Image.open(img_path).convert("RGB")
        cur_w, cur_h = img.size

        # Raw pixel boxes
        boxes = [list(b) for b in sample.get("boxes", [])]
        labels = list(sample.get("labels", []))

        # 2. Resize image and scale boxes
        target_size = (self.input_size, self.input_size)
        img_resized = img.resize(target_size, Image.Resampling.BILINEAR)

        scaled_boxes = []
        valid_labels = []
        for b, l in zip(boxes, labels):
            sb = transform_box_resize(b, cur_w, cur_h, self.input_size, self.input_size)
            # Ensure box remains valid
            if sb[2] > sb[0] and sb[3] > sb[1]:
                scaled_boxes.append(sb)
                valid_labels.append(l)

        # 3. Optional horizontal flip during training
        if self.horizontal_flip and random.random() > 0.5:
            img_resized = TF.hflip(img_resized)
            flipped_boxes = []
            for b in scaled_boxes:
                fb = transform_box_hflip(b, self.input_size)
                if fb[2] > fb[0] and fb[3] > fb[1]:
                    flipped_boxes.append(fb)
            scaled_boxes = flipped_boxes

        # 4. Convert image to Tensor & normalize
        tensor = TF.to_tensor(img_resized)
        tensor = TF.normalize(tensor, mean=IMAGENET_MEAN, std=IMAGENET_STD)

        # 5. Build target dictionary
        if scaled_boxes:
            boxes_tensor = torch.as_tensor(scaled_boxes, dtype=torch.float32).reshape(-1, 4)
            labels_tensor = torch.as_tensor(valid_labels, dtype=torch.int64)
            area_tensor = (boxes_tensor[:, 2] - boxes_tensor[:, 0]) * (boxes_tensor[:, 3] - boxes_tensor[:, 1])
            iscrowd_tensor = torch.zeros((len(scaled_boxes),), dtype=torch.int64)
        else:
            boxes_tensor = torch.zeros((0, 4), dtype=torch.float32)
            labels_tensor = torch.zeros((0,), dtype=torch.int64)
            area_tensor = torch.zeros((0,), dtype=torch.float32)
            iscrowd_tensor = torch.zeros((0,), dtype=torch.int64)

        target = {
            "boxes": boxes_tensor,
            "labels": labels_tensor,
            "image_id": torch.tensor([idx], dtype=torch.int64),
            "area": area_tensor,
            "iscrowd": iscrowd_tensor,
        }

        return tensor, target


class DetectionDatasetAdapter:
    """
    Adapter that bridges Phase 2 database object annotations and image files
    into a structured, reproducible, class-balanced dataset manifest for PyTorch detection.
    """

    @classmethod
    def validate_and_prepare_dataset(
        cls,
        db: Session,
        project_id: str,
        dataset_id: str,
        split_config: SplitConfig,
    ) -> Tuple[DatasetValidationResponse, Optional[Dict[str, Any]]]:
        """
        Validates the dataset annotations, image files, dimensions, and bounding boxes.
        Returns a detailed validation report and a reproducible split manifest dict.
        """
        errors: List[str] = []
        warnings: List[str] = []

        # 1. Project checks
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return DatasetValidationResponse(
                is_valid=False,
                project_id=project_id,
                dataset_id=dataset_id,
                task_type="Object Detection",
                total_images=0,
                valid_annotated_images=0,
                unannotated_images=0,
                invalid_annotations=0,
                negative_images=0,
                missing_files=0,
                classes=[],
                class_imbalance_warning=False,
                train_count=0,
                val_count=0,
                test_count=0,
                total_bounding_boxes=0,
                boxes_per_class={},
                images_per_class={},
                errors=[f"Project with ID '{project_id}' not found."],
                warnings=[],
            ), None

        if "Detection" not in project.task_type:
            errors.append(
                f"Project task type is '{project.task_type}', but Object Detection training requires an 'Object Detection' project."
            )

        # 2. Dataset checks
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            errors.append(f"Dataset with ID '{dataset_id}' not found.")
            return DatasetValidationResponse(
                is_valid=False,
                project_id=project_id,
                dataset_id=dataset_id,
                task_type="Object Detection",
                total_images=0,
                valid_annotated_images=0,
                unannotated_images=0,
                invalid_annotations=0,
                negative_images=0,
                missing_files=0,
                classes=[],
                class_imbalance_warning=False,
                train_count=0,
                val_count=0,
                test_count=0,
                total_bounding_boxes=0,
                boxes_per_class={},
                images_per_class={},
                errors=errors,
                warnings=warnings,
            ), None

        if dataset.project_id != project_id:
            errors.append(f"Dataset '{dataset.name}' does not belong to project '{project.name}'.")

        # 3. Project Labels
        labels = (
            db.query(ProjectLabel)
            .filter(ProjectLabel.project_id == project_id)
            .order_by(ProjectLabel.name.asc())
            .all()
        )
        if len(labels) < 1:
            errors.append(f"Project requires at least 1 object class for detection training, found {len(labels)}.")

        label_map: Dict[str, ProjectLabel] = {l.id: l for l in labels}

        # Build stable class mapping:
        # Index 0 is background for Faster R-CNN/Torchvision detection models.
        # Foreground classes start at index 1.
        class_mapping: List[Dict[str, Any]] = [
            {
                "index": 0,
                "label_id": "__background__",
                "name": "__background__",
                "color": "#64748b",
                "is_background": True,
            }
        ]
        label_id_to_index: Dict[str, int] = {}
        index_to_name: Dict[int, str] = {0: "__background__"}

        for idx, lbl in enumerate(labels, start=1):
            class_mapping.append({
                "index": idx,
                "label_id": lbl.id,
                "name": lbl.name,
                "color": lbl.color,
                "is_background": False,
            })
            label_id_to_index[lbl.id] = idx
            index_to_name[idx] = lbl.name

        # 4. Image Records & Annotations
        image_records = db.query(ImageRecord).filter(ImageRecord.dataset_id == dataset_id).all()
        total_images = len(image_records)
        if total_images == 0:
            errors.append("Dataset has no indexed images.")

        missing_files_count = 0
        unannotated_count = 0
        invalid_count = 0
        negative_count = 0
        total_boxes_count = 0

        boxes_per_class: Dict[str, int] = {lbl.name: 0 for lbl in labels}
        images_per_class: Dict[str, int] = {lbl.name: 0 for lbl in labels}

        valid_samples: List[Dict[str, Any]] = []

        for img in image_records:
            img_path = Path(img.absolute_path)
            if not img_path.exists() or not img_path.is_file():
                missing_files_count += 1
                continue

            # Determine dimensions
            w, h = img.width, img.height
            if not w or not h:
                try:
                    with Image.open(img_path) as p_img:
                        w, h = p_img.size
                except Exception:
                    invalid_count += 1
                    warnings.append(f"Cannot read image dimensions for '{img.relative_path}'.")
                    continue

            ann = db.query(ImageAnnotation).filter(ImageAnnotation.image_id == img.id).first()
            if not ann:
                unannotated_count += 1
                continue

            if ann.status == "INVALID":
                invalid_count += 1
                continue

            # Explicit negative image (contains 0 target objects)
            if ann.is_negative:
                negative_count += 1
                valid_samples.append({
                    "image_id": img.id,
                    "relative_path": img.relative_path,
                    "path": str(img_path),
                    "width": w,
                    "height": h,
                    "boxes": [],
                    "labels": [],
                    "is_negative": True,
                })
                continue

            if ann.status == "UNANNOTATED":
                unannotated_count += 1
                continue

            # Fetch object bounding boxes
            obj_anns = (
                db.query(ObjectAnnotation)
                .filter(ObjectAnnotation.image_annotation_id == ann.id)
                .all()
            )

            if not obj_anns:
                # If annotated status but no boxes and not negative, treat as unannotated
                unannotated_count += 1
                continue

            img_boxes: List[List[float]] = []
            img_labels: List[int] = []
            seen_classes_in_img = set()

            for obj in obj_anns:
                if obj.label_id not in label_id_to_index:
                    invalid_count += 1
                    warnings.append(f"Image '{img.relative_path}' has annotation referencing unknown label ID '{obj.label_id}'.")
                    continue

                c_idx = label_id_to_index[obj.label_id]
                c_name = index_to_name[c_idx]

                # Validate and convert box
                pix_box = validate_and_convert_box(
                    x_min=obj.x_min,
                    y_min=obj.y_min,
                    x_max=obj.x_max,
                    y_max=obj.y_max,
                    img_width=w,
                    img_height=h,
                )

                if pix_box is None:
                    invalid_count += 1
                    warnings.append(f"Image '{img.relative_path}' contains zero-area or out-of-bounds box [{obj.x_min:.3f}, {obj.y_min:.3f}, {obj.x_max:.3f}, {obj.y_max:.3f}]; box excluded.")
                    continue

                img_boxes.append(pix_box)
                img_labels.append(c_idx)
                boxes_per_class[c_name] += 1
                seen_classes_in_img.add(c_name)
                total_boxes_count += 1

            for c_name in seen_classes_in_img:
                images_per_class[c_name] += 1

            if img_boxes:
                valid_samples.append({
                    "image_id": img.id,
                    "relative_path": img.relative_path,
                    "path": str(img_path),
                    "width": w,
                    "height": h,
                    "boxes": img_boxes,
                    "labels": img_labels,
                    "is_negative": False,
                })
            else:
                invalid_count += 1

        valid_annotated_count = len(valid_samples)

        # 5. Class balance check
        class_items: List[ClassItem] = []
        for lbl in labels:
            c_count = boxes_per_class.get(lbl.name, 0)
            class_items.append(
                ClassItem(
                    index=label_id_to_index[lbl.id],
                    label_id=lbl.id,
                    name=lbl.name,
                    color=lbl.color,
                    count=c_count,
                )
            )

        counts = [item.count for item in class_items if item.count > 0]
        class_imbalance = False
        if len(counts) > 1:
            ratio = max(counts) / (min(counts) + 1e-5)
            if ratio > 5.0:
                class_imbalance = True
                warnings.append(f"Severe class imbalance detected: max class has {max(counts)} boxes while min has {min(counts)}.")

        for item in class_items:
            if item.count == 0:
                warnings.append(f"Class '{item.name}' has 0 valid bounding box annotations.")

        # 6. Check dataset size
        if valid_annotated_count == 0:
            errors.append("Dataset has no valid annotated images or negative images for detection training.")

        # Minimum images check
        min_required = 3
        if valid_annotated_count > 0 and valid_annotated_count < min_required:
            errors.append(f"Object Detection requires at least {min_required} valid annotated images, found {valid_annotated_count}.")

        # 7. Split generation
        train_samples: List[Dict[str, Any]] = []
        val_samples: List[Dict[str, Any]] = []
        test_samples: List[Dict[str, Any]] = []

        if not errors and valid_annotated_count > 0:
            # Deterministic reproducible random shuffle
            rng = random.Random(split_config.random_seed)
            shuffled = list(valid_samples)
            # Sort by image_id first for reproducibility across environments
            shuffled.sort(key=lambda s: s["image_id"])
            rng.shuffle(shuffled)

            n_total = len(shuffled)
            val_ratio = split_config.val_ratio
            test_ratio = split_config.test_ratio
            train_ratio = split_config.train_ratio

            # Normalize ratios
            sum_ratios = train_ratio + val_ratio + test_ratio
            if sum_ratios > 0:
                train_ratio /= sum_ratios
                val_ratio /= sum_ratios
                test_ratio /= sum_ratios

            n_val = max(1, int(round(n_total * val_ratio))) if val_ratio > 0 and n_total >= 2 else 0
            n_test = int(round(n_total * test_ratio)) if test_ratio > 0 and (n_total - n_val) >= 2 else 0
            n_train = n_total - n_val - n_test

            if n_train <= 0:
                n_train = max(1, n_total - 1)
                n_val = n_total - n_train
                n_test = 0

            train_samples = shuffled[:n_train]
            val_samples = shuffled[n_train : n_train + n_val]
            test_samples = shuffled[n_train + n_val :]

            # Check if classes are represented in train and val splits
            train_classes = set()
            for s in train_samples:
                for l in s.get("labels", []):
                    train_classes.add(l)

            val_classes = set()
            for s in val_samples:
                for l in s.get("labels", []):
                    val_classes.add(l)

            for lbl in labels:
                c_idx = label_id_to_index[lbl.id]
                if boxes_per_class.get(lbl.name, 0) > 0:
                    if c_idx not in train_classes:
                        warnings.append(f"Class '{lbl.name}' has no bounding boxes in the training split.")
                    if n_val > 0 and c_idx not in val_classes:
                        warnings.append(f"Class '{lbl.name}' is absent from the validation split.")

        is_valid = len(errors) == 0

        manifest = None
        if is_valid:
            manifest = {
                "manifest_version": "1.0",
                "task_type": "Object Detection",
                "project_id": project_id,
                "dataset_id": dataset_id,
                "split_config": split_config.model_dump(),
                "class_mapping": class_mapping,
                "total_images": valid_annotated_count,
                "total_bounding_boxes": total_boxes_count,
                "splits": {
                    "train": train_samples,
                    "val": val_samples,
                    "test": test_samples,
                },
            }

        response = DatasetValidationResponse(
            is_valid=is_valid,
            project_id=project_id,
            dataset_id=dataset_id,
            task_type="Object Detection",
            total_images=total_images,
            valid_annotated_images=valid_annotated_count,
            unannotated_images=unannotated_count,
            invalid_annotations=invalid_count,
            negative_images=negative_count,
            missing_files=missing_files_count,
            classes=class_items,
            class_imbalance_warning=class_imbalance,
            train_count=len(train_samples),
            val_count=len(val_samples),
            test_count=len(test_samples),
            total_bounding_boxes=total_boxes_count,
            boxes_per_class=boxes_per_class,
            images_per_class=images_per_class,
            split_manifest_id=dataset_id if is_valid else None,
            errors=errors,
            warnings=warnings,
        )

        return response, manifest

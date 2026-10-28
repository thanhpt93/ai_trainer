import os
import random
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from PIL import Image
from sqlalchemy.orm import Session

from backend.app.domain.models import (
    Project,
    Dataset,
    ImageRecord,
    ProjectLabel,
    ImageAnnotation,
    ClassificationAnnotation,
)
from backend.app.schemas.training_job import (
    SplitConfig,
    ClassItem,
    DatasetValidationResponse,
)


class ClassificationDatasetAdapter:
    """
    Adapter that bridges Phase 2 database annotations and image files
    into a structured, reproducible, stratified dataset manifest for PyTorch training.
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
        Performs thorough validation on the dataset and annotations.
        If valid, also returns the dataset split manifest dictionary.
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
                errors=[f"Project with ID '{project_id}' not found."],
                warnings=[],
            ), None

        if "Classification" not in project.task_type:
            errors.append(
                f"Project task type is '{project.task_type}', but Image Classification training requires an 'Image Classification' project."
            )

        # 2. Dataset checks
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            errors.append(f"Dataset with ID '{dataset_id}' not found.")
            return DatasetValidationResponse(
                is_valid=False,
                project_id=project_id,
                dataset_id=dataset_id,
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
                errors=errors,
                warnings=warnings,
            ), None

        if dataset.project_id != project_id:
            errors.append(f"Dataset '{dataset.name}' does not belong to project '{project.name}'.")

        # 3. Project Labels
        labels = db.query(ProjectLabel).filter(ProjectLabel.project_id == project_id).order_by(ProjectLabel.name.asc()).all()
        if len(labels) < 2:
            errors.append(f"Project requires at least 2 distinct classes for classification training, found {len(labels)}.")

        label_map: Dict[str, ProjectLabel] = {l.id: l for l in labels}

        # 4. Image Records & Annotations
        image_records = db.query(ImageRecord).filter(ImageRecord.dataset_id == dataset_id).all()
        total_images = len(image_records)
        if total_images == 0:
            errors.append("Dataset has no indexed images.")

        missing_files_count = 0
        unannotated_count = 0
        invalid_count = 0
        negative_count = 0

        # Map: label_id -> list of valid sample dicts
        class_samples: Dict[str, List[Dict[str, Any]]] = {l.id: [] for l in labels}
        valid_annotated_samples: List[Dict[str, Any]] = []

        for img in image_records:
            # Check file existence
            img_path = Path(img.absolute_path)
            if not img_path.exists() or not img_path.is_file():
                missing_files_count += 1
                continue

            ann = db.query(ImageAnnotation).filter(ImageAnnotation.image_id == img.id).first()
            if not ann or ann.status == "UNANNOTATED":
                unannotated_count += 1
                continue

            if ann.status == "INVALID":
                invalid_count += 1
                continue

            if ann.is_negative:
                negative_count += 1
                # Negative images contain no target classes; for standard single-label classification
                # we exclude negative images from class mapping unless an explicit background class is set
                continue

            cls_anns = db.query(ClassificationAnnotation).filter(ClassificationAnnotation.image_annotation_id == ann.id).all()
            if not cls_anns:
                unannotated_count += 1
                continue

            # Check single-label constraint
            if not project.is_multi_label and len(cls_anns) > 1:
                invalid_count += 1
                warnings.append(f"Image '{img.relative_path}' has {len(cls_anns)} labels in single-label mode; excluded from training.")
                continue

            assigned_label_id = cls_anns[0].label_id
            if assigned_label_id not in label_map:
                invalid_count += 1
                continue

            sample_entry = {
                "image_id": img.id,
                "relative_path": img.relative_path,
                "absolute_path": img.absolute_path,
                "label_id": assigned_label_id,
                "label_name": label_map[assigned_label_id].name,
            }
            class_samples[assigned_label_id].append(sample_entry)
            valid_annotated_samples.append(sample_entry)

        # 5. Class Distribution & Imbalance
        classes_summary: List[ClassItem] = []
        counts: List[int] = []

        for idx, lbl in enumerate(labels):
            c_count = len(class_samples[lbl.id])
            counts.append(c_count)
            classes_summary.append(
                ClassItem(
                    index=idx,
                    label_id=lbl.id,
                    name=lbl.name,
                    color=lbl.color,
                    count=c_count,
                )
            )
            if c_count < 2:
                errors.append(
                    f"Class '{lbl.name}' has only {c_count} annotated sample(s). Each class must have at least 2 samples to allow train/val split."
                )

        class_imbalance = False
        valid_counts = [c for c in counts if c > 0]
        if valid_counts:
            min_c = min(valid_counts)
            max_c = max(valid_counts)
            if min_c > 0 and (max_c / min_c) > 5.0:
                class_imbalance = True
                warnings.append(
                    f"Detected significant class imbalance: smallest class has {min_c} samples, largest has {max_c} samples."
                )

        if missing_files_count > 0:
            warnings.append(f"{missing_files_count} image file(s) are missing from the filesystem.")

        if unannotated_count > 0:
            warnings.append(f"{unannotated_count} image(s) are unannotated and excluded from training.")

        # 6. Generate Split Manifest if no critical errors
        train_samples: List[Dict[str, Any]] = []
        val_samples: List[Dict[str, Any]] = []
        test_samples: List[Dict[str, Any]] = []
        manifest_dict: Optional[Dict[str, Any]] = None

        is_valid = len(errors) == 0 and len(valid_annotated_samples) >= 4

        if is_valid:
            rng = random.Random(split_config.random_seed)

            # Stratified split per class
            for lbl in labels:
                s_list = list(class_samples[lbl.id])
                rng.shuffle(s_list)
                n = len(s_list)

                # Ensure at least 1 train and 1 val if n >= 2
                n_val = max(1, int(round(n * split_config.val_ratio)))
                n_test = int(round(n * split_config.test_ratio)) if split_config.test_ratio > 0.0 else 0

                # Ensure train has at least 1
                if n - n_val - n_test < 1:
                    if n_test > 0:
                        n_test = 0
                    if n - n_val < 1:
                        n_val = 1

                n_train = n - n_val - n_test

                class_train = s_list[:n_train]
                class_val = s_list[n_train : n_train + n_val]
                class_test = s_list[n_train + n_val :]

                train_samples.extend(class_train)
                val_samples.extend(class_val)
                test_samples.extend(class_test)

            # Shuffle combined splits deterministically
            rng.shuffle(train_samples)
            rng.shuffle(val_samples)
            rng.shuffle(test_samples)

            manifest_dict = {
                "project_id": project_id,
                "dataset_id": dataset_id,
                "random_seed": split_config.random_seed,
                "stratified": split_config.stratified,
                "class_mapping": [
                    {
                        "index": idx,
                        "label_id": lbl.id,
                        "name": lbl.name,
                        "color": lbl.color,
                    }
                    for idx, lbl in enumerate(labels)
                ],
                "splits": {
                    "train": train_samples,
                    "val": val_samples,
                    "test": test_samples,
                },
                "total_valid": len(valid_annotated_samples),
                "counts": {
                    "train": len(train_samples),
                    "val": len(val_samples),
                    "test": len(test_samples),
                },
            }

        response = DatasetValidationResponse(
            is_valid=is_valid,
            project_id=project_id,
            dataset_id=dataset_id,
            total_images=total_images,
            valid_annotated_images=len(valid_annotated_samples),
            unannotated_images=unannotated_count,
            invalid_annotations=invalid_count,
            negative_images=negative_count,
            missing_files=missing_files_count,
            classes=classes_summary,
            class_imbalance_warning=class_imbalance,
            train_count=len(train_samples),
            val_count=len(val_samples),
            test_count=len(test_samples),
            errors=errors,
            warnings=warnings,
        )

        return response, manifest_dict

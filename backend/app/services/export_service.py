import os
import csv
import json
from pathlib import Path
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.core.config import settings
from backend.app.domain.models import (
    Dataset,
    Project,
    ImageRecord,
    ProjectLabel,
    ImageAnnotation,
    ClassificationAnnotation,
    ObjectAnnotation,
)
from backend.app.schemas.annotation import ExportFormat, ExportRequest, ExportResponse
from backend.app.services.dataset_service import DatasetService


class ExportService:
    """Service to export dataset annotations into standard machine vision formats."""

    @classmethod
    def export_dataset(cls, db: Session, dataset_id: str, req: ExportRequest) -> ExportResponse:
        dataset = DatasetService.get_dataset_by_id(db, dataset_id)
        project = db.query(Project).filter(Project.id == dataset.project_id).first()

        # Determine target export directory
        if req.output_dir and req.output_dir.strip():
            export_dir = Path(req.output_dir.strip()).resolve()
        else:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            export_dir = settings.APP_DATA_DIR / "exports" / f"{dataset.name}_{req.format.value}_{timestamp}"

        export_dir.mkdir(parents=True, exist_ok=True)

        # Retrieve project labels for stable indexing
        labels = (
            db.query(ProjectLabel)
            .filter(ProjectLabel.project_id == project.id)
            .order_by(ProjectLabel.created_at.asc())
            .all()
        )
        label_id_to_idx = {lbl.id: i for i, lbl in enumerate(labels)}
        label_id_to_name = {lbl.id: lbl.name for lbl in labels}

        # Retrieve images and annotations
        images = (
            db.query(ImageRecord)
            .filter(ImageRecord.dataset_id == dataset_id)
            .order_by(ImageRecord.relative_path.asc())
            .all()
        )

        total_exported = 0

        if req.format == ExportFormat.YOLO:
            total_exported = cls._export_yolo(db, dataset, images, labels, label_id_to_idx, export_dir, req.include_unannotated)
        elif req.format == ExportFormat.COCO:
            total_exported = cls._export_coco(db, dataset, images, labels, label_id_to_idx, label_id_to_name, export_dir, req.include_unannotated)
        elif req.format == ExportFormat.PASCAL_VOC:
            total_exported = cls._export_pascal_voc(db, dataset, images, label_id_to_name, export_dir, req.include_unannotated)
        elif req.format == ExportFormat.CSV:
            total_exported = cls._export_csv(db, images, label_id_to_name, export_dir, req.include_unannotated)
        elif req.format == ExportFormat.JSON:
            total_exported = cls._export_json(db, images, label_id_to_name, export_dir, req.include_unannotated)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported export format: {req.format}",
            )

        return ExportResponse(
            export_path=str(export_dir),
            format=req.format.value,
            total_exported=total_exported,
            message=f"Successfully exported {total_exported} image annotations in {req.format.value.upper()} format to {export_dir}",
        )

    @classmethod
    def _export_yolo(
        cls,
        db: Session,
        dataset: Dataset,
        images: list,
        labels: list,
        label_id_to_idx: dict,
        export_dir: Path,
        include_unannotated: bool,
    ) -> int:
        labels_dir = export_dir / "labels"
        labels_dir.mkdir(parents=True, exist_ok=True)

        exported_count = 0

        for img in images:
            ann = db.query(ImageAnnotation).filter(ImageAnnotation.image_id == img.id).first()
            if not ann and not include_unannotated:
                continue

            txt_name = f"{Path(img.relative_path).stem}.txt"
            txt_path = labels_dir / txt_name

            lines = []
            if ann and not ann.is_negative:
                for obj in ann.objects:
                    if obj.label_id in label_id_to_idx:
                        cls_idx = label_id_to_idx[obj.label_id]
                        # Convert [x_min, y_min, x_max, y_max] to YOLO [x_center, y_center, width, height]
                        w = obj.x_max - obj.x_min
                        h = obj.y_max - obj.y_min
                        xc = obj.x_min + (w / 2.0)
                        yc = obj.y_min + (h / 2.0)
                        lines.append(f"{cls_idx} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}")

            # Write text file (empty file for negative images, as per YOLO convention)
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            exported_count += 1

        # Write data.yaml directly
        yaml_lines = [
            f"path: \"{dataset.root_path}\"",
            "train: images",
            "val: images",
            f"nc: {len(labels)}",
            "names:",
        ]
        for i, lbl in enumerate(labels):
            yaml_lines.append(f"  {i}: \"{lbl.name}\"")

        with open(export_dir / "data.yaml", "w", encoding="utf-8") as f:
            f.write("\n".join(yaml_lines) + "\n")

        return exported_count

    @classmethod
    def _export_coco(
        cls,
        db: Session,
        dataset: Dataset,
        images: list,
        labels: list,
        label_id_to_idx: dict,
        label_id_to_name: dict,
        export_dir: Path,
        include_unannotated: bool,
    ) -> int:
        categories = [
            {"id": i + 1, "name": lbl.name, "supercategory": "none"}
            for i, lbl in enumerate(labels)
        ]
        label_id_to_cat_id = {lbl.id: i + 1 for i, lbl in enumerate(labels)}

        coco_images = []
        coco_annotations = []
        ann_counter = 1
        exported_count = 0

        for img_idx, img in enumerate(images, start=1):
            ann = db.query(ImageAnnotation).filter(ImageAnnotation.image_id == img.id).first()
            if not ann and not include_unannotated:
                continue

            w_px = img.width or 1000
            h_px = img.height or 1000

            coco_images.append({
                "id": img_idx,
                "file_name": img.relative_path,
                "width": w_px,
                "height": h_px,
            })
            exported_count += 1

            if ann and not ann.is_negative:
                for obj in ann.objects:
                    if obj.label_id in label_id_to_cat_id:
                        cat_id = label_id_to_cat_id[obj.label_id]
                        x_min_px = round(obj.x_min * w_px, 2)
                        y_min_px = round(obj.y_min * h_px, 2)
                        width_px = round((obj.x_max - obj.x_min) * w_px, 2)
                        height_px = round((obj.y_max - obj.y_min) * h_px, 2)
                        area = round(width_px * height_px, 2)

                        coco_annotations.append({
                            "id": ann_counter,
                            "image_id": img_idx,
                            "category_id": cat_id,
                            "bbox": [x_min_px, y_min_px, width_px, height_px],
                            "area": area,
                            "iscrowd": 0,
                        })
                        ann_counter += 1

        coco_data = {
            "info": {
                "description": f"Exported from NOVA AI Trainer: {dataset.name}",
                "version": "1.0",
                "year": datetime.now(timezone.utc).year,
                "date_created": datetime.now(timezone.utc).isoformat(),
            },
            "licenses": [],
            "images": coco_images,
            "annotations": coco_annotations,
            "categories": categories,
        }

        with open(export_dir / "annotations.json", "w", encoding="utf-8") as f:
            json.dump(coco_data, f, indent=2)

        return exported_count

    @classmethod
    def _export_pascal_voc(
        cls,
        db: Session,
        dataset: Dataset,
        images: list,
        label_id_to_name: dict,
        export_dir: Path,
        include_unannotated: bool,
    ) -> int:
        ann_dir = export_dir / "Annotations"
        ann_dir.mkdir(parents=True, exist_ok=True)

        exported_count = 0
        for img in images:
            ann = db.query(ImageAnnotation).filter(ImageAnnotation.image_id == img.id).first()
            if not ann and not include_unannotated:
                continue

            w_px = img.width or 1000
            h_px = img.height or 1000
            channels = img.channels or 3

            root = ET.Element("annotation")
            ET.SubElement(root, "folder").text = dataset.name
            ET.SubElement(root, "filename").text = Path(img.relative_path).name
            ET.SubElement(root, "path").text = img.absolute_path

            size = ET.SubElement(root, "size")
            ET.SubElement(size, "width").text = str(w_px)
            ET.SubElement(size, "height").text = str(h_px)
            ET.SubElement(size, "depth").text = str(channels)

            if ann and not ann.is_negative:
                for obj in ann.objects:
                    lbl_name = label_id_to_name.get(obj.label_id, "unknown")
                    obj_el = ET.SubElement(root, "object")
                    ET.SubElement(obj_el, "name").text = lbl_name
                    ET.SubElement(obj_el, "pose").text = "Unspecified"
                    ET.SubElement(obj_el, "truncated").text = "0"
                    ET.SubElement(obj_el, "difficult").text = "0"

                    bndbox = ET.SubElement(obj_el, "bndbox")
                    ET.SubElement(bndbox, "xmin").text = str(int(round(obj.x_min * w_px)))
                    ET.SubElement(bndbox, "ymin").text = str(int(round(obj.y_min * h_px)))
                    ET.SubElement(bndbox, "xmax").text = str(int(round(obj.x_max * w_px)))
                    ET.SubElement(bndbox, "ymax").text = str(int(round(obj.y_max * h_px)))

            tree = ET.ElementTree(root)
            xml_file = ann_dir / f"{Path(img.relative_path).stem}.xml"
            tree.write(xml_file, encoding="utf-8", xml_declaration=True)
            exported_count += 1

        return exported_count

    @classmethod
    def _export_csv(
        cls,
        db: Session,
        images: list,
        label_id_to_name: dict,
        export_dir: Path,
        include_unannotated: bool,
    ) -> int:
        csv_file = export_dir / "annotations.csv"
        exported_count = 0

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["image_relative_path", "labels", "status", "is_negative"])

            for img in images:
                ann = db.query(ImageAnnotation).filter(ImageAnnotation.image_id == img.id).first()
                if not ann and not include_unannotated:
                    continue

                assigned = []
                status_str = "UNANNOTATED"
                is_neg = False
                if ann:
                    status_str = ann.status
                    is_neg = ann.is_negative
                    for ca in ann.classification_labels:
                        if ca.label_id in label_id_to_name:
                            assigned.append(label_id_to_name[ca.label_id])
                    for oa in ann.objects:
                        if oa.label_id in label_id_to_name and label_id_to_name[oa.label_id] not in assigned:
                            assigned.append(label_id_to_name[oa.label_id])

                writer.writerow([img.relative_path, ";".join(assigned), status_str, is_neg])
                exported_count += 1

        return exported_count

    @classmethod
    def _export_json(
        cls,
        db: Session,
        images: list,
        label_id_to_name: dict,
        export_dir: Path,
        include_unannotated: bool,
    ) -> int:
        json_file = export_dir / "annotations.json"
        data = {}
        exported_count = 0

        for img in images:
            ann = db.query(ImageAnnotation).filter(ImageAnnotation.image_id == img.id).first()
            if not ann and not include_unannotated:
                continue

            labels = []
            objects = []
            status_str = "UNANNOTATED"
            is_neg = False
            if ann:
                status_str = ann.status
                is_neg = ann.is_negative
                labels = [label_id_to_name.get(ca.label_id, "unknown") for ca in ann.classification_labels]
                objects = [
                    {
                        "label": label_id_to_name.get(oa.label_id, "unknown"),
                        "x_min": oa.x_min,
                        "y_min": oa.y_min,
                        "x_max": oa.x_max,
                        "y_max": oa.y_max,
                        "confidence": oa.confidence,
                    }
                    for oa in ann.objects
                ]

            data[img.relative_path] = {
                "status": status_str,
                "is_negative": is_neg,
                "labels": labels,
                "objects": objects,
            }
            exported_count += 1

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return exported_count

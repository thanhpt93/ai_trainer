import logging
from sqlalchemy import inspect, text

logger = logging.getLogger("nova.db.migrations")

MIGRATIONS = [
    ("projects", "is_multi_label", "BOOLEAN NOT NULL DEFAULT 0"),
    ("projects", "allow_negative_images", "BOOLEAN NOT NULL DEFAULT 1"),
    ("datasets", "annotation_count", "INTEGER NOT NULL DEFAULT 0"),
    ("training_jobs", "name", "VARCHAR(255)"),
    ("training_jobs", "task_type", "VARCHAR(50) NOT NULL DEFAULT 'Image Classification'"),
    ("training_jobs", "model_architecture", "VARCHAR(100)"),
    ("training_jobs", "device", "VARCHAR(50) DEFAULT 'cpu'"),
    ("training_jobs", "current_epoch", "INTEGER NOT NULL DEFAULT 0"),
    ("training_jobs", "total_epochs", "INTEGER NOT NULL DEFAULT 0"),
    ("training_jobs", "best_metric_name", "VARCHAR(50) DEFAULT 'val_accuracy'"),
    ("training_jobs", "best_metric_value", "FLOAT"),
    ("training_jobs", "checkpoint_dir", "VARCHAR(1024)"),
    ("training_jobs", "log_file_path", "VARCHAR(1024)"),
    ("training_jobs", "metrics_json", "TEXT"),
    ("training_jobs", "evaluation_json", "TEXT"),
    ("training_jobs", "pid", "INTEGER"),
    ("training_jobs", "is_cancelled", "BOOLEAN NOT NULL DEFAULT 0"),
    ("model_artifacts", "project_id", "VARCHAR(36)"),
    ("model_artifacts", "dataset_id", "VARCHAR(36)"),
    ("model_artifacts", "training_job_id", "VARCHAR(36)"),
    ("model_artifacts", "model_architecture", "VARCHAR(100)"),
    ("model_artifacts", "metrics_summary_json", "TEXT"),
    ("model_artifacts", "checksum_sha256", "VARCHAR(64)"),
    ("model_artifacts", "file_size_bytes", "INTEGER NOT NULL DEFAULT 0"),
    ("model_artifacts", "is_exported", "BOOLEAN NOT NULL DEFAULT 0"),
]


def run_db_migrations(engine) -> None:
    """
    Ensures that existing databases created in previous phases
    are automatically and safely updated with any new columns.
    """
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        with engine.begin() as conn:
            for table, col, col_def in MIGRATIONS:
                if table in existing_tables:
                    existing_cols = [c["name"] for c in inspector.get_columns(table)]
                    if col not in existing_cols:
                        logger.info(f"Auto-migrating: adding column '{col}' to table '{table}'")
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}"))
    except Exception as e:
        logger.error(f"Error during auto-migration: {e}")
        raise

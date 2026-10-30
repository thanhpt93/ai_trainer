import os
import shutil
import tempfile
from pathlib import Path

# Ensure all tests run against an isolated temporary app data directory and test export directory
_test_appdata = tempfile.mkdtemp(prefix="nova_test_appdata_")
_test_export = tempfile.mkdtemp(prefix="nova_test_export_")
os.environ.setdefault("NOVA_APP_DATA_DIR", _test_appdata)
os.environ.setdefault("NOVA_EXPORT_DIR", _test_export)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.config import settings
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.domain import models  # Ensure all models are registered


@pytest.fixture(scope="session")
def test_temp_dir():
    temp_dir = Path(tempfile.mkdtemp(prefix="nova_test_"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def test_db_engine(test_temp_dir):
    db_file = test_temp_dir / "test.db"
    db_url = f"sqlite:///{db_file.as_posix()}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_db_engine):
    connection = test_db_engine.connect()
    transaction = connection.begin()
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestingSessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_image_dataset(test_temp_dir):
    """Creates a temporary sample image folder with valid, corrupt, and unsupported files."""
    dataset_dir = test_temp_dir / "sample_dataset"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    subdir = dataset_dir / "subdir"
    subdir.mkdir(exist_ok=True)

    from PIL import Image

    # 1. Valid PNG
    img1 = Image.new("RGB", (64, 64), color="red")
    img1.save(dataset_dir / "image1.png")

    # 2. Valid JPEG in subfolder
    img2 = Image.new("RGB", (128, 96), color="blue")
    img2.save(subdir / "image2.jpg")

    # 3. Corrupt file with .jpg extension
    corrupt_file = dataset_dir / "corrupted.jpg"
    with open(corrupt_file, "wb") as f:
        f.write(b"NOT_A_VALID_IMAGE_HEADER_BYTES")

    # 4. Unsupported file (.txt)
    txt_file = dataset_dir / "notes.txt"
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write("Some notes about dataset")

    return dataset_dir

from fastapi import APIRouter
from backend.app.api.v1.endpoints import (
    health,
    projects,
    datasets,
    filesystem,
    labels,
    annotations,
    training,
    models,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health & System"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["Datasets"])
api_router.include_router(filesystem.router, prefix="/filesystem", tags=["Filesystem"])
api_router.include_router(labels.router, tags=["Labels"])
api_router.include_router(annotations.router, tags=["Annotations & Studio"])
api_router.include_router(training.router, prefix="/training", tags=["Training & Jobs"])
api_router.include_router(models.router, prefix="/models", tags=["Model Registry"])

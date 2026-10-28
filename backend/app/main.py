import os
import sys
import argparse
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.db.base import Base
from backend.app.db.session import engine
from backend.app.db.migrations import run_db_migrations
from backend.app.api.v1.api import api_router
from backend.app.domain import models  # Ensure all models are registered with Base metadata


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables are created and columns migrated
    Base.metadata.create_all(bind=engine)
    run_db_migrations(engine)
    yield
    # Shutdown logic if needed


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="NOVA AI Trainer Backend API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handlers for uniform responses
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Internal server error: {str(exc)}"},
    )


# Include API v1 router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "docs": "/docs",
        "api_v1": settings.API_V1_PREFIX,
    }


def run_server():
    import uvicorn

    parser = argparse.ArgumentParser(description="Run NOVA AI Trainer backend server")
    parser.add_argument("--host", default=settings.HOST, help="Host to bind (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=settings.PORT, help="Port to bind (default 8000)")
    parser.add_argument("--app-data-dir", default=None, help="Custom application data directory")
    args = parser.parse_args()

    if args.app_data_dir:
        os.environ["NOVA_APP_DATA_DIR"] = args.app_data_dir

    print(f"NOVA_BACKEND_READY:http://{args.host}:{args.port}", flush=True)

    uvicorn.run(
        "backend.app.main:app",
        host=args.host,
        port=args.port,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    run_server()

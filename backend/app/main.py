from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import get_settings
from app.db.database import init_db
from app.core.middleware import setup_middleware
from app.core.exceptions import AppError, app_error_handler
from app.api.routes import generate, drafts, images, publish, auth
from app.api.websocket import router as ws_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    storage = Path(settings.local_storage_path)
    storage.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="LinkedIn Post Generator",
    description="Agentic AI app that generates and publishes LinkedIn posts.",
    version="1.0.0",
    lifespan=lifespan,
)

setup_middleware(app, settings.cors_origins)
app.add_exception_handler(AppError, app_error_handler)

# API routes
app.include_router(generate.router, prefix="/api", tags=["Generate"])
app.include_router(drafts.router, prefix="/api", tags=["Drafts"])
app.include_router(images.router, prefix="/api", tags=["Images"])
app.include_router(publish.router, prefix="/api", tags=["Publish"])
app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(ws_router, tags=["WebSocket"])

# Serve generated images as static files
storage_path = Path(settings.local_storage_path)
storage_path.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=str(storage_path)), name="storage")


@app.get("/health")
async def health():
    return {"status": "ok"}

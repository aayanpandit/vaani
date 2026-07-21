from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import voice_router
from app.api.v1.admin_appointments_router import router as admin_appointments_router
from app.api.v1.admin_auth_router import router as admin_auth_router
from app.api.v1.router import router as v1_router
from app.config.settings import settings

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1", tags=["v1"])
app.include_router(voice_router.router, prefix="/api/v1", tags=["Voice"])
app.include_router(admin_auth_router, prefix="/api/v1")
app.include_router(admin_appointments_router, prefix="/api/v1")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def serve_home():
    return FileResponse(STATIC_DIR / "index.html")

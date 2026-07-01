from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.v1 import voice_router
from app.api.v1.router import router as v1_router
from app.config.settings import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)

app.include_router(
    v1_router,
    prefix="/api/v1",
    tags=["v1"],
)

app.include_router(
    voice_router.router,
    prefix="/api/v1",
    tags=["Voice"],
)

# Serve static frontend files
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)

# Home page
@app.get("/")
def serve_home():
    return FileResponse("static/index.html")
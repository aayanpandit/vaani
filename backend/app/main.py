from fastapi import FastAPI

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

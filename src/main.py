from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import settings
from src.routers.v1.router import router as v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Dream Lounge API",
    description="청주대학교 동아리 관리 시스템 백엔드 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}

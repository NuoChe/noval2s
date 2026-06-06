"""FastAPI application factory."""

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

load_dotenv()

from novel2script.api.routes import router
from novel2script.auth.database import init_db
from novel2script.auth.routes import router as auth_router
from novel2script.auth.service import seed_demo_users
from novel2script.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    settings = get_settings()
    seed_demo_users(settings.auth_demo_users)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Novel2Script",
        description="AI-assisted novel to screenplay conversion",
        version="0.2.0",
        lifespan=lifespan,
    )
    app.include_router(auth_router)
    app.include_router(router)

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    return app

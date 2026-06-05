"""FastAPI application factory."""

from fastapi import FastAPI

from novel2script.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Novel2Script",
        description="AI-assisted novel to screenplay conversion",
        version="0.1.0",
    )
    app.include_router(router)
    return app

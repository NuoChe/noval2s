"""FastAPI routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from novel2script.auth.deps import get_current_user
from novel2script.auth.models import UserPublic
from novel2script.config import get_settings
from novel2script.exceptions import Novel2ScriptError
from novel2script.llm.registry import (
    ModelNotConfiguredError,
    UnknownModelError,
    get_default_model_id,
    list_models,
    settings_for_model_id,
)
from novel2script.models.schema import ConversionOptions
from novel2script.pipeline.converter import convert_novel

router = APIRouter()
templates = Jinja2Templates(directory=str(__import__("pathlib").Path(__file__).parent / "templates"))


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    settings = get_settings()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "settings": settings,
            "default_model_id": get_default_model_id(settings),
        },
    )


@router.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "novel2script", "version": "0.2.0"}


@router.get("/api/models")
async def models_api() -> JSONResponse:
    settings = get_settings()
    return JSONResponse(
        {
            "models": list_models(settings),
            "default_model_id": get_default_model_id(settings),
        }
    )


@router.post("/api/convert")
async def convert_api(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    author: str | None = Form(None),
    model_id: str | None = Form(None),
    model: str | None = Form(None),
    user: UserPublic = Depends(get_current_user),
) -> JSONResponse:
    del user
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded") from exc

    base_settings = get_settings()
    try:
        if model_id:
            request_settings = settings_for_model_id(base_settings, model_id)
        else:
            request_settings = base_settings.model_copy()
            if model:
                request_settings.llm_model = model
            if not request_settings.llm_api_key and request_settings.llm_provider != "ollama":
                raise ModelNotConfiguredError("LLM_API_KEY not configured")
    except UnknownModelError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ModelNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    options = ConversionOptions(
        title=title,
        author=author,
        model=model,
        model_id=model_id,
    )

    try:
        result = convert_novel(text, options, settings=request_settings)
    except Novel2ScriptError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return JSONResponse(
        {
            "yaml_content": result.yaml_content,
            "report": result.report.model_dump(),
            "filename": file.filename.rsplit(".", 1)[0] + ".yaml",
        }
    )

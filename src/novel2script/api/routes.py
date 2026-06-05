"""FastAPI routes."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from novel2script.config import get_settings
from novel2script.models.schema import ConversionOptions
from novel2script.pipeline.converter import convert_novel

router = APIRouter()
templates = Jinja2Templates(directory=str(__import__("pathlib").Path(__file__).parent / "templates"))


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {"settings": get_settings()},
    )


@router.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "novel2script"}


@router.post("/api/convert")
async def convert_api(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    author: str | None = Form(None),
    model: str | None = Form(None),
) -> JSONResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded") from exc

    settings = get_settings()
    if model:
        settings.llm_model = model

    if not settings.llm_api_key and settings.llm_provider != "ollama":
        raise HTTPException(
            status_code=503,
            detail="LLM_API_KEY not configured. Set it in .env file.",
        )

    options = ConversionOptions(title=title, author=author, model=model)

    try:
        result = convert_novel(text, options, settings=settings)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return JSONResponse(
        {
            "yaml_content": result.yaml_content,
            "report": result.report.model_dump(),
            "filename": file.filename.rsplit(".", 1)[0] + ".yaml",
        }
    )

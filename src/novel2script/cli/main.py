"""Typer CLI entry point."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
import uvicorn
from dotenv import load_dotenv

from novel2script.config import get_settings
from novel2script.emitter.yaml_writer import load_screenplay
from novel2script.models.schema import ConversionOptions
from novel2script.pipeline.converter import convert_file
from novel2script.validator.validate import load_and_validate_yaml

load_dotenv()

app = typer.Typer(
    name="novel2script",
    help="AI-assisted novel to screenplay conversion tool.",
    no_args_is_help=True,
)


@app.command()
def convert(
    input: Path = typer.Argument(..., help="Input novel file (TXT/MD)", exists=True),
    output: Path = typer.Option(..., "-o", "--output", help="Output YAML path"),
    model: Optional[str] = typer.Option(None, "--model", help="LLM model name"),
    model_id: Optional[str] = typer.Option(None, "--model-id", help="V2 preset model id"),
    provider: Optional[str] = typer.Option(None, "--provider", help="LLM provider"),
    title: Optional[str] = typer.Option(None, "--title", help="Override work title"),
    author: Optional[str] = typer.Option(None, "--author", help="Override author name"),
) -> None:
    """Convert a novel (3+ chapters) to structured YAML screenplay."""
    settings = get_settings()
    if model_id:
        from novel2script.llm.registry import settings_for_model_id

        settings = settings_for_model_id(settings, model_id)
    else:
        if provider:
            settings.llm_provider = provider
        if model:
            settings.llm_model = model

    if not settings.llm_api_key and settings.llm_provider != "ollama":
        typer.echo(
            "Warning: LLM API key not set. Configure .env or use --model-id with a configured provider.",
            err=True,
        )

    options = ConversionOptions(
        title=title,
        author=author,
        model=model,
        provider=provider,
        model_id=model_id,
    )

    typer.echo(f"Converting {input} ...")
    result = convert_file(input, output, options, settings=settings)

    typer.echo(f"Status: {result.report.status}")
    typer.echo(
        f"Scenes: {result.report.stats.scenes} | "
        f"Characters: {result.report.stats.characters} | "
        f"Warnings: {result.report.stats.warnings}"
    )
    typer.echo(f"Output: {output}")
    typer.echo(f"Report: {output.with_suffix('.report.json')}")
    typer.echo(f"Duration: {result.report.duration_sec}s")


@app.command()
def validate(
    file: Path = typer.Argument(..., help="YAML screenplay to validate", exists=True),
) -> None:
    """Validate an existing YAML screenplay against the schema."""
    result = load_and_validate_yaml(file)

    typer.echo(f"Schema version: 1.0")
    typer.echo(f"Structure validation: {result.status.value}")

    if result.errors:
        typer.echo("Errors:", err=True)
        for err in result.errors:
            typer.echo(f"  - {err}", err=True)

    if result.warnings:
        typer.echo(f"Warnings: {len(result.warnings)}")
        for w in result.warnings[:10]:
            typer.echo(f"  [{w.severity}] {w.code}: {w.message}")
        if len(result.warnings) > 10:
            typer.echo(f"  ... and {len(result.warnings) - 10} more")

    if result.chapter_coverage:
        covered = sum(1 for v in result.chapter_coverage.values() if v)
        total = len(result.chapter_coverage)
        typer.echo(f"Chapter coverage: {covered}/{total}")

    typer.echo(f"\nResult: {result.status.value}")

    if result.status.value == "FAIL":
        raise typer.Exit(code=1)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind host"),
    port: int = typer.Option(8000, "--port", "-p", help="Bind port"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload"),
) -> None:
    """Start the FastAPI web UI."""
    typer.echo(f"Starting Novel2Script Web UI at http://{host}:{port}")
    uvicorn.run(
        "novel2script.api.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()

"""Main conversion pipeline orchestrating all stages."""

from __future__ import annotations

import time
from pathlib import Path

from novel2script.adapter.scene_adapter import SceneAdapter
from novel2script.config import Settings, get_settings
from novel2script.emitter.yaml_writer import serialize_screenplay, write_screenplay
from novel2script.extractor.entity import extract_entities
from novel2script.extractor.registry import EntityRegistry
from novel2script.llm.client import LLMClient, LiteLLMClient
from novel2script.models.schema import (
    Act,
    ChapterInfo,
    ConversionOptions,
    ConversionResult,
    Screenplay,
    build_meta,
)
from novel2script.parser.chapter import parse_book_metadata, parse_chapters
from novel2script.validator.validate import validate_screenplay


def convert_novel(
    text: str,
    options: ConversionOptions | None = None,
    *,
    llm: LLMClient | None = None,
    settings: Settings | None = None,
) -> ConversionResult:
    settings = settings or get_settings()
    options = options or ConversionOptions()
    start = time.time()

    if options.model_id:
        from novel2script.llm.registry import litellm_model_name, resolve_model, settings_for_model_id

        settings = settings_for_model_id(settings, options.model_id)
        llm = llm or LiteLLMClient(settings)
        model = litellm_model_name(resolve_model(options.model_id))
    else:
        llm = llm or LiteLLMClient(settings)
        model = options.model or llm.model_name

    chapters = parse_chapters(text, settings)
    registry = EntityRegistry()

    book_title, book_author = parse_book_metadata(text)

    for chapter in chapters:
        extract_entities(chapter, registry, llm)

    adapter = SceneAdapter(llm)
    for chapter in chapters:
        adapter.adapt_chapter(chapter, registry)
        adapter.set_first_appearances(registry, chapter.id)

    chapter_infos = [
        ChapterInfo(id=c.id, title=c.title, word_count=c.word_count) for c in chapters
    ]

    title = options.title or book_title or chapters[0].title or "未命名作品"
    author = options.author or book_author or "未知作者"

    scene_ids = [s.id for s in adapter.all_scenes]
    acts = [Act(id="act_1", title="第一幕", scenes=scene_ids)] if scene_ids else []

    screenplay = Screenplay(
        meta=build_meta(
            title=title,
            author=author,
            chapters=chapter_infos,
            model=model,
            prompt_version=settings.prompt_version,
        ),
        characters=registry.characters_list(),
        locations=registry.locations_list(),
        acts=acts,
        scenes=adapter.all_scenes,
        warnings=registry.warnings + adapter.all_warnings,
    )

    validation = validate_screenplay(screenplay)
    duration = time.time() - start

    from novel2script.emitter.yaml_writer import build_report

    yaml_content = serialize_screenplay(screenplay)
    report = build_report(validation, duration)

    return ConversionResult(
        screenplay=screenplay,
        report=report,
        yaml_content=yaml_content,
    )


def convert_file(
    input_path: Path,
    output_path: Path,
    options: ConversionOptions | None = None,
    *,
    llm: LLMClient | None = None,
    settings: Settings | None = None,
) -> ConversionResult:
    text = input_path.read_text(encoding="utf-8")
    result = convert_novel(text, options, llm=llm, settings=settings)

    validation = validate_screenplay(result.screenplay)
    duration = result.report.duration_sec
    yaml_content, report = write_screenplay(
        result.screenplay,
        output_path,
        validation,
        duration,
    )

    return ConversionResult(
        screenplay=result.screenplay,
        report=report,
        yaml_content=yaml_content,
    )

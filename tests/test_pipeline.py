"""End-to-end pipeline tests with mock LLM."""

from novel2script.models.enums import ValidationStatus
from novel2script.models.schema import ConversionOptions
from novel2script.pipeline.converter import convert_file, convert_novel
from novel2script.validator.validate import validate_screenplay


def test_convert_novel_with_mock(sample_novel_text, mock_llm, settings):
    result = convert_novel(
        sample_novel_text,
        ConversionOptions(title="晚风书店", author="测试作者"),
        llm=mock_llm,
        settings=settings,
    )

    assert result.screenplay.meta.source.chapter_count == 3
    assert len(result.screenplay.scenes) >= 3
    assert len(result.screenplay.characters) >= 2
    assert result.yaml_content
    assert "schema_version" in result.yaml_content

    validation = validate_screenplay(result.screenplay)
    assert validation.status in (ValidationStatus.PASS, ValidationStatus.PASS_WITH_WARNINGS)
    assert all(validation.chapter_coverage.values())

    assert mock_llm.calls


def test_convert_file_writes_disk(sample_novel_text, mock_llm, settings, tmp_path):
    input_file = tmp_path / "novel.txt"
    input_file.write_text(sample_novel_text, encoding="utf-8")
    output_file = tmp_path / "screenplay.yaml"

    result = convert_file(input_file, output_file, llm=mock_llm, settings=settings)

    assert output_file.exists()
    assert output_file.with_suffix(".report.json").exists()
    assert result.report.stats.scenes >= 3


def test_meta_title_author_override(sample_novel_text, mock_llm, settings):
    result = convert_novel(
        sample_novel_text,
        ConversionOptions(title="自定义标题", author="自定义作者"),
        llm=mock_llm,
        settings=settings,
    )
    assert result.screenplay.meta.title == "自定义标题"
    assert result.screenplay.meta.author == "自定义作者"


def test_warnings_present(sample_novel_text, mock_llm, settings):
    result = convert_novel(sample_novel_text, llm=mock_llm, settings=settings)
    assert len(result.screenplay.warnings) > 0


def test_all_element_types_in_output(sample_novel_text, mock_llm, settings):
    result = convert_novel(sample_novel_text, llm=mock_llm, settings=settings)
    types = {elem.type for scene in result.screenplay.scenes for elem in scene.elements}
    assert "action" in types
    assert "dialogue" in types
    assert "voiceover" in types or "transition" in types

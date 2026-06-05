"""Optional integration tests requiring real LLM API key."""

import os

import pytest

from novel2script.models.schema import ConversionOptions
from novel2script.models.enums import ValidationStatus
from novel2script.pipeline.converter import convert_novel
from novel2script.validator.validate import validate_screenplay


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("LLM_API_KEY"), reason="LLM_API_KEY not set")
def test_real_llm_convert(sample_novel_text):
    result = convert_novel(
        sample_novel_text,
        ConversionOptions(title="晚风书店", author="集成测试"),
    )
    validation = validate_screenplay(result.screenplay)
    assert validation.status in (ValidationStatus.PASS, ValidationStatus.PASS_WITH_WARNINGS)
    assert result.screenplay.meta.source.chapter_count == 3
    assert len(result.screenplay.scenes) >= 1
    assert all(validation.chapter_coverage.values())

"""CLI command tests."""

from pathlib import Path

from novel2script.cli.main import app
from novel2script.pipeline.converter import convert_file


def test_validate_sample_screenplay(cli_runner):
    examples = Path(__file__).parent.parent / "examples" / "sample-screenplay.yaml"
    result = cli_runner.invoke(app, ["validate", str(examples)])
    assert result.exit_code == 0
    assert "PASS" in result.stdout


def test_validate_missing_file(cli_runner):
    result = cli_runner.invoke(app, ["validate", "nonexistent.yaml"])
    assert result.exit_code != 0


def test_convert_writes_output(cli_runner, sample_novel_text, mock_llm, settings, tmp_path, monkeypatch):
    input_file = tmp_path / "input.txt"
    input_file.write_text(sample_novel_text, encoding="utf-8")
    output_file = tmp_path / "output.yaml"

    def patched_convert(input_path, output_path, options=None, llm=None, settings=None):
        return convert_file(input_path, output_path, options, llm=mock_llm, settings=settings)

    monkeypatch.setattr("novel2script.cli.main.convert_file", patched_convert)

    result = cli_runner.invoke(
        app,
        ["convert", str(input_file), "-o", str(output_file), "--title", "测试", "--author", "作者"],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert output_file.exists()
    assert output_file.with_suffix(".report.json").exists()


def test_convert_insufficient_chapters(cli_runner, two_chapter_novel_text, tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    input_file = tmp_path / "two.txt"
    input_file.write_text(two_chapter_novel_text, encoding="utf-8")
    output_file = tmp_path / "out.yaml"

    result = cli_runner.invoke(app, ["convert", str(input_file), "-o", str(output_file)])
    assert result.exit_code != 0

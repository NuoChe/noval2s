"""FastAPI endpoint tests."""

from io import BytesIO
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from novel2script.api.app import create_app
from novel2script.config import Settings


@pytest.fixture
def client(mock_llm, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    app = create_app()

    import novel2script.api.routes as routes_module
    import novel2script.pipeline.converter as converter_module

    original = converter_module.convert_novel

    def patched_convert(text, options=None, llm=None, settings=None):
        return original(text, options, llm=mock_llm, settings=settings)

    monkeypatch.setattr(routes_module, "convert_novel", patched_convert)
    monkeypatch.setattr(converter_module, "convert_novel", patched_convert)

    return TestClient(app)


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_index_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Novel2Script" in resp.text


def test_convert_api(client, sample_novel_text):
    resp = client.post(
        "/api/convert",
        files={"file": ("novel.txt", BytesIO(sample_novel_text.encode("utf-8")), "text/plain")},
        data={"title": "测试", "author": "作者"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "yaml_content" in data
    assert data["report"]["stats"]["scenes"] >= 3
    assert "schema_version" in data["yaml_content"]


def test_convert_response_report_structure(client, sample_novel_text):
    resp = client.post(
        "/api/convert",
        files={"file": ("novel.txt", BytesIO(sample_novel_text.encode("utf-8")), "text/plain")},
    )
    assert resp.status_code == 200
    report = resp.json()["report"]
    assert "stats" in report
    assert "chapters" in report["stats"]
    assert "scenes" in report["stats"]
    assert "characters" in report["stats"]
    assert "warnings" in report["stats"]
    assert "duration_sec" in report


def test_convert_missing_api_key(sample_novel_text, monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    get_settings = __import__("novel2script.config", fromlist=["get_settings"]).get_settings
    get_settings.cache_clear()

    with patch("novel2script.api.routes.get_settings") as mock_settings:
        mock_settings.return_value = Settings(
            llm_api_key="",
            llm_provider="openai",
            llm_model="gpt-4o-mini",
        )
        app = create_app()
        client = TestClient(app)
        resp = client.post(
            "/api/convert",
            files={"file": ("novel.txt", BytesIO(sample_novel_text.encode("utf-8")), "text/plain")},
        )
        assert resp.status_code == 503


def test_convert_two_chapters(client, two_chapter_novel_text):
    resp = client.post(
        "/api/convert",
        files={"file": ("novel.txt", BytesIO(two_chapter_novel_text.encode("utf-8")), "text/plain")},
    )
    assert resp.status_code == 422


def test_convert_invalid_encoding(client):
    resp = client.post(
        "/api/convert",
        files={"file": ("novel.txt", BytesIO(b"\xff\xfe invalid"), "text/plain")},
    )
    assert resp.status_code == 400

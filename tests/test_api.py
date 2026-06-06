"""FastAPI endpoint tests."""

from io import BytesIO
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from novel2script.auth.database import init_db
from novel2script.api.app import create_app
from novel2script.config import Settings, get_settings


def _login(client: TestClient, email: str = "api@example.com", password: str = "pass1234") -> None:
    resp = client.post("/api/auth/register", json={"email": email, "password": password})
    if resp.status_code == 409:
        resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200


@pytest.fixture
def client(mock_llm, monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("AUTH_DB_PATH", str(tmp_path / "api_test.db"))
    monkeypatch.setenv("AUTH_SECRET", "test-auth-secret-key")
    get_settings.cache_clear()
    app = create_app()

    import novel2script.api.routes as routes_module
    import novel2script.pipeline.converter as converter_module

    original = converter_module.convert_novel

    def patched_convert(text, options=None, llm=None, settings=None):
        return original(text, options, llm=mock_llm, settings=settings)

    monkeypatch.setattr(routes_module, "convert_novel", patched_convert)
    monkeypatch.setattr(converter_module, "convert_novel", patched_convert)

    c = TestClient(app)
    _login(c)
    return c


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.2.0"


def test_models_api(client):
    resp = client.get("/api/models")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["models"]) == 5
    assert data["default_model_id"]


def test_index_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Novel2Script" in resp.text
    assert "model-grid" in resp.text


def test_convert_requires_auth(mock_llm, monkeypatch, tmp_path, sample_novel_text):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("AUTH_DB_PATH", str(tmp_path / "unauth.db"))
    monkeypatch.setenv("AUTH_SECRET", "test-auth-secret-key")
    get_settings.cache_clear()
    app = create_app()
    anon = TestClient(app)
    resp = anon.post(
        "/api/convert",
        files={"file": ("novel.txt", BytesIO(sample_novel_text.encode("utf-8")), "text/plain")},
        data={"model_id": "openai-gpt-4o-mini"},
    )
    assert resp.status_code == 401


def test_convert_api(client, sample_novel_text):
    resp = client.post(
        "/api/convert",
        files={"file": ("novel.txt", BytesIO(sample_novel_text.encode("utf-8")), "text/plain")},
        data={"title": "测试", "author": "作者", "model_id": "openai-gpt-4o-mini"},
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
        data={"model_id": "openai-gpt-4o-mini"},
    )
    assert resp.status_code == 200
    report = resp.json()["report"]
    assert "stats" in report
    assert "chapters" in report["stats"]
    assert "scenes" in report["stats"]
    assert "characters" in report["stats"]
    assert "warnings" in report["stats"]
    assert "duration_sec" in report


def test_convert_missing_api_key(sample_novel_text, monkeypatch, tmp_path, mock_llm):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("AUTH_DB_PATH", str(tmp_path / "nokey.db"))
    monkeypatch.setenv("AUTH_SECRET", "test-auth-secret-key")
    get_settings.cache_clear()

    app = create_app()
    c = TestClient(app)
    _login(c)

    import novel2script.api.routes as routes_module
    import novel2script.pipeline.converter as converter_module

    original = converter_module.convert_novel

    def patched_convert(text, options=None, llm=None, settings=None):
        return original(text, options, llm=mock_llm, settings=settings)

    monkeypatch.setattr(routes_module, "convert_novel", patched_convert)

    resp = c.post(
        "/api/convert",
        files={"file": ("novel.txt", BytesIO(sample_novel_text.encode("utf-8")), "text/plain")},
        data={"model_id": "openai-gpt-4o-mini"},
    )
    assert resp.status_code == 503


def test_convert_two_chapters(client, two_chapter_novel_text):
    resp = client.post(
        "/api/convert",
        files={"file": ("novel.txt", BytesIO(two_chapter_novel_text.encode("utf-8")), "text/plain")},
        data={"model_id": "openai-gpt-4o-mini"},
    )
    assert resp.status_code == 422


def test_convert_invalid_encoding(client):
    resp = client.post(
        "/api/convert",
        files={"file": ("novel.txt", BytesIO(b"\xff\xfe invalid"), "text/plain")},
        data={"model_id": "openai-gpt-4o-mini"},
    )
    assert resp.status_code == 400

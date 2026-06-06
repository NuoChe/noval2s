"""Auth demo tests."""

import pytest
from fastapi.testclient import TestClient

from novel2script.auth.database import init_db
from novel2script.api.app import create_app
from novel2script.config import get_settings


@pytest.fixture
def auth_client(monkeypatch, tmp_path):
    monkeypatch.setenv("AUTH_DB_PATH", str(tmp_path / "auth.db"))
    monkeypatch.setenv("AUTH_SECRET", "test-auth-secret-key")
    get_settings.cache_clear()
    init_db()
    return TestClient(create_app())


def test_register_and_me(auth_client):
    resp = auth_client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "password": "pass1234"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "user@example.com"

    me = auth_client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"


def test_login_invalid_password(auth_client):
    auth_client.post(
        "/api/auth/register",
        json={"email": "user2@example.com", "password": "pass1234"},
    )
    resp = auth_client.post(
        "/api/auth/login",
        json={"email": "user2@example.com", "password": "wrong"},
    )
    assert resp.status_code == 401


def test_me_unauthenticated(auth_client):
    resp = auth_client.get("/api/auth/me")
    assert resp.status_code == 401

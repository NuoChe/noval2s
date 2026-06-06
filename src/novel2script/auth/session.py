"""Signed session cookies."""

from __future__ import annotations

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from novel2script.config import get_settings

SESSION_COOKIE = "novel2script_session"
SESSION_MAX_AGE = 86400


def _serializer() -> URLSafeTimedSerializer:
    secret = get_settings().auth_secret
    return URLSafeTimedSerializer(secret, salt="novel2script-auth")


def create_session_token(user_id: int, email: str) -> str:
    return _serializer().dumps({"user_id": user_id, "email": email})


def load_session_token(token: str) -> dict | None:
    try:
        return _serializer().loads(token, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None

"""FastAPI dependencies for auth."""

from __future__ import annotations

from fastapi import Cookie, HTTPException, Request

from novel2script.auth.models import UserPublic
from novel2script.auth.service import get_user_by_id
from novel2script.auth.session import SESSION_COOKIE, load_session_token


def get_current_user(
    request: Request,
    novel2script_session: str | None = Cookie(default=None),
) -> UserPublic:
    token = novel2script_session
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = load_session_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    user = get_user_by_id(int(payload["user_id"]))
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

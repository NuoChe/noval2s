"""Auth API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from novel2script.auth.deps import get_current_user
from novel2script.auth.models import LoginRequest, RegisterRequest, UserPublic
from novel2script.auth.service import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    authenticate,
    register_user,
)
from novel2script.auth.session import SESSION_COOKIE, SESSION_MAX_AGE, create_session_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_session_cookie(response: Response, user: UserPublic) -> None:
    token = create_session_token(user.id, user.email)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_MAX_AGE,
        path="/",
    )


@router.post("/register")
def register(body: RegisterRequest, response: Response) -> UserPublic:
    try:
        user = register_user(body.email, body.password)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _set_session_cookie(response, user)
    return user


@router.post("/login")
def login(body: LoginRequest, response: Response) -> UserPublic:
    try:
        user = authenticate(body.email, body.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    _set_session_cookie(response, user)
    return user


@router.post("/logout")
def logout(
    response: Response,
    user: UserPublic = Depends(get_current_user),
) -> dict[str, str]:
    del user
    response.delete_cookie(key=SESSION_COOKIE, path="/")
    return {"status": "ok"}


@router.get("/me")
def me(user: UserPublic = Depends(get_current_user)) -> UserPublic:
    return user

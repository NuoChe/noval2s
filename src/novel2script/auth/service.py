"""Register, login, and user lookup."""

from __future__ import annotations

import sqlite3

import bcrypt

from novel2script.auth.database import connect, init_db
from novel2script.auth.models import UserPublic


class AuthError(Exception):
    """Base auth error."""


class EmailAlreadyRegisteredError(AuthError):
    pass


class InvalidCredentialsError(AuthError):
    pass


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def get_user_by_id(user_id: int) -> UserPublic | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT id, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    if row is None:
        return None
    return UserPublic(id=row["id"], email=row["email"], created_at=row["created_at"])


def get_user_by_email(email: str) -> tuple[UserPublic, str] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT id, email, password_hash, created_at FROM users WHERE email = ?",
            (email.lower(),),
        ).fetchone()
    if row is None:
        return None
    user = UserPublic(id=row["id"], email=row["email"], created_at=row["created_at"])
    return user, row["password_hash"]


def register_user(email: str, password: str) -> UserPublic:
    email = email.lower().strip()
    password_hash = _hash_password(password)
    with connect() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                (email, password_hash),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            raise EmailAlreadyRegisteredError("Email already registered") from exc
    user = get_user_by_id(int(cur.lastrowid))
    assert user is not None
    return user


def authenticate(email: str, password: str) -> UserPublic:
    record = get_user_by_email(email)
    if record is None:
        raise InvalidCredentialsError("Invalid email or password")
    user, password_hash = record
    if not _verify_password(password, password_hash):
        raise InvalidCredentialsError("Invalid email or password")
    return user


def seed_demo_users(spec: str) -> None:
    if not spec.strip():
        return
    init_db()
    for part in spec.split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        email, password = part.split(":", 1)
        try:
            register_user(email, password)
        except EmailAlreadyRegisteredError:
            continue

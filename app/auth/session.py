"""Signed session cookie (itsdangerous). The cookie carries only the user id."""

from __future__ import annotations

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings

COOKIE_NAME = "brightloop_session"
SESSION_MAX_AGE = 14 * 24 * 60 * 60  # 14 days

_serializer = URLSafeTimedSerializer(settings.secret_key, salt="brightloop-session")


def sign_session(user_id: int) -> str:
    return _serializer.dumps({"uid": int(user_id)})


def read_session(request: Request) -> int | None:
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        return None
    try:
        data = _serializer.loads(raw, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    uid = data.get("uid") if isinstance(data, dict) else None
    return int(uid) if uid is not None else None


def set_session_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        COOKIE_NAME,
        sign_session(user_id),
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")

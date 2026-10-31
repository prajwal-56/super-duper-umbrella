"""Request dependencies: the signed-in User and the require(permission) guard."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from fastapi import HTTPException, Request
from starlette.responses import RedirectResponse

from app.auth.session import read_session
from app.config import settings
from app.db import fetch_one
from app.permissions import DEMO_ONLY, can


@dataclass(frozen=True)
class User:
    id: int
    email: str
    role: str
    customer_id: int | None = None


def _load_user(user_id: int) -> User | None:
    row = fetch_one(
        "SELECT id, email, role, customer_id, is_active FROM users WHERE id = %s",
        (user_id,),
    )
    if row is None or not row["is_active"]:
        return None
    return User(
        id=int(row["id"]),
        email=str(row["email"]),
        role=str(row["role"]),
        customer_id=row["customer_id"],
    )


def current_user(request: Request) -> User | None:
    """Resolve the signed-in user from the session cookie, or None."""
    if settings.dev_auth_bypass:
        return User(id=1, email="dev@localhost", role="admin", customer_id=None)
    cached = getattr(request.state, "user", None)
    if cached is not None:
        return cached
    user_id = read_session(request)
    if user_id is None:
        return None
    user = _load_user(user_id)
    request.state.user = user
    return user


def _wants_html(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "text/html" in accept


def _unauthenticated(request: Request) -> HTTPException:
    if _wants_html(request):
        target = quote(request.url.path, safe="/")
        return HTTPException(
            status_code=303, headers={"Location": f"/login?next={target}"}
        )
    return HTTPException(status_code=401, detail="Authentication required")


def require(permission: str):
    """Return a FastAPI dependency that enforces `permission` (BUILD_PLAN §14).

    Unauthenticated browser requests are redirected to /login; API-style
    requests get 401. A signed-in user without the permission gets 403.
    """

    def dependency(request: Request) -> User:
        user = current_user(request)
        if user is None:
            raise _unauthenticated(request)
        if permission in DEMO_ONLY and not settings.demo_mode:
            raise HTTPException(status_code=403, detail="Demo mode is off")
        if not can(user.role, permission):
            raise HTTPException(status_code=403, detail="Forbidden")
        request.state.user = user
        return user

    dependency.permission = permission  # type: ignore[attr-defined]
    return dependency


def require_login(request: Request) -> User:
    """Dependency for pages that any signed-in role may see."""
    user = current_user(request)
    if user is None:
        raise _unauthenticated(request)
    return user


def redirect_to_login(next_path: str = "/") -> RedirectResponse:
    return RedirectResponse(f"/login?next={quote(next_path, safe='/')}", status_code=303)

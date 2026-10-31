"""Staff user administration (A). Admin only: R-RBAC-02."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.auth import service
from app.db import conn, fetch_all
from app.deps import User, require
from app.templating import render

router = APIRouter(tags=["users"])
NAV: list[tuple[str, str, str]] = [("Users", "/app/users", "staff:manage")]

ManageStaff = Annotated[User, Depends(require("staff:manage"))]


def _users() -> list[dict]:
    return fetch_all(
        "SELECT id, email, role, is_active, created_at FROM users ORDER BY role, email"
    )


def _page(
    request: Request,
    user: User,
    *,
    status_code: int = 200,
    errors: list[str] | None = None,
    name: str = "",
    email: str = "",
    created: bool = False,
):
    return render(
        request,
        "users/index.html",
        status_code=status_code,
        user=user,
        users=_users(),
        errors=errors or [],
        name=name,
        email=email,
        created=created,
    )


@router.get("/app/users")
def users_page(request: Request, user: ManageStaff, created: str = ""):
    return _page(request, user, created=bool(created))


@router.post("/app/users")
def users_create(
    request: Request,
    user: ManageStaff,
    name: str = Form(""),
    email: str = Form(""),
    password: str = Form(""),
):
    try:
        with conn() as c:
            service.create_staff(
                c,
                name=name,
                email=email,
                password=password,
                actor_id=user.id,
            )
    except service.EmailTaken:
        return _page(
            request,
            user,
            status_code=422,
            errors=["An account with this email already exists."],
            name=name,
            email=email,
        )
    except service.InvalidPassword as exc:
        return _page(
            request,
            user,
            status_code=422,
            errors=exc.errors,
            name=name,
            email=email,
        )
    except ValueError as exc:
        return _page(
            request,
            user,
            status_code=422,
            errors=[str(exc)],
            name=name,
            email=email,
        )
    return RedirectResponse("/app/users?created=1", status_code=303)

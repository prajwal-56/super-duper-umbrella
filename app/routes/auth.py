"""Authentication pages: signup, login, logout, forgot and reset (A)."""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.auth import service
from app.auth.session import clear_session_cookie, set_session_cookie
from app.db import conn
from app.deps import current_user
from app.templating import render

router = APIRouter(tags=["auth"])
NAV: list[tuple[str, str, str]] = []


def _safe_next(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith("/") and not value.startswith("//") and "\\" not in value:
        return value
    return None


@router.get("/login")
def login_page(request: Request, next: str = ""):
    user = current_user(request)
    if user is not None:
        return RedirectResponse("/", status_code=303)
    return render(request, "auth/login.html", next=_safe_next(next) or "", user=None)


@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(""),
    password: str = Form(""),
    next: str = Form(""),
):
    email = email.strip()
    if not email or not password:
        return render(
            request,
            "auth/login.html",
            status_code=422,
            user=None,
            next=_safe_next(next) or "",
            email=email,
            error="Email and password are required.",
        )
    user = service.authenticate(email, password)
    if user is None:
        return render(
            request,
            "auth/login.html",
            status_code=401,
            user=None,
            next=_safe_next(next) or "",
            email=email,
            error="Email or password is incorrect.",
        )
    response = RedirectResponse(_safe_next(next) or "/", status_code=303)
    set_session_cookie(response, user.id)
    return response


@router.get("/signup")
def signup_page(request: Request):
    if current_user(request) is not None:
        return RedirectResponse("/", status_code=303)
    return render(request, "auth/signup.html", user=None)


@router.post("/signup")
def signup_submit(
    request: Request,
    name: str = Form(""),
    email: str = Form(""),
    password: str = Form(""),
):
    email = email.strip()
    try:
        with conn() as c:
            service.create_account(c, name=name, email=email, password=password)
    except service.EmailTaken:
        return render(
            request,
            "auth/signup.html",
            status_code=422,
            user=None,
            name=name,
            email=email,
            errors=["An account with this email already exists."],
        )
    except service.InvalidPassword as exc:
        return render(
            request,
            "auth/signup.html",
            status_code=422,
            user=None,
            name=name,
            email=email,
            errors=exc.errors,
        )
    except ValueError as exc:
        return render(
            request,
            "auth/signup.html",
            status_code=422,
            user=None,
            name=name,
            email=email,
            errors=[str(exc)],
        )
    return RedirectResponse("/login?signed_up=1", status_code=303)


@router.post("/logout")
def logout(request: Request):
    response = RedirectResponse("/login", status_code=303)
    clear_session_cookie(response)
    return response


@router.get("/forgot")
def forgot_page(request: Request):
    return render(request, "auth/forgot.html", user=None)


@router.post("/forgot")
def forgot_submit(request: Request, email: str = Form("")):
    email = email.strip()
    if not email or "@" not in email:
        return render(
            request,
            "auth/forgot.html",
            status_code=422,
            user=None,
            email=email,
            errors=["Enter the email address you registered with."],
        )
    with conn() as c:
        service.create_reset_request(c, email)
    return render(request, "auth/forgot.html", user=None, email=email, sent=True)


@router.get("/reset/{token}")
def reset_page(request: Request, token: str):
    with conn() as c:
        row = service.find_reset_token(c, token)
    if row is None:
        return render(
            request, "auth/reset.html", status_code=410, user=None, token=token, invalid=True
        )
    return render(request, "auth/reset.html", user=None, token=token)


@router.post("/reset/{token}")
def reset_submit(
    request: Request,
    token: str,
    password: str = Form(""),
    password_confirm: str = Form(""),
):
    if password != password_confirm:
        return render(
            request,
            "auth/reset.html",
            status_code=422,
            user=None,
            token=token,
            errors=["The two passwords do not match."],
        )
    try:
        with conn() as c:
            user_id = service.consume_reset(c, token, password)
    except service.InvalidPassword as exc:
        return render(
            request,
            "auth/reset.html",
            status_code=422,
            user=None,
            token=token,
            errors=exc.errors,
        )
    if user_id is None:
        return render(
            request, "auth/reset.html", status_code=410, user=None, token=token, invalid=True
        )
    return RedirectResponse("/login?reset=1", status_code=303)

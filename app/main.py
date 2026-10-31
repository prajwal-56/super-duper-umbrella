"""FastAPI application. Routers auto-register; nobody edits this file to add a page."""

from __future__ import annotations

import importlib
import pkgutil
import time
from contextlib import asynccontextmanager
from pathlib import Path

import psycopg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app import clock, db
from app.config import settings
from app.templating import render

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


def _discover_routes(application: FastAPI) -> list[tuple[str, str, str]]:
    """Import every app/routes/*.py, include its `router`, collect its `NAV`."""
    nav: list[tuple[str, str, str]] = []
    from app import routes as routes_package

    for module_info in sorted(pkgutil.iter_modules(routes_package.__path__), key=lambda m: m.name):
        module = importlib.import_module(f"app.routes.{module_info.name}")
        router = getattr(module, "router", None)
        if router is not None:
            application.include_router(router)
        nav.extend(getattr(module, "NAV", []))
    return nav


@asynccontextmanager
async def lifespan(application: FastAPI):
    if settings.seed_on_boot:
        from scripts.seed_demo import seed_if_empty

        seed_if_empty()
    try:
        from app.auth.service import ensure_admin

        if ensure_admin():
            print("startup: created the first admin account from ADMIN_EMAIL")
    except psycopg.OperationalError as exc:
        print(f"startup: database not reachable ({exc}); /health will report it")
    yield
    db.close_pool()


app = FastAPI(title="Brightloop Ledger", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.state.nav = _discover_routes(app)


def _bad_origin(request: Request) -> bool:
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return False
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    base = settings.app_base_url
    if origin:
        return not origin.startswith(base)
    if referer:
        return not referer.startswith(base)
    return False  # non-browser clients (curl, tests) send neither


@app.middleware("http")
async def request_context(request: Request, call_next):
    started = time.perf_counter()  # real-time-ok: request timing
    request.state.t_start = started
    request.state.user = None
    request.state.clock_state = None
    path = request.url.path
    if path.startswith("/static") or path == "/health":
        return await call_next(request)

    if _bad_origin(request):
        return JSONResponse({"detail": "Request origin is not allowed"}, status_code=403)

    from app.deps import current_user

    request.state.user = current_user(request)
    state = clock.get_state()
    request.state.clock_state = {"mode": state["mode"], "today": state["today"]}

    response = await call_next(request)
    duration = (time.perf_counter() - started) * 1000  # real-time-ok: request timing
    response.headers["X-Render-Time-Ms"] = f"{duration:.0f}"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


@app.get("/health")
def health() -> JSONResponse:
    database_up = db.ping()
    return JSONResponse(
        {"status": "ok", "database": "up" if database_up else "down"},
        status_code=200 if database_up else 503,
    )


@app.get("/")
def index(request: Request):
    from app.deps import current_user

    user = current_user(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return render(request, "home.html", user=user)


@app.exception_handler(403)
def forbidden(request: Request, exc):
    return render(
        request,
        "error.html",
        status_code=403,
        title="Not allowed",
        message="Your role does not have access to this page.",
    )


@app.exception_handler(404)
def not_found(request: Request, exc):
    return render(
        request,
        "error.html",
        status_code=404,
        title="Page not found",
        message="The page you asked for does not exist.",
    )

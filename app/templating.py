"""Shared Jinja2 environment and the one render helper every route uses.

`base.html` receives: user, nav (already filtered by role), system_date,
simulated, duration_ms. Routes pass page-specific context.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.money import fmt
from app.permissions import can

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["settings"] = settings
templates.env.globals["currency"] = settings.currency_code
templates.env.filters["money"] = fmt
templates.env.filters["can"] = can


def elapsed_ms(request: Request) -> int:
    started = getattr(request.state, "t_start", None)
    if started is None:
        return 0
    return int((time.perf_counter() - started) * 1000)  # real-time-ok: request timing


def render(
    request: Request,
    template: str,
    *,
    user: Any = None,
    status_code: int = 200,
    **context: Any,
):
    """Render a template with the shared layout context."""
    if user is None:
        user = getattr(request.state, "user", None)
    raw_nav = getattr(request.state, "nav", []) or []
    nav_items = [
        (label, path)
        for label, path, permission in raw_nav
        if user is not None and can(user.role, permission)
    ]
    clock_state = getattr(request.state, "clock_state", None) or {}
    payload = dict(context)
    payload.update(
        request=request,
        user=user,
        nav=nav_items,
        system_date=clock_state.get("today"),
        simulated=clock_state.get("mode") == "simulated",
        duration_ms=elapsed_ms(request),
    )
    return templates.TemplateResponse(request, template, payload, status_code=status_code)

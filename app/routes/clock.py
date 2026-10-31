"""Simulated clock controls (A). Demo only: `clock:admin` is in DEMO_ONLY."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app import clock
from app.deps import User, require
from app.templating import render

router = APIRouter(tags=["clock"])
NAV: list[tuple[str, str, str]] = [("Clock", "/app/clock", "clock:admin")]

ClockAdmin = Annotated[User, Depends(require("clock:admin"))]


def _page(request: Request, user: User, *, status_code: int = 200, errors=None, done=False):
    return render(
        request,
        "clock/index.html",
        status_code=status_code,
        user=user,
        state=clock.get_state(),
        errors=errors or [],
        done=done,
    )


@router.get("/app/clock")
def clock_page(request: Request, user: ClockAdmin, done: str = ""):
    return _page(request, user, done=bool(done))


@router.post("/app/clock")
def clock_action(
    request: Request,
    user: ClockAdmin,
    action: str = Form(""),
    days: str = Form(""),
    months: str = Form(""),
    day: str = Form(""),
):
    if action == "advance":
        try:
            step_days = int(days or 0)
            step_months = int(months or 0)
        except ValueError:
            return _page(
                request,
                user,
                status_code=422,
                errors=["Days and months must be whole numbers."],
            )
        if step_days < 0 or step_months < 0:
            return _page(
                request, user, status_code=422, errors=["The clock only moves forward."]
            )
        if step_days == 0 and step_months == 0:
            return _page(
                request,
                user,
                status_code=422,
                errors=["Enter a number of days or months to advance."],
            )
        clock.advance(days=step_days, months=step_months, actor_id=user.id)
    elif action == "set":
        try:
            target = date.fromisoformat((day or "").strip())
        except ValueError:
            return _page(
                request,
                user,
                status_code=422,
                errors=["Enter a date as YYYY-MM-DD."],
            )
        clock.set_simulated(target, actor_id=user.id)
    elif action == "reset":
        clock.reset(actor_id=user.id)
    else:
        return _page(request, user, status_code=422, errors=["Choose an action."])
    return RedirectResponse("/app/clock?done=1", status_code=303)

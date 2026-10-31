"""Demo reset and control endpoints (owner: A).

Protected by DEMO_MODE configuration (BUILD_PLAN §18, A-15).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.deps import User, require
from app.templating import render

router = APIRouter(tags=["demo"])

DemoAdmin = Annotated[User, Depends(require("demo:admin"))]


@router.get("/app/demo/reset")
def demo_reset_page(
    request: Request,
    _user: DemoAdmin,
):
    """Confirm page for resetting the demo database."""
    return render(
        request,
        "demo/reset.html",
        title="Reset Demo Dataset",
    )


@router.post("/app/demo/reset")
def demo_reset_submit(
    request: Request,
    confirm: Annotated[str, Form(...)],
    _user: DemoAdmin,
):
    """Perform database purge and re-seed in DEMO_MODE."""
    if confirm != "RESET":
        return render(
            request,
            "demo/reset.html",
            error="Type RESET exactly to confirm.",
            status_code=422,
        )

    from scripts.seed_demo import reset_database, seed

    reset_database()
    seed()
    return RedirectResponse("/app/dashboard?seeded=1", status_code=303)

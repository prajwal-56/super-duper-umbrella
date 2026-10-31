"""Integrity page route. Owner: D."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.db import conn
from app.deps import User, require
from app.services.invariants import run_all
from app.templating import render

router = APIRouter(tags=["integrity"])
NAV = [("Integrity", "/app/integrity", "report:read")]

ReportRead = Annotated[User, Depends(require("report:read"))]


@router.get("/app/integrity")
def integrity_page(
    request: Request,
    user: ReportRead,
):
    with conn() as c:
        results = run_all(c)
    all_ok = all(r.ok for r in results)
    return render(
        request,
        "integrity/index.html",
        results=results,
        all_ok=all_ok,
    )


@router.post("/app/integrity/run")
def integrity_run(
    request: Request,
    user: ReportRead,
):
    return RedirectResponse("/app/integrity", status_code=303)

"""Outbox viewer (A). Every email the system wrote, newest first."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.db import fetch_all
from app.deps import User, require
from app.templating import render

router = APIRouter(tags=["outbox"])
NAV: list[tuple[str, str, str]] = [("Outbox", "/app/outbox", "report:read")]

ReadReports = Annotated[User, Depends(require("report:read"))]

PAGE_SIZE = 50


def _kinds() -> list[str]:
    rows = fetch_all("SELECT DISTINCT kind FROM emails_outbox ORDER BY kind")
    return [str(row["kind"]) for row in rows]


def _emails(kind: str) -> list[dict]:
    if kind:
        return fetch_all(
            "SELECT id, kind, to_email, subject, body_html, link, smtp_status, created_at "
            "FROM emails_outbox WHERE kind = %s ORDER BY id DESC LIMIT %s",
            (kind, PAGE_SIZE),
        )
    return fetch_all(
        "SELECT id, kind, to_email, subject, body_html, link, smtp_status, created_at "
        "FROM emails_outbox ORDER BY id DESC LIMIT %s",
        (PAGE_SIZE,),
    )


@router.get("/app/outbox")
def outbox_page(request: Request, user: ReadReports, kind: str = ""):
    kinds = _kinds()
    if kind not in kinds:
        kind = ""
    return render(
        request,
        "outbox/index.html",
        user=user,
        emails=_emails(kind),
        kinds=kinds,
        kind=kind,
        page_size=PAGE_SIZE,
    )

"""Internal cron endpoints (owner: B)."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.jobs import daily

router = APIRouter(tags=["internal"])


@router.post("/internal/daily")
def daily_job(request: Request) -> JSONResponse:
    supplied = request.headers.get("X-Cron-Token", "")
    if not settings.cron_token or not secrets.compare_digest(
        supplied, settings.cron_token
    ):
        return JSONResponse({"detail": "Forbidden"}, status_code=403)
    return JSONResponse(daily.run())

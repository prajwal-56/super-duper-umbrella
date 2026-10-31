"""Billing-run pages (A page, B logic): list, run, result."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app import clock
from app.db import fetch_all, fetch_one
from app.deps import User, require
from app.services import billing
from app.templating import render

router = APIRouter(tags=["billing-runs"])
NAV: list[tuple[str, str, str]] = [("Billing runs", "/app/billing-runs", "billing:run")]

RunBilling = Annotated[User, Depends(require("billing:run"))]

MODES = ("dry", "live")


def _runs() -> list[dict]:
    return fetch_all(
        "SELECT id, mode, as_of, status, started_at, considered, invoices_created, "
        "amount_minor, blocked_duplicates FROM billing_runs ORDER BY id DESC LIMIT 20"
    )


def _run(run_id: int) -> dict | None:
    return fetch_one(
        "SELECT id, mode, as_of, status, started_at, finished_at, considered, "
        "invoices_created, amount_minor, blocked_duplicates, integrity_summary "
        "FROM billing_runs WHERE id = %s",
        (run_id,),
    )


def _items(run_id: int, query: str) -> list[dict]:
    pattern = f"%{query}%"
    return fetch_all(
        """
        SELECT i.id, i.subscription_id, i.disposition, i.periods_billed, i.invoice_ids,
               i.reason, i.error, c.name AS customer_name
        FROM billing_run_items i
        JOIN subscriptions s ON s.id = i.subscription_id
        LEFT JOIN customers c ON c.id = s.customer_id
        WHERE i.run_id = %s
          AND (%s = '' OR c.name ILIKE %s OR CAST(i.subscription_id AS TEXT) = %s)
        ORDER BY i.id
        """,
        (run_id, query, pattern, query),
    )


@router.get("/app/billing-runs")
def runs_page(request: Request, user: RunBilling):
    return render(
        request,
        "billing_runs/index.html",
        user=user,
        runs=_runs(),
        today=clock.today().isoformat(),
        modes=MODES,
    )


@router.post("/app/billing-runs")
def run_billing_action(
    request: Request,
    user: RunBilling,
    as_of: str = Form(""),
    mode: str = Form("dry"),
    auto_confirm: str = Form(""),
):
    errors = []
    try:
        run_date = date.fromisoformat((as_of or "").strip())
    except ValueError:
        run_date = clock.today()
        errors.append("Enter the as-of date as YYYY-MM-DD.")
    if mode not in MODES:
        errors.append("Choose a dry run or a live run.")
    if errors:
        return render(
            request,
            "billing_runs/index.html",
            status_code=422,
            user=user,
            runs=_runs(),
            today=run_date.isoformat(),
            modes=MODES,
            errors=errors,
            as_of=as_of,
            mode=mode,
            auto_confirm=bool(auto_confirm),
        )

    run_id = billing.run_billing(
        run_date, mode, user.id, auto_confirm=bool(auto_confirm)
    )
    return RedirectResponse(f"/app/billing-runs/{run_id}", status_code=303)


@router.get("/app/billing-runs/{run_id}")
def run_page(request: Request, run_id: int, user: RunBilling, q: str = ""):
    run = _run(run_id)
    if run is None:
        return render(
            request,
            "error.html",
            status_code=404,
            title="Run not found",
            message="That billing run does not exist.",
        )
    items = _items(run_id, q.strip())
    return render(
        request,
        "billing_runs/show.html",
        user=user,
        run=run,
        items=items,
        q=q.strip(),
    )

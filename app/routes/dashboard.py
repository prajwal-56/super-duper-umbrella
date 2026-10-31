"""Dashboard and overdue routes. Owner: D."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.db import conn
from app.deps import User, require
from app.services import invoices as inv_svc
from app.services import reports as rpt_svc
from app.templating import render

router = APIRouter(tags=["dashboard"])
NAV = [
    ("Dashboard", "/app/dashboard", "report:read"),
    ("Overdue", "/app/overdue", "report:read"),
]

ReportRead = Annotated[User, Depends(require("report:read"))]
InvoiceWrite = Annotated[User, Depends(require("invoice:write"))]


@router.get("/app/dashboard")
def dashboard(
    request: Request,
    user: ReportRead,
):
    filters: dict = {}
    with conn() as c:
        data = rpt_svc.dashboard(c, filters)
    return render(request, "dashboard/index.html", **data)


@router.get("/app/overdue")
def overdue_list(
    request: Request,
    user: ReportRead,
    page: int = 1,
    customer_id: str = "",
):
    filters: dict = {}
    if customer_id:
        try:
            filters["customer_id"] = int(customer_id)
        except ValueError:
            pass

    with conn() as c:
        data = rpt_svc.overdue(c, filters, page=page, page_size=50)
    return render(request, "dashboard/overdue.html", **data, customer_id_filter=customer_id)


@router.post("/app/overdue/{invoice_id}/remind")
def send_reminder(
    request: Request,
    invoice_id: int,
    user: InvoiceWrite,
):
    """Send a payment reminder for an overdue invoice (writes to outbox)."""
    try:
        with conn() as c:
            inv_svc.send(c, invoice_id, user.id)
    except ValueError as exc:
        return render(request, "error.html", status_code=422, detail=str(exc))
    return RedirectResponse("/app/overdue", status_code=303)

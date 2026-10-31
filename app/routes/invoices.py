"""Invoice routes. Owner: D."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.db import conn
from app.deps import User, require
from app.services import invoices as inv_svc
from app.templating import render

router = APIRouter(prefix="/app/invoices", tags=["invoices"])
NAV = [("Invoices", "/app/invoices", "invoice:read")]

InvoiceRead = Annotated[User, Depends(require("invoice:read"))]
InvoiceWrite = Annotated[User, Depends(require("invoice:write"))]


@router.get("")
def invoice_list(
    request: Request,
    user: InvoiceRead,
    status: str = "",
    page: int = 1,
):
    with conn() as c:
        result = inv_svc.list_invoices(
            c,
            status=status or None,
            page=page,
        )
    return render(request, "invoices/list.html", **result, status_filter=status)


@router.get("/{invoice_id}")
def invoice_detail(
    request: Request,
    invoice_id: int,
    user: InvoiceRead,
):
    with conn() as c:
        invoice = inv_svc.get_invoice(c, invoice_id)
    if invoice is None:
        return render(request, "error.html", status_code=404, detail="Invoice not found")
    return render(request, "invoices/detail.html", invoice=invoice)


@router.get("/{invoice_id}/print")
def invoice_print(
    request: Request,
    invoice_id: int,
    user: InvoiceRead,
):
    with conn() as c:
        invoice = inv_svc.get_invoice(c, invoice_id)
    if invoice is None:
        return render(request, "error.html", status_code=404, detail="Invoice not found")
    return render(request, "invoices/print.html", invoice=invoice)


@router.post("/{invoice_id}/confirm")
def invoice_confirm(
    request: Request,
    invoice_id: int,
    user: InvoiceWrite,
):
    try:
        with conn() as c:
            inv_svc.confirm(c, invoice_id, user.id)
    except ValueError as exc:
        return render(
            request,
            "error.html",
            status_code=422,
            detail=str(exc),
        )
    return RedirectResponse(f"/app/invoices/{invoice_id}", status_code=303)


@router.post("/{invoice_id}/cancel")
def invoice_cancel(
    request: Request,
    invoice_id: int,
    user: InvoiceWrite,
    reason: str = Form(""),
):
    try:
        with conn() as c:
            inv_svc.cancel(c, invoice_id, user.id, reason or "cancelled by staff")
    except ValueError as exc:
        return render(request, "error.html", status_code=422, detail=str(exc))
    return RedirectResponse(f"/app/invoices/{invoice_id}", status_code=303)


@router.post("/{invoice_id}/send")
def invoice_send(
    request: Request,
    invoice_id: int,
    user: InvoiceWrite,
):
    try:
        with conn() as c:
            inv_svc.send(c, invoice_id, user.id)
    except ValueError as exc:
        return render(request, "error.html", status_code=422, detail=str(exc))
    return RedirectResponse(f"/app/invoices/{invoice_id}", status_code=303)

"""Payment routes. Owner: D."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.db import conn
from app.deps import User, require
from app.money import parse as money_parse
from app.services import payments as pay_svc
from app.templating import render

router = APIRouter(prefix="/app/payments", tags=["payments"])
NAV: list[tuple[str, str, str]] = []

PaymentWrite = Annotated[User, Depends(require("payment:write"))]


@router.post("/record")
def record_payment(
    request: Request,
    user: PaymentWrite,
    invoice_id: Annotated[int, Form()],
    method: Annotated[str, Form()],
    amount: Annotated[str, Form()],
    paid_on: Annotated[date, Form()],
    note: Annotated[str, Form()] = "",
    idempotency_key: Annotated[str, Form()] = "",
):
    errors = []
    amount_minor = 0
    try:
        amount_minor = money_parse(amount)
        if amount_minor <= 0:
            errors.append("Amount must be positive.")
    except ValueError as exc:
        errors.append(str(exc))

    if errors:
        return render(
            request,
            "error.html",
            status_code=422,
            detail="; ".join(errors),
        )

    try:
        with conn() as c:
            pay_svc.record(
                c,
                invoice_id=invoice_id,
                method=method,
                amount_minor=amount_minor,
                paid_on=paid_on,
                note=note or None,
                actor_id=user.id,
                idempotency_key=idempotency_key or None,
            )
    except Exception as exc:
        return render(request, "error.html", status_code=422, detail=str(exc))

    return RedirectResponse(f"/app/invoices/{invoice_id}", status_code=303)

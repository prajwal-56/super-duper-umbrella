from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.services.payments import record
from app.db import get_conn
from app.auth import require

router = APIRouter(prefix="/app/payments", tags=["payments"])
templates = Jinja2Templates(directory="app/templates")


@router.post("/{invoice_id}")
@require("payment:write")
async def record_payment(request: Request, invoice_id: int):
    method = request.form["method"]
    amount = int(request.form["amount_minor"])
    paid_on = request.form.get("paid_on") or None
    note = request.form.get("note", "")
    idempotency_key = request.form.get("idempotency_key", None)
    conn = get_conn()
    record(conn, invoice_id, method, amount, paid_on, note, request.user["id"], idempotency_key)
    return RedirectResponse(url=f"/app/invoices/{invoice_id}", status_code=302)
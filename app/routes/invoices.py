from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.services.invoices import confirm, confirm_many, cancel, send, get_for_customer
from app.db import get_conn
from app.auth import require

router = APIRouter(prefix="/app/invoices", tags=["invoices"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
@require("billing:run")
async def list_invoices(request: Request):
    conn = get_conn()
    # ... list invoices with filters
    return templates.TemplateResponse("invoices/list.html", {"request": request})


@router.get("/{invoice_id}", response_class=HTMLResponse)
@require("invoice:read")
async def invoice_detail(request: Request, invoice_id: int):
    conn = get_conn()
    data = get_for_customer(conn, invoice_id, request.user["customer_id"])
    if not data and request.user["role"] != "admin":
        raise HTTPException(404)
    return templates.TemplateResponse("invoices/detail.html", {"request": request, "data": data})


@router.post("/{invoice_id}/confirm")
@require("invoice:write")
async def invoice_confirm(request: Request, invoice_id: int):
    conn = get_conn()
    confirm(conn, invoice_id, request.user["id"])
    return RedirectResponse(url="/app/invoices", status_code=302)


@router.post("/{invoice_id}/cancel")
@require("invoice:write")
async def invoice_cancel(request: Request, invoice_id: int):
    conn = get_conn()
    cancel(conn, invoice_id, request.user["id"], reason=request.form.get("reason", ""))
    return RedirectResponse(url="/app/invoices", status_code=302)


@router.post("/{invoice_id}/send")
@require("invoice:write")
async def invoice_send(request: Request, invoice_id: int):
    conn = get_conn()
    send(conn, invoice_id, request.user["id"])
    return RedirectResponse(url="/app/invoices", status_code=302)
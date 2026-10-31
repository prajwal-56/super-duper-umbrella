from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.services.reports import dashboard, overdue
from app.db import get_conn
from app.auth import require

router = APIRouter(prefix="/app", tags=["reports"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
@require("report:read")
async def dashboard_page(request: Request):
    conn = get_conn()
    filters = {}
    # Parse query params for filters
    ds = request.query_params.get("date_start")
    de = request.query_params.get("date_end")
    if ds: filters["date_from"] = ds
    if de: filters["date_to"] = de
    cid = request.query_params.get("customer_id")
    if cid: filters["customer_id"] = int(cid)
    d = dashboard(conn, filters)
    return templates.TemplateResponse("dashboard/index.html", {"request": request, "dashboard": d, "filters": filters})


@router.get("/overdue", response_class=HTMLResponse)
@require("report:read")
async def overdue_page(request: Request):
    conn = get_conn()
    page = int(request.query_params.get("page", 1))
    p = int(request.query_params.get("page_size", 20))
    d = overdue(conn, filters={}, page=page, page_size=p)
    return templates.TemplateResponse("overdue/index.html", {"request": request, "overdue": d})
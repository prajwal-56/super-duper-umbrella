"""Catalog pages: taxes, payment terms, products (+ variants), plans (+ price
overrides).  All under /app/catalog/.  Owner: C.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.db import conn
from app.deps import User, require
from app.money import parse
from app.services import catalog as svc
from app.templating import render

router = APIRouter(prefix="/app/catalog", tags=["catalog"])
NAV: list[tuple[str, str, str]] = [
    ("Catalog", "/app/catalog/products", "catalog:read"),
]


# ── helpers ──────────────────────────────────────────────────────────────────

def _int(value: str | None, default: int = 0) -> int:
    if value is None or str(value).strip() == "":
        return default
    return int(value)


def _bps_from_percent(text: str) -> int:
    """'18' or '18.5' → basis points (1800 or 1850)."""
    from decimal import ROUND_HALF_UP, Decimal
    d = Decimal(text.strip())
    return int((d * 100).to_integral_value(rounding=ROUND_HALF_UP))


def _percent_from_bps(bps: int) -> str:
    """1800 → '18.00'."""
    whole, frac = divmod(bps, 100)
    return f"{whole}.{frac:02d}"


# ═══════════════════════════════════════════════════════════════════════════
#  TAXES
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/taxes")
def tax_list(request: Request, user: User = Depends(require("catalog:read"))):
    with conn() as c:
        taxes = svc.list_taxes(c)
    return render(request, "catalog/taxes.html", taxes=taxes)


@router.get("/taxes/new")
def tax_new(request: Request, user: User = Depends(require("catalog:write"))):
    return render(request, "catalog/tax_form.html", tax=None)


@router.post("/taxes/new")
def tax_create(
    request: Request,
    user: User = Depends(require("catalog:write")),
    name: str = Form(""),
    rate_percent: str = Form("0"),
    inclusive: bool = Form(False),
):
    errors = []
    name = name.strip()
    if not name:
        errors.append("Name is required.")
    try:
        rate_bps = _bps_from_percent(rate_percent)
    except Exception:
        errors.append("Rate must be a number (e.g. 18 for 18%).")
        rate_bps = 0
    if errors:
        return render(request, "catalog/tax_form.html", status_code=422,
                      tax=None, errors=errors, name=name,
                      rate_percent=rate_percent, inclusive=inclusive)
    with conn() as c:
        svc.create_tax(c, name, rate_bps, inclusive, user.id)
    return RedirectResponse("/app/catalog/taxes", status_code=303)


@router.get("/taxes/{tax_id}")
def tax_edit(request: Request, tax_id: int,
             user: User = Depends(require("catalog:write"))):
    with conn() as c:
        tax = svc.get_tax(c, tax_id)
    if tax is None:
        return render(request, "error.html", status_code=404,
                      title="Not found", message="Tax rule not found.")
    return render(request, "catalog/tax_form.html", tax=tax)


@router.post("/taxes/{tax_id}")
def tax_update(
    request: Request,
    tax_id: int,
    user: User = Depends(require("catalog:write")),
    name: str = Form(""),
    rate_percent: str = Form("0"),
    inclusive: bool = Form(False),
    active: bool = Form(False),
):
    errors = []
    name = name.strip()
    if not name:
        errors.append("Name is required.")
    try:
        rate_bps = _bps_from_percent(rate_percent)
    except Exception:
        errors.append("Rate must be a number.")
        rate_bps = 0
    if errors:
        with conn() as c:
            tax = svc.get_tax(c, tax_id)
        return render(request, "catalog/tax_form.html", status_code=422,
                      tax=tax, errors=errors, name=name,
                      rate_percent=rate_percent, inclusive=inclusive, active=active)
    with conn() as c:
        svc.update_tax(c, tax_id, name, rate_bps, inclusive, active, user.id)
    return RedirectResponse("/app/catalog/taxes", status_code=303)


# ═══════════════════════════════════════════════════════════════════════════
#  PAYMENT TERMS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/terms")
def terms_list(request: Request, user: User = Depends(require("catalog:read"))):
    with conn() as c:
        terms = svc.list_payment_terms(c)
    return render(request, "catalog/terms.html", terms=terms)


@router.get("/terms/new")
def term_new(request: Request, user: User = Depends(require("catalog:write"))):
    return render(request, "catalog/term_form.html", term=None)


@router.post("/terms/new")
def term_create(
    request: Request,
    user: User = Depends(require("catalog:write")),
    name: str = Form(""),
    due_days: str = Form("0"),
):
    errors = []
    name = name.strip()
    if not name:
        errors.append("Name is required.")
    try:
        days = int(due_days)
        if days < 0:
            raise ValueError
    except ValueError:
        errors.append("Due days must be a non-negative number.")
        days = 0
    if errors:
        return render(request, "catalog/term_form.html", status_code=422,
                      term=None, errors=errors, name=name, due_days=due_days)
    with conn() as c:
        svc.create_payment_term(c, name, days, user.id)
    return RedirectResponse("/app/catalog/terms", status_code=303)


@router.get("/terms/{term_id}")
def term_edit(request: Request, term_id: int,
              user: User = Depends(require("catalog:write"))):
    with conn() as c:
        term = svc.get_payment_term(c, term_id)
    if term is None:
        return render(request, "error.html", status_code=404,
                      title="Not found", message="Payment term not found.")
    return render(request, "catalog/term_form.html", term=term)


@router.post("/terms/{term_id}")
def term_update(
    request: Request,
    term_id: int,
    user: User = Depends(require("catalog:write")),
    name: str = Form(""),
    due_days: str = Form("0"),
):
    errors = []
    name = name.strip()
    if not name:
        errors.append("Name is required.")
    try:
        days = int(due_days)
        if days < 0:
            raise ValueError
    except ValueError:
        errors.append("Due days must be a non-negative number.")
        days = 0
    if errors:
        with conn() as c:
            term = svc.get_payment_term(c, term_id)
        return render(request, "catalog/term_form.html", status_code=422,
                      term=term, errors=errors, name=name, due_days=due_days)
    with conn() as c:
        svc.update_payment_term(c, term_id, name, days, user.id)
    return RedirectResponse("/app/catalog/terms", status_code=303)


# ═══════════════════════════════════════════════════════════════════════════
#  PRODUCTS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/products")
def product_list(request: Request, user: User = Depends(require("catalog:read"))):
    with conn() as c:
        products = svc.list_products(c)
        taxes = svc.list_taxes(c)
    return render(request, "catalog/products.html", products=products, taxes=taxes)


@router.get("/products/new")
def product_new(request: Request, user: User = Depends(require("catalog:write"))):
    with conn() as c:
        taxes = svc.list_taxes(c)
    return render(request, "catalog/product_form.html", product=None, taxes=taxes)


@router.post("/products/new")
def product_create(
    request: Request,
    user: User = Depends(require("catalog:write")),
    name: str = Form(""),
    product_type: str = Form("service"),
    sales_price: str = Form("0"),
    cost_price: str = Form("0"),
    tax_id: str = Form(""),
    notes: str = Form(""),
):
    errors = []
    name = name.strip()
    if not name:
        errors.append("Name is required.")
    try:
        sp = parse(sales_price)
    except ValueError:
        errors.append("Sales price is not valid.")
        sp = 0
    try:
        cp = parse(cost_price)
    except ValueError:
        errors.append("Cost price is not valid.")
        cp = 0
    tid = int(tax_id) if tax_id.strip() else None
    if errors:
        with conn() as c:
            taxes = svc.list_taxes(c)
        return render(request, "catalog/product_form.html", status_code=422,
                      product=None, taxes=taxes, errors=errors,
                      name=name, product_type=product_type,
                      sales_price=sales_price, cost_price=cost_price,
                      tax_id=tax_id, notes=notes)
    with conn() as c:
        pid = svc.create_product(c, name, product_type, sp, cp, tid,
                                  notes.strip() or None, user.id)
    return RedirectResponse(f"/app/catalog/products/{pid}", status_code=303)


@router.get("/products/{product_id}")
def product_detail(request: Request, product_id: int,
                   user: User = Depends(require("catalog:read"))):
    with conn() as c:
        product = svc.get_product(c, product_id)
        if product is None:
            return render(request, "error.html", status_code=404,
                          title="Not found", message="Product not found.")
        variants = svc.list_variants(c, product_id)
        overrides = svc.list_price_overrides_for_product(c, product_id)
        taxes = svc.list_taxes(c)
        plans = svc.list_plans(c, active_only=True)
    return render(request, "catalog/product_detail.html",
                  product=product, variants=variants, overrides=overrides,
                  taxes=taxes, plans=plans)


@router.get("/products/{product_id}/edit")
def product_edit(request: Request, product_id: int,
                 user: User = Depends(require("catalog:write"))):
    with conn() as c:
        product = svc.get_product(c, product_id)
        if product is None:
            return render(request, "error.html", status_code=404,
                          title="Not found", message="Product not found.")
        taxes = svc.list_taxes(c)
    return render(request, "catalog/product_form.html", product=product, taxes=taxes)


@router.post("/products/{product_id}/edit")
def product_update(
    request: Request,
    product_id: int,
    user: User = Depends(require("catalog:write")),
    name: str = Form(""),
    product_type: str = Form("service"),
    sales_price: str = Form("0"),
    cost_price: str = Form("0"),
    tax_id: str = Form(""),
    notes: str = Form(""),
    active: bool = Form(False),
):
    errors = []
    name = name.strip()
    if not name:
        errors.append("Name is required.")
    try:
        sp = parse(sales_price)
    except ValueError:
        errors.append("Sales price is not valid.")
        sp = 0
    try:
        cp = parse(cost_price)
    except ValueError:
        errors.append("Cost price is not valid.")
        cp = 0
    tid = int(tax_id) if tax_id.strip() else None
    if errors:
        with conn() as c:
            product = svc.get_product(c, product_id)
            taxes = svc.list_taxes(c)
        return render(request, "catalog/product_form.html", status_code=422,
                      product=product, taxes=taxes, errors=errors,
                      name=name, product_type=product_type,
                      sales_price=sales_price, cost_price=cost_price,
                      tax_id=tax_id, notes=notes, active=active)
    with conn() as c:
        svc.update_product(c, product_id, name, product_type, sp, cp, tid,
                           notes.strip() or None, active, user.id)
    return RedirectResponse(f"/app/catalog/products/{product_id}", status_code=303)


# ── Variants (nested under product) ─────────────────────────────────────

@router.post("/products/{product_id}/variants")
def variant_create(
    request: Request,
    product_id: int,
    user: User = Depends(require("catalog:write")),
    attribute: str = Form(""),
    value: str = Form(""),
    extra_price: str = Form("0"),
):
    errors = []
    attribute = attribute.strip()
    value = value.strip()
    if not attribute:
        errors.append("Attribute is required.")
    if not value:
        errors.append("Value is required.")
    try:
        ep = parse(extra_price)
    except ValueError:
        errors.append("Extra price is not valid.")
        ep = 0
    if errors:
        with conn() as c:
            product = svc.get_product(c, product_id)
            variants = svc.list_variants(c, product_id)
            overrides = svc.list_price_overrides_for_product(c, product_id)
            taxes = svc.list_taxes(c)
            plans = svc.list_plans(c, active_only=True)
        return render(request, "catalog/product_detail.html", status_code=422,
                      product=product, variants=variants, overrides=overrides,
                      taxes=taxes, plans=plans,
                      variant_errors=errors, v_attribute=attribute,
                      v_value=value, v_extra_price=extra_price)
    with conn() as c:
        svc.create_variant(c, product_id, attribute, value, ep, user.id)
    return RedirectResponse(f"/app/catalog/products/{product_id}", status_code=303)


@router.post("/products/{product_id}/variants/{variant_id}/delete")
def variant_delete(
    request: Request,
    product_id: int,
    variant_id: int,
    user: User = Depends(require("catalog:write")),
):
    with conn() as c:
        svc.delete_variant(c, variant_id, user.id)
    return RedirectResponse(f"/app/catalog/products/{product_id}", status_code=303)


# ── Price overrides (nested under product) ──────────────────────────────

@router.post("/products/{product_id}/overrides")
def override_set(
    request: Request,
    product_id: int,
    user: User = Depends(require("catalog:write")),
    plan_id: str = Form(""),
    price: str = Form("0"),
):
    errors = []
    if not plan_id.strip():
        errors.append("Plan is required.")
    try:
        pm = parse(price)
    except ValueError:
        errors.append("Price is not valid.")
        pm = 0
    if errors:
        with conn() as c:
            product = svc.get_product(c, product_id)
            variants = svc.list_variants(c, product_id)
            overrides = svc.list_price_overrides_for_product(c, product_id)
            taxes = svc.list_taxes(c)
            plans = svc.list_plans(c, active_only=True)
        return render(request, "catalog/product_detail.html", status_code=422,
                      product=product, variants=variants, overrides=overrides,
                      taxes=taxes, plans=plans,
                      override_errors=errors, o_plan_id=plan_id, o_price=price)
    with conn() as c:
        svc.set_price_override(c, product_id, int(plan_id), pm, user.id)
    return RedirectResponse(f"/app/catalog/products/{product_id}", status_code=303)


@router.post("/products/{product_id}/overrides/{plan_id}/delete")
def override_delete(
    request: Request,
    product_id: int,
    plan_id: int,
    user: User = Depends(require("catalog:write")),
):
    with conn() as c:
        svc.delete_price_override(c, product_id, plan_id, user.id)
    return RedirectResponse(f"/app/catalog/products/{product_id}", status_code=303)


# ═══════════════════════════════════════════════════════════════════════════
#  PLANS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/plans")
def plan_list(request: Request, user: User = Depends(require("catalog:read"))):
    with conn() as c:
        plans = svc.list_plans(c)
    return render(request, "catalog/plans.html", plans=plans)


@router.get("/plans/new")
def plan_new(request: Request, user: User = Depends(require("catalog:write"))):
    return render(request, "catalog/plan_form.html", plan=None)


@router.post("/plans/new")
def plan_create(
    request: Request,
    user: User = Depends(require("catalog:write")),
    name: str = Form(""),
    price: str = Form("0"),
    billing_interval: str = Form("month"),
    interval_count: str = Form("1"),
    min_quantity: str = Form("1"),
    available_from: str = Form(""),
    available_to: str = Form(""),
    auto_close: bool = Form(False),
    allow_early_close: bool = Form(True),
    allow_pause: bool = Form(True),
    allow_renew: bool = Form(True),
):
    errors = []
    name = name.strip()
    if not name:
        errors.append("Name is required.")
    try:
        pm = parse(price)
    except ValueError:
        errors.append("Plan fee is not valid.")
        pm = 0
    try:
        ic = int(interval_count)
        if ic < 1:
            raise ValueError
    except ValueError:
        errors.append("Interval count must be ≥ 1.")
        ic = 1
    try:
        mq = int(min_quantity)
        if mq < 1:
            raise ValueError
    except ValueError:
        errors.append("Minimum quantity must be ≥ 1.")
        mq = 1
    if billing_interval not in ("day", "week", "month", "year"):
        errors.append("Invalid billing interval.")
    if errors:
        return render(request, "catalog/plan_form.html", status_code=422,
                      plan=None, errors=errors,
                      name=name, price=price,
                      billing_interval=billing_interval,
                      interval_count=interval_count,
                      min_quantity=min_quantity,
                      available_from=available_from, available_to=available_to,
                      auto_close=auto_close, allow_early_close=allow_early_close,
                      allow_pause=allow_pause, allow_renew=allow_renew)
    with conn() as c:
        pid = svc.create_plan(c, name, pm, billing_interval, ic, mq,
                               available_from or None, available_to or None,
                               auto_close, allow_early_close,
                               allow_pause, allow_renew, user.id)
    return RedirectResponse(f"/app/catalog/plans/{pid}", status_code=303)


@router.get("/plans/{plan_id}")
def plan_detail(request: Request, plan_id: int,
                user: User = Depends(require("catalog:read"))):
    with conn() as c:
        plan = svc.get_plan(c, plan_id)
        if plan is None:
            return render(request, "error.html", status_code=404,
                          title="Not found", message="Plan not found.")
        overrides = svc.list_price_overrides(c, plan_id)
        products = svc.list_products(c, active_only=True)
    return render(request, "catalog/plan_detail.html",
                  plan=plan, overrides=overrides, products=products)


@router.get("/plans/{plan_id}/edit")
def plan_edit(request: Request, plan_id: int,
              user: User = Depends(require("catalog:write"))):
    with conn() as c:
        plan = svc.get_plan(c, plan_id)
        if plan is None:
            return render(request, "error.html", status_code=404,
                          title="Not found", message="Plan not found.")
    return render(request, "catalog/plan_form.html", plan=plan)


@router.post("/plans/{plan_id}/edit")
def plan_update(
    request: Request,
    plan_id: int,
    user: User = Depends(require("catalog:write")),
    name: str = Form(""),
    price: str = Form("0"),
    billing_interval: str = Form("month"),
    interval_count: str = Form("1"),
    min_quantity: str = Form("1"),
    available_from: str = Form(""),
    available_to: str = Form(""),
    auto_close: bool = Form(False),
    allow_early_close: bool = Form(True),
    allow_pause: bool = Form(True),
    allow_renew: bool = Form(True),
    active: bool = Form(False),
):
    errors = []
    name = name.strip()
    if not name:
        errors.append("Name is required.")
    try:
        pm = parse(price)
    except ValueError:
        errors.append("Plan fee is not valid.")
        pm = 0
    try:
        ic = int(interval_count)
        if ic < 1:
            raise ValueError
    except ValueError:
        errors.append("Interval count must be ≥ 1.")
        ic = 1
    try:
        mq = int(min_quantity)
        if mq < 1:
            raise ValueError
    except ValueError:
        errors.append("Minimum quantity must be ≥ 1.")
        mq = 1
    if errors:
        with conn() as c:
            plan = svc.get_plan(c, plan_id)
        return render(request, "catalog/plan_form.html", status_code=422,
                      plan=plan, errors=errors,
                      name=name, price=price,
                      billing_interval=billing_interval,
                      interval_count=interval_count,
                      min_quantity=min_quantity,
                      available_from=available_from, available_to=available_to,
                      auto_close=auto_close, allow_early_close=allow_early_close,
                      allow_pause=allow_pause, allow_renew=allow_renew, active=active)
    with conn() as c:
        svc.update_plan(c, plan_id, name, pm, billing_interval, ic, mq,
                        available_from or None, available_to or None,
                        auto_close, allow_early_close, allow_pause,
                        allow_renew, active, user.id)
    return RedirectResponse(f"/app/catalog/plans/{plan_id}", status_code=303)


# ── Price overrides (nested under plan) ──────────────────────────────────

@router.post("/plans/{plan_id}/overrides")
def plan_override_set(
    request: Request,
    plan_id: int,
    user: User = Depends(require("catalog:write")),
    product_id: str = Form(""),
    price: str = Form("0"),
):
    errors = []
    if not product_id.strip():
        errors.append("Product is required.")
    try:
        pm = parse(price)
    except ValueError:
        errors.append("Price is not valid.")
        pm = 0
    if errors:
        with conn() as c:
            plan = svc.get_plan(c, plan_id)
            overrides = svc.list_price_overrides(c, plan_id)
            products = svc.list_products(c, active_only=True)
        return render(request, "catalog/plan_detail.html", status_code=422,
                      plan=plan, overrides=overrides, products=products,
                      override_errors=errors, o_product_id=product_id, o_price=price)
    with conn() as c:
        svc.set_price_override(c, int(product_id), plan_id, pm, user.id)
    return RedirectResponse(f"/app/catalog/plans/{plan_id}", status_code=303)


@router.post("/plans/{plan_id}/overrides/{product_id}/delete")
def plan_override_delete(
    request: Request,
    plan_id: int,
    product_id: int,
    user: User = Depends(require("catalog:write")),
):
    with conn() as c:
        svc.delete_price_override(c, product_id, plan_id, user.id)
    return RedirectResponse(f"/app/catalog/plans/{plan_id}", status_code=303)

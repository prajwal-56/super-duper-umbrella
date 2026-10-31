"""Customer portal (A): own subscriptions, own invoices, own profile.

Every page is behind `portal:own` and every query is scoped by the customer id
from the session; another customer's id answers 404, never 403 (§14).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.db import conn
from app.deps import User, require
from app.services import lifecycle, portal
from app.templating import render

router = APIRouter(tags=["portal"])
NAV: list[tuple[str, str, str]] = [("Portal", "/portal", "portal:own")]

OwnPortal = Annotated[User, Depends(require("portal:own"))]


def _customer_id(user: User) -> int:
    if user.customer_id is None:
        raise HTTPException(status_code=404, detail="No customer record")
    return int(user.customer_id)


def _not_found(request: Request, user: User):
    return render(
        request,
        "error.html",
        status_code=404,
        user=user,
        title="Page not found",
        message="That record does not exist.",
    )


@router.get("/portal")
def portal_home(request: Request, user: OwnPortal):
    customer_id = _customer_id(user)
    with conn() as c:
        subscriptions = portal.subscriptions_for_customer(c, customer_id)
        invoices = portal.invoices_for_customer(c, customer_id)
        customer = portal.profile(c, customer_id)
    outstanding = sum(
        int(invoice["total_minor"]) - int(invoice["amount_paid_minor"])
        for invoice in invoices
        if invoice["status"] in {"confirmed", "paid"}
    )
    return render(
        request,
        "portal/index.html",
        user=user,
        customer=customer,
        subscriptions=subscriptions,
        invoices=invoices[:10],
        outstanding=outstanding,
    )


def _subscription_page(
    request: Request,
    user: User,
    subscription: dict,
    lines: list[dict],
    invoices: list[dict],
    actions: list[str],
    *,
    status_code: int = 200,
    errors: list[str] | None = None,
    done: bool = False,
):
    return render(
        request,
        "portal/subscription.html",
        status_code=status_code,
        user=user,
        subscription=subscription,
        lines=lines,
        invoices=invoices,
        actions=actions,
        errors=errors or [],
        done=done,
    )


def _load_subscription(c, subscription_id: int, customer_id: int, role: str):
    subscription = portal.subscription_for_customer(c, subscription_id, customer_id)
    if subscription is None:
        return None, [], [], []
    lines = portal.subscription_lines(c, subscription_id)
    invoices = [
        invoice
        for invoice in portal.invoices_for_customer(c, customer_id)
        if int(invoice["subscription_id"]) == subscription_id
    ]
    actions = lifecycle.allowed_actions(c, subscription_id, role)
    return subscription, lines, invoices, actions


@router.get("/portal/subscriptions/{subscription_id}")
def portal_subscription(request: Request, subscription_id: int, user: OwnPortal, done: str = ""):
    customer_id = _customer_id(user)
    with conn() as c:
        subscription, lines, invoices, actions = _load_subscription(
            c, subscription_id, customer_id, user.role
        )
    if subscription is None:
        return _not_found(request, user)
    return _subscription_page(
        request, user, subscription, lines, invoices, actions, done=bool(done)
    )


@router.post("/portal/subscriptions/{subscription_id}/action")
def portal_action(
    request: Request,
    subscription_id: int,
    user: OwnPortal,
    action: str = Form(""),
    reason: str = Form(""),
):
    customer_id = _customer_id(user)
    with conn() as c:
        subscription, lines, invoices, actions = _load_subscription(
            c, subscription_id, customer_id, user.role
        )
        if subscription is None:
            return _not_found(request, user)
        if action not in actions:
            return _subscription_page(
                request,
                user,
                subscription,
                lines,
                invoices,
                actions,
                status_code=409,
                errors=["That action is not available for this subscription now."],
            )
        if action == "pause":
            lifecycle.pause(c, subscription_id, user.id)
        elif action == "resume":
            lifecycle.resume(c, subscription_id, user.id)
        elif action == "renew":
            lifecycle.renew(c, subscription_id, user.id)
        elif action == "close":
            lifecycle.close(
                c, subscription_id, user.id, reason.strip() or "closed by the customer"
            )
        elif action == "confirm":
            lifecycle.transition(c, subscription_id, "confirmed", user.id)
        else:
            raise HTTPException(status_code=409, detail="Unknown action")
    return RedirectResponse(
        f"/portal/subscriptions/{subscription_id}?done=1", status_code=303
    )


@router.get("/portal/invoices")
def portal_invoices(request: Request, user: OwnPortal):
    customer_id = _customer_id(user)
    with conn() as c:
        invoices = portal.invoices_for_customer(c, customer_id)
    return render(request, "portal/invoices.html", user=user, invoices=invoices)


@router.get("/portal/invoices/{invoice_id}")
def portal_invoice(request: Request, invoice_id: int, user: OwnPortal):
    customer_id = _customer_id(user)
    with conn() as c:
        invoice = portal.invoice_for_customer(c, invoice_id, customer_id)
        if invoice is None:
            return _not_found(request, user)
        lines = portal.invoice_lines(c, invoice_id)
        customer = portal.profile(c, customer_id)
    return render(
        request,
        "portal/invoice.html",
        user=user,
        invoice=invoice,
        lines=lines,
        customer=customer,
    )


@router.get("/portal/profile")
def portal_profile(request: Request, user: OwnPortal):
    customer_id = _customer_id(user)
    with conn() as c:
        customer = portal.profile(c, customer_id)
    return render(request, "portal/profile.html", user=user, customer=customer)

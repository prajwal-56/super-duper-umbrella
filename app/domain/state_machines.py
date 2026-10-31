"""State machines (pure domain). Owner: B.

BUILD_PLAN §13.4 & §11.
"""

from __future__ import annotations

# Subscription states: draft, quotation, confirmed, active, closed
SUBSCRIPTION_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"quotation", "confirmed"}),
    "quotation": frozenset({"confirmed", "draft", "closed"}),
    "confirmed": frozenset({"active", "closed"}),
    "active": frozenset({"closed"}),
    "closed": frozenset(),
}

# Invoice states: draft, confirmed, paid, cancelled
INVOICE_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"confirmed", "cancelled"}),
    "confirmed": frozenset({"paid", "cancelled"}),
    "paid": frozenset(),
    "cancelled": frozenset(),
}


def can_transition(entity: str, from_status: str, to_status: str) -> bool:
    """True when `entity` ('subscription' or 'invoice') may move between the two states.

    Subscription: draft->quotation, quotation->confirmed, draft->confirmed,
    confirmed->active, active->closed (BUILD_PLAN §13.4). Invoice:
    draft->confirmed, draft->cancelled, confirmed->cancelled, confirmed->paid
    (paid only through a payment). Invalid transitions are rejected with 409.
    """
    if entity == "subscription":
        allowed = SUBSCRIPTION_TRANSITIONS.get(from_status, frozenset())
        return to_status in allowed
    elif entity == "invoice":
        allowed = INVOICE_TRANSITIONS.get(from_status, frozenset())
        return to_status in allowed
    else:
        raise ValueError(f"Unknown entity type: {entity}")

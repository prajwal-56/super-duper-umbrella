"""State machines (pure domain). Owner: B. Created as a contract stub by A."""

from __future__ import annotations

SUBSCRIPTION_TRANSITIONS: dict[str, frozenset[str]] = {}
INVOICE_TRANSITIONS: dict[str, frozenset[str]] = {}


def can_transition(entity: str, from_status: str, to_status: str) -> bool:
    """True when `entity` ('subscription' or 'invoice') may move between the two states.

    Subscription: draft->quotation, quotation->confirmed, draft->confirmed,
    confirmed->active, active->closed (BUILD_PLAN §13.4). Invoice:
    draft->confirmed, draft->cancelled, confirmed->cancelled, confirmed->paid
    (paid only through a payment). Invalid transitions are rejected with 409.
    """
    raise NotImplementedError("CONTRACT-STUB owner=B")  # CONTRACT-STUB owner=B

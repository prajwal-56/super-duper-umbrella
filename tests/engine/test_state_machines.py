import pytest

from app.domain.state_machines import (
    can_transition,
)


def test_subscription_allowed_transitions():
    assert can_transition("subscription", "draft", "quotation")
    assert can_transition("subscription", "draft", "confirmed")
    assert can_transition("subscription", "quotation", "confirmed")
    assert can_transition("subscription", "quotation", "draft")
    assert can_transition("subscription", "confirmed", "active")
    assert can_transition("subscription", "active", "closed")


def test_subscription_disallowed_transitions():
    assert not can_transition("subscription", "draft", "active")
    assert not can_transition("subscription", "closed", "active")
    assert not can_transition("subscription", "closed", "draft")
    assert not can_transition("subscription", "active", "draft")


def test_invoice_allowed_transitions():
    assert can_transition("invoice", "draft", "confirmed")
    assert can_transition("invoice", "draft", "cancelled")
    assert can_transition("invoice", "confirmed", "paid")
    assert can_transition("invoice", "confirmed", "cancelled")


def test_invoice_disallowed_transitions():
    assert not can_transition("invoice", "draft", "paid")
    assert not can_transition("invoice", "paid", "cancelled")
    assert not can_transition("invoice", "paid", "confirmed")
    assert not can_transition("invoice", "cancelled", "draft")


def test_unknown_entity():
    with pytest.raises(ValueError):
        can_transition("unknown", "draft", "confirmed")

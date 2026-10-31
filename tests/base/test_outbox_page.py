"""The outbox viewer: staff only, newest first, body rendered, link clickable."""

from __future__ import annotations

from app.db import conn
from app.outbox import queue_email


def _queue(kind: str = "password_reset", subject: str = "Reset your password") -> int:
    with conn() as c:
        return queue_email(
            c,
            kind=kind,
            to_email="sam@example.com",
            subject=subject,
            body_html="<p>Hello from the ledger.</p>",
            link="http://testserver/reset/abc123",
        )


def test_staff_sees_a_queued_email(as_role, client):
    as_role("staff")
    _queue()

    response = client.get("/app/outbox")

    assert response.status_code == 200
    assert "Reset your password" in response.text
    assert "sam@example.com" in response.text
    assert "<p>Hello from the ledger.</p>" in response.text
    assert 'href="http://testserver/reset/abc123"' in response.text


def test_newest_message_comes_first(as_role, client):
    as_role("staff")
    _queue(subject="Older message")
    _queue(subject="Newer message")

    body = client.get("/app/outbox").text

    assert body.index("Newer message") < body.index("Older message")


def test_the_kind_filter_narrows_the_list(as_role, client):
    as_role("staff")
    _queue(kind="password_reset", subject="A reset")
    _queue(kind="invoice_reminder", subject="A reminder")

    body = client.get("/app/outbox", params={"kind": "invoice_reminder"}).text

    assert "A reminder" in body
    assert "A reset" not in body


def test_an_unknown_kind_falls_back_to_everything(as_role, client):
    as_role("staff")
    _queue(subject="A reset")

    response = client.get("/app/outbox", params={"kind": "not-a-kind"})

    assert response.status_code == 200
    assert "A reset" in response.text


def test_the_empty_state_says_what_to_do(as_role, client):
    as_role("staff")

    body = client.get("/app/outbox").text

    assert "No messages yet" in body


def test_a_customer_cannot_read_the_outbox(as_role, client):
    as_role("customer")
    _queue()

    assert client.get("/app/outbox").status_code == 403

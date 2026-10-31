"""Billing-run pages: staff only, validated form, readable result page."""

from __future__ import annotations

from app.db import conn


def _insert_run(*, mode: str = "dry", considered: int = 3, created: int = 2) -> int:
    """Write a finished run in its own transaction so the page can read it."""
    with conn() as c:
        row = c.execute(
            "INSERT INTO billing_runs "
            "(mode, as_of, status, considered, invoices_created, amount_minor) "
            "VALUES (%s, DATE '2026-10-01', 'completed', %s, %s, 1234500) RETURNING id",
            (mode, considered, created),
        ).fetchone()
    return int(row["id"])


def test_staff_sees_the_run_form(as_role, client):
    as_role("staff")

    response = client.get("/app/billing-runs")

    assert response.status_code == 200
    assert "Run billing" in response.text
    assert "Dry run" in response.text


def test_a_customer_cannot_run_billing(as_role, client):
    as_role("customer")

    assert client.get("/app/billing-runs").status_code == 403
    assert client.post("/app/billing-runs", data={"mode": "live"}).status_code == 403


def test_a_malformed_date_returns_422(as_role, client):
    as_role("staff")

    response = client.post(
        "/app/billing-runs", data={"as_of": "01/10/2026", "mode": "dry"},
        follow_redirects=False,
    )

    assert response.status_code == 422
    assert "YYYY-MM-DD" in response.text


def test_an_unknown_mode_returns_422(as_role, client):
    as_role("staff")

    response = client.post(
        "/app/billing-runs", data={"as_of": "2026-10-01", "mode": "turbo"},
        follow_redirects=False,
    )

    assert response.status_code == 422
    assert "dry run or a live run" in response.text


def test_the_result_page_shows_the_header_counts(as_role, client):
    as_role("staff")
    run_id = _insert_run(considered=3, created=2)

    response = client.get(f"/app/billing-runs/{run_id}")

    assert response.status_code == 200
    assert "Billing run " + str(run_id) in response.text
    assert "12,345.00" in response.text
    assert "nothing was written" in response.text


def test_an_unknown_run_is_a_404(as_role, client):
    as_role("staff")

    assert client.get("/app/billing-runs/999999").status_code == 404


def test_the_list_shows_a_previous_run(as_role, client):
    as_role("staff")
    run_id = _insert_run()

    body = client.get("/app/billing-runs").text

    assert f'href="/app/billing-runs/{run_id}"' in body

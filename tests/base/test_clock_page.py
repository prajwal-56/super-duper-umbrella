"""The clock page: demo only, moves business time, and runs the daily job once."""

from __future__ import annotations

import dataclasses
from datetime import date

import pytest

from app import clock as clock_module
from app import deps
from app.config import settings


@pytest.fixture
def demo(monkeypatch):
    """Turn DEMO_MODE on for this test, in every module that reads it."""
    demo_settings = dataclasses.replace(settings, demo_mode=True)
    monkeypatch.setattr(deps, "settings", demo_settings)
    monkeypatch.setattr(clock_module, "settings", demo_settings)
    return demo_settings


@pytest.fixture
def daily_calls(monkeypatch):
    """Record the daily job instead of running B's lifecycle (tested in tests/engine)."""
    import app.services.lifecycle as lifecycle

    calls: list[tuple[date, int | None]] = []
    monkeypatch.setattr(
        lifecycle, "run_daily", lambda day, actor_id: calls.append((day, actor_id))
    )
    return calls


def _admin_id(db) -> int:
    return int(db.execute("SELECT id FROM users WHERE role = 'admin'").fetchone()["id"])


def test_an_admin_sees_the_clock_page(demo, as_role, client):
    as_role("admin")

    response = client.get("/app/clock")

    assert response.status_code == 200
    assert "Business date" in response.text


def test_staff_is_refused(demo, as_role, client):
    as_role("staff")

    assert client.get("/app/clock").status_code == 403


def test_without_demo_mode_the_page_is_off(as_role, client):
    as_role("admin")

    assert client.get("/app/clock").status_code == 403


def test_advancing_one_month_moves_business_time(demo, daily_calls, as_role, client, db):
    as_role("admin")
    clock_module.set_simulated(date(2026, 1, 31), actor_id=None)
    daily_calls.clear()

    response = client.post(
        "/app/clock", data={"action": "advance", "days": "0", "months": "1"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert clock_module.today() == date(2026, 2, 28)
    assert daily_calls == [(date(2026, 2, 28), _admin_id(db))]


def test_advancing_a_week_moves_seven_days(demo, daily_calls, as_role, client):
    as_role("admin")
    clock_module.set_simulated(date(2026, 3, 1), actor_id=None)

    client.post(
        "/app/clock", data={"action": "advance", "days": "7", "months": "0"},
        follow_redirects=False,
    )

    assert clock_module.today() == date(2026, 3, 8)


def test_jumping_to_a_date_sets_the_mode(demo, daily_calls, as_role, client):
    as_role("admin")

    response = client.post(
        "/app/clock", data={"action": "set", "day": "2026-12-01"}, follow_redirects=False
    )

    assert response.status_code == 303
    state = clock_module.get_state()
    assert state["mode"] == "simulated"
    assert state["today"] == date(2026, 12, 1)


def test_reset_returns_to_the_real_date(demo, daily_calls, as_role, client):
    as_role("admin")
    clock_module.set_simulated(date(2030, 1, 1), actor_id=None)

    response = client.post("/app/clock", data={"action": "reset"}, follow_redirects=False)

    assert response.status_code == 303
    assert clock_module.get_state()["mode"] == "real"


def test_a_malformed_date_returns_the_page_with_a_message(demo, as_role, client):
    as_role("admin")

    response = client.post(
        "/app/clock", data={"action": "set", "day": "31/12/2026"}, follow_redirects=False
    )

    assert response.status_code == 422
    assert "YYYY-MM-DD" in response.text


def test_a_zero_advance_is_rejected(demo, as_role, client):
    as_role("admin")

    response = client.post(
        "/app/clock", data={"action": "advance", "days": "0", "months": "0"},
        follow_redirects=False,
    )

    assert response.status_code == 422
    assert "Enter a number of days or months" in response.text

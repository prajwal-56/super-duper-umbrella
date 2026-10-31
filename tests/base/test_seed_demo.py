"""Tests for seed_demo and demo reset endpoint (A-15)."""

from __future__ import annotations

import dataclasses

from app.config import settings
from app.db import conn
from app.services import invariants
from scripts import seed_demo


def test_seed_demo_idempotent_and_invariants_pass():
    seed_demo.reset_database()
    counts = seed_demo.seed()
    assert counts["customers"] == 25
    assert counts["subscriptions"] == 60
    assert counts["active_subscriptions"] == 35

    with conn() as c:
        results = invariants.run_all(c)
        assert all(r.ok for r in results), [(r.id, r.violations) for r in results if not r.ok]

    # Calling seed_if_empty does nothing if already seeded
    assert not seed_demo.seed_if_empty()


def test_demo_reset_endpoint(client, as_role, monkeypatch):
    as_role("admin")
    from app import deps

    demo_settings = dataclasses.replace(settings, demo_mode=True)
    monkeypatch.setattr(deps, "settings", demo_settings)

    # Requires admin permissions
    resp = client.get("/app/demo/reset")
    assert resp.status_code == 200
    assert "Reset Demo Dataset" in resp.text

    # Invalid confirm text gives 422
    post_fail = client.post("/app/demo/reset", data={"confirm": "WRONG"})
    assert post_fail.status_code == 422

    # Success confirms and redirects to dashboard
    post_ok = client.post("/app/demo/reset", data={"confirm": "RESET"}, follow_redirects=False)
    assert post_ok.status_code == 303
    assert post_ok.headers["location"] == "/app/dashboard?seeded=1"


def test_demo_reset_disabled_outside_demo_mode(client, as_role, monkeypatch):
    as_role("admin")
    from app import deps

    non_demo_settings = dataclasses.replace(settings, demo_mode=False)
    monkeypatch.setattr(deps, "settings", non_demo_settings)
    resp = client.get("/app/demo/reset")
    assert resp.status_code == 403

    resp_post = client.post("/app/demo/reset", data={"confirm": "RESET"})
    assert resp_post.status_code == 403

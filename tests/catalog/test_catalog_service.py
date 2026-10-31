"""Tests for catalog service: resolve_unit_price, build_line_snapshot, CRUD.

Runs against real Postgres (BUILD_PLAN §19).  Owner: C.
"""

from __future__ import annotations

import pytest

from app.services import catalog as svc


# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def tax_gst(db):
    """Create a GST 18% exclusive tax rule."""
    return svc.create_tax(db, "GST 18%", 1800, False, actor_id=1)


@pytest.fixture
def tax_inclusive(db):
    """Create an inclusive 5% tax rule."""
    return svc.create_tax(db, "GST 5% incl", 500, True, actor_id=1)


@pytest.fixture
def term_net30(db):
    return svc.create_payment_term(db, "Net 30", 30, actor_id=1)


@pytest.fixture
def product_basic(db, tax_gst):
    """A simple product with sales price 10000 paise (₹100)."""
    return svc.create_product(
        db, "Web Hosting", "service", 10000, 5000, tax_gst, None, actor_id=1
    )


@pytest.fixture
def plan_monthly(db):
    return svc.create_plan(
        db, "Monthly", 0, "month", 1, 1,
        None, None, False, True, True, True, actor_id=1
    )


# ── Tax CRUD ─────────────────────────────────────────────────────────────

class TestTaxCRUD:
    def test_create_and_list(self, db, tax_gst):
        taxes = svc.list_taxes(db)
        assert len(taxes) == 1
        assert taxes[0]["name"] == "GST 18%"
        assert taxes[0]["rate_bps"] == 1800

    def test_get(self, db, tax_gst):
        tax = svc.get_tax(db, tax_gst)
        assert tax is not None
        assert tax["inclusive"] is False

    def test_update(self, db, tax_gst):
        svc.update_tax(db, tax_gst, "CGST 9%", 900, False, True, actor_id=1)
        tax = svc.get_tax(db, tax_gst)
        assert tax["name"] == "CGST 9%"
        assert tax["rate_bps"] == 900

    def test_deactivate(self, db, tax_gst):
        svc.update_tax(db, tax_gst, "GST 18%", 1800, False, False, actor_id=1)
        tax = svc.get_tax(db, tax_gst)
        assert tax["active"] is False


# ── Payment term CRUD ────────────────────────────────────────────────────

class TestPaymentTermCRUD:
    def test_create_and_list(self, db, term_net30):
        terms = svc.list_payment_terms(db)
        assert len(terms) == 1
        assert terms[0]["due_days"] == 30

    def test_update(self, db, term_net30):
        svc.update_payment_term(db, term_net30, "Net 15", 15, actor_id=1)
        term = svc.get_payment_term(db, term_net30)
        assert term["name"] == "Net 15"
        assert term["due_days"] == 15


# ── Product CRUD ─────────────────────────────────────────────────────────

class TestProductCRUD:
    def test_create_and_list(self, db, product_basic, tax_gst):
        products = svc.list_products(db)
        assert len(products) == 1
        assert products[0]["name"] == "Web Hosting"
        assert products[0]["sales_price_minor"] == 10000
        assert products[0]["tax_name"] == "GST 18%"

    def test_get(self, db, product_basic):
        p = svc.get_product(db, product_basic)
        assert p is not None
        assert p["type"] == "service"

    def test_update(self, db, product_basic):
        svc.update_product(
            db, product_basic, "Premium Hosting", "service",
            20000, 10000, None, "upgraded", True, actor_id=1
        )
        p = svc.get_product(db, product_basic)
        assert p["name"] == "Premium Hosting"
        assert p["sales_price_minor"] == 20000

    def test_active_only_filter(self, db, product_basic):
        svc.update_product(
            db, product_basic, "Web Hosting", "service",
            10000, 5000, None, None, False, actor_id=1
        )
        assert len(svc.list_products(db, active_only=True)) == 0
        assert len(svc.list_products(db)) == 1


# ── Variant CRUD ─────────────────────────────────────────────────────────

class TestVariantCRUD:
    def test_create_and_list(self, db, product_basic):
        vid = svc.create_variant(db, product_basic, "Storage", "100GB", 5000, actor_id=1)
        variants = svc.list_variants(db, product_basic)
        assert len(variants) == 1
        assert variants[0]["attribute"] == "Storage"
        assert variants[0]["extra_price_minor"] == 5000

    def test_update(self, db, product_basic):
        vid = svc.create_variant(db, product_basic, "Storage", "100GB", 5000, actor_id=1)
        svc.update_variant(db, vid, "Storage", "200GB", 8000, actor_id=1)
        v = svc.get_variant(db, vid)
        assert v["value"] == "200GB"
        assert v["extra_price_minor"] == 8000

    def test_delete(self, db, product_basic):
        vid = svc.create_variant(db, product_basic, "Storage", "100GB", 5000, actor_id=1)
        svc.delete_variant(db, vid, actor_id=1)
        assert len(svc.list_variants(db, product_basic)) == 0


# ── Plan CRUD ────────────────────────────────────────────────────────────

class TestPlanCRUD:
    def test_create_and_list(self, db, plan_monthly):
        plans = svc.list_plans(db)
        assert len(plans) == 1
        assert plans[0]["billing_interval"] == "month"

    def test_update(self, db, plan_monthly):
        svc.update_plan(
            db, plan_monthly, "Quarterly", 0, "month", 3, 1,
            None, None, False, True, True, True, True, actor_id=1
        )
        p = svc.get_plan(db, plan_monthly)
        assert p["name"] == "Quarterly"
        assert p["interval_count"] == 3


# ── Price overrides ──────────────────────────────────────────────────────

class TestPriceOverrides:
    def test_set_and_list(self, db, product_basic, plan_monthly):
        svc.set_price_override(db, product_basic, plan_monthly, 7500, actor_id=1)
        overrides = svc.list_price_overrides(db, plan_monthly)
        assert len(overrides) == 1
        assert overrides[0]["price_minor"] == 7500

    def test_upsert(self, db, product_basic, plan_monthly):
        svc.set_price_override(db, product_basic, plan_monthly, 7500, actor_id=1)
        svc.set_price_override(db, product_basic, plan_monthly, 6000, actor_id=1)
        overrides = svc.list_price_overrides(db, plan_monthly)
        assert len(overrides) == 1
        assert overrides[0]["price_minor"] == 6000

    def test_delete(self, db, product_basic, plan_monthly):
        svc.set_price_override(db, product_basic, plan_monthly, 7500, actor_id=1)
        svc.delete_price_override(db, product_basic, plan_monthly, actor_id=1)
        assert len(svc.list_price_overrides(db, plan_monthly)) == 0


# ── resolve_unit_price ───────────────────────────────────────────────────

class TestResolveUnitPrice:
    def test_default_sales_price(self, db, product_basic, plan_monthly):
        """No override, no variant → product.sales_price_minor."""
        price = svc.resolve_unit_price(db, product_basic, None, plan_monthly)
        assert price == 10000

    def test_with_variant_extra(self, db, product_basic, plan_monthly):
        """Variant adds extra_price to the base."""
        vid = svc.create_variant(db, product_basic, "Storage", "100GB", 5000, actor_id=1)
        price = svc.resolve_unit_price(db, product_basic, vid, plan_monthly)
        assert price == 15000  # 10000 + 5000

    def test_plan_override(self, db, product_basic, plan_monthly):
        """product_plan_prices override replaces sales_price."""
        svc.set_price_override(db, product_basic, plan_monthly, 7500, actor_id=1)
        price = svc.resolve_unit_price(db, product_basic, None, plan_monthly)
        assert price == 7500

    def test_plan_override_plus_variant(self, db, product_basic, plan_monthly):
        """Override + variant extra."""
        svc.set_price_override(db, product_basic, plan_monthly, 7500, actor_id=1)
        vid = svc.create_variant(db, product_basic, "Storage", "100GB", 5000, actor_id=1)
        price = svc.resolve_unit_price(db, product_basic, vid, plan_monthly)
        assert price == 12500  # 7500 + 5000

    def test_nonexistent_product_raises(self, db, plan_monthly):
        with pytest.raises(ValueError, match="product 99999 not found"):
            svc.resolve_unit_price(db, 99999, None, plan_monthly)


# ── build_line_snapshot ──────────────────────────────────────────────────

class TestBuildLineSnapshot:
    def test_basic_snapshot(self, db, product_basic, plan_monthly, tax_gst):
        snap = svc.build_line_snapshot(db, product_basic, None, 2, plan_monthly)
        assert snap["unit_price_minor"] == 10000
        assert snap["tax_id"] == tax_gst
        assert snap["tax_rate_bps"] == 1800
        assert snap["tax_inclusive"] is False

    def test_no_tax(self, db, plan_monthly):
        """Product without tax_id → zero tax."""
        pid = svc.create_product(db, "Consulting", "service", 50000, 0, None, None, actor_id=1)
        snap = svc.build_line_snapshot(db, pid, None, 1, plan_monthly)
        assert snap["tax_id"] is None
        assert snap["tax_rate_bps"] == 0
        assert snap["tax_inclusive"] is False

    def test_inclusive_tax(self, db, tax_inclusive, plan_monthly):
        pid = svc.create_product(db, "Food Pack", "goods", 10500, 0, tax_inclusive, None, actor_id=1)
        snap = svc.build_line_snapshot(db, pid, None, 1, plan_monthly)
        assert snap["tax_inclusive"] is True
        assert snap["tax_rate_bps"] == 500

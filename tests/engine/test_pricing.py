from datetime import date

from app.domain.pricing import (
    DiscountInput,
    LineInput,
    allocate_subscription_discount,
    price_invoice,
)


def test_allocate_subscription_discount_largest_remainder():
    nets = [1000, 2000, 3000]
    allocated = allocate_subscription_discount(nets, 1001)
    assert allocated == [167, 334, 500]
    assert sum(allocated) == 1001


def test_exclusive_tax_calculation():
    line = LineInput(
        description="Plan fee",
        quantity=1,
        unit_price_minor=10000,
        tax_rate_bps=1800,
        tax_inclusive=False,
    )
    res = price_invoice([line], [], date(2026, 1, 1))
    assert res.subtotal_minor == 10000
    assert res.discount_minor == 0
    assert res.tax_minor == 1800
    assert res.total_minor == 11800
    assert len(res.lines) == 1
    pl = res.lines[0]
    assert pl.total_minor == 11800
    assert pl.tax_minor == 1800


def test_inclusive_tax_calculation():
    line = LineInput(
        description="Inclusive item",
        quantity=1,
        unit_price_minor=11800,
        tax_rate_bps=1800,
        tax_inclusive=True,
    )
    res = price_invoice([line], [], date(2026, 1, 1))
    assert res.subtotal_minor == 11800
    assert res.discount_minor == 0
    assert res.tax_minor == 1800
    assert res.total_minor == 11800
    assert res.lines[0].total_minor == 11800


def test_calc_trace_reconciliation():
    line = LineInput(
        description="ERP Suite",
        quantity=3,
        unit_price_minor=555900,
        tax_rate_bps=1800,
        tax_inclusive=False,
        product_id=1,
        base_price_minor=499900,
        variant_label="Brand = Odoo",
    )
    disc = DiscountInput(
        id=1,
        name="SEATS10",
        kind="percent",
        value=1000,
        scope="product",
        product_id=1,
    )
    res = price_invoice([line], [disc], date(2026, 1, 1))
    pl = res.lines[0]
    assert pl.subtotal_minor == 1667700
    assert pl.discount_minor == 166770
    assert pl.tax_minor == 270167
    assert pl.total_minor == 1771097

    trace_labels = [step["label"] for step in pl.calc_trace]
    assert "Product price" in trace_labels
    assert "Variant: Brand = Odoo" in trace_labels
    assert "Unit price" in trace_labels
    assert "x 3 units" in trace_labels
    assert "Discount SEATS10" in trace_labels
    assert "Net" in trace_labels
    assert "Tax 18.0% (exclusive)" in trace_labels
    assert "Line total" in trace_labels
    assert pl.calc_trace[-1]["amount_minor"] == pl.total_minor


def test_property_sum_of_lines_equals_totals():
    lines = [
        LineInput(
            description="Item A",
            quantity=2,
            unit_price_minor=25000,
            tax_rate_bps=1800,
            tax_inclusive=False,
            product_id=1,
        ),
        LineInput(
            description="Item B",
            quantity=5,
            unit_price_minor=12000,
            tax_rate_bps=500,
            tax_inclusive=True,
            product_id=2,
        ),
        LineInput(
            description="Item C",
            quantity=1,
            unit_price_minor=8000,
            tax_rate_bps=0,
            tax_inclusive=False,
            product_id=3,
        ),
    ]
    sub_discount = DiscountInput(
        id=1,
        name="GLOBAL15",
        kind="percent",
        value=1500,
        scope="subscription",
    )

    res = price_invoice(lines, [sub_discount], date(2026, 1, 1))

    assert res.subtotal_minor == sum(pl.subtotal_minor for pl in res.lines)
    assert res.discount_minor == sum(pl.discount_minor for pl in res.lines)
    assert res.tax_minor == sum(pl.tax_minor for pl in res.lines)
    assert res.total_minor == sum(pl.total_minor for pl in res.lines)

    for pl in res.lines:
        assert pl.discount_minor <= pl.subtotal_minor
        assert pl.total_minor >= 0

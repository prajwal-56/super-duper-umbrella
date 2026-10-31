from datetime import date

from app.domain.discounts import select
from app.domain.pricing import DiscountInput, LineInput


def test_select_discounts_best_per_line_and_subscription():
    as_of = date(2026, 6, 15)
    lines = [
        LineInput(
            description="Product 1",
            product_id=1,
            quantity=3,
            unit_price_minor=10000,
        ),
        LineInput(
            description="Product 2",
            product_id=2,
            quantity=1,
            unit_price_minor=20000,
        ),
    ]

    cand_p1_a = DiscountInput(
        id=1,
        name="P1-10%",
        kind="percent",
        value=1000,
        scope="product",
        product_id=1,
    )
    cand_p1_b = DiscountInput(
        id=2,
        name="P1-Fixed",
        kind="fixed",
        value=2000,
        scope="product",
        product_id=1,
    )
    cand_sub = DiscountInput(
        id=3,
        name="SUB-5%",
        kind="percent",
        value=500,
        scope="subscription",
    )

    applied = select(lines, [cand_p1_a, cand_p1_b, cand_sub], as_of)
    assert len(applied) == 2

    p_disc = [a for a in applied if a.scope == "product"][0]
    assert p_disc.discount_id == 1
    assert p_disc.amount_minor == 3000
    assert p_disc.line_index == 0

    s_disc = [a for a in applied if a.scope == "subscription"][0]
    assert s_disc.discount_id == 3
    assert s_disc.amount_minor == 2350

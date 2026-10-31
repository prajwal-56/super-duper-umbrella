"""Catalog services: taxes, payment terms, products, variants, plans, price
overrides, and the two contract functions resolve_unit_price and
build_line_snapshot.  Owner: C.
"""

from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.audit import audit


# ---------------------------------------------------------------------------
# resolve_unit_price / build_line_snapshot  (contract stubs filled)
# ---------------------------------------------------------------------------

def resolve_unit_price(
    conn: psycopg.Connection, product_id: int, variant_id: int | None, plan_id: int
) -> int:
    """Unit price in minor units (D-04).

    product_plan_prices override when present, else product.sales_price, plus
    the variant's extra_price (0 when no variant).
    """
    row = conn.execute(
        """
        SELECT
          COALESCE(pp.price_minor, p.sales_price_minor) AS base,
          COALESCE(v.extra_price_minor, 0) AS extra
        FROM products p
        LEFT JOIN product_plan_prices pp
               ON pp.product_id = p.id AND pp.plan_id = %s
        LEFT JOIN product_variants v
               ON v.id = %s AND v.product_id = p.id
        WHERE p.id = %s
        """,
        (plan_id, variant_id, product_id),
    ).fetchone()
    if row is None:
        raise ValueError(f"product {product_id} not found")
    return int(row["base"]) + int(row["extra"])


def build_line_snapshot(
    conn: psycopg.Connection,
    product_id: int,
    variant_id: int | None,
    quantity: int,
    plan_id: int,
) -> dict:
    """The price and tax facts snapshotted onto a subscription line (D-04).

    Returns unit_price_minor, tax_id, tax_rate_bps, tax_inclusive.  Later
    catalog edits never change an existing subscription.
    """
    unit_price = resolve_unit_price(conn, product_id, variant_id, plan_id)
    row = conn.execute(
        """
        SELECT t.id AS tax_id, t.rate_bps, t.inclusive
        FROM products p
        LEFT JOIN taxes t ON t.id = p.tax_id
        WHERE p.id = %s
        """,
        (product_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"product {product_id} not found")
    return {
        "unit_price_minor": unit_price,
        "tax_id": row["tax_id"],
        "tax_rate_bps": int(row["rate_bps"]) if row["rate_bps"] is not None else 0,
        "tax_inclusive": bool(row["inclusive"]) if row["inclusive"] is not None else False,
    }


# ---------------------------------------------------------------------------
# Taxes
# ---------------------------------------------------------------------------

def list_taxes(conn: psycopg.Connection) -> list[dict[str, Any]]:
    return conn.execute(
        "SELECT * FROM taxes ORDER BY name"
    ).fetchall()


def get_tax(conn: psycopg.Connection, tax_id: int) -> dict[str, Any] | None:
    return conn.execute(
        "SELECT * FROM taxes WHERE id = %s", (tax_id,)
    ).fetchone()


def create_tax(
    conn: psycopg.Connection,
    name: str,
    rate_bps: int,
    inclusive: bool,
    actor_id: int,
) -> int:
    row = conn.execute(
        "INSERT INTO taxes (name, rate_bps, inclusive) VALUES (%s, %s, %s) RETURNING id",
        (name, rate_bps, inclusive),
    ).fetchone()
    tax_id = int(row["id"])
    audit(conn, actor_id, "tax.create", "tax", tax_id,
          after={"name": name, "rate_bps": rate_bps, "inclusive": inclusive})
    return tax_id


def update_tax(
    conn: psycopg.Connection,
    tax_id: int,
    name: str,
    rate_bps: int,
    inclusive: bool,
    active: bool,
    actor_id: int,
) -> None:
    old = get_tax(conn, tax_id)
    if old is None:
        raise ValueError(f"tax {tax_id} not found")
    conn.execute(
        "UPDATE taxes SET name=%s, rate_bps=%s, inclusive=%s, active=%s WHERE id=%s",
        (name, rate_bps, inclusive, active, tax_id),
    )
    audit(conn, actor_id, "tax.update", "tax", tax_id,
          before=dict(old), after={"name": name, "rate_bps": rate_bps,
                                   "inclusive": inclusive, "active": active})


# ---------------------------------------------------------------------------
# Payment terms
# ---------------------------------------------------------------------------

def list_payment_terms(conn: psycopg.Connection) -> list[dict[str, Any]]:
    return conn.execute(
        "SELECT * FROM payment_terms ORDER BY name"
    ).fetchall()


def get_payment_term(conn: psycopg.Connection, term_id: int) -> dict[str, Any] | None:
    return conn.execute(
        "SELECT * FROM payment_terms WHERE id = %s", (term_id,)
    ).fetchone()


def create_payment_term(
    conn: psycopg.Connection, name: str, due_days: int, actor_id: int
) -> int:
    row = conn.execute(
        "INSERT INTO payment_terms (name, due_days) VALUES (%s, %s) RETURNING id",
        (name, due_days),
    ).fetchone()
    term_id = int(row["id"])
    audit(conn, actor_id, "payment_term.create", "payment_term", term_id,
          after={"name": name, "due_days": due_days})
    return term_id


def update_payment_term(
    conn: psycopg.Connection, term_id: int, name: str, due_days: int, actor_id: int
) -> None:
    old = get_payment_term(conn, term_id)
    if old is None:
        raise ValueError(f"payment term {term_id} not found")
    conn.execute(
        "UPDATE payment_terms SET name=%s, due_days=%s WHERE id=%s",
        (name, due_days, term_id),
    )
    audit(conn, actor_id, "payment_term.update", "payment_term", term_id,
          before=dict(old), after={"name": name, "due_days": due_days})


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

def list_products(conn: psycopg.Connection, *, active_only: bool = False) -> list[dict[str, Any]]:
    sql = """
        SELECT p.*, t.name AS tax_name, t.rate_bps AS tax_rate,
               (SELECT count(*) FROM product_variants v WHERE v.product_id = p.id) AS variant_count
        FROM products p
        LEFT JOIN taxes t ON t.id = p.tax_id
    """
    if active_only:
        sql += " WHERE p.active = true"
    sql += " ORDER BY p.name"
    return conn.execute(sql).fetchall()


def get_product(conn: psycopg.Connection, product_id: int) -> dict[str, Any] | None:
    return conn.execute(
        """SELECT p.*, t.name AS tax_name, t.rate_bps AS tax_rate
           FROM products p LEFT JOIN taxes t ON t.id = p.tax_id
           WHERE p.id = %s""",
        (product_id,),
    ).fetchone()


def create_product(
    conn: psycopg.Connection,
    name: str,
    product_type: str,
    sales_price_minor: int,
    cost_price_minor: int,
    tax_id: int | None,
    notes: str | None,
    actor_id: int,
) -> int:
    row = conn.execute(
        """INSERT INTO products (name, type, sales_price_minor, cost_price_minor,
                                 tax_id, notes)
           VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
        (name, product_type, sales_price_minor, cost_price_minor, tax_id, notes),
    ).fetchone()
    pid = int(row["id"])
    audit(conn, actor_id, "product.create", "product", pid,
          after={"name": name, "type": product_type,
                 "sales_price_minor": sales_price_minor})
    return pid


def update_product(
    conn: psycopg.Connection,
    product_id: int,
    name: str,
    product_type: str,
    sales_price_minor: int,
    cost_price_minor: int,
    tax_id: int | None,
    notes: str | None,
    active: bool,
    actor_id: int,
) -> None:
    old = get_product(conn, product_id)
    if old is None:
        raise ValueError(f"product {product_id} not found")
    conn.execute(
        """UPDATE products SET name=%s, type=%s, sales_price_minor=%s,
              cost_price_minor=%s, tax_id=%s, notes=%s, active=%s
           WHERE id=%s""",
        (name, product_type, sales_price_minor, cost_price_minor,
         tax_id, notes, active, product_id),
    )
    audit(conn, actor_id, "product.update", "product", product_id,
          before={"name": old["name"], "sales_price_minor": old["sales_price_minor"]},
          after={"name": name, "sales_price_minor": sales_price_minor, "active": active})


# ---------------------------------------------------------------------------
# Product variants
# ---------------------------------------------------------------------------

def list_variants(conn: psycopg.Connection, product_id: int) -> list[dict[str, Any]]:
    return conn.execute(
        "SELECT * FROM product_variants WHERE product_id = %s ORDER BY attribute, value",
        (product_id,),
    ).fetchall()


def get_variant(conn: psycopg.Connection, variant_id: int) -> dict[str, Any] | None:
    return conn.execute(
        "SELECT * FROM product_variants WHERE id = %s", (variant_id,)
    ).fetchone()


def create_variant(
    conn: psycopg.Connection,
    product_id: int,
    attribute: str,
    value: str,
    extra_price_minor: int,
    actor_id: int,
) -> int:
    row = conn.execute(
        """INSERT INTO product_variants (product_id, attribute, value, extra_price_minor)
           VALUES (%s, %s, %s, %s) RETURNING id""",
        (product_id, attribute, value, extra_price_minor),
    ).fetchone()
    vid = int(row["id"])
    audit(conn, actor_id, "variant.create", "product_variant", vid,
          after={"product_id": product_id, "attribute": attribute,
                 "value": value, "extra_price_minor": extra_price_minor})
    return vid


def update_variant(
    conn: psycopg.Connection,
    variant_id: int,
    attribute: str,
    value: str,
    extra_price_minor: int,
    actor_id: int,
) -> None:
    old = get_variant(conn, variant_id)
    if old is None:
        raise ValueError(f"variant {variant_id} not found")
    conn.execute(
        """UPDATE product_variants SET attribute=%s, value=%s, extra_price_minor=%s
           WHERE id=%s""",
        (attribute, value, extra_price_minor, variant_id),
    )
    audit(conn, actor_id, "variant.update", "product_variant", variant_id,
          before=dict(old),
          after={"attribute": attribute, "value": value,
                 "extra_price_minor": extra_price_minor})


def delete_variant(conn: psycopg.Connection, variant_id: int, actor_id: int) -> None:
    old = get_variant(conn, variant_id)
    if old is None:
        raise ValueError(f"variant {variant_id} not found")
    conn.execute("DELETE FROM product_variants WHERE id = %s", (variant_id,))
    audit(conn, actor_id, "variant.delete", "product_variant", variant_id,
          before=dict(old))


# ---------------------------------------------------------------------------
# Plans
# ---------------------------------------------------------------------------

def list_plans(conn: psycopg.Connection, *, active_only: bool = False) -> list[dict[str, Any]]:
    sql = "SELECT * FROM plans"
    if active_only:
        sql += " WHERE active = true"
    sql += " ORDER BY name"
    return conn.execute(sql).fetchall()


def get_plan(conn: psycopg.Connection, plan_id: int) -> dict[str, Any] | None:
    return conn.execute(
        "SELECT * FROM plans WHERE id = %s", (plan_id,)
    ).fetchone()


def create_plan(
    conn: psycopg.Connection,
    name: str,
    price_minor: int,
    billing_interval: str,
    interval_count: int,
    min_quantity: int,
    available_from: str | None,
    available_to: str | None,
    auto_close: bool,
    allow_early_close: bool,
    allow_pause: bool,
    allow_renew: bool,
    actor_id: int,
) -> int:
    row = conn.execute(
        """INSERT INTO plans (name, price_minor, billing_interval, interval_count,
                              min_quantity, available_from, available_to,
                              auto_close, allow_early_close, allow_pause, allow_renew)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
        (name, price_minor, billing_interval, interval_count, min_quantity,
         available_from or None, available_to or None,
         auto_close, allow_early_close, allow_pause, allow_renew),
    ).fetchone()
    pid = int(row["id"])
    audit(conn, actor_id, "plan.create", "plan", pid,
          after={"name": name, "billing_interval": billing_interval,
                 "interval_count": interval_count})
    return pid


def update_plan(
    conn: psycopg.Connection,
    plan_id: int,
    name: str,
    price_minor: int,
    billing_interval: str,
    interval_count: int,
    min_quantity: int,
    available_from: str | None,
    available_to: str | None,
    auto_close: bool,
    allow_early_close: bool,
    allow_pause: bool,
    allow_renew: bool,
    active: bool,
    actor_id: int,
) -> None:
    old = get_plan(conn, plan_id)
    if old is None:
        raise ValueError(f"plan {plan_id} not found")
    conn.execute(
        """UPDATE plans SET name=%s, price_minor=%s, billing_interval=%s,
              interval_count=%s, min_quantity=%s, available_from=%s, available_to=%s,
              auto_close=%s, allow_early_close=%s, allow_pause=%s, allow_renew=%s,
              active=%s
           WHERE id=%s""",
        (name, price_minor, billing_interval, interval_count, min_quantity,
         available_from or None, available_to or None,
         auto_close, allow_early_close, allow_pause, allow_renew, active, plan_id),
    )
    audit(conn, actor_id, "plan.update", "plan", plan_id,
          before={"name": old["name"]},
          after={"name": name, "active": active})


# ---------------------------------------------------------------------------
# Product–plan price overrides
# ---------------------------------------------------------------------------

def list_price_overrides(
    conn: psycopg.Connection, plan_id: int
) -> list[dict[str, Any]]:
    return conn.execute(
        """SELECT pp.*, p.name AS product_name
           FROM product_plan_prices pp
           JOIN products p ON p.id = pp.product_id
           WHERE pp.plan_id = %s ORDER BY p.name""",
        (plan_id,),
    ).fetchall()


def list_price_overrides_for_product(
    conn: psycopg.Connection, product_id: int
) -> list[dict[str, Any]]:
    return conn.execute(
        """SELECT pp.*, pl.name AS plan_name
           FROM product_plan_prices pp
           JOIN plans pl ON pl.id = pp.plan_id
           WHERE pp.product_id = %s ORDER BY pl.name""",
        (product_id,),
    ).fetchall()


def set_price_override(
    conn: psycopg.Connection,
    product_id: int,
    plan_id: int,
    price_minor: int,
    actor_id: int,
) -> None:
    conn.execute(
        """INSERT INTO product_plan_prices (product_id, plan_id, price_minor)
           VALUES (%s, %s, %s)
           ON CONFLICT (product_id, plan_id)
           DO UPDATE SET price_minor = EXCLUDED.price_minor""",
        (product_id, plan_id, price_minor),
    )
    audit(conn, actor_id, "price_override.set", "product_plan_price", product_id,
          after={"product_id": product_id, "plan_id": plan_id,
                 "price_minor": price_minor})


def delete_price_override(
    conn: psycopg.Connection, product_id: int, plan_id: int, actor_id: int
) -> None:
    conn.execute(
        "DELETE FROM product_plan_prices WHERE product_id = %s AND plan_id = %s",
        (product_id, plan_id),
    )
    audit(conn, actor_id, "price_override.delete", "product_plan_price", product_id,
          before={"product_id": product_id, "plan_id": plan_id})

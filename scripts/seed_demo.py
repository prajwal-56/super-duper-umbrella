"""Seed demo dataset. Owner: A.

BUILD_PLAN §18:
- 1 admin, 2 staff, ~25 customers (realistic Indian small-business names)
- 6 products:
    - ERP Suite with Brand variants: Odoo +560.00, Zoho +0.00, Tally +240.00
    - CRM
    - Books
    - Analytics add-on
    - Support add-on
    - One product without variants
- 4 plans:
    - monthly
    - yearly
    - weekly trial
    - auto_close with near end date
- 3 taxes:
    - GST 18% exclusive
    - GST 5% exclusive
    - GST 12% inclusive
- Payment terms:
    - Immediate (0 days)
    - Net 15 (15 days)
    - Net 30 (30 days)
- 3 quotation templates
- 3 discounts:
    - 10% on >= 5 seats
    - fixed 500 off >= 5,000
    - one already expiring
- ~60 subscriptions across all states with history
- All invariants must be green afterward.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is in sys.path when executed directly
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from datetime import date  # noqa: E402

from app import clock  # noqa: E402
from app.auth.passwords import hash_password  # noqa: E402
from app.config import settings  # noqa: E402
from app.db import conn  # noqa: E402
from app.services import invariants  # noqa: E402


def is_seeded() -> bool:
    """Return True if any customer or user exists."""
    with conn() as c:
        row = c.execute("SELECT 1 FROM users LIMIT 1").fetchone()
        return row is not None


def seed_if_empty() -> bool:
    """Seed only if database has no users (used by SEED_ON_BOOT)."""
    if is_seeded():
        return False
    seed()
    return True


def reset_database() -> None:
    """Truncate all application tables (preserving schema)."""
    tables = [
        "emails_outbox",
        "payments",
        "discount_redemptions",
        "invoice_lines",
        "invoices",
        "billing_run_items",
        "billing_runs",
        "subscription_discounts",
        "discounts",
        "subscription_pauses",
        "subscription_lines",
        "subscriptions",
        "quotation_template_lines",
        "quotation_templates",
        "product_plan_prices",
        "product_variants",
        "products",
        "plans",
        "payment_terms",
        "taxes",
        "password_reset_tokens",
        "users",
        "customers",
    ]
    with conn() as c:
        # We need to temporarily disable the audit_log trigger if audit_log is truncated,
        # or leave audit_log intact. Let's truncate data tables and audit_log safely.
        c.execute("ALTER TABLE audit_log DISABLE TRIGGER audit_log_immutable")
        c.execute(f"TRUNCATE {', '.join(tables)}, audit_log RESTART IDENTITY CASCADE")
        c.execute("ALTER TABLE audit_log ENABLE TRIGGER audit_log_immutable")
        c.execute("ALTER SEQUENCE subscription_number_seq RESTART WITH 1")
        c.execute("ALTER SEQUENCE invoice_number_seq RESTART WITH 1")
        c.execute(
            "UPDATE clock_state SET mode = 'real', simulated_today = NULL, updated_at = now() WHERE id = 1"  # real-time-ok
        )
        


def seed() -> dict[str, int]:
    """Populate realistic small-business data per §18."""
    # Set simulated clock anchor for demo consistency
    demo_today = date(2026, 4, 1)
    clock.set_simulated(demo_today, None)

    with conn() as c:
        # 1. Taxes
        tax_gst18 = c.execute(
            "INSERT INTO taxes (name, rate_bps, inclusive, active) VALUES ('GST 18%', 1800, false, true) RETURNING id"
        ).fetchone()["id"]
        tax_gst5 = c.execute(
            "INSERT INTO taxes (name, rate_bps, inclusive, active) VALUES ('GST 5%', 500, false, true) RETURNING id"
        ).fetchone()["id"]
        tax_gst12_inc = c.execute(
            "INSERT INTO taxes (name, rate_bps, inclusive, active) VALUES ('GST 12% Inc', 1200, true, true) RETURNING id"
        ).fetchone()["id"]

        # 2. Payment Terms
        c.execute(
            "INSERT INTO payment_terms (name, due_days) VALUES ('Immediate', 0) RETURNING id"
        ).fetchone()["id"]
        term_net15 = c.execute(
            "INSERT INTO payment_terms (name, due_days) VALUES ('Net 15', 15) RETURNING id"
        ).fetchone()["id"]
        term_net30 = c.execute(
            "INSERT INTO payment_terms (name, due_days) VALUES ('Net 30', 30) RETURNING id"
        ).fetchone()["id"]

        # 3. Products & Variants
        # Product 1: ERP Suite (with Brand variants: Odoo +560.00, Zoho +0.00, Tally +240.00)
        prod_erp = c.execute(
            """
            INSERT INTO products (name, type, sales_price_minor, cost_price_minor, notes, tax_id, active)
            VALUES ('ERP Suite', 'service', 250000, 100000, 'Core business resource planning platform', %s, true)
            RETURNING id
            """,
            (tax_gst18,),
        ).fetchone()["id"]

        var_odoo = c.execute(
            "INSERT INTO product_variants (product_id, attribute, value, extra_price_minor) VALUES (%s, 'Brand', 'Odoo', 56000) RETURNING id",
            (prod_erp,),
        ).fetchone()["id"]
        var_zoho = c.execute(
            "INSERT INTO product_variants (product_id, attribute, value, extra_price_minor) VALUES (%s, 'Brand', 'Zoho', 0) RETURNING id",
            (prod_erp,),
        ).fetchone()["id"]
        var_tally = c.execute(
            "INSERT INTO product_variants (product_id, attribute, value, extra_price_minor) VALUES (%s, 'Brand', 'Tally', 24000) RETURNING id",
            (prod_erp,),
        ).fetchone()["id"]

        # Product 2: CRM
        prod_crm = c.execute(
            """
            INSERT INTO products (name, type, sales_price_minor, cost_price_minor, notes, tax_id, active)
            VALUES ('BrightCRM', 'service', 120000, 40000, 'Customer relationship & lead management', %s, true)
            RETURNING id
            """,
            (tax_gst18,),
        ).fetchone()["id"]

        # Product 3: Books
        prod_books = c.execute(
            """
            INSERT INTO products (name, type, sales_price_minor, cost_price_minor, notes, tax_id, active)
            VALUES ('BrightBooks', 'service', 80000, 20000, 'Double-entry automated accounting ledger', %s, true)
            RETURNING id
            """,
            (tax_gst18,),
        ).fetchone()["id"]

        # Product 4: Analytics add-on
        prod_analytics = c.execute(
            """
            INSERT INTO products (name, type, sales_price_minor, cost_price_minor, notes, tax_id, active)
            VALUES ('Analytics Add-on', 'service', 50000, 15000, 'Real-time telemetry and reporting engine', %s, true)
            RETURNING id
            """,
            (tax_gst5,),
        ).fetchone()["id"]

        # Product 5: Support add-on
        prod_support = c.execute(
            """
            INSERT INTO products (name, type, sales_price_minor, cost_price_minor, notes, tax_id, active)
            VALUES ('Priority Support Add-on', 'service', 35000, 10000, '24/7 dedicated support desk with 1h SLA', %s, true)
            RETURNING id
            """,
            (tax_gst18,),
        ).fetchone()["id"]

        # Product 6: Standalone Security Dongle (hardware, no variants)
        c.execute(
            """
            INSERT INTO products (name, type, sales_price_minor, cost_price_minor, notes, tax_id, active)
            VALUES ('FIDO2 Hardware Key', 'consumable', 200000, 120000, 'Hardware security 2FA authenticator', %s, true)
            RETURNING id
            """,
            (tax_gst12_inc,),
        ).fetchone()["id"]

        # 4. Plans
        # Plan 1: Monthly
        plan_monthly = c.execute(
            """
            INSERT INTO plans (name, price_minor, billing_interval, interval_count, min_quantity,
                               available_from, auto_close, allow_early_close, allow_pause, allow_renew, active)
            VALUES ('Standard Monthly', 0, 'month', 1, 1, '2025-01-01', false, true, true, true, true)
            RETURNING id
            """
        ).fetchone()["id"]

        # Plan 2: Yearly
        plan_yearly = c.execute(
            """
            INSERT INTO plans (name, price_minor, billing_interval, interval_count, min_quantity,
                               available_from, auto_close, allow_early_close, allow_pause, allow_renew, active)
            VALUES ('Enterprise Annual', 0, 'year', 1, 1, '2025-01-01', false, true, true, true, true)
            RETURNING id
            """
        ).fetchone()["id"]

        # Plan 3: Weekly Trial
        c.execute(
            """
            INSERT INTO plans (name, price_minor, billing_interval, interval_count, min_quantity,
                               available_from, auto_close, allow_early_close, allow_pause, allow_renew, active)
            VALUES ('Pilot Weekly Trial', 0, 'week', 1, 1, '2025-01-01', false, true, true, true, true)
            RETURNING id
            """
        ).fetchone()["id"]

        # Plan 4: Auto-close Fixed Quarter
        c.execute(
            """
            INSERT INTO plans (name, price_minor, billing_interval, interval_count, min_quantity,
                               available_from, available_to, auto_close, allow_early_close, allow_pause, allow_renew, active)
            VALUES ('Quarterly Fixed Term', 0, 'month', 1, 1, '2025-01-01', '2026-12-31', true, true, false, false, true)
            RETURNING id
            """
        ).fetchone()["id"]

        # 5. Quotation Templates
        qt_startup = c.execute(
            """
            INSERT INTO quotation_templates (name, plan_id, validity_days, payment_term_id)
            VALUES ('Startup Foundation Pack', %s, 15, %s) RETURNING id
            """,
            (plan_monthly, term_net15),
        ).fetchone()["id"]
        c.execute(
            """
            INSERT INTO quotation_template_lines (template_id, product_id, variant_id, quantity)
            VALUES (%s, %s, %s, 2), (%s, %s, NULL, 1)
            """,
            (qt_startup, prod_erp, var_zoho, qt_startup, prod_books),
        )

        qt_growth_id = c.execute(
            """
            INSERT INTO quotation_templates (name, plan_id, validity_days, payment_term_id)
            VALUES ('Growth Commerce Pack', %s, 30, %s) RETURNING id
            """,
            (plan_monthly, term_net30),
        ).fetchone()["id"]
        c.execute(
            """
            INSERT INTO quotation_template_lines (template_id, product_id, variant_id, quantity)
            VALUES (%s, %s, %s, 5), (%s, %s, NULL, 1), (%s, %s, NULL, 1)
            """,
            (qt_growth_id, prod_erp, var_odoo, qt_growth_id, prod_crm, qt_growth_id, prod_analytics),
        )

        qt_enterprise = c.execute(
            """
            INSERT INTO quotation_templates (name, plan_id, validity_days, payment_term_id)
            VALUES ('Enterprise Annual Commitment', %s, 30, %s) RETURNING id
            """,
            (plan_yearly, term_net30),
        ).fetchone()["id"]
        c.execute(
            """
            INSERT INTO quotation_template_lines (template_id, product_id, variant_id, quantity)
            VALUES (%s, %s, %s, 10), (%s, %s, NULL, 1)
            """,
            (qt_enterprise, prod_erp, var_tally, qt_enterprise, prod_support),
        )

        # 6. Users: 1 Admin, 2 Staff
        pwd_hash = hash_password(settings.admin_password or "Brightloop#2026")
        admin_id = c.execute(
            """
            INSERT INTO users (email, password_hash, role, is_active)
            VALUES (%s, %s, 'admin', true) RETURNING id
            """,
            (settings.admin_email or "admin@example.com", pwd_hash),
        ).fetchone()["id"]

        staff1_id = c.execute(
            """
            INSERT INTO users (email, password_hash, role, is_active)
            VALUES ('arun.billing@brightloop.io', %s, 'staff', true) RETURNING id
            """,
            (pwd_hash,),
        ).fetchone()["id"]

        staff2_id = c.execute(
            """
            INSERT INTO users (email, password_hash, role, is_active)
            VALUES ('priya.finance@brightloop.io', %s, 'staff', true) RETURNING id
            """,
            (pwd_hash,),
        ).fetchone()["id"]

        # 7. Discounts (§18)
        # 10% on >= 5 seats, fixed 500 off >= 5,000, one already expiring
        c.execute(
            """
            INSERT INTO discounts (
                name, kind, value, min_quantity, starts_on, ends_on, scope, auto_apply, active, created_by
            ) VALUES (
                '10%% Volume Discount (5+ seats)', 'percent', 1000, 5, '2025-01-01', '2026-12-31', 'subscription', true, true, %s
            ) RETURNING id
            """,
            (admin_id,),
        ).fetchone()["id"]

        c.execute(
            """
            INSERT INTO discounts (
                name, kind, value, min_purchase_minor, starts_on, ends_on, scope, auto_apply, active, created_by
            ) VALUES (
                '₹500 Enterprise Off (Min ₹5,000)', 'fixed', 50000, 500000, '2025-01-01', '2026-12-31', 'subscription', true, true, %s
            ) RETURNING id
            """,
            (admin_id,),
        ).fetchone()["id"]

        c.execute(
            """
            INSERT INTO discounts (
                name, kind, value, starts_on, ends_on, usage_limit, usage_count, scope, auto_apply, active, created_by
            ) VALUES (
                'Q1 New Year Special (Expired)', 'fixed', 25000, '2026-01-01', '2026-03-31', 50, 0, 'subscription', true, false, %s
            ) RETURNING id
            """,
            (admin_id,),
        ).fetchone()["id"]

        # 8. 25 Customers (Indian small-business names)
        customer_data = [
            ("Kaveri Textiles Pvt Ltd", "accounts@kaveritextiles.in", "+91 98401 22334", "142 Cross Cut Road, Coimbatore, Tamil Nadu"),
            ("Aura Logistics India LLP", "billing@auralogistics.in", "+91 98200 44556", "Plot 88, Taloja MIDC, Navi Mumbai, Maharashtra"),
            ("Saffron Cloud Innovations", "finance@saffroncloud.co", "+91 98800 11223", "4th Block, Koramangala, Bengaluru, Karnataka"),
            ("Deccan Foundry Works", "deccan.foundry@rediffmail.com", "+91 94440 55667", "Industrial Estate, Guindy, Chennai, Tamil Nadu"),
            ("Narmada Spices & Agro", "sales@narmadaspices.com", "+91 97555 88990", "Mandideep Industrial Area, Bhopal, Madhya Pradesh"),
            ("Brahmaputra Tea Traders", "info@brahmaputratea.in", "+91 94350 33445", "Rukminigaon, G.S. Road, Guwahati, Assam"),
            ("Bluechip Retail Solutions", "ops@bluechipretail.in", "+91 98111 66778", "Nehru Place, New Delhi, Delhi"),
            ("Zenith Precision Engineering", "zenith.precision@gmail.com", "+91 99000 22119", "Peenya Industrial Area, Bengaluru, Karnataka"),
            ("Malabar Spices & Extracts", "contact@malabarspices.net", "+91 94471 99882", "Beach Road, Calicut, Kerala"),
            ("Godavari Paper Mills Ltd", "accounts@godavaripaper.com", "+91 98490 77112", "Dowleswaram, Rajahmundry, Andhra Pradesh"),
            ("Shree Ganesh Steels", "shreeganeshsteels@yahoo.com", "+91 98220 33114", "Bhavani Peth, Pune, Maharashtra"),
            ("Thar Hospitality Group", "finance@tharhospitality.com", "+91 98290 55443", "MI Road, Jaipur, Rajasthan"),
            ("Vindhya Pharma Formulations", "tax@vindhyapharma.co.in", "+91 97130 88221", "Pithampur Sector 3, Dhar, Madhya Pradesh"),
            ("Konkan Cold Storage & Logistics", "konkan.cold@gmail.com", "+91 98230 44118", "APMC Market 2, Vashi, Navi Mumbai, Maharashtra"),
            ("Sundarban Organic Honey FPO", "sundarban.fpo@wb.gov.in", "+91 94330 11229", "Canning Town, South 24 Parganas, West Bengal"),
            ("Himalayan Pure Spring Waters", "info@himalayanwaters.in", "+91 98160 77331", "Baddi Industrial Area, Solan, Himachal Pradesh"),
            ("Kalinga Ceramic Tiles", "kalingaceramics@outlook.com", "+91 94370 66224", "Chandaka Industrial Estate, Bhubaneswar, Odisha"),
            ("Chola Maritime Freight Agency", "ops@cholamaritime.com", "+91 98410 88992", "North Beach Road, George Town, Chennai, Tamil Nadu"),
            ("Ganga Valley Edutech LLP", "admin@gangavalleyedu.com", "+91 98390 44551", "Civil Lines, Prayagraj, Uttar Pradesh"),
            ("Surat Diamond Crafters", "sdc.surat@gmail.com", "+91 98250 99887", "Mahidharpura, Surat, Gujarat"),
            ("Nellore Aqua Farms Association", "nellore.aqua@yahoo.co.in", "+91 98480 33221", "Dargamitta, Nellore, Andhra Pradesh"),
            ("Punjab Agro Tech Equipment", "sales@punjabagrotech.in", "+91 98140 55662", "GT Road, Ludhiana, Punjab"),
            ("Coorg Estate Roasted Coffee", "hello@coorgcoffee.in", "+91 94480 22339", "Madikeri Main Road, Kodagu, Karnataka"),
            ("Indus Clean Energy Systems", "info@indusenergy.co.in", "+91 98201 55660", "Bandra Kurla Complex, Mumbai, Maharashtra"),
            ("Tirupur Knitwear Exporters", "accounts@tirupurknit.com", "+91 98422 11993", "Avinashi Road, Tirupur, Tamil Nadu"),
        ]

        customers = []
        for name, email, phone, addr in customer_data:
            cid = c.execute(
                """
                INSERT INTO customers (name, email, phone, address)
                VALUES (%s, %s, %s, %s) RETURNING id
                """,
                (name, email, phone, addr),
            ).fetchone()["id"]

            # Customer portal login user for first 5 customers
            if len(customers) < 5:
                c.execute(
                    """
                    INSERT INTO users (email, password_hash, role, customer_id, is_active)
                    VALUES (%s, %s, 'customer', %s, true)
                    """,
                    (email, pwd_hash, cid),
                )
            customers.append({"id": cid, "name": name, "email": email})

        # 9. Subscriptions (~60 total across all states: draft, quotation, confirmed, active, closed)
        # States breakdown:
        # - 5 Drafts
        # - 5 Quotations
        # - 5 Confirmed (starts in future, e.g. 2026-05-01)
        # - 35 Active (billed monthly from 2026-01-01 through 2026-04-01 with payments)
        # - 10 Closed (5 natural end, 5 early close)
        #
        # For active subscriptions, generate clean consistent invoices and payments
        # so that INV-01 through INV-08 are completely green.

        # Let's seed 5 Drafts
        for i in range(5):
            cust = customers[i % len(customers)]
            sub_id = c.execute(
                """
                INSERT INTO subscriptions (
                    customer_id, plan_id, status, start_date, expiry_date, payment_term_id, created_by
                ) VALUES (%s, %s, 'draft', '2026-04-01', '2027-03-31', %s, %s) RETURNING id
                """,
                (cust["id"], plan_monthly, term_net30, staff1_id),
            ).fetchone()["id"]
            c.execute(
                """
                INSERT INTO subscription_lines (
                    subscription_id, product_id, variant_id, quantity, unit_price_minor, tax_id, tax_rate_bps, tax_inclusive
                ) VALUES (%s, %s, %s, 1, 250000 + 56000, %s, 1800, false)
                """,
                (sub_id, prod_erp, var_odoo, tax_gst18),
            )

        # 5 Quotations
        for i in range(5):
            cust = customers[(i + 5) % len(customers)]
            sub_id = c.execute(
                """
                INSERT INTO subscriptions (
                    customer_id, plan_id, status, start_date, expiry_date, payment_term_id,
                    quote_sent_on, quote_valid_until, created_by
                ) VALUES (%s, %s, 'quotation', '2026-04-15', '2027-04-14', %s, '2026-03-25', '2026-04-25', %s) RETURNING id
                """,
                (cust["id"], plan_monthly, term_net15, staff2_id),
            ).fetchone()["id"]
            c.execute(
                """
                INSERT INTO subscription_lines (
                    subscription_id, product_id, variant_id, quantity, unit_price_minor, tax_id, tax_rate_bps, tax_inclusive
                ) VALUES (%s, %s, %s, 2, 250000, %s, 1800, false)
                """,
                (sub_id, prod_erp, var_zoho, tax_gst18),
            )

        # 5 Confirmed (future start)
        for i in range(5):
            cust = customers[(i + 10) % len(customers)]
            sub_id = c.execute(
                """
                INSERT INTO subscriptions (
                    customer_id, plan_id, status, start_date, expiry_date, payment_term_id, created_by
                ) VALUES (%s, %s, 'confirmed', '2026-05-01', '2027-04-30', %s, %s) RETURNING id
                """,
                (cust["id"], plan_monthly, term_net30, staff1_id),
            ).fetchone()["id"]
            c.execute(
                """
                INSERT INTO subscription_lines (
                    subscription_id, product_id, variant_id, quantity, unit_price_minor, tax_id, tax_rate_bps, tax_inclusive
                ) VALUES (%s, %s, %s, 3, 250000 + 24000, %s, 1800, false)
                """,
                (sub_id, prod_erp, var_tally, tax_gst18),
            )

        # 35 Active subscriptions starting 2026-01-01
        # Billed for Jan, Feb, Mar, Apr (4 periods up to as_of = 2026-04-01)
        active_sub_ids = []
        for i in range(35):
            cust = customers[i % len(customers)]
            sub_id = c.execute(
                """
                INSERT INTO subscriptions (
                    customer_id, plan_id, status, start_date, expiry_date, payment_term_id, created_by
                ) VALUES (%s, %s, 'active', '2026-01-01', '2026-12-31', %s, %s) RETURNING id
                """,
                (cust["id"], plan_monthly, term_net30, staff1_id),
            ).fetchone()["id"]

            c.execute(
                """
                INSERT INTO subscription_lines (
                    subscription_id, product_id, variant_id, quantity, unit_price_minor, tax_id, tax_rate_bps, tax_inclusive
                ) VALUES (%s, %s, %s, 1, 250000, %s, 1800, false),
                         (%s, %s, NULL, 1, 50000, %s, 500, false)
                """,
                (sub_id, prod_erp, var_zoho, tax_gst18, sub_id, prod_analytics, tax_gst5),
            )
            active_sub_ids.append((sub_id, cust["id"]))

        # 10 Closed subscriptions
        # 5 closed naturally (start 2026-01-01, closed_on 2026-01-01 -> 0 periods)
        # 5 early closed (start 2026-01-01, closed_on 2026-02-15)
        early_closed_subs = []
        for i in range(5):
            cust = customers[(i + 15) % len(customers)]
            c.execute(
                """
                INSERT INTO subscriptions (
                    customer_id, plan_id, status, start_date, expiry_date, payment_term_id,
                    closed_on, close_reason, billing_complete, created_by
                ) VALUES (
                    %s, %s, 'closed', '2026-01-01', '2026-12-31', %s,
                    '2026-01-01', 'contract_withdrawn', true, %s
                )
                """,
                (cust["id"], plan_monthly, term_net30, staff1_id),
            )

        for i in range(5):
            cust = customers[(i + 20) % len(customers)]
            sub_id = c.execute(
                """
                INSERT INTO subscriptions (
                    customer_id, plan_id, status, start_date, expiry_date, payment_term_id,
                    closed_on, close_reason, billing_complete, created_by
                ) VALUES (
                    %s, %s, 'closed', '2026-01-01', '2026-12-31', %s,
                    '2026-02-15', 'customer_cancelled', true, %s
                ) RETURNING id
                """,
                (cust["id"], plan_monthly, term_net30, staff2_id),
            ).fetchone()["id"]
            early_closed_subs.append((sub_id, cust["id"]))

        # Create realistic invoices for active & early-closed subscriptions to satisfy INV-04
        # Active: Jan (2026-01-01..2026-01-31), Feb (2026-02-01..2026-02-28), Mar (2026-03-01..2026-03-31), Apr (2026-04-01..2026-04-30)
        # Each line:
        # Line 1: 1 * 250000, tax 18% = 45000 -> total 295000
        # Line 2: 1 * 50000, tax 5% = 2500 -> total 52500
        # Invoice Subtotal = 300000, Discount = 0, Tax = 47500, Total = 347500
        periods = [
            (date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 1), date(2026, 1, 31)),
            (date(2026, 2, 1), date(2026, 2, 28), date(2026, 2, 1), date(2026, 3, 3)),
            (date(2026, 3, 1), date(2026, 3, 31), date(2026, 3, 1), date(2026, 3, 31)),
            (date(2026, 4, 1), date(2026, 4, 30), date(2026, 4, 1), date(2026, 5, 1)),
        ]

        # Initial billing run record
        run_id = c.execute(
            """
            INSERT INTO billing_runs (mode, as_of, status, started_by, considered, invoices_created, amount_minor)
            VALUES ('live', '2026-04-01', 'completed', %s, 35, 140, 140 * 347500) RETURNING id
            """,
            (admin_id,),
        ).fetchone()["id"]

        for sub_id, cust_id in active_sub_ids:
            for p_idx, (p_start, p_end, iss_date, due_d) in enumerate(periods):
                # Status: Jan & Feb paid, Mar confirmed/overdue or partial, Apr confirmed draft/recent
                inv_status = "paid" if p_idx < 2 else ("confirmed" if p_idx == 2 else "confirmed")
                amount_paid = 347500 if inv_status == "paid" else (100000 if (p_idx == 2 and sub_id % 3 == 0) else 0)

                inv_id = c.execute(
                    """
                    INSERT INTO invoices (
                        subscription_id, customer_id, period_start, period_end,
                        issue_date, due_date, status, subtotal_minor, discount_minor,
                        tax_minor, total_minor, amount_paid_minor, billing_run_id
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, 300000, 0, 47500, 347500, %s, %s
                    ) RETURNING id
                    """,
                    (sub_id, cust_id, p_start, p_end, iss_date, due_d, inv_status, amount_paid, run_id),
                ).fetchone()["id"]

                # Invoice Lines
                c.execute(
                    """
                    INSERT INTO invoice_lines (
                        invoice_id, description, product_id, variant_id, quantity,
                        unit_price_minor, line_subtotal_minor, discount_minor,
                        tax_rate_bps, tax_inclusive, tax_minor, total_minor
                    ) VALUES (
                        %s, 'ERP Suite (Zoho)', %s, %s, 1, 250000, 250000, 0, 1800, false, 45000, 295000
                    ), (
                        %s, 'Analytics Add-on', %s, NULL, 1, 50000, 50000, 0, 500, false, 2500, 52500
                    )
                    """,
                    (inv_id, prod_erp, var_zoho, inv_id, prod_analytics),
                )

                # Payment records if paid or partial
                if amount_paid > 0:
                    c.execute(
                        """
                        INSERT INTO payments (
                            invoice_id, method, amount_minor, paid_on, note, recorded_by
                        ) VALUES (
                            %s, 'bank_transfer', %s, %s, 'Payment via NEFT/RTGS', %s
                        )
                        """,
                        (inv_id, amount_paid, due_d, staff1_id),
                    )

            c.execute(
                """
                INSERT INTO billing_run_items (
                    run_id, subscription_id, disposition, periods_billed
                ) VALUES (%s, %s, 'billed', 4)
                """,
                (run_id, sub_id),
            )

        # Early closed subs only need periods before closed_on (2026-02-15), which is Jan and Feb
        for sub_id, cust_id in early_closed_subs:
            for p_start, p_end, iss_date, due_d in periods[:2]:
                inv_id = c.execute(
                    """
                    INSERT INTO invoices (
                        subscription_id, customer_id, period_start, period_end,
                        issue_date, due_date, status, subtotal_minor, discount_minor,
                        tax_minor, total_minor, amount_paid_minor
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, 'paid', 250000, 0, 45000, 295000, 295000
                    ) RETURNING id
                    """,
                    (sub_id, cust_id, p_start, p_end, iss_date, due_d),
                ).fetchone()["id"]
                c.execute(
                    """
                    INSERT INTO invoice_lines (
                        invoice_id, description, product_id, variant_id, quantity,
                        unit_price_minor, line_subtotal_minor, discount_minor,
                        tax_rate_bps, tax_inclusive, tax_minor, total_minor
                    ) VALUES (
                        %s, 'ERP Suite (Zoho)', %s, %s, 1, 250000, 250000, 0, 1800, false, 45000, 295000
                    )
                    """,
                    (inv_id, prod_erp, var_zoho),
                )
                c.execute(
                    """
                    INSERT INTO payments (
                        invoice_id, method, amount_minor, paid_on, note, recorded_by
                    ) VALUES (
                        %s, 'upi', 295000, %s, 'UPI Ref 2026010099', %s
                    )
                    """,
                    (inv_id, due_d, staff2_id),
                )

        

        # Check invariants
        results = invariants.run_all(c)
        bad = [r for r in results if not r.ok]
        if bad:
            for b in bad:
                print(f"FAILED {b.id}: violations={b.violations}, samples={b.sample_rows}")
            raise RuntimeError(f"Seed produced invariant violations: {[b.id for b in bad]}")

    return {
        "customers": len(customers),
        "subscriptions": 5 + 5 + 5 + 35 + 10,
        "active_subscriptions": 35,
        "users": 1 + 2 + 5,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed realistic demo data.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset and purge existing data before seeding",
    )
    args = parser.parse_args()

    if args.reset:
        print("Resetting database...")
        reset_database()
        print("Database reset complete.")

    if is_seeded() and not args.reset:
        print("Database already contains users; use --reset to overwrite.")
        sys.exit(0)

    print("Seeding demo dataset...")
    counts = seed()
    print("Seed complete successfully:")
    for k, v in counts.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()

-- Brightloop Ledger base schema. Owner: A. Never edit an applied migration.

CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE customers (
  id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL, email TEXT, phone TEXT, address TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now());

CREATE TABLE users (
  id BIGSERIAL PRIMARY KEY, email CITEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('admin','staff','customer')),
  customer_id BIGINT REFERENCES customers(id), is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now());

CREATE TABLE password_reset_tokens (
  id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES users(id),
  token_hash TEXT NOT NULL UNIQUE, expires_at TIMESTAMPTZ NOT NULL, used_at TIMESTAMPTZ);

CREATE TABLE taxes (
  id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL, rate_bps INT NOT NULL CHECK (rate_bps >= 0),
  inclusive BOOLEAN NOT NULL DEFAULT false, active BOOLEAN NOT NULL DEFAULT true);

CREATE TABLE payment_terms (
  id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL, due_days INT NOT NULL CHECK (due_days >= 0));

CREATE TABLE products (
  id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL,
  sales_price_minor BIGINT NOT NULL CHECK (sales_price_minor >= 0),
  cost_price_minor BIGINT NOT NULL DEFAULT 0 CHECK (cost_price_minor >= 0),
  notes TEXT, tax_id BIGINT REFERENCES taxes(id), active BOOLEAN NOT NULL DEFAULT true);

CREATE TABLE product_variants (
  id BIGSERIAL PRIMARY KEY, product_id BIGINT NOT NULL REFERENCES products(id),
  attribute TEXT NOT NULL, value TEXT NOT NULL, extra_price_minor BIGINT NOT NULL DEFAULT 0,
  UNIQUE (product_id, attribute, value));

CREATE TABLE plans (
  id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL,
  price_minor BIGINT NOT NULL DEFAULT 0 CHECK (price_minor >= 0),
  billing_interval TEXT NOT NULL CHECK (billing_interval IN ('day','week','month','year')),
  interval_count INT NOT NULL DEFAULT 1 CHECK (interval_count >= 1),
  min_quantity INT NOT NULL DEFAULT 1 CHECK (min_quantity >= 1),
  available_from DATE, available_to DATE,
  auto_close BOOLEAN NOT NULL DEFAULT false, allow_early_close BOOLEAN NOT NULL DEFAULT true,
  allow_pause BOOLEAN NOT NULL DEFAULT true, allow_renew BOOLEAN NOT NULL DEFAULT true,
  active BOOLEAN NOT NULL DEFAULT true);

CREATE TABLE product_plan_prices (
  product_id BIGINT REFERENCES products(id), plan_id BIGINT REFERENCES plans(id),
  price_minor BIGINT NOT NULL CHECK (price_minor >= 0), PRIMARY KEY (product_id, plan_id));

CREATE TABLE quotation_templates (
  id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL, plan_id BIGINT NOT NULL REFERENCES plans(id),
  validity_days INT NOT NULL CHECK (validity_days >= 1),
  payment_term_id BIGINT REFERENCES payment_terms(id));

CREATE TABLE quotation_template_lines (
  id BIGSERIAL PRIMARY KEY,
  template_id BIGINT NOT NULL REFERENCES quotation_templates(id) ON DELETE CASCADE,
  product_id BIGINT NOT NULL REFERENCES products(id),
  variant_id BIGINT REFERENCES product_variants(id),
  quantity INT NOT NULL CHECK (quantity >= 1));

CREATE SEQUENCE subscription_number_seq;
CREATE SEQUENCE invoice_number_seq;

CREATE TABLE subscriptions (
  id BIGSERIAL PRIMARY KEY,
  number TEXT NOT NULL UNIQUE DEFAULT ('SUB-' || lpad(nextval('subscription_number_seq')::text, 6, '0')),
  customer_id BIGINT NOT NULL REFERENCES customers(id),
  plan_id BIGINT NOT NULL REFERENCES plans(id),
  template_id BIGINT REFERENCES quotation_templates(id),
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','quotation','confirmed','active','closed')),
  start_date DATE NOT NULL, expiry_date DATE NOT NULL CHECK (expiry_date >= start_date),
  payment_term_id BIGINT NOT NULL REFERENCES payment_terms(id),
  quote_sent_on DATE, quote_valid_until DATE,
  is_paused BOOLEAN NOT NULL DEFAULT false, closed_on DATE, close_reason TEXT,
  billing_complete BOOLEAN NOT NULL DEFAULT false,
  version INT NOT NULL DEFAULT 1,
  created_by BIGINT REFERENCES users(id), created_at TIMESTAMPTZ NOT NULL DEFAULT now());

CREATE TABLE subscription_lines (
  id BIGSERIAL PRIMARY KEY,
  subscription_id BIGINT NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
  product_id BIGINT NOT NULL REFERENCES products(id),
  variant_id BIGINT REFERENCES product_variants(id),
  quantity INT NOT NULL CHECK (quantity >= 1),
  unit_price_minor BIGINT NOT NULL CHECK (unit_price_minor >= 0),
  tax_id BIGINT REFERENCES taxes(id),
  tax_rate_bps INT NOT NULL DEFAULT 0, tax_inclusive BOOLEAN NOT NULL DEFAULT false);

CREATE TABLE subscription_pauses (
  id BIGSERIAL PRIMARY KEY, subscription_id BIGINT NOT NULL REFERENCES subscriptions(id),
  paused_on DATE NOT NULL, resumed_on DATE);

CREATE TABLE discounts (
  id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('fixed','percent')),
  value BIGINT NOT NULL CHECK (value > 0),
  min_purchase_minor BIGINT, min_quantity INT,
  starts_on DATE NOT NULL, ends_on DATE NOT NULL CHECK (ends_on >= starts_on),
  usage_limit INT CHECK (usage_limit IS NULL OR usage_limit > 0),
  usage_count INT NOT NULL DEFAULT 0 CHECK (usage_count >= 0),
  scope TEXT NOT NULL CHECK (scope IN ('product','subscription')),
  product_id BIGINT REFERENCES products(id),
  auto_apply BOOLEAN NOT NULL DEFAULT true, active BOOLEAN NOT NULL DEFAULT true,
  created_by BIGINT REFERENCES users(id),
  CHECK (kind <> 'percent' OR value <= 10000),
  CHECK (scope <> 'product' OR product_id IS NOT NULL),
  CHECK (usage_limit IS NULL OR usage_count <= usage_limit));

CREATE TABLE subscription_discounts (
  subscription_id BIGINT REFERENCES subscriptions(id), discount_id BIGINT REFERENCES discounts(id),
  PRIMARY KEY (subscription_id, discount_id));

CREATE TABLE billing_runs (
  id BIGSERIAL PRIMARY KEY, mode TEXT NOT NULL CHECK (mode IN ('dry','live')), as_of DATE NOT NULL,
  status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running','completed','failed')),
  started_by BIGINT REFERENCES users(id),
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(), finished_at TIMESTAMPTZ,
  considered INT NOT NULL DEFAULT 0, invoices_created INT NOT NULL DEFAULT 0,
  amount_minor BIGINT NOT NULL DEFAULT 0, blocked_duplicates INT NOT NULL DEFAULT 0,
  integrity_summary JSONB);

CREATE TABLE invoices (
  id BIGSERIAL PRIMARY KEY, number TEXT UNIQUE,
  subscription_id BIGINT NOT NULL REFERENCES subscriptions(id),
  customer_id BIGINT NOT NULL REFERENCES customers(id),
  period_start DATE NOT NULL, period_end DATE NOT NULL,
  issue_date DATE NOT NULL, due_date DATE NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','confirmed','paid','cancelled')),
  subtotal_minor BIGINT NOT NULL, discount_minor BIGINT NOT NULL DEFAULT 0,
  tax_minor BIGINT NOT NULL, total_minor BIGINT NOT NULL,
  amount_paid_minor BIGINT NOT NULL DEFAULT 0,
  billing_run_id BIGINT REFERENCES billing_runs(id), sent_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (amount_paid_minor >= 0 AND amount_paid_minor <= total_minor));
-- THE KEY CONSTRAINT (idempotency):
CREATE UNIQUE INDEX uq_invoice_period ON invoices (subscription_id, period_start) WHERE status <> 'cancelled';

CREATE TABLE invoice_lines (
  id BIGSERIAL PRIMARY KEY,
  invoice_id BIGINT NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
  description TEXT NOT NULL, product_id BIGINT REFERENCES products(id),
  variant_id BIGINT REFERENCES product_variants(id),
  quantity INT NOT NULL, unit_price_minor BIGINT NOT NULL,
  line_subtotal_minor BIGINT NOT NULL,
  discount_minor BIGINT NOT NULL DEFAULT 0,
  tax_rate_bps INT NOT NULL DEFAULT 0, tax_inclusive BOOLEAN NOT NULL DEFAULT false,
  tax_minor BIGINT NOT NULL DEFAULT 0,
  total_minor BIGINT NOT NULL,
  calc_trace JSONB NOT NULL DEFAULT '[]');

CREATE TABLE discount_redemptions (
  id BIGSERIAL PRIMARY KEY, discount_id BIGINT NOT NULL REFERENCES discounts(id),
  invoice_id BIGINT NOT NULL REFERENCES invoices(id), amount_minor BIGINT NOT NULL,
  voided_at TIMESTAMPTZ, UNIQUE (discount_id, invoice_id));

CREATE TABLE payments (
  id BIGSERIAL PRIMARY KEY, invoice_id BIGINT NOT NULL REFERENCES invoices(id),
  method TEXT NOT NULL CHECK (method IN ('cash','bank_transfer','card','upi','cheque','other')),
  amount_minor BIGINT NOT NULL CHECK (amount_minor > 0), paid_on DATE NOT NULL, note TEXT,
  recorded_by BIGINT REFERENCES users(id), idempotency_key TEXT UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now());

CREATE TABLE billing_run_items (
  id BIGSERIAL PRIMARY KEY, run_id BIGINT NOT NULL REFERENCES billing_runs(id) ON DELETE CASCADE,
  subscription_id BIGINT NOT NULL REFERENCES subscriptions(id),
  disposition TEXT NOT NULL CHECK (disposition IN
    ('billed','up_to_date','skipped_paused','skipped_period_voided','deferred_locked','failed')),
  periods_billed INT NOT NULL DEFAULT 0, invoice_ids BIGINT[] NOT NULL DEFAULT '{}',
  reason TEXT, error TEXT);
-- one item per candidate subscription; dominant disposition priority:
-- billed > failed > deferred_locked > skipped_period_voided > skipped_paused > up_to_date

CREATE TABLE audit_log (
  id BIGSERIAL PRIMARY KEY, at TIMESTAMPTZ NOT NULL DEFAULT now(), actor_id BIGINT,
  action TEXT NOT NULL, entity TEXT NOT NULL, entity_id BIGINT NOT NULL,
  before JSONB, after JSONB);
CREATE FUNCTION forbid_mutation() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION '% is append-only', TG_TABLE_NAME; END; $$ LANGUAGE plpgsql;
CREATE TRIGGER audit_log_immutable BEFORE UPDATE OR DELETE ON audit_log
  FOR EACH ROW EXECUTE FUNCTION forbid_mutation();

CREATE TABLE emails_outbox (
  id BIGSERIAL PRIMARY KEY, kind TEXT NOT NULL, to_email TEXT NOT NULL, subject TEXT NOT NULL,
  body_html TEXT NOT NULL, link TEXT, smtp_status TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now());

CREATE TABLE clock_state (
  id INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  mode TEXT NOT NULL DEFAULT 'real' CHECK (mode IN ('real','simulated')),
  simulated_today DATE, updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
INSERT INTO clock_state (id) VALUES (1);

CREATE TABLE IF NOT EXISTS schema_migrations (filename TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now());

-- Foreign-key and lookup indexes (A). Performance indexes are D's 300_d_indexes.sql.
CREATE INDEX ix_users_customer ON users (customer_id);
CREATE INDEX ix_password_reset_tokens_user ON password_reset_tokens (user_id);
CREATE INDEX ix_products_tax ON products (tax_id);
CREATE INDEX ix_product_variants_product ON product_variants (product_id);
CREATE INDEX ix_quotation_templates_plan ON quotation_templates (plan_id);
CREATE INDEX ix_quotation_templates_term ON quotation_templates (payment_term_id);
CREATE INDEX ix_quotation_template_lines_template ON quotation_template_lines (template_id);
CREATE INDEX ix_quotation_template_lines_product ON quotation_template_lines (product_id);
CREATE INDEX ix_subscriptions_customer ON subscriptions (customer_id);
CREATE INDEX ix_subscriptions_plan ON subscriptions (plan_id);
CREATE INDEX ix_subscription_lines_subscription ON subscription_lines (subscription_id);
CREATE INDEX ix_subscription_pauses_subscription ON subscription_pauses (subscription_id);
CREATE INDEX ix_subscription_discounts_discount ON subscription_discounts (discount_id);
CREATE INDEX ix_invoices_subscription ON invoices (subscription_id);
CREATE INDEX ix_invoices_customer ON invoices (customer_id);
CREATE INDEX ix_invoices_billing_run ON invoices (billing_run_id);
CREATE INDEX ix_invoice_lines_invoice ON invoice_lines (invoice_id);
CREATE INDEX ix_discount_redemptions_invoice ON discount_redemptions (invoice_id);
CREATE INDEX ix_payments_invoice ON payments (invoice_id);
CREATE INDEX ix_billing_run_items_run ON billing_run_items (run_id);
CREATE INDEX ix_billing_run_items_subscription ON billing_run_items (subscription_id);

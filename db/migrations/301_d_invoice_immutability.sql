-- Invoice immutability trigger (BUILD_PLAN §10 D-14). Owner: D.
-- "A DB trigger blocks changes to financial columns of non-draft invoices."
-- Financial columns: subtotal_minor, discount_minor, tax_minor, total_minor, period_start, period_end.
-- Status transitions (confirmed, paid, cancelled) and amount_paid_minor changes are allowed.
-- DELETE on non-draft invoices is completely forbidden.

CREATE OR REPLACE FUNCTION forbid_invoice_mutation() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    IF OLD.status <> 'draft' THEN
      RAISE EXCEPTION 'non-draft invoices cannot be deleted (cancel instead)';
    END IF;
    RETURN OLD;
  ELSIF TG_OP = 'UPDATE' THEN
    IF OLD.status <> 'draft' THEN
      IF (OLD.subtotal_minor <> NEW.subtotal_minor)
         OR (OLD.discount_minor <> NEW.discount_minor)
         OR (OLD.tax_minor <> NEW.tax_minor)
         OR (OLD.total_minor <> NEW.total_minor)
         OR (OLD.period_start <> NEW.period_start)
         OR (OLD.period_end <> NEW.period_end)
         OR (OLD.customer_id <> NEW.customer_id)
         OR (OLD.subscription_id <> NEW.subscription_id) THEN
        RAISE EXCEPTION 'financial columns of non-draft invoices are immutable';
      END IF;
    END IF;
    RETURN NEW;
  END IF;
  RETURN NULL;
END; $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS invoice_immutability ON invoices;

CREATE TRIGGER invoice_immutability
  BEFORE UPDATE OR DELETE ON invoices
  FOR EACH ROW EXECUTE FUNCTION forbid_invoice_mutation();

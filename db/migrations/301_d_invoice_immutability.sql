-- Invoice immutability trigger. Owner: D.
-- Prevents direct UPDATE/DELETE on invoices once confirmed;
-- all state changes must go through app/services/invoices.py which calls audit().

CREATE OR REPLACE FUNCTION forbid_invoice_mutation() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'invoices are append-only, use the service layer to cancel';
  ELSIF TG_OP = 'UPDATE' THEN
    RAISE EXCEPTION 'invoices are append-only, use the service layer to update status';
  END IF;
  RETURN NULL;
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER invoice_immutability
  BEFORE UPDATE OR DELETE ON invoices
  FOR EACH ROW EXECUTE FUNCTION forbid_invoice_mutation();
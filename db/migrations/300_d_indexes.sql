-- Partial index on confirmed invoices by due date
CREATE INDEX idx_invoices_confirmed_due ON invoices (due_date) WHERE status = 'confirmed' AND total_minor > amount_paid_minor;

-- Invoices by customer/issue date/subscription
CREATE INDEX idx_invoices_customer_issue ON invoices (customer_id, issue_date);
CREATE INDEX idx_invoices_subscription ON invoices (subscription_id);

-- Payments by invoice and paid date
CREATE INDEX idx_payments_invoice ON payments (invoice_id);
CREATE INDEX idx_payments_paid_date ON payments (paid_date);

-- Subscriptions by status and customer
CREATE INDEX idx_subscriptions_status ON subscriptions (status, customer_id);

-- Trigram GIN on customer name, subscription number, invoice number
CREATE INDEX idx_customers_name_trgm ON customers USING gin (name gin_trgm_ops);
CREATE INDEX idx_subscriptions_number_trgm ON subscriptions USING gin (number gin_trgm_ops);
CREATE INDEX idx_invoices_number_trgm ON invoices USING gin (number gin_trgm_ops);
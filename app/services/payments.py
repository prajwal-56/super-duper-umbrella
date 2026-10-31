def record(conn, invoice_id, method, amount_minor, paid_on, note, actor_id, idempotency_key=None):
    invoice = conn.execute(
        "SELECT * FROM invoices WHERE id = %s FOR UPDATE",
        (invoice_id,),
    ).fetchone()
    if not invoice:
        raise ValueError("Invoice not found")
    if invoice["status"] != "confirmed":
        raise ValueError("Payments only against confirmed invoices")
    outstanding = invoice["total_minor"] - invoice["amount_paid_minor"]
    if amount_minor > outstanding:
        raise ValueError("Overpayment rejected: amount > outstanding")
    if amount_minor <= 0:
        raise ValueError("Amount must be positive")
    # Check idempotency
    existing = conn.execute(
        "SELECT id FROM payments WHERE invoice_id = %s AND idempotency_key = %s",
        (invoice_id, idempotency_key),
    ).fetchone()
    if existing:
        return existing["id"]
    # Insert payment
    payment_id = conn.execute(
        "INSERT INTO payments (invoice_id, method, amount_minor, paid_on, note, recorded_by, idempotency_key) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (invoice_id, method, amount_minor, paid_on, note, actor_id, idempotency_key),
    ).fetchone()["id"]
    # Update invoice amount_paid
    new_paid = invoice["amount_paid_minor"] + amount_minor
    conn.execute(
        "UPDATE invoices SET amount_paid_minor = %s WHERE id = %s",
        (new_paid, invoice_id),
    )
    # Set status to paid if fully paid
    if new_paid >= invoice["total_minor"]:
        conn.execute(
            "UPDATE invoices SET status = 'paid' WHERE id = %s",
            (invoice_id,),
        )
    _audit(conn, actor_id, "payment_record", "payments", payment_id,
            before=None,
            after={"method": method, "amount_minor": amount_minor, "paid_on": paid_on})
    return payment_id


def _audit(conn, actor_id, action, entity, entity_id, before=None, after=None):
    conn.execute(
        "INSERT INTO audit_log (actor_id, action, entity, entity_id, before, after) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (actor_id, action, entity, entity_id, before, after),
    )
def confirm(conn, invoice_id, actor_id):
    invoice = conn.execute(
        "SELECT * FROM invoices WHERE id = %s FOR UPDATE",
        (invoice_id,),
    ).fetchone()
    if not invoice:
        raise ValueError("Invoice not found")
    if invoice["status"] != "draft":
        raise ValueError("Invoice not in draft status")
    number = _next_invoice_number(conn, invoice["issue_date"])
    conn.execute(
        "UPDATE invoices SET status = 'confirmed', number = %s, issue_date = %s, due_date = %s WHERE id = %s",
        (number, invoice["issue_date"], invoice["due_date"], invoice_id),
    )
    _audit(conn, actor_id, "invoice_confirm", "invoices", invoice_id,
            before={"status": "draft", "number": None},
            after={"status": "confirmed", "number": number})
    return invoice_id


def confirm_many(conn, invoice_ids, actor_id):
    count = 0
    for invoice_id in invoice_ids:
        try:
            confirm(conn, invoice_id, actor_id)
            count += 1
        except ValueError:
            continue
    return count


def cancel(conn, invoice_id, actor_id, reason):
    invoice = conn.execute(
        "SELECT * FROM invoices WHERE id = %s FOR UPDATE",
        (invoice_id,),
    ).fetchone()
    if not invoice:
        raise ValueError("Invoice not found")
    if invoice["status"] == "paid":
        raise ValueError("Cannot cancel a paid invoice")
    if invoice["amount_paid_minor"] > 0:
        raise ValueError("Cannot cancel an invoice with payments")
    # Void redemptions and release usage
    conn.execute(
        "UPDATE discount_redemptions SET voided_at = now() WHERE invoice_id = %s",
        (invoice_id,),
    )
    conn.execute(
        "UPDATE discounts SET usage_count = usage_count - 1 WHERE id IN "
        "(SELECT discount_id FROM discount_redemptions WHERE invoice_id = %s)",
        (invoice_id,),
    )
    conn.execute(
        "UPDATE invoices SET status = 'cancelled' WHERE id = %s",
        (invoice_id,),
    )
    _audit(conn, actor_id, "invoice_cancel", "invoices", invoice_id,
            before={"status": invoice["status"], "amount_paid": invoice["amount_paid_minor"]},
            after={"status": "cancelled", "reason": reason})
    return invoice_id


def send(conn, invoice_id, actor_id):
    invoice = conn.execute(
        "SELECT * FROM invoices WHERE id = %s FOR UPDATE",
        (invoice_id,),
    ).fetchone()
    if invoice["status"] != "confirmed":
        raise ValueError("Only confirmed invoices can be sent")
    conn.execute(
        "UPDATE invoices SET sent_at = now() WHERE id = %s",
        (invoice_id,),
    )
    queue_email(conn, "invoice_send", invoice["customer_email"], ...)
    _audit(conn, actor_id, "invoice_send", "invoices", invoice_id,
            before={"status": "confirmed"}, after={"status": "confirmed", "sent_at": "now"})
    return invoice_id


def get_for_customer(conn, invoice_id, customer_id):
    invoice = conn.execute(
        "SELECT * FROM invoices WHERE id = %s AND customer_id = %s",
        (invoice_id, customer_id),
    ).fetchone()
    if not invoice:
        return None
    lines = conn.execute(
        "SELECT * FROM invoice_lines WHERE invoice_id = %s",
        (invoice_id,),
    ).fetchall()
    return {"invoice": invoice, "lines": lines}


def _next_invoice_number(conn, issue_date):
    year = issue_date.year
    last = conn.execute(
        "SELECT number FROM invoices WHERE status <> 'cancelled' ORDER BY number DESC LIMIT 1"
    ).fetchone()
    if not last:
        return f"INV-{year}-000001"
    last_num = int(last["number"].split("-")[2])
    return f"INV-{year}-{(last_num + 1):06d}"


def _audit(conn, actor_id, action, entity, entity_id, before=None, after=None):
    conn.execute(
        "INSERT INTO audit_log (actor_id, action, entity, entity_id, before, after) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (actor_id, action, entity, entity_id, before, after),
    )
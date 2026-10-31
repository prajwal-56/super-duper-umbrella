def dashboard(conn, filters=None):
    query = """
        SELECT
            COUNT(*) FILTER (WHERE status = 'active') AS active_count,
            COALESCE(SUM(total_minor - amount_paid_minor), 0) AS outstanding,
            COALESCE(SUM(amount_paid_minor), 0) AS collected
        FROM invoices
    """
    if filters:
        # Apply filters like status, date range, customer, etc.
        conditions = []
        if filters.get("status"):
            conditions.append(f"status = '{filters['status']}'")
        if filters.get("date_from"):
            conditions.append(f"issue_date >= '{filters['date_from']}'")
        if filters.get("date_to"):
            conditions.append(f"issue_date <= '{filters['date_to']}'")
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
    query += """
    UNION ALL
    SELECT
        COUNT(*) FILTER (WHERE status = 'confirmed' AND total_minor > amount_paid_minor AND due_date < CURRENT_DATE) AS overdue_count,
        COALESCE(SUM(CASE WHEN status = 'confirmed' AND total_minor > amount_paid_minor AND due_date < CURRENT_DATE THEN total_minor - amount_paid_minor END), 0) AS overdue_amount
    FROM invoices
    """
    result = conn.execute(query).fetchone()
    return {
        "active_count": result["active_count"],
        "outstanding": result["outstanding"],
        "collected": result["collected"],
        "overdue_count": result["overdue_count"],
        "overdue_amount": result["overdue_amount"],
    }


def overdue(conn, filters=None, page=1, page_size=20):
    query = """
        SELECT i.id, i.number, i.period_start, i.period_end, i.issue_date, i.due_date,
               i.total_minor, i.amount_paid_minor,
               (i.total_minor - i.amount_paid_minor) AS outstanding
        FROM invoices i
        WHERE i.status = 'confirmed'
          AND i.total_minor > i.amount_paid_minor
          AND i.due_date < CURRENT_DATE
    """
    if filters:
        if filters.get("customer_id"):
            query += f" AND i.customer_id = {filters['customer_id']}"
    query += " ORDER BY i.due_date LIMIT %s OFFSET %s"
    params = [page_size, (page - 1) * page_size]
    invoices = conn.execute(query, params).fetchall()
    total = conn.execute(
        """SELECT COUNT(*) FROM invoices i
           WHERE i.status = 'confirmed'
             AND i.total_minor > i.amount_paid_minor
             AND i.due_date < CURRENT_DATE""",
    ).fetchone()["count"]
    return {"invoices": invoices, "page": page, "page_size": page_size, "total": total}
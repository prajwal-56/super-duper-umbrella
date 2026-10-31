"""Email outbox. Every email is stored first (D-21); SMTP delivery is optional."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

import psycopg

from app.config import settings


def queue_email(
    conn: psycopg.Connection,
    kind: str,
    to_email: str,
    subject: str,
    body_html: str,
    link: str | None = None,
) -> int:
    """Insert an email into emails_outbox and return its id.

    The row is written in the caller's transaction. If SMTP is configured,
    delivery is attempted after the insert and the outcome stored in
    smtp_status; delivery failures never lose the stored email.
    """
    row = conn.execute(
        """
        INSERT INTO emails_outbox (kind, to_email, subject, body_html, link)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (kind, to_email, subject, body_html, link),
    ).fetchone()
    email_id = int(row["id"])
    if settings.smtp_host:
        status = _send(to_email, subject, body_html, link)
        conn.execute(
            "UPDATE emails_outbox SET smtp_status = %s WHERE id = %s",
            (status, email_id),
        )
    return email_id


def _send(to_email: str, subject: str, body_html: str, link: str | None) -> str:
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to_email
    message["Subject"] = subject
    text = body_html
    if link:
        text = f"{body_html}\n\n{link}"
    message.set_content(text)
    message.add_alternative(body_html, subtype="html")
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.ehlo()
            if settings.smtp_user:
                smtp.starttls()
                smtp.login(settings.smtp_user, settings.smtp_pass)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        return f"failed: {exc}"
    return "sent"

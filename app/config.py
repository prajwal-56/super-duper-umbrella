"""Application configuration, read from the environment (and an optional .env file)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader: KEY=VALUE lines, '#' comments, no overriding real env."""
    if not path.is_file():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv(ROOT / ".env")


def _bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str
    test_database_url: str
    secret_key: str
    app_base_url: str
    demo_mode: bool
    seed_on_boot: bool
    admin_email: str
    admin_password: str
    cron_token: str
    currency_code: str
    business_tz: str
    dev_auth_bypass: bool
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_pass: str
    smtp_from: str

    @property
    def is_production(self) -> bool:
        return self.app_base_url.startswith("https://")


def load_settings() -> Settings:
    return Settings(
        database_url=os.environ.get(
            "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/brightloop"
        ),
        test_database_url=os.environ.get(
            "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/brightloop_test"
        ),
        secret_key=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        app_base_url=os.environ.get("APP_BASE_URL", "http://localhost:8000").rstrip("/"),
        demo_mode=_bool("DEMO_MODE", False),
        seed_on_boot=_bool("SEED_ON_BOOT", False),
        admin_email=os.environ.get("ADMIN_EMAIL", "admin@example.com"),
        admin_password=os.environ.get("ADMIN_PASSWORD", ""),
        cron_token=os.environ.get("CRON_TOKEN", ""),
        currency_code=os.environ.get("CURRENCY_CODE", "INR"),
        business_tz=os.environ.get("BUSINESS_TZ", "Asia/Kolkata"),
        dev_auth_bypass=_bool("DEV_AUTH_BYPASS", False),
        smtp_host=os.environ.get("SMTP_HOST", ""),
        smtp_port=int(os.environ.get("SMTP_PORT", "587") or 587),
        smtp_user=os.environ.get("SMTP_USER", ""),
        smtp_pass=os.environ.get("SMTP_PASS", ""),
        smtp_from=os.environ.get("SMTP_FROM", "billing@brightloop.example"),
    )


settings = load_settings()

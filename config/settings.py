"""Runtime configuration, loaded from environment variables / .env.

Real environment variables win over .env, so CI can inject secrets without a file.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from utils.masking import register_account, register_secret
from utils.safety import assert_safe_url

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env", override=False)


def _str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value.strip())


@dataclass(frozen=True)
class Settings:
    base_url: str
    browser: str
    headless: bool
    timeout: int
    page_load_timeout: int
    accept_insecure_certs: bool
    session_timeout_seconds: int
    session_timeout_grace_seconds: int
    mask_screenshots: bool
    screenshot_dir: Path
    # Secrets and account numbers are excluded from repr so they never show up
    # in tracebacks, --showlocals output or the HTML report.
    username: str = field(repr=False)
    password: str = field(repr=False)
    test_otp: str = field(repr=False)
    lockout_username: str = field(repr=False)
    lockout_password: str = field(repr=False)
    from_account: str = field(repr=False)
    own_to_account: str = field(repr=False)
    third_party_account: str = field(repr=False)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    base_url = _str("BASE_URL").rstrip("/")
    assert_safe_url(base_url)

    settings = Settings(
        base_url=base_url,
        browser=_str("BROWSER", "chrome").lower(),
        headless=_bool("HEADLESS", False),
        timeout=_int("TIMEOUT", 15),
        page_load_timeout=_int("PAGE_LOAD_TIMEOUT", 60),
        accept_insecure_certs=_bool("ACCEPT_INSECURE_CERTS", False),
        session_timeout_seconds=_int("SESSION_TIMEOUT_SECONDS", 300),
        session_timeout_grace_seconds=_int("SESSION_TIMEOUT_GRACE_SECONDS", 30),
        mask_screenshots=_bool("MASK_SCREENSHOTS", True),
        screenshot_dir=PROJECT_ROOT / "reports" / "screenshots",
        username=_str("TEST_USERNAME"),
        password=_str("TEST_PASSWORD"),
        test_otp=_str("TEST_OTP"),
        lockout_username=_str("LOCKOUT_USERNAME"),
        lockout_password=_str("LOCKOUT_PASSWORD"),
        from_account=_str("FROM_ACCOUNT"),
        own_to_account=_str("OWN_TO_ACCOUNT"),
        third_party_account=_str("THIRD_PARTY_ACCOUNT"),
    )

    for secret in (settings.password, settings.lockout_password, settings.test_otp):
        register_secret(secret)
    for account in (settings.from_account, settings.own_to_account, settings.third_party_account):
        register_account(account)

    return settings

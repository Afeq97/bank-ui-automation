"""OTP retrieval behind a single function.

Today it returns the fixed UAT OTP from .env. To switch to a test API or DB
lookup later, implement OtpProvider and call set_otp_provider() (e.g. in conftest.py).
Tests and pages only ever call get_otp().
"""
from __future__ import annotations

from typing import Protocol

from config.settings import get_settings


class OtpProvider(Protocol):
    def get_otp(self, username: str, purpose: str = "login") -> str: ...


class StaticOtpProvider:
    """Returns the fixed TEST_OTP configured for the UAT environment."""

    def get_otp(self, username: str, purpose: str = "login") -> str:
        otp = get_settings().test_otp
        if not otp:
            raise RuntimeError("TEST_OTP is not set in .env")
        return otp


# Example of a future replacement:
#
# class UatApiOtpProvider:
#     def get_otp(self, username, purpose="login"):
#         resp = requests.get(f"{UAT_OTP_API}/otp/latest", params={"user": username, "purpose": purpose})
#         return resp.json()["otp"]

_provider: OtpProvider = StaticOtpProvider()


def set_otp_provider(provider: OtpProvider) -> None:
    global _provider
    _provider = provider


def get_otp(username: str, purpose: str = "login") -> str:
    """Return the OTP the given user should enter for the given purpose ("login", "transfer")."""
    return _provider.get_otp(username, purpose)

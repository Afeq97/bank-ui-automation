"""Environment safety guard: this suite must never touch production."""
from __future__ import annotations

FORBIDDEN_MARKERS = ("prod", "live", "www.")


class UnsafeEnvironmentError(RuntimeError):
    """Raised when a URL looks like a production environment."""


def find_forbidden_markers(url: str) -> list[str]:
    lowered = (url or "").lower()
    return [marker for marker in FORBIDDEN_MARKERS if marker in lowered]


def assert_safe_url(url: str) -> None:
    """Raise if the URL is empty or looks like production.

    Deliberately strict: any URL containing one of the markers is refused,
    even if that produces a false positive.
    """
    if not url:
        raise UnsafeEnvironmentError("BASE_URL is not set. Copy .env.example to .env and set the UAT URL.")
    hits = find_forbidden_markers(url)
    if hits:
        raise UnsafeEnvironmentError(
            f"Refusing to run: URL '{url}' contains {hits}. "
            "This suite may only run against the test/UAT environment."
        )

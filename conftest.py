"""Shared fixtures, safety guard and failure screenshots."""
from __future__ import annotations

import base64
import os
import re
from datetime import datetime

import pytest
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver

from config.settings import Settings, get_settings
from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage
from utils.data_loader import load_test_data
from utils.driver_factory import create_driver
from utils.logger import get_logger, install_log_masking
from utils.masking import account_pattern_sources, mask_text, secrets_for_browser_masking
from utils.safety import UnsafeEnvironmentError

log = get_logger(__name__)

try:
    from pytest_html import extras as html_extras
except ImportError:  # pytest-html not installed
    html_extras = None


# ---------------------------------------------------------------- safety guard
def pytest_configure(config):
    install_log_masking()
    if not os.getenv("BASE_URL", "").strip():
        # Allowed so offline unit tests can run; browser fixtures fail with a clear message.
        return
    try:
        settings = get_settings()
    except UnsafeEnvironmentError as exc:
        pytest.exit(str(exc), returncode=3)

    try:
        from pytest_metadata.plugin import metadata_key
        config.stash[metadata_key]["Base URL"] = settings.base_url
        config.stash[metadata_key]["Browser"] = f"{settings.browser} (headless={settings.headless})"
    except Exception:
        pass


# ---------------------------------------------------------------- fixtures
@pytest.fixture(scope="session")
def settings() -> Settings:
    try:
        return get_settings()
    except UnsafeEnvironmentError as exc:
        pytest.exit(str(exc), returncode=3)


@pytest.fixture(scope="session")
def test_data() -> dict:
    return load_test_data()


@pytest.fixture(scope="session")
def credentials(settings):
    if not (settings.username and settings.password):
        pytest.skip("TEST_USERNAME / TEST_PASSWORD not set in .env")
    return settings.username, settings.password


@pytest.fixture
def driver(settings) -> WebDriver:
    """Fresh browser per test, always quit afterwards."""
    drv = create_driver(settings)
    yield drv
    drv.quit()


class _SharedBrowser:
    """One browser per test session (per xdist worker), restarted if it crashes,
    so a single browser crash doesn't error every remaining test."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.driver: WebDriver | None = None

    def get(self) -> WebDriver:
        if self.driver is not None:
            try:
                self.driver.current_url  # cheap liveness check
                return self.driver
            except WebDriverException:
                log.warning("Shared browser is no longer responding - starting a new one")
                self.quit()
        self.driver = create_driver(self.settings)
        return self.driver

    def quit(self) -> None:
        if self.driver is not None:
            try:
                self.driver.quit()
            except WebDriverException:
                pass
            self.driver = None


@pytest.fixture(scope="session")
def _shared_browser(settings):
    browser = _SharedBrowser(settings)
    yield browser
    browser.quit()


@pytest.fixture
def logged_in(_shared_browser, credentials) -> DashboardPage:
    """Dashboard of a user that is logged in once per session.

    Each test starts from a freshly loaded dashboard. If the session has expired
    (or was ended by another login), it logs in again.
    """
    drv = _shared_browser.get()
    dashboard = DashboardPage(drv).open()
    if not dashboard.is_loaded(timeout=5):
        log.info("Not logged in (or session expired) - logging in")
        dashboard = LoginPage(drv).open().login(*credentials)
    return dashboard


# ---------------------------------------------------------------- failure screenshots
_MASK_PAGE_JS = """
const patterns = arguments[0].map(p => new RegExp(p, 'g'));
const secrets = arguments[1];
const maskAcct = s => '****' + s.replace(/\\D/g, '').slice(-4);
const apply = t => {
  for (const s of secrets) t = t.split(s).join('****');
  for (const re of patterns) t = t.replace(re, maskAcct);
  return t;
};
const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
let node;
while ((node = walker.nextNode())) {
  const v = apply(node.nodeValue);
  if (v !== node.nodeValue) node.nodeValue = v;
}
document.querySelectorAll('input, textarea').forEach(el => {
  if (el.type === 'password' || !el.value) return;
  const v = apply(el.value);
  if (v !== el.value) el.value = v;
});
"""


def _find_driver(item) -> WebDriver | None:
    for value in getattr(item, "funcargs", {}).values():
        if isinstance(value, WebDriver):
            return value
        drv = getattr(value, "driver", None)
        if isinstance(drv, WebDriver):
            return drv
    return None


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when not in ("setup", "call") or not report.failed:
        return
    drv = _find_driver(item)
    if drv is None:
        return
    try:
        settings = get_settings()
        if settings.mask_screenshots:
            # The test already failed, so changing the DOM can no longer affect it.
            drv.execute_script(_MASK_PAGE_JS, account_pattern_sources(), secrets_for_browser_masking())
        png_b64 = drv.get_screenshot_as_base64()

        settings.screenshot_dir.mkdir(parents=True, exist_ok=True)
        name = re.sub(r"[^A-Za-z0-9_.-]+", "_", item.nodeid)[-120:]
        path = settings.screenshot_dir / f"{name}_{datetime.now():%Y%m%d_%H%M%S}.png"
        path.write_bytes(base64.b64decode(png_b64))
        log.info("Failure screenshot saved: %s", path)

        if html_extras is not None:
            extras = getattr(report, "extras", [])
            extras.append(html_extras.url(mask_text(drv.current_url)))
            extras.append(html_extras.png(png_b64, "Screenshot on failure"))
            report.extras = extras
    except Exception as exc:  # never hide the real failure behind a screenshot error
        log.warning("Could not capture failure screenshot: %s", exc)

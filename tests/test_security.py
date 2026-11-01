import pytest

from pages.base_page import BasePage
from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage
from utils.data_loader import load_test_data

PROTECTED_PATHS = load_test_data()["security"]["protected_paths"]


@pytest.mark.smoke
@pytest.mark.security
@pytest.mark.regression
@pytest.mark.parametrize("path", PROTECTED_PATHS)
def test_protected_page_redirects_to_login_when_not_logged_in(driver, path):
    BasePage(driver).navigate(path)

    login = LoginPage(driver)
    assert login.is_displayed(timeout=login.timeout), f"{path} did not redirect to login"
    assert not DashboardPage(driver).has_account_data(timeout=1), f"{path} exposed account data"


@pytest.mark.security
@pytest.mark.regression
def test_back_button_after_logout_does_not_show_account_data(driver, credentials):
    dashboard = LoginPage(driver).open().login(*credentials)
    assert dashboard.has_account_data()
    dashboard.logout()

    driver.back()

    # Give the app time to redirect; the redirect itself is optional, hiding the data is not.
    LoginPage(driver).is_displayed(timeout=dashboard.timeout)
    assert not dashboard.has_account_data(timeout=2), "Account data visible after logout + back button"


@pytest.mark.security
@pytest.mark.session
@pytest.mark.regression
def test_user_logged_out_after_inactivity(driver, credentials, settings):
    if settings.session_timeout_seconds <= 0:
        pytest.skip("SESSION_TIMEOUT_SECONDS is 0 - session timeout test disabled")
    dashboard = LoginPage(driver).open().login(*credentials)
    login = LoginPage(driver)
    max_wait = settings.session_timeout_seconds + settings.session_timeout_grace_seconds

    # Stay idle (no clicks, typing or navigation) and wait explicitly for the app to log out.
    # Polling only reads the DOM, which does not count as user activity.
    logged_out_by_app = login.wait_until(
        lambda d: login.is_displayed(timeout=0) or login.is_session_expired_message_displayed(timeout=0),
        timeout=max_wait, poll=5,
    )
    if not logged_out_by_app:
        # App has no client-side timer: the server session should still be gone,
        # which shows up on the next request.
        dashboard.open()

    assert login.is_displayed(timeout=login.timeout) or login.is_session_expired_message_displayed(), \
        f"User still logged in after {max_wait}s of inactivity"
    assert not dashboard.has_account_data(timeout=1)

from decimal import Decimal

import pytest

from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage


@pytest.mark.smoke
@pytest.mark.regression
def test_account_balance_is_displayed(logged_in, settings):
    balances = logged_in.get_all_balances()

    assert balances, "No accounts shown on the dashboard"
    assert all(isinstance(b, Decimal) for b in balances)
    if settings.from_account:
        assert isinstance(logged_in.get_balance(settings.from_account), Decimal)


@pytest.mark.smoke
@pytest.mark.regression
def test_logout_returns_to_login(driver, credentials):
    dashboard = LoginPage(driver).open().login(*credentials)

    login = dashboard.logout()

    assert login.is_displayed()
    # The session must really be gone, not just the screen.
    DashboardPage(driver).open()
    assert login.is_displayed(timeout=login.timeout)

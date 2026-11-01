from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

from pages.base_page import BasePage
from utils.masking import digits_only, mask_account
from utils.money import parse_amount

if TYPE_CHECKING:
    from pages.login_page import LoginPage
    from pages.transaction_history_page import TransactionHistoryPage
    from pages.transfer_page import TransferPage


def account_matches(displayed: str, account_number: str) -> bool:
    """True if a displayed account number (full or masked like '****1234') refers to account_number."""
    shown, target = digits_only(displayed), digits_only(account_number)
    if not shown or not target:
        return False
    if len(shown) >= len(target):
        return shown == target
    return len(shown) >= 4 and target.endswith(shown)


class DashboardPage(BasePage):
    PATH = "/dashboard"  # update to match the real app

    # --- Locators: placeholders - update to match the real app ---
    WELCOME_BANNER = (By.CSS_SELECTOR, '[data-testid="welcome-banner"]')
    ACCOUNT_ROWS = (By.CSS_SELECTOR, '[data-testid="account-row"]')
    ACCOUNT_NUMBER_IN_ROW = (By.CSS_SELECTOR, '[data-testid="account-number"]')
    ACCOUNT_BALANCE_IN_ROW = (By.CSS_SELECTOR, '[data-testid="account-balance"]')  # available balance
    NAV_TRANSFER = (By.CSS_SELECTOR, '[data-testid="nav-transfer"]')
    NAV_HISTORY = (By.CSS_SELECTOR, '[data-testid="nav-transactions"]')
    LOGOUT_BUTTON = (By.CSS_SELECTOR, '[data-testid="logout"]')

    def wait_until_loaded(self, timeout: float | None = None) -> "DashboardPage":
        self.find(self.ACCOUNT_ROWS, timeout)
        return self

    def is_loaded(self, timeout: float = 2) -> bool:
        return self.is_visible(self.ACCOUNT_ROWS, timeout)

    def has_account_data(self, timeout: float = 2) -> bool:
        """True if any account row or balance is visible on the current page."""
        return self.is_visible(self.ACCOUNT_ROWS, timeout) or self.is_visible(self.ACCOUNT_BALANCE_IN_ROW, 0)

    def account_count(self) -> int:
        return len(self.find_all_visible(self.ACCOUNT_ROWS))

    def get_all_balances(self) -> list[Decimal]:
        self.wait_until_loaded()
        return [
            parse_amount(row.find_element(*self.ACCOUNT_BALANCE_IN_ROW).text)
            for row in self.find_all_visible(self.ACCOUNT_ROWS)
        ]

    def get_balance(self, account_number: str, timeout: float | None = None) -> Decimal:
        def _balance_text(driver):
            for row in driver.find_elements(*self.ACCOUNT_ROWS):
                if account_matches(row.find_element(*self.ACCOUNT_NUMBER_IN_ROW).text, account_number):
                    text = row.find_element(*self.ACCOUNT_BALANCE_IN_ROW).text.strip()
                    return text or False
            return False

        text = self._wait(timeout).until(
            _balance_text, message=f"Balance not found for account {mask_account(account_number)}"
        )
        return parse_amount(text)

    def wait_for_balance_change(self, account_number: str, previous: Decimal,
                                timeout: float | None = None) -> Decimal:
        """Reload the dashboard until the balance differs from `previous`; return the latest balance.
        Returns the unchanged balance if it never changes (the caller's assertion then fails clearly)."""
        def _changed(driver):
            self.open()
            current = self.get_balance(account_number)
            return current if current != previous else False

        try:
            return self._wait(timeout or self.timeout * 2, poll=2).until(_changed)
        except TimeoutException:
            return self.get_balance(account_number)

    def go_to_transfer(self) -> "TransferPage":
        from pages.transfer_page import TransferPage
        self.click(self.NAV_TRANSFER)
        return TransferPage(self.driver).wait_until_loaded()

    def go_to_history(self) -> "TransactionHistoryPage":
        from pages.transaction_history_page import TransactionHistoryPage
        self.click(self.NAV_HISTORY)
        return TransactionHistoryPage(self.driver).wait_until_loaded()

    def logout(self) -> "LoginPage":
        from pages.login_page import LoginPage
        self.click(self.LOGOUT_BUTTON)
        login = LoginPage(self.driver)
        login.find(login.USERNAME_INPUT)
        return login

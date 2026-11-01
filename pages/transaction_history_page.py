from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

from pages.base_page import BasePage
from utils.money import parse_amount


@dataclass
class Transaction:
    reference: str
    amount: Decimal
    description: str
    date: str


class TransactionHistoryPage(BasePage):
    PATH = "/transactions"  # update to match the real app

    # --- Locators: placeholders - update to match the real app ---
    TABLE = (By.CSS_SELECTOR, '[data-testid="transaction-table"]')
    ROWS = (By.CSS_SELECTOR, '[data-testid="transaction-row"]')
    ROW_REFERENCE = (By.CSS_SELECTOR, '[data-testid="txn-reference"]')
    ROW_AMOUNT = (By.CSS_SELECTOR, '[data-testid="txn-amount"]')
    ROW_DESCRIPTION = (By.CSS_SELECTOR, '[data-testid="txn-description"]')
    ROW_DATE = (By.CSS_SELECTOR, '[data-testid="txn-date"]')

    def wait_until_loaded(self, timeout: float | None = None) -> "TransactionHistoryPage":
        self.find(self.TABLE, timeout)
        return self

    def get_transactions(self, timeout: float = 5) -> list[Transaction]:
        return [
            Transaction(
                reference=row.find_element(*self.ROW_REFERENCE).text.strip(),
                amount=parse_amount(row.find_element(*self.ROW_AMOUNT).text),
                description=row.find_element(*self.ROW_DESCRIPTION).text.strip(),
                date=row.find_element(*self.ROW_DATE).text.strip(),
            )
            for row in self.find_all_visible(self.ROWS, timeout)
        ]

    def find_by_reference(self, reference: str, timeout: float | None = None) -> Transaction | None:
        """Find a transaction by reference, reloading the page while waiting for it to post.
        Returns None if it never appears within the timeout."""
        def _lookup(driver):
            for txn in self.get_transactions():
                if txn.reference == reference:
                    return txn
            driver.refresh()
            return False

        try:
            return self._wait(timeout or self.timeout * 4, poll=3).until(_lookup)
        except TimeoutException:
            return None

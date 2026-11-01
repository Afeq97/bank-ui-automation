from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from pages.base_page import BasePage, Locator
from pages.dashboard_page import account_matches
from utils.logger import get_logger
from utils.masking import mask_account
from utils.money import format_amount
from utils.otp import get_otp

log = get_logger(__name__)

OWN = "own"
THIRD_PARTY = "third_party"


@dataclass
class TransferOutcome:
    success: bool
    reference: str | None = None
    message: str = ""


class TransferPage(BasePage):
    PATH = "/transfer"  # update to match the real app

    # --- Locators: placeholders - update to match the real app ---
    TYPE_OWN = (By.CSS_SELECTOR, '[data-testid="transfer-type-own"]')
    TYPE_THIRD_PARTY = (By.CSS_SELECTOR, '[data-testid="transfer-type-third-party"]')
    FROM_ACCOUNT_SELECT = (By.CSS_SELECTOR, '[data-testid="from-account"]')        # native <select>
    TO_OWN_ACCOUNT_SELECT = (By.CSS_SELECTOR, '[data-testid="to-own-account"]')    # native <select>
    RECIPIENT_ACCOUNT_INPUT = (By.CSS_SELECTOR, '[data-testid="recipient-account"]')
    RECIPIENT_BANK_SELECT = (By.CSS_SELECTOR, '[data-testid="recipient-bank"]')    # optional
    AMOUNT_INPUT = (By.CSS_SELECTOR, '[data-testid="transfer-amount"]')
    DESCRIPTION_INPUT = (By.CSS_SELECTOR, '[data-testid="transfer-description"]')
    SUBMIT_BUTTON = (By.CSS_SELECTOR, '[data-testid="transfer-submit"]')           # "Next"/"Continue"
    CONFIRM_BUTTON = (By.CSS_SELECTOR, '[data-testid="transfer-confirm"]')         # review screen
    TRANSFER_OTP_INPUT = (By.CSS_SELECTOR, '[data-testid="transfer-otp-input"]')   # TAC, if required
    TRANSFER_OTP_SUBMIT = (By.CSS_SELECTOR, '[data-testid="transfer-otp-submit"]')
    SUCCESS_MESSAGE = (By.CSS_SELECTOR, '[data-testid="transfer-success"]')
    REFERENCE_NUMBER = (By.CSS_SELECTOR, '[data-testid="transfer-reference"]')
    # Any validation / business error on the transfer flow (field-level or banner)
    ANY_ERROR = (By.CSS_SELECTOR,
                 '[data-testid="amount-error"], [data-testid="recipient-error"], [data-testid="transfer-error"]')

    def wait_until_loaded(self, timeout: float | None = None) -> "TransferPage":
        self.find(self.AMOUNT_INPUT, timeout)
        return self

    # ---------- form ----------
    def _select_account(self, locator: Locator, account_number: str) -> None:
        """Pick the option whose value or text refers to the account (full or masked number).
        If the real app uses a custom dropdown instead of <select>, rewrite this method."""
        select = Select(self.find(locator))
        for option in select.options:
            if account_matches(option.get_attribute("value") or "", account_number) or \
                    account_matches(option.text, account_number):
                select.select_by_visible_text(option.text)
                return
        raise AssertionError(f"Account {mask_account(account_number)} not available in {locator}")

    def fill_form(self, *, transfer_type: str, from_account: str, to_account: str,
                  amount: Decimal | str, description: str = "", recipient_bank: str | None = None) -> None:
        log.info("Transfer %s: %s -> %s, amount %s", transfer_type,
                 mask_account(from_account), mask_account(to_account), amount)
        if transfer_type == OWN:
            self.click(self.TYPE_OWN)
            self._select_account(self.FROM_ACCOUNT_SELECT, from_account)
            self._select_account(self.TO_OWN_ACCOUNT_SELECT, to_account)
        elif transfer_type == THIRD_PARTY:
            self.click(self.TYPE_THIRD_PARTY)
            self._select_account(self.FROM_ACCOUNT_SELECT, from_account)
            if recipient_bank:
                Select(self.find(self.RECIPIENT_BANK_SELECT)).select_by_visible_text(recipient_bank)
            self.type(self.RECIPIENT_ACCOUNT_INPUT, to_account)
        else:
            raise ValueError(f"Unknown transfer type: {transfer_type}")

        # Negative amounts ("-10.00") are typed as-is so the app's validation is exercised.
        amount_text = amount if isinstance(amount, str) and amount.strip().startswith("-") else format_amount(amount)
        self.type(self.AMOUNT_INPUT, amount_text)
        if description:
            self.type(self.DESCRIPTION_INPUT, description)

    # ---------- submit ----------
    def submit_and_get_outcome(self, timeout: float | None = None) -> TransferOutcome:
        """Submit, step through the review and OTP/TAC screens if they appear, and return
        the final outcome. Each step is performed at most once - never double-submits."""
        self.click(self.SUBMIT_BUTTON)
        handled: set[str] = set()
        while True:
            states = {"success": self.SUCCESS_MESSAGE, "error": self.ANY_ERROR}
            if "confirm" not in handled:
                states["confirm"] = self.CONFIRM_BUTTON
            if "otp" not in handled:
                states["otp"] = self.TRANSFER_OTP_INPUT
            state = self.wait_for_first(states, timeout)

            if state == "success":
                return TransferOutcome(True, self.get_text(self.REFERENCE_NUMBER), self.get_text(self.SUCCESS_MESSAGE))
            if state == "error":
                return TransferOutcome(False, None, self.get_error_text())

            handled.add(state)
            if state == "confirm":
                self.click(self.CONFIRM_BUTTON)
            else:
                self.type(self.TRANSFER_OTP_INPUT, get_otp(self.settings.username, purpose="transfer"),
                          sensitive=True)
                self.click(self.TRANSFER_OTP_SUBMIT)

    def get_error_text(self) -> str:
        texts = [e.text.strip() for e in self.driver.find_elements(*self.ANY_ERROR) if e.is_displayed()]
        return " | ".join(t for t in texts if t)

    def transfer(self, *, transfer_type: str, from_account: str, to_account: str, amount: Decimal | str,
                 description: str = "", recipient_bank: str | None = None) -> TransferOutcome:
        self.fill_form(transfer_type=transfer_type, from_account=from_account, to_account=to_account,
                       amount=amount, description=description, recipient_bank=recipient_bank)
        outcome = self.submit_and_get_outcome()
        log.info("Transfer outcome: success=%s reference=%s message=%s",
                 outcome.success, outcome.reference, outcome.message)
        return outcome

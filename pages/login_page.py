from __future__ import annotations

from selenium.webdriver.common.by import By

from pages.base_page import BasePage
from pages.dashboard_page import DashboardPage
from utils.otp import get_otp


class LoginPage(BasePage):
    PATH = "/login"  # update to match the real app

    # --- Locators: placeholders - update to match the real app ---
    USERNAME_INPUT = (By.ID, "username")
    PASSWORD_INPUT = (By.ID, "password")
    LOGIN_BUTTON = (By.CSS_SELECTOR, '[data-testid="login-submit"]')
    OTP_INPUT = (By.CSS_SELECTOR, '[data-testid="otp-input"]')
    OTP_SUBMIT_BUTTON = (By.CSS_SELECTOR, '[data-testid="otp-submit"]')
    LOGIN_ERROR = (By.CSS_SELECTOR, '[data-testid="login-error"]')        # wrong password / locked banner
    OTP_ERROR = (By.CSS_SELECTOR, '[data-testid="otp-error"]')
    USERNAME_FIELD_ERROR = (By.CSS_SELECTOR, '[data-testid="username-error"]')
    PASSWORD_FIELD_ERROR = (By.CSS_SELECTOR, '[data-testid="password-error"]')
    SESSION_EXPIRED_MESSAGE = (By.CSS_SELECTOR, '[data-testid="session-expired"]')

    def is_displayed(self, timeout: float = 2) -> bool:
        return self.is_visible(self.USERNAME_INPUT, timeout)

    def submit_credentials(self, username: str, password: str) -> None:
        self.type(self.USERNAME_INPUT, username)
        self.type(self.PASSWORD_INPUT, password, sensitive=True)
        self.click(self.LOGIN_BUTTON)

    def is_otp_step_displayed(self, timeout: float = 2) -> bool:
        return self.is_visible(self.OTP_INPUT, timeout)

    def submit_otp(self, otp: str) -> None:
        self.type(self.OTP_INPUT, otp, sensitive=True)
        self.click(self.OTP_SUBMIT_BUTTON)

    def login(self, username: str, password: str, otp: str | None = None) -> DashboardPage:
        """Full login: credentials -> OTP -> dashboard."""
        self.submit_credentials(username, password)
        self.find(self.OTP_INPUT)
        self.submit_otp(otp if otp is not None else get_otp(username, purpose="login"))
        return DashboardPage(self.driver).wait_until_loaded()

    def get_login_error(self, timeout: float | None = None) -> str:
        return self.get_text(self.LOGIN_ERROR, timeout)

    def get_otp_error(self, timeout: float | None = None) -> str:
        return self.get_text(self.OTP_ERROR, timeout)

    def get_field_validation(self, field: str, timeout: float = 5) -> str:
        """Validation message for 'username' or 'password'.

        Checks the app's inline error element first; falls back to the browser's
        native HTML5 validation message (used when inputs have the 'required' attribute).
        """
        error_locator, input_locator = {
            "username": (self.USERNAME_FIELD_ERROR, self.USERNAME_INPUT),
            "password": (self.PASSWORD_FIELD_ERROR, self.PASSWORD_INPUT),
        }[field]
        if self.is_visible(error_locator, timeout):
            return self.get_text(error_locator)
        return (self.find(input_locator).get_property("validationMessage") or "").strip()

    def is_session_expired_message_displayed(self, timeout: float = 2) -> bool:
        return self.is_visible(self.SESSION_EXPIRED_MESSAGE, timeout)

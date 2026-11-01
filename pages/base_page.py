"""BasePage: navigation plus explicit-wait helpers. No time.sleep() anywhere."""
from __future__ import annotations

from urllib.parse import urlparse

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config.settings import get_settings
from utils.logger import get_logger
from utils.safety import assert_safe_url

Locator = tuple[str, str]
log = get_logger(__name__)


class BasePage:
    PATH = ""  # relative path of the screen, e.g. "/login"

    def __init__(self, driver: WebDriver, timeout: int | None = None):
        self.driver = driver
        self.settings = get_settings()
        self.timeout = timeout or self.settings.timeout

    # ---------- navigation ----------
    def url_for(self, path: str) -> str:
        return f"{self.settings.base_url}/{path.lstrip('/')}"

    def navigate(self, path: str) -> None:
        url = self.url_for(path)
        assert_safe_url(url)
        log.info("Navigating to %s", path)
        self.driver.get(url)
        # Also guard against the app redirecting somewhere it should not.
        assert_safe_url(self.driver.current_url)

    def open(self):
        self.navigate(self.PATH)
        return self

    @property
    def current_path(self) -> str:
        return urlparse(self.driver.current_url).path

    # ---------- waits ----------
    def _wait(self, timeout: float | None = None, poll: float = 0.5) -> WebDriverWait:
        return WebDriverWait(
            self.driver,
            self.timeout if timeout is None else timeout,
            poll_frequency=poll,
            ignored_exceptions=(StaleElementReferenceException,),
        )

    def find(self, locator: Locator, timeout: float | None = None) -> WebElement:
        return self._wait(timeout).until(
            EC.visibility_of_element_located(locator), message=f"Element not visible: {locator}"
        )

    def find_all_visible(self, locator: Locator, timeout: float | None = None) -> list[WebElement]:
        """Visible elements matching the locator, or [] if none appear within the timeout."""
        try:
            return self._wait(timeout).until(EC.visibility_of_all_elements_located(locator))
        except TimeoutException:
            return []

    def click(self, locator: Locator, timeout: float | None = None) -> None:
        def _click(driver):
            element = EC.element_to_be_clickable(locator)(driver)
            if not element:
                return False
            try:
                element.click()
                return True
            except (ElementClickInterceptedException, StaleElementReferenceException):
                return False  # overlay/spinner still on top - retry until timeout

        log.info("Click %s", locator)
        self._wait(timeout).until(_click, message=f"Element not clickable: {locator}")

    def type(self, locator: Locator, text: str, *, sensitive: bool = False, clear: bool = True,
             timeout: float | None = None) -> None:
        element = self._wait(timeout).until(
            EC.element_to_be_clickable(locator), message=f"Input not interactable: {locator}"
        )
        if clear:
            element.clear()
            if element.get_attribute("value"):  # JS-framework inputs sometimes ignore clear()
                element.send_keys(Keys.CONTROL, "a")
                element.send_keys(Keys.DELETE)
        log.info("Type into %s: %s", locator, "****" if sensitive else text)
        if text:
            element.send_keys(text)

    def get_text(self, locator: Locator, timeout: float | None = None) -> str:
        """Visible, non-empty text of the element (waits for the text to be populated)."""
        def _text(driver):
            element = EC.visibility_of_element_located(locator)(driver)
            if not element:
                return False
            return element.text.strip() or False

        return self._wait(timeout).until(_text, message=f"No text in element: {locator}")

    def is_visible(self, locator: Locator, timeout: float = 2) -> bool:
        try:
            self._wait(timeout).until(EC.visibility_of_element_located(locator))
            return True
        except TimeoutException:
            return False

    def wait_until_invisible(self, locator: Locator, timeout: float | None = None) -> bool:
        try:
            self._wait(timeout).until(EC.invisibility_of_element_located(locator))
            return True
        except TimeoutException:
            return False

    def wait_for_path(self, path: str, timeout: float | None = None) -> None:
        self._wait(timeout).until(
            lambda d: urlparse(d.current_url).path.rstrip("/").endswith(path.rstrip("/")),
            message=f"URL path did not become {path}",
        )

    def wait_until(self, condition, timeout: float | None = None, poll: float = 0.5) -> bool:
        """Wait for an arbitrary condition(driver); True if it became truthy, False on timeout."""
        try:
            self._wait(timeout, poll).until(condition)
            return True
        except TimeoutException:
            return False

    def wait_for_first(self, states: dict[str, Locator], timeout: float | None = None) -> str:
        """Wait until any of the locators is visible; return its key (first match in dict order)."""
        def _first(driver):
            for name, locator in states.items():
                for element in driver.find_elements(*locator):
                    if element.is_displayed():
                        return name
            return False

        return self._wait(timeout).until(_first, message=f"None of {list(states)} appeared")

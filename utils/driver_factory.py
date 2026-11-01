"""Creates WebDriver instances. Selenium Manager (Selenium 4.6+) downloads drivers automatically."""
from __future__ import annotations

from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver

from config.settings import Settings
from utils.logger import get_logger

log = get_logger(__name__)

WINDOW_SIZE = (1920, 1080)


def _chromium_options(options, settings: Settings):
    if settings.headless:
        options.add_argument("--headless=new")
    options.add_argument(f"--window-size={WINDOW_SIZE[0]},{WINDOW_SIZE[1]}")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-dev-shm-usage")
    # Stop the password-manager / leaked-password popups from covering the login form.
    options.add_experimental_option("prefs", {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.password_manager_leak_detection": False,
    })
    options.accept_insecure_certs = settings.accept_insecure_certs
    return options


def create_driver(settings: Settings) -> WebDriver:
    browser = settings.browser
    log.info("Starting %s (headless=%s)", browser, settings.headless)

    if browser == "chrome":
        driver = webdriver.Chrome(options=_chromium_options(webdriver.ChromeOptions(), settings))
    elif browser == "edge":
        driver = webdriver.Edge(options=_chromium_options(webdriver.EdgeOptions(), settings))
    elif browser == "firefox":
        options = webdriver.FirefoxOptions()
        if settings.headless:
            options.add_argument("-headless")
        options.accept_insecure_certs = settings.accept_insecure_certs
        driver = webdriver.Firefox(options=options)
    else:
        raise ValueError(f"Unsupported BROWSER '{browser}'. Use chrome, edge or firefox.")

    driver.implicitly_wait(0)  # explicit waits only
    driver.set_page_load_timeout(settings.page_load_timeout)
    driver.set_window_size(*WINDOW_SIZE)
    return driver

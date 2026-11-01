import pytest

from pages.login_page import LoginPage
from utils.data_loader import as_params, load_test_data
from utils.otp import get_otp

DATA = load_test_data()["login"]


def _assert_message(actual: str, expected: str | None):
    assert actual, "Expected an error message but none was shown"
    if expected:
        assert expected.lower() in actual.lower(), f"Expected '{expected}' in error, got '{actual}'"


@pytest.mark.smoke
@pytest.mark.regression
def test_valid_login_with_otp_goes_to_dashboard(driver, credentials):
    dashboard = LoginPage(driver).open().login(*credentials)

    assert dashboard.is_loaded()
    assert dashboard.current_path.rstrip("/").endswith(dashboard.PATH)


# Note: each wrong-password / wrong-OTP case is a failed attempt on TEST_USERNAME.
# Keep the number of cases below the lockout threshold (the next valid login resets the counter).
@pytest.mark.regression
@pytest.mark.negative
@pytest.mark.parametrize("case", as_params(DATA["wrong_password"]))
def test_wrong_password_shows_error(driver, credentials, case):
    page = LoginPage(driver).open()
    page.submit_credentials(case["username"], case["password"])

    _assert_message(page.get_login_error(), case["expected_error"])
    assert not page.is_otp_step_displayed(timeout=1), "OTP step must not be reached with a wrong password"


@pytest.mark.regression
@pytest.mark.negative
@pytest.mark.parametrize("case", as_params(DATA["wrong_otp"]))
def test_wrong_otp_shows_error(driver, credentials, case):
    if case["otp"] == get_otp(credentials[0]):
        pytest.skip("Configured wrong OTP equals the real test OTP")
    page = LoginPage(driver).open()
    page.submit_credentials(*credentials)
    assert page.is_otp_step_displayed(timeout=page.timeout), "OTP step not shown after valid credentials"

    page.submit_otp(case["otp"])

    _assert_message(page.get_otp_error(), case["expected_error"])
    assert page.is_otp_step_displayed(timeout=1) or page.is_displayed(timeout=1), \
        "User must stay on the OTP/login screen after a wrong OTP"


@pytest.mark.regression
@pytest.mark.negative
def test_account_locks_after_failed_attempts(driver, settings, test_data):
    """Locks LOCKOUT_USERNAME. Ask the UAT admin to unlock it before the next run."""
    if not (settings.lockout_username and settings.lockout_password):
        pytest.skip("LOCKOUT_USERNAME / LOCKOUT_PASSWORD not set - dedicated lockout account required")
    attempts = test_data["limits"]["max_failed_login_attempts"]
    lockout = DATA["lockout"]
    page = LoginPage(driver)

    for attempt in range(1, attempts + 1):
        page.open()  # fresh page so the previous error message is not re-read
        page.submit_credentials(settings.lockout_username, lockout["wrong_password"])
        assert page.get_login_error(), f"No error shown on failed attempt {attempt}"

    # Even the correct password must now be refused.
    page.open()
    page.submit_credentials(settings.lockout_username, settings.lockout_password)

    _assert_message(page.get_login_error(), lockout["expected_message"])
    assert not page.is_otp_step_displayed(timeout=1), "Locked account must not reach the OTP step"


@pytest.mark.regression
@pytest.mark.negative
@pytest.mark.parametrize("case", as_params(DATA["empty_fields"]))
def test_empty_fields_show_validation(driver, case):
    page = LoginPage(driver).open()
    page.submit_credentials(case["username"], case["password"])

    if case["expect_username_error"]:
        assert page.get_field_validation("username"), "No validation message for empty username"
    if case["expect_password_error"]:
        assert page.get_field_validation("password"), "No validation message for empty password"
    assert not page.is_otp_step_displayed(timeout=1)

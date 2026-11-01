"""Fund transfer tests. They move small amounts between dummy UAT accounts.

All tests share FROM_ACCOUNT, so exact-balance checks would race if run in parallel.
They are grouped with xdist_group; run parallel with `--dist loadgroup` to keep them on one worker.
"""
import re
from decimal import Decimal

import pytest

from pages.dashboard_page import DashboardPage
from pages.transfer_page import OWN, THIRD_PARTY
from utils.data_loader import as_params, load_test_data
from utils.money import to_decimal

DATA = load_test_data()
TRANSFER = DATA["transfer"]

pytestmark = [pytest.mark.transfer, pytest.mark.regression, pytest.mark.xdist_group("transfers")]


@pytest.fixture(scope="session")
def accounts(settings):
    missing = [name for name, value in (("FROM_ACCOUNT", settings.from_account),
                                        ("OWN_TO_ACCOUNT", settings.own_to_account),
                                        ("THIRD_PARTY_ACCOUNT", settings.third_party_account)) if not value]
    if missing:
        pytest.skip(f"Not set in .env: {', '.join(missing)}")
    return {OWN: settings.own_to_account, THIRD_PARTY: settings.third_party_account,
            "from": settings.from_account}


def _do_transfer(dashboard, case):
    return dashboard.go_to_transfer().transfer(
        transfer_type=case["type"], from_account=case["from_account"], to_account=case["to_account"],
        amount=to_decimal(case["amount"]), description=case.get("description", ""),
        recipient_bank=case.get("recipient_bank"),
    )


def _assert_rejected(outcome, expected: str | None):
    assert not outcome.success, f"Transfer should have been rejected but succeeded (ref {outcome.reference})"
    assert outcome.message, "Transfer was not completed, but no error message was shown"
    if expected:
        assert expected.lower() in outcome.message.lower(), \
            f"Expected '{expected}' in error, got '{outcome.message}'"


# ---------------------------------------------------------------- happy path
@pytest.mark.parametrize("case", as_params(TRANSFER["valid"]))
def test_valid_transfer_shows_success_and_reference(logged_in, accounts, case):
    outcome = _do_transfer(logged_in, case)

    assert outcome.success, f"Transfer failed: {outcome.message}"
    assert outcome.reference, "No transaction reference shown"
    assert re.match(DATA["limits"]["reference_pattern"], outcome.reference), \
        f"Unexpected reference format: {outcome.reference}"


@pytest.mark.parametrize("case", as_params(TRANSFER["valid"]))
def test_balance_decreases_by_exact_transfer_amount(logged_in, accounts, case):
    amount, fee = to_decimal(case["amount"]), to_decimal(case.get("fee") or "0")
    from_before = logged_in.get_balance(case["from_account"])
    to_before = logged_in.get_balance(case["to_account"]) if case["type"] == OWN else None

    outcome = _do_transfer(logged_in, case)
    assert outcome.success, f"Transfer failed: {outcome.message}"

    dashboard = DashboardPage(logged_in.driver).open()
    from_after = dashboard.wait_for_balance_change(case["from_account"], from_before)
    assert from_before - from_after == amount + fee, \
        f"Source balance changed by {from_before - from_after}, expected {amount + fee}"

    if to_before is not None:
        to_after = dashboard.get_balance(case["to_account"])
        assert to_after - to_before == amount, \
            f"Destination balance changed by {to_after - to_before}, expected {amount}"


def test_transfer_appears_in_history_with_amount_and_reference(logged_in, accounts):
    case = TRANSFER["valid"][0]
    amount = to_decimal(case["amount"])
    outcome = _do_transfer(logged_in, case)
    assert outcome.success, f"Transfer failed: {outcome.message}"

    history = DashboardPage(logged_in.driver).open().go_to_history()
    txn = history.find_by_reference(outcome.reference)

    assert txn is not None, f"Transaction {outcome.reference} not found in history"
    assert txn.reference == outcome.reference
    assert abs(txn.amount) == amount, f"History shows {txn.amount}, expected {amount}"


# ---------------------------------------------------------------- negative
@pytest.mark.negative
@pytest.mark.parametrize("case", as_params(TRANSFER["invalid_amounts"]))
def test_invalid_amount_is_rejected(logged_in, accounts, case):
    page = logged_in.go_to_transfer()

    outcome = page.transfer(transfer_type=case["type"], from_account=accounts["from"],
                            to_account=accounts[case["type"]], amount=case["amount"],
                            description=f"AUTO invalid amount {case['id']}")

    _assert_rejected(outcome, case["expected_error"])


@pytest.mark.negative
def test_amount_more_than_balance_is_rejected(logged_in, accounts):
    cfg = TRANSFER["over_balance"]
    balance = logged_in.get_balance(accounts["from"])
    amount: Decimal = balance + to_decimal(cfg["margin"])

    outcome = logged_in.go_to_transfer().transfer(
        transfer_type=cfg["type"], from_account=accounts["from"], to_account=accounts[cfg["type"]],
        amount=amount, description="AUTO over balance")

    _assert_rejected(outcome, cfg["expected_error"])


@pytest.mark.negative
@pytest.mark.parametrize("case", as_params(TRANSFER["invalid_recipients"]))
def test_invalid_recipient_is_rejected(logged_in, accounts, case):
    page = logged_in.go_to_transfer()

    outcome = page.transfer(transfer_type=THIRD_PARTY, from_account=accounts["from"],
                            to_account=case["to_account"], amount=TRANSFER["invalid_recipient_amount"],
                            description=f"AUTO invalid recipient {case['id']}")

    _assert_rejected(outcome, case["expected_error"])

# Bank UI Automation (UAT only)

UI test automation for the internet banking web app: Python, Selenium 4, pytest, Page Object Model.

> **This suite runs only against test/UAT.** It refuses to start if `BASE_URL` contains
> `prod`, `live` or `www.`, and checks every navigation (including redirects) the same way.

## Project layout

```
config/settings.py          .env loading (Settings dataclass; secrets hidden from repr)
pages/                      Page objects: BasePage + Login, Dashboard, Transfer, TransactionHistory
utils/
  safety.py                 production guard
  money.py                  Decimal helpers - parse_amount("RM 1,250.50") -> Decimal("1250.50")
  masking.py, logger.py     masking of account numbers (****1234) and secrets in logs/reports
  otp.py                    get_otp() - single place to swap the fixed OTP for an API/DB lookup
  driver_factory.py         Chrome / Edge / Firefox, headless option
  data_loader.py            YAML test data; ${VAR} values resolved from .env
test_data/test_data.yaml    parametrized test data (no real account numbers - those stay in .env)
tests/                      UI tests; tests/unit = offline helper tests
conftest.py                 fixtures, safety guard, failure screenshots
```

## Setup

Requires Python 3.10+ and Chrome/Edge/Firefox. Drivers are downloaded automatically by Selenium Manager.

```powershell
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # macOS/Linux: cp .env.example .env
```

Fill in `.env` with the UAT URL, dummy test user, fixed test OTP and dummy UAT account numbers.
`.env` is in `.gitignore` - never commit it. In CI, set the same names as environment variables instead.

Then update the placeholder locators in `pages/` (search for `update to match the real app`)
and the expected message texts in `test_data/test_data.yaml`.

## Running

```powershell
pytest tests/unit                 # offline helper tests - no browser, no UAT needed
pytest -m smoke                   # smoke tests
pytest                            # everything
pytest -m "regression and not session"   # full regression without the slow timeout test
pytest -m transfer                # fund transfer tests only
pytest -m negative                # negative tests only
pytest tests/test_login.py -k wrong_password   # a single test
```

Switch browser / headless per run without editing `.env`:

```powershell
$env:BROWSER="edge"; $env:HEADLESS="true"; pytest -m smoke     # PowerShell
BROWSER=firefox HEADLESS=true pytest -m smoke                  # bash
```

### Parallel (pytest-xdist)

```powershell
pytest -n 4 --dist loadgroup
```

`--dist loadgroup` is required: transfer tests share the same source account and are pinned to a
single worker via `xdist_group("transfers")`, otherwise exact-balance checks would race.
Each worker logs the test user in once. If the bank allows only one active session per user,
parallel workers will kick each other out - run serially or give each worker its own user.

## Demo against a local mock bank

`demo/` contains a small mock bank app (localhost only) that uses the placeholder locators,
so you can watch the framework work before the real locators are in place:

```powershell
.\demo\run_demo.ps1                  # smoke tests in a visible browser
.\demo\run_demo.ps1 -m transfer -v   # any pytest arguments
```

It sets its own settings for the run only and leaves `.env` untouched.

## Reports

- HTML report: `reports/report.html` (self-contained, generated on every run).
- On failure, a screenshot is embedded in the report and saved to `reports/screenshots/`.
  Before the screenshot, account numbers on the page are masked to the last 4 digits and the OTP is
  hidden (`MASK_SCREENSHOTS=true`).

## Banking rules built in

| Rule | Where |
|---|---|
| Refuse prod/live/www URLs | `utils/safety.py`, checked at startup and on every navigation |
| No hard-coded credentials / accounts | `.env` only; YAML refers to them as `${VAR}` |
| Masking (last 4 digits; passwords/OTP fully hidden) | `utils/masking.py`, log record factory in `utils/logger.py`, screenshot JS in `conftest.py`. Selenium's own DEBUG logs are silenced because they contain raw typed keys. |
| Decimal for money | `utils/money.py` (`to_decimal` rejects floats) |
| OTP behind one function | `utils/otp.py` - implement `OtpProvider` and call `set_otp_provider()` |
| Explicit waits only | `pages/base_page.py`; implicit wait set to 0, no `time.sleep` |
| Session timeout | `tests/test_security.py::test_user_logged_out_after_inactivity`, `SESSION_TIMEOUT_SECONDS` |

## Things to know about specific tests

- **Lockout test** locks `LOCKOUT_USERNAME` (a separate dummy user). It is skipped if not set.
  Ask the UAT admin to unlock that user before the next run.
- **Wrong password / wrong OTP tests** use `TEST_USERNAME`. That's 2 failed attempts per run,
  below the lockout threshold of 3; the next successful login resets the counter. Don't add more
  wrong-password cases for the main user without accounting for this.
- **Daily limit test** (`above_daily_limit`) needs a source balance above RM 10,000.01, otherwise the app
  may reject it as insufficient funds instead.
- **Over-balance test** uses an own-account transfer so it isn't blocked by the third-party daily limit first.
- **Session timeout test** stays idle for `SESSION_TIMEOUT_SECONDS + SESSION_TIMEOUT_GRACE_SECONDS`.
  Ask UAT to configure a short timeout (e.g. 120s), or skip it with `-m "not session"` or `SESSION_TIMEOUT_SECONDS=0`.
- **Transfer OTP/TAC and review screen** are handled automatically if they appear; each step runs at most once,
  so a transfer is never submitted twice.

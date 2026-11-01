# Runs the test suite against a local mock bank so you can watch the browser.
# Usage (from the project folder):
#   .\demo\run_demo.ps1                      # smoke tests, visible browser
#   .\demo\run_demo.ps1 -m transfer -v       # any pytest arguments
#   .\demo\run_demo.ps1 -Headless            # no browser window
# Your .env and terminal settings are left untouched.
param(
    [switch]$Headless,
    [Parameter(ValueFromRemainingArguments = $true)]$PytestArgs
)

$root = Split-Path $PSScriptRoot -Parent
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not $PytestArgs) { $PytestArgs = @("-m", "smoke", "-v") }

$demoEnv = @{
    BASE_URL = "http://127.0.0.1:8765"
    HEADLESS = $(if ($Headless) { "true" } else { "false" })
    TIMEOUT = "8"
    TEST_USERNAME = "tester"; TEST_PASSWORD = "Passw0rd!"; TEST_OTP = "123456"
    LOCKOUT_USERNAME = "locker"; LOCKOUT_PASSWORD = "L0ckPass!"
    FROM_ACCOUNT = "1111222233334444"; OWN_TO_ACCOUNT = "5555666677778888"
    THIRD_PARTY_ACCOUNT = "9999888877776666"
    SESSION_TIMEOUT_SECONDS = "8"; SESSION_TIMEOUT_GRACE_SECONDS = "10"
}

$saved = @{}
foreach ($key in $demoEnv.Keys) {
    $saved[$key] = [Environment]::GetEnvironmentVariable($key, "Process")
    [Environment]::SetEnvironmentVariable($key, $demoEnv[$key], "Process")
}

$server = Start-Process -FilePath $python -ArgumentList "`"$PSScriptRoot\mock_server.py`"", "8765" `
    -PassThru -WindowStyle Hidden
Push-Location $root
try {
    Write-Host "Mock bank running at http://127.0.0.1:8765 (user: tester / Passw0rd!, OTP 123456)"
    & $python -m pytest @PytestArgs
} finally {
    Pop-Location
    Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
    foreach ($key in $saved.Keys) {
        [Environment]::SetEnvironmentVariable($key, $saved[$key], "Process")
    }
}

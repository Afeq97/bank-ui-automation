"""Logging with automatic masking of secrets and account numbers."""
from __future__ import annotations

import logging

from utils.masking import mask_text

_installed = False


def install_log_masking() -> None:
    """Mask every log record at creation time, so all handlers (console, pytest
    captured logs, HTML report) only ever see masked text."""
    global _installed
    if _installed:
        return
    original_factory = logging.getLogRecordFactory()

    def masking_factory(*args, **kwargs):
        record = original_factory(*args, **kwargs)
        try:
            message = record.getMessage()
        except Exception:  # malformed record - leave it to logging to report
            return record
        masked = mask_text(message)
        if masked != message:
            record.msg, record.args = masked, None
        return record

    logging.setLogRecordFactory(masking_factory)

    # Selenium's DEBUG logs include raw WebDriver payloads, where send_keys text
    # is sent as single characters that no pattern can reliably mask. Keep them quiet.
    for noisy in ("selenium", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    _installed = True


def get_logger(name: str) -> logging.Logger:
    install_log_masking()
    return logging.getLogger(name)

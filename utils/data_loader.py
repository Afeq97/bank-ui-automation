"""Loads test data from YAML. "${VAR}" values are resolved from the environment / .env,
so account numbers and usernames live only in .env, never in code or the data file."""
from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest
import yaml

import config.settings  # noqa: F401  - ensures .env is loaded before resolving ${VAR}

DATA_FILE = Path(__file__).resolve().parent.parent / "test_data" / "test_data.yaml"
_ENV_REF = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _resolve(value: Any) -> Any:
    if isinstance(value, str):
        return _ENV_REF.sub(lambda m: os.getenv(m.group(1), "").strip(), value)
    if isinstance(value, list):
        return [_resolve(v) for v in value]
    if isinstance(value, dict):
        return {k: _resolve(v) for k, v in value.items()}
    return value


@lru_cache(maxsize=1)
def load_test_data(path: Path = DATA_FILE) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return _resolve(yaml.safe_load(fh))


def as_params(cases: list[dict[str, Any]]) -> list:
    """Turn data cases into pytest params. Each case's 'id' becomes the test id,
    so account numbers never appear in test names or the report."""
    return [pytest.param(case, id=case["id"]) for case in cases]

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

OPPORTUNITIES_FILE = DATA_DIR / "opportunities.json"
PRODUCT_PROFILE_FILE = DATA_DIR / "product_profile.json"


def make_json_safe(value: Any) -> Any:
    """
    Convert objects that JSON cannot serialize into safe values.
    Handles pandas/numpy timestamps, NaN, arrays, and other non-JSON objects.
    """

    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        # JSON does not safely support NaN/Infinity
        if isinstance(value, float):
            if value != value or value in [float("inf"), float("-inf")]:
                return None
        return value

    if isinstance(value, list):
        return [make_json_safe(item) for item in value]

    if isinstance(value, tuple):
        return [make_json_safe(item) for item in value]

    if isinstance(value, dict):
        return {
            str(key): make_json_safe(item)
            for key, item in value.items()
        }

    # Handles pandas Timestamp, datetime, numpy arrays, etc.
    return str(value)


def load_opportunities() -> list[dict]:
    """Load saved opportunities safely."""

    if not OPPORTUNITIES_FILE.exists():
        return []

    try:
        with open(OPPORTUNITIES_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            return data

        return []

    except json.JSONDecodeError:
        # If the file is corrupted, reset it instead of crashing the app.
        save_opportunities([])
        return []


def save_opportunities(opportunities: list[dict]) -> None:
    """Save opportunities safely as valid JSON."""

    safe_opportunities = make_json_safe(opportunities)

    with open(OPPORTUNITIES_FILE, "w", encoding="utf-8") as file:
        json.dump(
            safe_opportunities,
            file,
            indent=2,
            ensure_ascii=False,
        )


def load_product_profile() -> dict:
    """Load saved product profile safely."""

    if not PRODUCT_PROFILE_FILE.exists():
        return {}

    try:
        with open(PRODUCT_PROFILE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, dict):
            return data

        return {}

    except json.JSONDecodeError:
        save_product_profile({})
        return {}


def save_product_profile(product_profile: dict) -> None:
    """Save product profile safely as valid JSON."""

    safe_profile = make_json_safe(product_profile)

    with open(PRODUCT_PROFILE_FILE, "w", encoding="utf-8") as file:
        json.dump(
            safe_profile,
            file,
            indent=2,
            ensure_ascii=False,
        )
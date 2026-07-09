import json
from pathlib import Path
from typing import Any


DATA_DIRECTORY = Path("data")

OPPORTUNITIES_PATH = (
    DATA_DIRECTORY / "opportunities.json"
)

PRODUCT_PROFILE_PATH = (
    DATA_DIRECTORY / "product_profile.json"
)


def ensure_data_directory() -> None:
    """Create the data directory when needed."""

    DATA_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )


def save_opportunities(
    opportunities: list[dict[str, Any]],
) -> None:
    """Save analyzed growth opportunities."""

    ensure_data_directory()

    with OPPORTUNITIES_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            opportunities,
            file,
            indent=2,
            ensure_ascii=False,
        )


def load_opportunities() -> list[dict[str, Any]]:
    """Load saved growth opportunities."""

    if not OPPORTUNITIES_PATH.exists():
        return []

    with OPPORTUNITIES_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def save_product_profile(
    product_profile: dict[str, Any],
) -> None:
    """Save the active product profile."""

    ensure_data_directory()

    with PRODUCT_PROFILE_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            product_profile,
            file,
            indent=2,
            ensure_ascii=False,
        )


def load_product_profile() -> dict[str, Any]:
    """Load the saved product profile."""

    if not PRODUCT_PROFILE_PATH.exists():
        return {}

    with PRODUCT_PROFILE_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)
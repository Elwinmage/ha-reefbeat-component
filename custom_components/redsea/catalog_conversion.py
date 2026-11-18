# Generated from reeftech-catalog/client/catalog_conversion.py by scripts/sync_client.py: do not edit this copy.
"""Turn what a water test shows into a value, with the table of its manufacturer.

A titration test gives an amount of reagent (mL or drops). The catalog holds the
points `amount -> value` of the manufacturer; between two points the value is
interpolated linearly. Outside the table nothing is extrapolated: a dose must
never rest on a guess.
"""

from __future__ import annotations

from typing import Any


def table_bounds(table: dict[str, Any]) -> tuple[float, float]:
    """Smallest and largest amount of reagent the table covers."""
    amounts = [point["amount"] for point in table["points"]]
    return min(amounts), max(amounts)


def reading_range(test: dict[str, Any]) -> tuple[float, float] | None:
    """Smallest and largest value a test can read, or None when not stated."""
    if test["method"] == "titration":
        values = [point["value"] for point in test["table"]["points"]]
        return min(values), max(values)
    band = test.get("range")
    return (band["min"], band["max"]) if band else None


def to_value(table: dict[str, Any], amount: float) -> float | None:
    """The value for an amount of reagent, None when outside the table."""
    points = sorted(table["points"], key=lambda point: point["amount"])
    if not points[0]["amount"] <= amount <= points[-1]["amount"]:
        return None
    index = next(i for i, point in enumerate(points) if i and amount <= point["amount"])
    low, high = points[index - 1], points[index]
    share = (amount - low["amount"]) / (high["amount"] - low["amount"])
    return low["value"] + share * (high["value"] - low["value"])


def convert(test: dict[str, Any], reading: float) -> float | None:
    """The value of a reading: the reading itself for a direct test, the
    interpolated value for a titration (None when outside the table)."""
    if test["method"] == "direct":
        return reading
    return to_value(test["table"], reading)

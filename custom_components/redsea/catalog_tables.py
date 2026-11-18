"""Parameters and water tests of the ReefTech catalog, as the regulation reads them.

The dose regulation (dose_regulation.py) is pure code that needs, at any time,
the parameters it can regulate (target, tolerance, largest daily correction,
step) and the water tests a result can be read with. Both come from the
catalog (sections ``parameters`` and ``water_tests`` of reeftech-catalog), which
the catalog updaters keep up to date; this module holds the current copy, built
from the built-in snapshot at import and replaced by ``install`` each time a
catalog is loaded or updated. No Home Assistant import.

Units. The catalog gives the trace elements in ppb; the regulation (settings,
history, entities) has always counted them in ppm (mg/L). The conversion is made
here, once, when an entry is read: nothing stored has to change.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from .catalog_conversion import convert, table_bounds
from .catalog_pack import Layer, build_view

_LOGGER = logging.getLogger(__name__)

#: The test result is typed in by hand
MANUAL: Final[str] = "manual"

#: Unit of the catalog -> (unit the regulation counts in, factor)
_UNITS: Final[dict[str, tuple[str, float]]] = {
    "dkh": ("dKH", 1.0),
    "ppm": ("ppm", 1.0),
    "mg_l": ("ppm", 1.0),
    "ppb": ("ppm", 0.001),
    "ppt": ("ppt", 1.0),
}

#: Usual order of the parameters (the others follow, alphabetically)
_ORDER: Final[tuple[str, ...]] = (
    "kh",
    "ca",
    "mg",
    "k",
    "sr",
    "no3",
    "po4",
    "i",
    "fe",
    "salinity",
)

#: Ids of the kits of the first versions (stored in the settings of the heads)
#: and the catalog test that replaces each
LEGACY_TEST_IDS: Final[dict[str, str]] = {
    "redsea_kh": "red-sea-foundation-pro-kh",
    "redsea_ca": "red-sea-foundation-pro-ca",
    "redsea_mg": "red-sea-foundation-pro-mg",
    "salifert_kh": "salifert-kh-profi",
    "salifert_ca": "salifert-ca-profi",
    "salifert_mg": "salifert-mg-profi",
    "colombo_kh": "colombo-marine-kh",
}

_PARAMETERS_BUILTIN = Path(__file__).parent / "catalog_builtin_parameters"
_WATER_TESTS_BUILTIN = Path(__file__).parent / "catalog_builtin_water_tests"


def _round(value: float) -> float:
    return round(value, 9)


@dataclass(frozen=True, slots=True)
class Parameter:
    """A water parameter a head can regulate, in the unit of the regulation.

    ``max_rate`` is the largest correction per day (in ``unit``) the
    regulation asks for, whatever the gap to the target.
    """

    unit: str
    target: float
    tolerance: float
    max_rate: float
    step: float


def parameter_from_entry(entry: Mapping[str, Any]) -> Parameter | None:
    """The regulation data of a catalog parameter, None when it has none.

    The target is the optimal value of the reference band.
    """
    regulation = entry.get("regulation")
    optimal = (entry.get("range") or {}).get("optimal")
    unit = _UNITS.get(str(entry.get("unit")))
    if not regulation or optimal is None or unit is None:
        return None
    name, factor = unit
    return Parameter(
        name,
        _round(optimal * factor),
        _round(regulation["tolerance"] * factor),
        _round(regulation["max_rate"] * factor),
        _round(regulation["step"] * factor),
    )


@dataclass(frozen=True, slots=True)
class WaterTest:
    """A water test of the catalog (one parameter).

    A titration test turns the amount of reagent used (``amount_unit``) into
    a value with the table of its manufacturer; between two points the value is
    interpolated linearly and nothing is extrapolated. ``verified`` is False
    when the table was not checked against the manual: the test works, the
    cards warn.
    """

    id: str
    brand: str
    name: str
    parameter: str
    method: str
    verified: bool
    amount_unit: str
    factor: float
    test: Mapping[str, Any]
    image: str | None = None
    thumb: str | None = None

    @property
    def label(self) -> str:
        """Brand and product, as the select shows them."""
        if self.name.lower().startswith(self.brand.lower()):
            return self.name
        return f"{self.brand} {self.name}"

    def amounts(self) -> tuple[float, float]:
        """Smallest and largest amount of reagent the table covers."""
        return table_bounds(self.test["table"])

    def value(self, reading: float) -> float:
        """Value of a reading, in the unit of the regulation.

        @raise ValueError: a reading the table does not cover
        """
        if reading < 0:
            raise ValueError("the reagent amount cannot be negative")
        # convert() takes a dict (shared catalog client): a shallow copy
        value = convert(dict(self.test), reading)
        if value is None:
            low, high = self.amounts()
            raise ValueError(
                f"{self.label}: the table covers {low} to {high} {self.amount_unit}"
            )
        return value * self.factor


def water_test_from_entry(test_id: str, entry: Mapping[str, Any]) -> WaterTest | None:
    """A catalog water test, None when it is not a titration the regulation knows."""
    tests = entry.get("tests") or []
    if not tests:
        return None
    test = tests[0]
    unit = _UNITS.get(str(test.get("unit")))
    if unit is None or test.get("method") != "titration" or "table" not in test:
        return None
    return WaterTest(
        id=test_id,
        brand=str(entry.get("brand", "")),
        name=str(entry.get("name", test_id)),
        parameter=str(test["parameter"]),
        method="titration",
        verified=bool(entry.get("verified", False)),
        amount_unit=str(test["table"]["amount_unit"]),
        factor=unit[1],
        test=test,
        image=entry.get("image"),
        thumb=entry.get("thumb"),
    )


def _sorted_ids(ids: list[str]) -> list[str]:
    def key(identifier: str) -> tuple[int, str]:
        return (
            _ORDER.index(identifier) if identifier in _ORDER else len(_ORDER),
            identifier,
        )

    return sorted(ids, key=key)


def _parameters_of(view: Mapping[str, Any]) -> dict[str, Parameter]:
    found: dict[str, Parameter] = {}
    items = view.get("items") or {}
    for identifier in _sorted_ids(list(items)):
        parameter = parameter_from_entry(items[identifier])
        if parameter is not None:
            found[identifier] = parameter
    return found


def _tests_of(view: Mapping[str, Any]) -> dict[str, WaterTest]:
    found: dict[str, WaterTest] = {}
    items = view.get("items") or {}
    for identifier in sorted(items, key=lambda i: (items[i].get("brand", ""), i)):
        test = water_test_from_entry(identifier, items[identifier])
        if test is not None:
            found[identifier] = test
    return found


def _builtin(path: Path, section: str) -> dict[str, Any]:
    return build_view([Layer("builtin", path, "/", "builtin")], section)


class _Live(Mapping[str, Any]):
    """Read-only view of a table that ``install`` replaces."""

    def __init__(self, holder: _State, name: str) -> None:
        self._holder = holder
        self._name = name

    def _table(self) -> dict[str, Any]:
        return getattr(self._holder, self._name)

    def __getitem__(self, key: str) -> Any:
        return self._table()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._table())

    def __len__(self) -> int:
        return len(self._table())


class _State:
    """The tables in use."""

    def __init__(self) -> None:
        self.parameters: dict[str, Parameter] = {}
        self.tests: dict[str, WaterTest] = {}
        self.reset()

    def reset(self) -> None:
        """Back to the built-in snapshots."""
        self.parameters = _parameters_of(_builtin(_PARAMETERS_BUILTIN, "parameters"))
        self.tests = _tests_of(_builtin(_WATER_TESTS_BUILTIN, "water_tests"))


_STATE = _State()

#: Parameters a head can regulate, by id (those with `regulation`)
PARAMETERS: Final[Mapping[str, Parameter]] = _Live(_STATE, "parameters")
#: Titration tests a result can be read with, by catalog id
WATER_TESTS: Final[Mapping[str, WaterTest]] = _Live(_STATE, "tests")


def install(section: str, view: Mapping[str, Any]) -> None:
    """Use a loaded catalog view (``parameters`` or ``water_tests``).

    A view that leaves nothing usable (empty or damaged) keeps the tables in
    use: the regulation must not lose its parameters to a bad release.
    """
    if section == "parameters":
        found = _parameters_of(view)
        if found:
            _STATE.parameters = found
        else:
            _LOGGER.debug("Parameters catalog without regulation data: kept")
    elif section == "water_tests":
        _STATE.tests = _tests_of(view)


def reset() -> None:
    """Forget the loaded catalogs (the integration stops)."""
    _STATE.reset()


def parameter_options() -> list[str]:
    """Parameters of the parameter select, in their usual order."""
    return list(PARAMETERS)


def assisted_parameters() -> list[str]:
    """Parameters offered in assisted mode (the salinity is the brine's)."""
    return [p for p in PARAMETERS if p != "salinity"]


def tests_for(parameter: str) -> list[str]:
    """Ids of the titration tests of a parameter."""
    return [i for i, test in WATER_TESTS.items() if test.parameter == parameter]


def test_options(parameter: str) -> list[str]:
    """Options of the test select for a parameter: typed in first."""
    return [MANUAL, *tests_for(parameter)]


def test_value(test_id: str, reading: float) -> float | None:
    """Value of a reading of a test, None for a typed in result.

    @raise ValueError: unknown test or a reading its table does not cover
    """
    if test_id == MANUAL:
        return None
    test = WATER_TESTS.get(test_id)
    if test is None:
        raise ValueError(f"unknown water test {test_id!r}")
    return test.value(reading)


def decimals(step: float) -> int:
    """Digits of a step (0.01 -> 2)."""
    return max(0, -math.floor(math.log10(step)))

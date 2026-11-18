"""Tests of catalog_tables.py: the parameters and water tests of the catalog."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from custom_components.redsea import catalog_sections as S
from custom_components.redsea import catalog_tables as T


@pytest.fixture(autouse=True)
def _builtin_tables():
    T.reset()
    yield
    T.reset()


def _parameter(unit: str = "dkh", optimal: float = 8.0) -> dict[str, Any]:
    return {
        "unit": unit,
        "range": {"optimal": optimal},
        "regulation": {"tolerance": 0.2, "max_rate": 0.5, "step": 0.01},
    }


def _test(unit: str = "dkh", **extra: Any) -> dict[str, Any]:
    return {
        "brand": "Acme",
        "name": "Acme KH",
        "verified": True,
        "tests": [
            {
                "parameter": "kh",
                "unit": unit,
                "method": "titration",
                "table": {
                    "amount_unit": "ml",
                    "points": [
                        {"amount": 0, "value": 0},
                        {"amount": 1, "value": 16},
                    ],
                },
            }
        ],
        **extra,
    }


def test_builtin_snapshots() -> None:
    assert list(T.PARAMETERS)[:3] == ["kh", "ca", "mg"]
    assert len(T.PARAMETERS) == len(T.parameter_options()) == 9
    kh = T.PARAMETERS["kh"]
    assert (kh.unit, kh.target, kh.tolerance, kh.max_rate, kh.step) == (
        "dKH",
        8.0,
        0.2,
        0.5,
        0.01,
    )
    # sr has no regulation data; the salinity is not assisted
    assert "sr" not in T.PARAMETERS
    assert "salinity" in T.PARAMETERS and "salinity" not in T.assisted_parameters()
    assert T.PARAMETERS["mg"].target == 1340.0
    assert T.decimals(0.01) == 2 and T.decimals(1) == 0 and T.decimals(0.001) == 3


def test_trace_elements_are_converted_to_ppm() -> None:
    iodine = T.PARAMETERS["i"]
    assert iodine.unit == "ppm" and iodine.step == 0.001
    assert T.PARAMETERS["fe"].target == 0.005


def test_parameter_from_entry() -> None:
    assert T.parameter_from_entry(_parameter()) == T.Parameter(
        "dKH", 8.0, 0.2, 0.5, 0.01
    )
    assert T.parameter_from_entry({"unit": "dkh"}) is None
    assert T.parameter_from_entry({**_parameter(), "unit": "furlong"}) is None
    no_optimal = _parameter()
    no_optimal["range"] = {}
    assert T.parameter_from_entry(no_optimal) is None
    assert T.parameter_from_entry({**_parameter(), "range": None}) is None


def test_water_test_from_entry() -> None:
    test = T.water_test_from_entry("acme-kh", _test())
    assert test is not None
    assert (test.brand, test.label, test.parameter) == ("Acme", "Acme KH", "kh")
    assert test.amounts() == (0, 1) and test.verified
    assert test.value(0.5) == 8.0
    other = T.water_test_from_entry(
        "x", _test() | {"name": "KH Pro", "verified": False}
    )
    assert other is not None and other.label == "Acme KH Pro" and not other.verified
    assert T.water_test_from_entry("x", {}) is None
    assert T.water_test_from_entry("x", _test(unit="furlong")) is None
    colour = _test()
    colour["tests"][0]["method"] = "colorimetric"
    assert T.water_test_from_entry("x", colour) is None
    no_table = _test()
    del no_table["tests"][0]["table"]
    assert T.water_test_from_entry("x", no_table) is None


def test_water_test_values() -> None:
    test = T.WATER_TESTS["red-sea-foundation-pro-kh"]
    assert test.value(0.4) == pytest.approx(5.6)
    with pytest.raises(ValueError, match="negative"):
        test.value(-0.1)
    with pytest.raises(ValueError, match="covers 0 to 1 ml"):
        test.value(1.5)
    # Trace elements: from ppb to ppm
    ppb = T.water_test_from_entry("i", _test(unit="ppb"))
    assert ppb is not None and ppb.value(1) == pytest.approx(0.016)


def test_install_parameters() -> None:
    T.install(
        "parameters", {"items": {"zz": _parameter(), "kh": _parameter(optimal=7)}}
    )
    assert list(T.PARAMETERS) == ["kh", "zz"]
    assert T.PARAMETERS["kh"].target == 7.0
    # A view without usable data keeps the tables in use
    T.install("parameters", {"items": {}})
    assert list(T.PARAMETERS) == ["kh", "zz"]
    T.install("parameters", {})
    assert len(T.PARAMETERS) == 2
    T.install("other", {"items": {}})
    T.reset()
    assert len(T.PARAMETERS) == 9


def test_install_water_tests() -> None:
    T.install("water_tests", {"items": {"b": _test(), "a": _test() | {"brand": "Abc"}}})
    assert T.tests_for("kh") == ["a", "b"]
    assert T.tests_for("ca") == []
    assert T.test_options("kh") == ["manual", "a", "b"]
    assert T.test_value("manual", 3) is None
    assert T.test_value("b", 1) == 16
    with pytest.raises(ValueError, match="unknown water test"):
        T.test_value("zz", 1)
    # Tests are replaced as a whole, even by none
    T.install("water_tests", {"items": {}})
    assert len(T.WATER_TESTS) == 0
    with pytest.raises(KeyError):
        T.WATER_TESTS["a"]


def test_legacy_ids_exist_in_the_catalog() -> None:
    for legacy, current in T.LEGACY_TEST_IDS.items():
        assert current in T.WATER_TESTS, legacy


def test_sections() -> None:
    assert [spec.section for spec in S.CATALOGS] == [
        "supplements",
        "water_tests",
        "parameters",
    ]
    assert S.WATER_TESTS_CATALOG.by_section and S.PARAMETERS_CATALOG.by_section


def test_install_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    updater = MagicMock()
    updater.view = {"items": {"kh": _parameter(optimal=7.5)}}
    monkeypatch.setattr(S, "get_updater", lambda hass, domain, section: updater)
    S._install(MagicMock(), S.PARAMETERS_CATALOG)
    assert T.PARAMETERS["kh"].target == 7.5
    # No updater yet: nothing changes
    monkeypatch.setattr(S, "get_updater", lambda hass, domain, section: None)
    S._install(MagicMock(), S.PARAMETERS_CATALOG)
    assert T.PARAMETERS["kh"].target == 7.5

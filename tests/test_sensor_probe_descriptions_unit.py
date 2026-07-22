"""Unit tests for the two internal helpers in sensor.py that were not
reached by the platform-level setup tests: ``_epoch_to_iso`` (a small
timestamp helper) and ``_build_probe_descriptions`` (which fans out sensor
descriptions per probe type).

Each probe type has its own branch in ``_build_probe_descriptions``. The
platform-level test only exercises ``ph`` and ``temperature``; here we
call the helper directly with the four other types (``orp``, ``ec``,
``ato``, ``leak``) plus an unknown fallback, and pipe through the value_fn
lambdas that internally call ``_epoch_to_iso`` so both helpers reach
100% coverage.
"""

from __future__ import annotations

import datetime as _datetime
from typing import Any


from custom_components.redsea.sensor import (
    _build_probe_descriptions,
    _epoch_to_iso,
)


# ---------------------------------------------------------------------------
# _epoch_to_iso
# ---------------------------------------------------------------------------


def test_epoch_to_iso_none() -> None:
    """`None` short-circuits before any parsing."""
    assert _epoch_to_iso(None) is None


def test_epoch_to_iso_non_numeric_string() -> None:
    """A string that isn't parseable as float returns None (not raise)."""
    assert _epoch_to_iso("not-a-number") is None


def test_epoch_to_iso_zero_or_negative() -> None:
    """Zero and negatives are treated as "unset" by the firmware."""
    assert _epoch_to_iso(0) is None
    assert _epoch_to_iso(-1) is None


def test_epoch_to_iso_valid_epoch_returns_utc_isoformat() -> None:
    """Positive epoch → tz-aware UTC ISO 8601 string."""
    # 2024-01-01T00:00:00Z = 1704067200
    got = _epoch_to_iso(1704067200)
    assert got == _datetime.datetime(2024, 1, 1, tzinfo=_datetime.UTC).isoformat()


def test_epoch_to_iso_accepts_string_epoch() -> None:
    """Some payloads report the epoch as a string — must still work."""
    got = _epoch_to_iso("1704067200")
    assert got is not None
    assert got.startswith("2024-01-01T")


# ---------------------------------------------------------------------------
# _build_probe_descriptions — per-type branches
# ---------------------------------------------------------------------------


def _keys(descs: list[Any]) -> set[str]:
    return {d.key for d in descs}


def test_build_probe_descriptions_missing_type_returns_empty() -> None:
    """No ``type`` → the helper bails out early (defensive guard)."""
    descs = _build_probe_descriptions({"uid": "0xDEAD", "name": "orphan"})
    assert descs == []


def test_build_probe_descriptions_missing_uid_returns_empty() -> None:
    """No ``uid`` → the helper bails out early too."""
    descs = _build_probe_descriptions({"type": "ph", "name": "orphan"})
    assert descs == []


def test_build_probe_descriptions_orp() -> None:
    """ORP probes report in mV with 0-decimal precision."""
    descs = _build_probe_descriptions(
        {"uid": "0x0ORP1", "type": "orp", "name": "Sump ORP"}
    )
    keys = _keys(descs)
    assert any(k.endswith("_value") for k in keys)
    # Main value entity must carry the ORP unit and translation key.
    main = next(d for d in descs if d.key == "probe_0x0orp1_value")
    assert main.native_unit_of_measurement == "mV"
    assert main.suggested_display_precision == 0
    assert main.translation_key == "probe_orp_value"


def test_build_probe_descriptions_ec() -> None:
    """EC probes expose ec/ppt/sg raw derivatives + a measurement_unit entity."""
    descs = _build_probe_descriptions(
        {
            "uid": "0x0EC01",
            "type": "ec",
            "name": "EC1",
            "measurement_unit": "ppt",
        }
    )
    keys = _keys(descs)
    # Main value + the three raw derivatives all present.
    assert "probe_0x0ec01_value" in keys
    assert "probe_0x0ec01_ec" in keys
    assert "probe_0x0ec01_ppt" in keys
    assert "probe_0x0ec01_sg" in keys
    # Main value should carry the display unit read from the payload.
    main = next(d for d in descs if d.key == "probe_0x0ec01_value")
    assert main.native_unit_of_measurement == "ppt"


def test_build_probe_descriptions_ato() -> None:
    """ATO probes have no canonical unit and 1-decimal display precision."""
    descs = _build_probe_descriptions({"uid": "0x0AT01", "type": "ato", "name": "ATO1"})
    main = next(d for d in descs if d.key == "probe_0x0at01_value")
    assert main.native_unit_of_measurement is None
    assert main.suggested_display_precision == 1
    assert main.translation_key == "probe_ato_value"


def test_build_probe_descriptions_leak() -> None:
    """Leak probes: unit-less, 0-decimal precision, dedicated translation."""
    descs = _build_probe_descriptions(
        {"uid": "0x0LEAK", "type": "leak", "name": "Leak Sensor"}
    )
    main = next(d for d in descs if d.key == "probe_0x0leak_value")
    assert main.native_unit_of_measurement is None
    assert main.suggested_display_precision == 0
    assert main.translation_key == "probe_leak_value"


def test_build_probe_descriptions_unknown_type_falls_back() -> None:
    """An unknown probe type falls into the generic ``probe_value`` branch."""
    descs = _build_probe_descriptions(
        {"uid": "0x0UNK1", "type": "mystery", "name": "?"}
    )
    main = next(d for d in descs if d.key == "probe_0x0unk1_value")
    assert main.native_unit_of_measurement is None
    assert main.suggested_display_precision == 2
    assert main.translation_key == "probe_value"


# ---------------------------------------------------------------------------
# value_fn plumbing — proves the _epoch_to_iso callback fires end-to-end
# ---------------------------------------------------------------------------


class _StaticDevice:
    """Tiny stand-in for a coordinator: `get_data` returns a fixed value."""

    def __init__(self, value: Any) -> None:
        self._value = value

    def get_data(self, _path: str, is_None_possible: bool = False) -> Any:  # noqa: N803
        return self._value


def test_last_installation_value_fn_converts_epoch() -> None:
    """The ``last_installation`` sensor pipes get_data through _epoch_to_iso.

    We simulate a probe that reports its install date as an epoch, then
    invoke the sensor's value_fn to make sure the datetime helper actually
    fires (this covers _epoch_to_iso end-to-end from the description path).
    """
    descs = _build_probe_descriptions({"uid": "0xTIME1", "type": "ph", "name": "T"})
    install_desc = next(d for d in descs if d.key == "probe_0xtime1_last_installation")
    device = _StaticDevice(1704067200)  # 2024-01-01T00:00:00Z
    assert install_desc.value_fn is not None
    got = install_desc.value_fn(device)  # type: ignore[misc]
    assert isinstance(got, str)
    assert got.startswith("2024-01-01T")


def test_last_adjustment_value_fn_handles_missing_field() -> None:
    """When the epoch field is absent, value_fn cleanly returns None."""
    descs = _build_probe_descriptions(
        {"uid": "0xTIME2", "type": "ec", "name": "T", "measurement_unit": "ppt"}
    )
    adj_desc = next(d for d in descs if d.key == "probe_0xtime2_last_adjustment")
    device = _StaticDevice(None)
    assert adj_desc.value_fn is not None
    assert adj_desc.value_fn(device) is None  # type: ignore[misc]

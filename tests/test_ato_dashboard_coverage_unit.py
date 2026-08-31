"""Every RSATO+ entity description is checked against the captured payload.

The ATO descriptions are pure JSONPath lookups into `/dashboard`. A typo in a
path, or a firmware field that moves, is invisible at import time and only
shows up as an `unknown` entity at runtime — so each `value_fn` is executed
here against `tests/fixtures/devices/ATO/dashboard/data`, the real payload of
a ReefATO+.

The reverse direction is checked too: any `/dashboard` field that no
description reads is reported, so a firmware field cannot be silently ignored.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any, cast

import pytest
from homeassistant.components.sensor import SensorDeviceClass
from jsonpath_ng.ext import parse

from custom_components.redsea.binary_sensor import ATO_SENSORS as ATO_BINARY_SENSORS
from custom_components.redsea.sensor import (
    ATO_SENSORS,
    ReefBeatSensorEntity,
    _epoch_to_datetime,
)

FIXTURE = Path(__file__).parent / "fixtures" / "devices" / "ATO" / "dashboard" / "data"

# Fields deliberately not exposed as entities.
_NOT_EXPOSED: frozenset[str] = frozenset(
    {
        # Surfaced by dedicated code paths rather than a description:
        # `/mode` for the operating mode, a computed binary_sensor for the
        # water level, and a number entity for the reservoir volume.
        "mode",
        "water_level",
        "volume_left",
    }
)


class _FakeATO:
    """Minimal coordinator exposing `get_data()` over the captured payload."""

    def __init__(self, dashboard: dict[str, Any]) -> None:
        self.data: dict[str, Any] = {
            "sources": [{"name": "/dashboard", "type": "data", "data": dashboard}]
        }

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:
        matches = parse(name).find(self.data)
        if not matches:
            if is_None_possible:
                return None
            raise KeyError(name)
        return matches[0].value


@pytest.fixture(name="dashboard")
def _dashboard() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(name="device")
def _device(dashboard: dict[str, Any]) -> _FakeATO:
    return _FakeATO(dashboard)


def _paths(payload: dict[str, Any]) -> set[str]:
    """Flatten the payload into `key` / `parent.child` dotted paths."""
    out: set[str] = set()
    for key, value in payload.items():
        if isinstance(value, dict):
            out.update(f"{key}.{sub}" for sub in value)
        else:
            out.add(key)
    return out


# -----------------------------------------------------------------------------
# Every description resolves
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "description", ATO_SENSORS, ids=lambda d: getattr(d, "key", "?")
)
def test_ato_sensor_paths_resolve(description: Any, device: _FakeATO) -> None:
    """Each sensor `value_fn` runs without raising on the real payload."""
    description.value_fn(device)


@pytest.mark.parametrize(
    "description", ATO_BINARY_SENSORS, ids=lambda d: getattr(d, "key", "?")
)
def test_ato_binary_sensor_paths_resolve(description: Any, device: _FakeATO) -> None:
    """Each binary sensor `value_fn` runs without raising on the real payload."""
    description.value_fn(device)


def test_ato_sensor_keys_are_unique() -> None:
    """Two descriptions sharing a key would silently shadow one another."""
    keys = [d.key for d in ATO_SENSORS]
    assert len(keys) == len(set(keys))

    binary_keys = [d.key for d in ATO_BINARY_SENSORS]
    assert len(binary_keys) == len(set(binary_keys))


# -----------------------------------------------------------------------------
# Coverage of the payload
# -----------------------------------------------------------------------------


def test_every_dashboard_field_is_exposed(dashboard: dict[str, Any]) -> None:
    """No `/dashboard` field is left without an entity."""
    read = "".join(
        str(getattr(d, "value_fn", "")) for d in (*ATO_SENSORS, *ATO_BINARY_SENSORS)
    )
    # `value_fn` is a lambda, so its source is not introspectable; compare
    # against the module source instead, which is what actually holds the
    # JSONPath strings.
    #
    # `const` and `switch` are scanned too: a writable setting is a switch
    # reading a named constant, not a sensor with an inline path, and
    # `leak_sensor.buzzer_enabled` is exposed exactly that way.
    import custom_components.redsea.binary_sensor as binary_sensor_platform
    import custom_components.redsea.const as const_module
    import custom_components.redsea.sensor as sensor_platform
    import custom_components.redsea.switch as switch_platform

    source = (
        Path(sensor_platform.__file__).read_text(encoding="utf-8")
        + Path(binary_sensor_platform.__file__).read_text(encoding="utf-8")
        + Path(switch_platform.__file__).read_text(encoding="utf-8")
        + Path(const_module.__file__).read_text(encoding="utf-8")
        + read
    )

    missing = {
        path
        for path in _paths(dashboard) - _NOT_EXPOSED
        # The longer paths are split across two string literals to fit the line
        # length, so match on the leaf rather than the full dotted path.
        if f".{path}" not in source and f'.{path.split(".")[-1]}"' not in source
    }
    assert not missing, f"/dashboard fields with no entity: {sorted(missing)}"


# -----------------------------------------------------------------------------
# Values actually observed on the wire
# -----------------------------------------------------------------------------


def test_leak_status_is_dry_on_a_healthy_probe(device: _FakeATO) -> None:
    """`dry` is the healthy leak state, not an absent-probe marker.

    Guards the `_ATO_LEAK_STATUS_OPTIONS` regression: the app's `$Keys.aquarium`
    field holds `aquarium_water_leak`, so the short names never appear here.
    """
    status = device.get_data(
        "$.sources[?(@.name=='/dashboard')].data.leak_sensor.status"
    )
    assert status == "dry"

    from custom_components.redsea.sensor import _ATO_LEAK_STATUS_OPTIONS

    assert status in _ATO_LEAK_STATUS_OPTIONS
    assert "aquarium_water_leak" in _ATO_LEAK_STATUS_OPTIONS
    assert "rodi_water_leak" in _ATO_LEAK_STATUS_OPTIONS


def test_last_pump_on_cause_is_covered_by_the_options(device: _FakeATO) -> None:
    """The firmware reports level-sensor causes the Red Sea app never models."""
    cause = device.get_data(
        "$.sources[?(@.name=='/dashboard')].data.last_pump_on_cause"
    )
    assert cause == "ec_sensor_s1"

    from custom_components.redsea.sensor import _ATO_PUMP_CAUSE_OPTIONS

    assert cause in _ATO_PUMP_CAUSE_OPTIONS


def test_timestamps_are_tz_aware_datetimes(device: _FakeATO) -> None:
    """`last_fill_date` is an epoch in the payload, a tz-aware datetime here.

    Regression guard: `SensorDeviceClass.TIMESTAMP` reads `value.tzinfo`, so an
    ISO-8601 *string* aborts `_async_add_entity` and then raises again on every
    coordinator refresh. An earlier revision of this test asserted the string
    form and therefore passed while the entity was broken in Home Assistant.
    """
    description = next(d for d in ATO_SENSORS if d.key == "last_fill_date")
    value = description.value_fn(cast(Any, device))
    assert isinstance(value, datetime.datetime)
    assert value.tzinfo is not None
    assert value.year == 2025


def test_every_timestamp_sensor_returns_a_tz_aware_datetime(
    device: _FakeATO,
) -> None:
    """No TIMESTAMP description may return a string, on any platform.

    Covers the ATO descriptions directly; the per-probe and per-port ones are
    built dynamically, so `_epoch_to_datetime` itself is checked as the single
    conversion point they all share.
    """
    for description in ATO_SENSORS:
        if description.device_class is not SensorDeviceClass.TIMESTAMP:
            continue
        value = description.value_fn(cast(Any, device))
        assert value is None or (
            isinstance(value, datetime.datetime) and value.tzinfo is not None
        ), f"{description.key} returned {value!r}"

    converted = _epoch_to_datetime(1751219015)
    assert isinstance(converted, datetime.datetime)
    assert converted.tzinfo is not None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        ("", None),
        (0, None),
        (-1, None),
        ("not-a-number", None),
        ("1751219015", datetime.datetime(2025, 6, 29, 17, 43, 35, tzinfo=datetime.UTC)),
        (1751219015, datetime.datetime(2025, 6, 29, 17, 43, 35, tzinfo=datetime.UTC)),
    ],
)
def test_epoch_conversion_edge_cases(raw: Any, expected: Any) -> None:
    """Unusable epochs yield None rather than an exception or a bogus date."""
    assert _epoch_to_datetime(raw) == expected


def test_restored_timestamp_state_comes_back_as_a_datetime() -> None:
    """Restoring from the state machine must not reintroduce the string.

    The stored state of a TIMESTAMP sensor is its ISO-8601 rendering, so the
    restore parser has to turn it back into a tz-aware datetime.
    """
    restored = ReefBeatSensorEntity._restore_native_value("2025-06-29T17:43:35+00:00")
    assert isinstance(restored, datetime.datetime)
    assert restored.tzinfo is not None

    # Plain text and numeric sensors keep their existing behaviour.
    assert ReefBeatSensorEntity._restore_native_value("dry") == "dry"
    assert ReefBeatSensorEntity._restore_native_value("2500") == 2500.0
    # A bare date has no offset: not a timestamp, left as text.
    assert ReefBeatSensorEntity._restore_native_value("2025-06-29") == "2025-06-29"


def test_null_fields_do_not_raise(device: _FakeATO) -> None:
    """Fields the device reports as null yield None, not an exception.

    `last_adjustment_date` is null until the probe is adjusted for the first
    time; the timestamp helper has to absorb that.
    """
    description = next(
        d for d in ATO_SENSORS if d.key == "ato_sensor_last_adjustment_date"
    )
    assert description.value_fn(cast(Any, device)) is None

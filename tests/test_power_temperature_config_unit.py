"""Coverage for the RSPower local temperature probe's ``/temperature/config``
entities: the four desired/acceptable range numbers, the probe name text, and
the notifications/logging switches.

All are always created and gated by ``has_local_temperature()`` (available
only while a probe is installed, reactive across a swap without a reload —
see the ``available`` overrides). Writes flow through each platform's
generic push mechanism, which resends the whole cached ``/temperature/config``
object (the firmware expects every field together).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from homeassistant.helpers.device_registry import DeviceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.number as number_platform
import custom_components.redsea.switch as switch_platform
import custom_components.redsea.text as text_platform
from custom_components.redsea.const import DOMAIN
from custom_components.redsea.coordinator import ReefPowerCoordinator
from custom_components.redsea.reefbeat import api as api_module
from custom_components.redsea.reefbeat.power import ReefPowerAPI

_CFG = "$.sources[?(@.name=='/temperature/config')].data."


@dataclass
class _FakePower:
    """Minimal RSPower surface for setup + the temperature/config entities."""

    serial: str = "PWR123"
    title: str = "RSPOWER"
    socket_count: int = 6
    hass: Any | None = None
    last_update_success: bool = True
    device_info: DeviceInfo = field(
        default_factory=lambda: DeviceInfo(identifiers={("redsea", "PWR123")})
    )
    get_data_map: dict[str, Any] = field(default_factory=dict)
    local_probe: bool = True
    push_calls: list[tuple[str, str]] = field(default_factory=list)
    refresh_calls: int = 0
    _listeners: list[Any] = field(default_factory=list)

    def async_add_listener(self, cb: Any, ctx: Any = None) -> Any:
        self._listeners.append(cb)
        return lambda: None

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:
        return self.get_data_map.get(name)

    def set_data(self, name: str, value: Any) -> None:
        self.get_data_map[name] = value

    def has_local_temperature(self) -> bool:
        return self.local_probe

    async def push_values(self, source: str, method: str = "put") -> None:
        self.push_calls.append((source, method))

    async def async_request_refresh(self, source: str | None = None) -> None:
        self.refresh_calls += 1

    def async_update_listeners(self) -> None:
        pass


async def _run_setup(module: Any, hass: Any, device: _FakePower) -> list[Any]:
    entry = MockConfigEntry(domain=DOMAIN, title="pwr", data={}, unique_id="pwr-cfg")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device
    added: list[Any] = []
    await module.async_setup_entry(
        hass,
        cast(Any, entry),
        cast(Any, lambda new, update_before_add=False: added.extend(list(new))),
    )
    return added


# ---------------------------------------------------------------------------
# setup wiring
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_number_setup_builds_range_bounds(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(number_platform, "ReefPowerCoordinator", _FakePower)
    added = await _run_setup(number_platform, hass, _FakePower(socket_count=0))
    keys = {e._description.key for e in added}
    assert {
        "temperature_calibration",
        "temperature_desired_range_low",
        "temperature_desired_range_high",
        "temperature_acceptable_range_low",
        "temperature_acceptable_range_high",
    } <= keys

    desired = next(
        e for e in added if e._description.key == "temperature_desired_range_low"
    )
    assert desired._description.native_min_value == 24.1
    assert desired._description.native_max_value == 29
    acceptable = next(
        e for e in added if e._description.key == "temperature_acceptable_range_high"
    )
    assert acceptable._description.native_min_value == 1
    assert acceptable._description.native_max_value == 60


@pytest.mark.asyncio
async def test_text_setup_builds_probe_name(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(text_platform, "ReefPowerCoordinator", _FakePower)
    added = await _run_setup(text_platform, hass, _FakePower(socket_count=0))
    keys = {e._desc.key for e in added}
    assert "temperature_probe_name" in keys


@pytest.mark.asyncio
async def test_switch_setup_builds_notifications_and_log(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(switch_platform, "ReefPowerCoordinator", _FakePower)
    added = await _run_setup(switch_platform, hass, _FakePower(socket_count=0))
    keys = {e.entity_description.key for e in added}
    assert {"temperature_notifications_enabled", "temperature_log_enabled"} <= keys


# ---------------------------------------------------------------------------
# number entity behavior
# ---------------------------------------------------------------------------


def _range_number(device: Any, field_name: str) -> Any:
    desc = number_platform.ReefBeatNumberEntityDescription(
        key=f"temperature_{field_name}",
        translation_key=f"temperature_{field_name}",
        native_min_value=24.1,
        native_max_value=29,
        native_step=0.1,
        value_name=_CFG + field_name,
    )
    return number_platform.ReefPowerTemperatureConfigNumberEntity(device, desc)


@pytest.mark.asyncio
async def test_range_number_available_follows_probe_presence() -> None:
    device = _FakePower(local_probe=True)
    ent = _range_number(device, "desired_range_low")
    assert ent.available is True

    device.local_probe = False
    assert ent.available is False

    device.local_probe = True  # re-paired -> comes back without a reload
    assert ent.available is True


@pytest.mark.asyncio
async def test_range_number_write_pushes_whole_config_object() -> None:
    device = _FakePower(local_probe=True)
    ent = _range_number(device, "desired_range_low")

    await ent.async_set_native_value(24.5)

    assert ent.native_value == 24.5
    assert device.get_data_map[_CFG + "desired_range_low"] == 24.5
    # The base class's generic write path resends the whole cached
    # /temperature/config object (method defaults to PUT), not a single field.
    assert device.push_calls == [("/temperature/config", "put")]
    assert device.refresh_calls == 1


# ---------------------------------------------------------------------------
# text entity behavior
# ---------------------------------------------------------------------------


def _name_text(device: Any) -> Any:
    desc = text_platform.ReefBeatTextEntityDescription(
        key="temperature_probe_name",
        translation_key="temperature_probe_name",
        value_name=_CFG + "name",
    )
    return text_platform.ReefPowerTemperatureNameTextEntity(device, desc)


@pytest.mark.asyncio
async def test_name_text_available_follows_probe_presence() -> None:
    device = _FakePower(local_probe=True)
    ent = _name_text(device)
    assert ent.available is True
    device.local_probe = False
    assert ent.available is False
    device.local_probe = True
    assert ent.available is True


@pytest.mark.asyncio
async def test_name_text_write_pushes_whole_config_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device = _FakePower(local_probe=True)
    ent = _name_text(device)
    monkeypatch.setattr(ent, "async_write_ha_state", lambda: None, raising=False)

    await ent.async_set_value("Sump")

    assert ent.native_value == "Sump"
    assert device.get_data_map[_CFG + "name"] == "Sump"
    assert device.push_calls == [("/temperature/config", "put")]
    assert device.refresh_calls == 1


# ---------------------------------------------------------------------------
# switch entity behavior
# ---------------------------------------------------------------------------


def _config_switch(device: Any, field_name: str) -> Any:
    desc = switch_platform.ReefBeatSwitchEntityDescription(
        key=f"temperature_{field_name}",
        translation_key=f"temperature_{field_name}",
        value_name=_CFG + field_name,
    )
    return switch_platform.ReefPowerTemperatureConfigSwitchEntity(device, desc)


@pytest.mark.asyncio
async def test_config_switch_available_follows_probe_presence() -> None:
    device = _FakePower(local_probe=True)
    ent = _config_switch(device, "notifications_enabled")
    assert ent.available is True
    device.local_probe = False
    assert ent.available is False
    device.local_probe = True
    assert ent.available is True


@pytest.mark.asyncio
async def test_config_switch_toggle_pushes_whole_config_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device = _FakePower(local_probe=True)
    device.get_data_map[_CFG + "log_enabled"] = True
    ent = _config_switch(device, "log_enabled")
    monkeypatch.setattr(ent, "async_write_ha_state", lambda: None, raising=False)

    await ent.async_turn_off()
    assert ent.is_on is False
    assert device.get_data_map[_CFG + "log_enabled"] is False
    assert device.push_calls == [("/temperature/config", "put")]

    await ent.async_turn_on()
    assert ent.is_on is True
    assert device.get_data_map[_CFG + "log_enabled"] is True
    assert device.push_calls == [
        ("/temperature/config", "put"),
        ("/temperature/config", "put"),
    ]


# ---------------------------------------------------------------------------
# regression: no probe installed must not error-log (real get_data/_get_data)
# ---------------------------------------------------------------------------


def _real_power_no_probe() -> ReefPowerCoordinator:
    """A real (offline) ReefPowerAPI/ReefPowerCoordinator with no probe: the
    dashboard reports `temperature: null`, so /temperature/config is never
    registered as a source — the exact "not found" state a device (or the
    project's own simulator) reports when no local probe is installed.
    """
    api = ReefPowerAPI.__new__(ReefPowerAPI)
    api.data = {
        "sources": [
            {"name": "/dashboard", "type": "data", "data": {"temperature": None}}
        ]
    }
    api._data_db = {}
    api._base_url = "http://test"

    coord = ReefPowerCoordinator.__new__(ReefPowerCoordinator)
    coord.my_api = api
    coord._listeners = {}
    coord._title = "PWR123"  # `serial` property returns _title
    return coord


def test_switch_read_no_probe_does_not_error_log(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression for the ERROR log seen in production: reading a
    notifications/logging toggle while no probe is installed (so
    /temperature/config is not a registered source) must resolve to `off`
    quietly, not call _LOGGER.error.
    """
    device = _real_power_no_probe()
    logger_error = MagicMock()
    monkeypatch.setattr(api_module._LOGGER, "error", logger_error)

    ent = _config_switch(cast(Any, device), "notifications_enabled")

    assert ent.is_on is False
    logger_error.assert_not_called()


def test_name_text_read_no_probe_does_not_error_log(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device = _real_power_no_probe()
    logger_error = MagicMock()
    monkeypatch.setattr(api_module._LOGGER, "error", logger_error)

    ent = _name_text(cast(Any, device))

    assert ent.native_value is None
    logger_error.assert_not_called()


def test_switch_read_placeholder_source_does_not_error_log(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """/temperature/config is registered unconditionally at __init__ (see
    ReefPowerAPI.__init__), starting with its placeholder `""` data before
    the first real fetch populates it — that transient state must also read
    quietly, not error-log.
    """
    device = _real_power_no_probe()
    device.my_api.data["sources"].append(
        {"name": "/temperature/config", "type": "config", "data": ""}
    )
    logger_error = MagicMock()
    monkeypatch.setattr(api_module._LOGGER, "error", logger_error)

    ent = _config_switch(cast(Any, device), "log_enabled")

    assert ent.is_on is False
    logger_error.assert_not_called()

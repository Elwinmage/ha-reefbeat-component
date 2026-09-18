"""Coverage for the RSCONTROL fusion and RSPOWER temperature-offset paths of
`number.async_setup_entry`, plus the two dedicated offset entity classes.

Uses the same lightweight-fake / monkeypatched-isinstance harness as the other
control platform tests: a fake coordinator is patched onto the platform's
`ReefControlCoordinator` / `ReefPowerCoordinator` symbol so the dispatcher
takes the branch under test, and `/dashboard` reads are served from a map.
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any, cast

import pytest
from homeassistant.helpers.device_registry import DeviceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.number as number_platform
from custom_components.redsea.const import DOMAIN

_PROBES_PATH = "$.sources[?(@.name=='/dashboard')].data.probes"


@dataclass
class _FakeCtl:
    """Minimal RSCONTROL surface for the number dispatcher + offset entities."""

    serial: str = "CTL123"
    title: str = "RSCONTROL"
    port_count: int = 2
    src_count: int = 2
    hass: Any | None = None
    last_update_success: bool = True
    device_info: DeviceInfo = field(
        default_factory=lambda: DeviceInfo(identifiers={("redsea", "CTL123")})
    )
    get_data_map: dict[str, Any] = field(default_factory=dict)
    offset_calls: list[tuple[str, float]] = field(default_factory=list)
    _listeners: list[Any] = field(default_factory=list)

    def async_add_listener(self, cb: Any) -> Any:
        self._listeners.append(cb)

        def _remove() -> None:
            with suppress(Exception):
                self._listeners.remove(cb)

        return _remove

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:
        return self.get_data_map.get(name)

    def set_data(self, name: str, value: Any) -> None:
        self.get_data_map[name] = value

    def temperature_source_count(self) -> int:
        return self.src_count

    async def set_probe_offset(self, uid: str, value: float) -> None:
        self.offset_calls.append((uid, value))

    async def async_request_refresh(self) -> None:
        return None


@dataclass
class _FakePower:
    """Minimal RSPOWER surface for the temperature-offset number + entity."""

    serial: str = "PWR123"
    title: str = "RSPOWER"
    hass: Any | None = None
    last_update_success: bool = True
    device_info: DeviceInfo = field(
        default_factory=lambda: DeviceInfo(identifiers={("redsea", "PWR123")})
    )
    get_data_map: dict[str, Any] = field(default_factory=dict)
    local_probe: bool = True
    offset_value: float = 0.0
    _listeners: list[Any] = field(default_factory=list)

    def async_add_listener(self, cb: Any) -> Any:
        self._listeners.append(cb)
        return lambda: None

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:
        return self.get_data_map.get(name)

    def set_data(self, name: str, value: Any) -> None:
        self.get_data_map[name] = value

    def has_local_temperature(self) -> bool:
        return self.local_probe

    async def set_temperature_offset(self, value: float) -> None:
        self.offset_value = value

    async def async_request_refresh(self) -> None:
        return None


async def _run_setup(hass: Any, entry: MockConfigEntry, device: Any) -> list[Any]:
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device
    added: list[Any] = []
    await number_platform.async_setup_entry(
        hass,
        cast(Any, entry),
        cast(Any, lambda new, update_before_add=False: added.extend(list(new))),
    )
    return added


# ---------------------------------------------------------------------------
# async_setup_entry — RSCONTROL branch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_control_builds_probe_offset_and_coherence_threshold(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(number_platform, "ReefControlCoordinator", _FakeCtl)

    device = _FakeCtl(src_count=2)
    device.get_data_map[_PROBES_PATH] = [
        {"type": "temperature", "uid": "0xT1", "name": "Sump Temp"},
        {"type": "ph", "uid": "0xP1"},  # not a temperature probe -> no offset
    ]
    entry = MockConfigEntry(domain=DOMAIN, title="ctl", data={}, unique_id="c1")
    added = await _run_setup(hass, entry, device)

    keys = {e._description.key for e in added}
    assert "probe_temperature_0xt1_offset" in keys
    assert "probe_temperature_0xp1_offset" not in keys  # ph is not temperature
    # Two sources -> the coherence-threshold number is offered.
    assert "temperature_coherence_threshold" in keys


@pytest.mark.asyncio
async def test_control_no_coherence_threshold_below_two_sources(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(number_platform, "ReefControlCoordinator", _FakeCtl)

    device = _FakeCtl(src_count=1)
    device.get_data_map[_PROBES_PATH] = [
        {"type": "temperature", "uid": "0xT1", "name": "Only Temp"},
    ]
    entry = MockConfigEntry(domain=DOMAIN, title="ctl", data={}, unique_id="c2")
    added = await _run_setup(hass, entry, device)

    keys = {e._description.key for e in added}
    assert "probe_temperature_0xt1_offset" in keys
    assert "temperature_coherence_threshold" not in keys


# ---------------------------------------------------------------------------
# async_setup_entry — RSPOWER branch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_power_builds_temperature_offset(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(number_platform, "ReefPowerCoordinator", _FakePower)

    entry = MockConfigEntry(domain=DOMAIN, title="pwr", data={}, unique_id="p1")
    added = await _run_setup(hass, entry, _FakePower())

    keys = {e._description.key for e in added}
    assert "temperature_offset" in keys


# ---------------------------------------------------------------------------
# entity methods
# ---------------------------------------------------------------------------


def _probe_offset_entity(device: Any) -> Any:
    desc = number_platform.ReefBeatNumberEntityDescription(
        key="probe_temperature_0xt1_offset",
        translation_key="probe_offset",
        value_name=(
            "$.sources[?(@.name=='/probe/offset?type=temperature&uid=0xT1')].data.offset"
        ),
    )
    return number_platform.ReefControlProbeOffsetNumberEntity(device, desc, uid="0xT1")


@pytest.mark.asyncio
async def test_probe_offset_entity_writes_offset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device = _FakeCtl()
    ent = _probe_offset_entity(device)
    monkeypatch.setattr(ent, "async_write_ha_state", lambda: None, raising=False)

    await ent.async_set_native_value(1.2)
    assert ent.native_value == 1.2
    assert device.offset_calls == [("0xT1", 1.2)]


def test_probe_offset_entity_handle_coordinator_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device = _FakeCtl()
    ent = _probe_offset_entity(device)
    device.get_data_map[ent._description.value_name] = 0.7
    monkeypatch.setattr(ent, "async_write_ha_state", lambda: None, raising=False)

    ent._handle_coordinator_update()
    assert ent.native_value == 0.7
    assert ent.available is True  # no dependency -> always available


@pytest.mark.asyncio
async def test_power_offset_entity_available_and_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device = _FakePower(local_probe=True)
    desc = number_platform.ReefBeatNumberEntityDescription(
        key="temperature_offset",
        translation_key="temperature_offset",
        value_name="$.sources[?(@.name=='/temperature/config')].data.offset",
    )
    ent = number_platform.ReefPowerTemperatureOffsetNumberEntity(
        cast(Any, device), desc
    )

    # Available only while a local probe is installed.
    assert ent.available is True
    device.local_probe = False
    assert ent.available is False

    # Re-paired (a different probe swapped in): the same entity becomes
    # available again — no new entity, no history loss across the swap.
    device.local_probe = True
    assert ent.available is True

    monkeypatch.setattr(ent, "async_write_ha_state", lambda: None, raising=False)
    await ent.async_set_native_value(-0.3)
    assert device.offset_value == -0.3

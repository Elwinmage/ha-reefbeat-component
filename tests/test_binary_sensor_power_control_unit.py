"""Coverage for `binary_sensor.async_setup_entry` on RSPOWER / RSCONTROL.

Covers lines 494, 502–507, 519, 524 of `binary_sensor.py` — the two branches
that materialise per-socket enabled diagnostics on a RSPOWER and the
CONTROL_SENSORS list on a RSCONTROL. Both platforms are read-only for now,
so we simply assert that the dispatcher builds entities without raising.
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any, cast

import pytest
from homeassistant.helpers.device_registry import DeviceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.binary_sensor as binary_platform
from custom_components.redsea.const import DOMAIN


@dataclass
class _FakeCoordinator:
    """Minimum surface required by the binary_sensor dispatcher."""

    serial: str = "SERIAL"
    title: str = "Device"
    hass: Any | None = None
    last_update_success: bool = True
    device_info: DeviceInfo = field(
        default_factory=lambda: DeviceInfo(identifiers={("redsea", "SERIAL")})
    )
    _listeners: list[Any] = field(default_factory=list)

    def async_add_listener(self, update_callback: Any) -> Any:
        self._listeners.append(update_callback)

        def _remove() -> None:
            with suppress(Exception):
                self._listeners.remove(update_callback)

        return _remove

    def get_data(self, _name: str, is_None_possible: bool = False) -> Any:  # noqa: N803
        return None


@dataclass
class _FakePowerDevice(_FakeCoordinator):
    socket_count: int = 6


@dataclass
class _FakeControlDevice(_FakeCoordinator):
    port_count: int = 2


def _neutralise_other_coordinators(monkeypatch: pytest.MonkeyPatch) -> None:
    """Substitute unrelated coordinator symbols in the binary_sensor module.

    async_setup_entry uses a chain of isinstance() checks; we swap the other
    branches with unrelated placeholder types so they never match our fakes.
    """
    for name in (
        "ReefATOCoordinator",
        "ReefBeatCloudCoordinator",
        "ReefDoseCoordinator",
        "ReefLedCoordinator",
        "ReefLedG2Coordinator",
        "ReefMatCoordinator",
        "ReefRunCoordinator",
        "ReefVirtualLedCoordinator",
        "ReefWaveCoordinator",
    ):
        monkeypatch.setattr(
            binary_platform, name, type(f"_Stub{name}", (), {}), raising=False
        )


@pytest.mark.asyncio
async def test_rspower_setup_creates_per_socket_binary_sensors(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RSPOWER path builds one `socket_{n}_enabled` diagnostic per AC socket."""

    class _Power(_FakePowerDevice):
        pass

    monkeypatch.setattr(binary_platform, "ReefPowerCoordinator", _Power, raising=True)
    monkeypatch.setattr(
        binary_platform, "ReefControlCoordinator", type("_Ctl", (), {}), raising=True
    )
    _neutralise_other_coordinators(monkeypatch)

    entry = MockConfigEntry(domain=DOMAIN, title="power", data={}, unique_id="p")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = _Power(socket_count=6)

    added: list[Any] = []

    def _add(new_entities: Any, update_before_add: bool = False) -> None:
        added.extend(list(new_entities))

    await binary_platform.async_setup_entry(hass, cast(Any, entry), cast(Any, _add))

    keys = {e.entity_description.key for e in added}
    for i in range(6):
        assert f"socket_{i}_enabled" in keys


@pytest.mark.asyncio
async def test_rscontrol_setup_builds_control_sensors(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RSCONTROL path emits the top-level CONTROL_SENSORS (leak/buzzer/etc.)."""

    class _Ctl(_FakeControlDevice):
        pass

    monkeypatch.setattr(binary_platform, "ReefControlCoordinator", _Ctl, raising=True)
    monkeypatch.setattr(
        binary_platform, "ReefPowerCoordinator", type("_Pow", (), {}), raising=True
    )
    _neutralise_other_coordinators(monkeypatch)

    entry = MockConfigEntry(domain=DOMAIN, title="ctl", data={}, unique_id="c")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = _Ctl(port_count=2)

    added: list[Any] = []

    def _add(new_entities: Any, update_before_add: bool = False) -> None:
        added.extend(list(new_entities))

    await binary_platform.async_setup_entry(hass, cast(Any, entry), cast(Any, _add))

    # The dispatcher extended entities from CONTROL_SENSORS — the exact set
    # depends on the module, so assert existence rather than a specific size.
    assert added, "CONTROL_SENSORS branch must materialise at least one entity"

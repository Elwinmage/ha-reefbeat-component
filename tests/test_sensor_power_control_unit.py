"""Coverage for `sensor.async_setup_entry` on RSPOWER and RSCONTROL, plus
the probe-discovery fallback when the /dashboard payload is missing/malformed.

Covers lines 1605, 1613–1617, 1671, 1677, 1684–1687, 1745, 1755, 1759, 1768–1769
in `sensor.py`.
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any, cast

import pytest
from homeassistant.helpers.device_registry import DeviceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.sensor as sensor_platform
from custom_components.redsea.const import DOMAIN


@dataclass
class _FakeCoordinator:
    serial: str = "SERIAL"
    title: str = "Device"
    hass: Any | None = None
    last_update_success: bool = True
    device_info: DeviceInfo = field(
        default_factory=lambda: DeviceInfo(identifiers={("redsea", "SERIAL")})
    )
    get_data_map: dict[str, Any] = field(default_factory=dict)
    _listeners: list[Any] = field(default_factory=list)

    def async_add_listener(self, update_callback: Any) -> Any:
        self._listeners.append(update_callback)

        def _remove() -> None:
            with suppress(Exception):
                self._listeners.remove(update_callback)

        return _remove

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:  # noqa: N803
        return self.get_data_map.get(name)


@dataclass
class _FakePowerDevice(_FakeCoordinator):
    socket_count: int = 6


@dataclass
class _FakeControlDevice(_FakeCoordinator):
    port_count: int = 2


def _neutralise_other_coordinators(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace every branch we don't want to hit with a placeholder type."""
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
            sensor_platform, name, type(f"_Stub{name}", (), {}), raising=False
        )


@pytest.mark.asyncio
async def test_rspower_setup_builds_per_socket_sensors(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RSPOWER path emits the 4 per-socket sensors × socket_count."""

    class _Power(_FakePowerDevice):
        pass

    monkeypatch.setattr(sensor_platform, "ReefPowerCoordinator", _Power, raising=True)
    monkeypatch.setattr(
        sensor_platform, "ReefControlCoordinator", type("_Ctl", (), {}), raising=True
    )
    _neutralise_other_coordinators(monkeypatch)

    entry = MockConfigEntry(domain=DOMAIN, title="power", data={}, unique_id="p")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = _Power(socket_count=6)

    added: list[Any] = []

    def _add(new_entities: Any, update_before_add: bool = False) -> None:
        added.extend(list(new_entities))

    await sensor_platform.async_setup_entry(hass, cast(Any, entry), cast(Any, _add))

    keys = {e.entity_description.key for e in added}
    # 4 sensor types per socket: name / state / mode / consumption.
    for i in range(6):
        assert f"socket_{i}_name" in keys
        assert f"socket_{i}_state" in keys
        assert f"socket_{i}_mode" in keys
        assert f"socket_{i}_consumption" in keys


@pytest.mark.asyncio
async def test_rscontrol_setup_builds_per_port_sensors_without_probes(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RSCONTROL path emits per-port sensors, and probe discovery gracefully
    returns nothing when /dashboard.probes is not a list (fallback branch).
    """

    class _Ctl(_FakeControlDevice):
        pass

    monkeypatch.setattr(sensor_platform, "ReefControlCoordinator", _Ctl, raising=True)
    monkeypatch.setattr(
        sensor_platform, "ReefPowerCoordinator", type("_Pow", (), {}), raising=True
    )
    _neutralise_other_coordinators(monkeypatch)

    entry = MockConfigEntry(domain=DOMAIN, title="ctl", data={}, unique_id="c")
    entry.add_to_hass(hass)
    # No probes key returned from get_data → probes list resolves to [].
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = _Ctl(port_count=2)

    added: list[Any] = []

    def _add(new_entities: Any, update_before_add: bool = False) -> None:
        added.extend(list(new_entities))

    await sensor_platform.async_setup_entry(hass, cast(Any, entry), cast(Any, _add))

    keys = {e.entity_description.key for e in added}
    # 5 sensor types per port: name / state / mode / type / consumption.
    for i in range(2):
        assert f"port_{i}_name" in keys
        assert f"port_{i}_state" in keys
        assert f"port_{i}_mode" in keys
        assert f"port_{i}_type" in keys
        assert f"port_{i}_consumption" in keys


@pytest.mark.asyncio
async def test_rscontrol_setup_builds_probe_sensors_from_dashboard(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Probes appear in /dashboard.probes → their sensor entities are built."""

    class _Ctl(_FakeControlDevice):
        pass

    monkeypatch.setattr(sensor_platform, "ReefControlCoordinator", _Ctl, raising=True)
    monkeypatch.setattr(
        sensor_platform, "ReefPowerCoordinator", type("_Pow", (), {}), raising=True
    )
    _neutralise_other_coordinators(monkeypatch)

    device = _Ctl(port_count=1)
    # Two valid probes + one malformed entry that must be filtered out.
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.probes"] = [
        {"uid": "0x0071C", "type": "ph", "name": "Sump pH"},
        {"uid": "0x00842", "type": "temperature", "name": "Display Temp"},
        {"uid": None, "type": "ph"},  # missing uid — filtered
        "garbage",  # not a dict — filtered
    ]

    entry = MockConfigEntry(domain=DOMAIN, title="ctl", data={}, unique_id="c")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[Any] = []

    def _add(new_entities: Any, update_before_add: bool = False) -> None:
        added.extend(list(new_entities))

    await sensor_platform.async_setup_entry(hass, cast(Any, entry), cast(Any, _add))

    keys = {e.entity_description.key for e in added}
    # At least one entity per surviving probe (uid is sanitised, hex only).
    assert any(k.startswith("probe_0x0071c") for k in keys)
    assert any(k.startswith("probe_0x00842") for k in keys)

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
    device_info: DeviceInfo = field(
        default_factory=lambda: DeviceInfo(identifiers={("redsea", "SERIAL")})
    )
    hass: Any | None = None
    last_update_success: bool = False

    _listeners: list[Any] = field(default_factory=list)

    def async_add_listener(self, update_callback: Any) -> Any:
        self._listeners.append(update_callback)

        def _remove() -> None:
            with suppress(Exception):
                self._listeners.remove(update_callback)

        return _remove

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:  # noqa: N803
        return None


@pytest.mark.asyncio
async def test_async_setup_entry_ato_branch(monkeypatch: Any, hass: Any) -> None:
    class _ATO(_FakeCoordinator):
        pass

    monkeypatch.setattr(sensor_platform, "ReefATOCoordinator", _ATO)
    monkeypatch.setattr(sensor_platform, "ReefLedCoordinator", type("L", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefLedG2Coordinator", type("G", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefVirtualLedCoordinator", type("V", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefMatCoordinator", type("M", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefWaveCoordinator", type("W", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefDoseCoordinator", type("D", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefRunCoordinator", type("R", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefBeatCloudCoordinator", type("C", (), {}))

    one = sensor_platform.ReefBeatSensorEntityDescription(
        key="ato", translation_key="ato", value_fn=lambda _: 1
    )

    monkeypatch.setattr(sensor_platform, "CLOUD_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "G2_LED_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "LED_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "MAT_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "WAVE_SCHEDULE_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "LED_SCHEDULES", tuple())
    monkeypatch.setattr(sensor_platform, "ATO_SENSORS", (one,))
    monkeypatch.setattr(sensor_platform, "COMMON_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "USER_SENSORS", tuple())

    entry = MockConfigEntry(domain=DOMAIN, data={"host": "1.2.3.4"})
    entry.add_to_hass(hass)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = _ATO(hass=hass)

    added: list[Any] = []

    def _add_entities(new_entities: Any, update_before_add: bool = False) -> None:
        added.extend(list(new_entities))

    await sensor_platform.async_setup_entry(
        hass, cast(Any, entry), cast(Any, _add_entities)
    )

    assert any(isinstance(e, sensor_platform.ReefBeatSensorEntity) for e in added)

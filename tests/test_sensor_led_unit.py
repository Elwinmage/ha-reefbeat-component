from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any, cast

import pytest
from homeassistant.helpers.device_registry import DeviceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.sensor as sensor_platform
from custom_components.redsea.const import DOMAIN
from custom_components.redsea.sensor import (
    ReefBeatSensorEntityDescription,
    ReefLedScheduleSensorEntity,
    ReefLedScheduleSensorEntityDescription,
)


@dataclass
class _FakeCoordinator:
    serial: str = "SERIAL"
    title: str = "Device"
    hass: Any | None = None
    device_info: DeviceInfo = field(
        default_factory=lambda: DeviceInfo(identifiers={("redsea", "SERIAL")})
    )
    last_update_success: bool = False

    _listeners: list[Any] = field(default_factory=list)

    def async_add_listener(self, update_callback: Any) -> Any:
        self._listeners.append(update_callback)

        def _remove() -> None:
            with suppress(Exception):
                self._listeners.remove(update_callback)

        return _remove

    get_data_map: dict[str, Any] = field(default_factory=dict)

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:  # noqa: N803
        return self.get_data_map.get(name)


def test_led_schedule_sensor_sets_value_and_attributes() -> None:
    device = _FakeCoordinator()
    device.get_data_map["$.schedule"] = "Prog"
    device.get_data_map["$.sources[?(@.name=='/auto/1')].data"] = {"auto": True}
    device.get_data_map["$.sources[?(@.name=='/clouds/1')].data"] = {"cloud": True}

    desc = ReefLedScheduleSensorEntityDescription(
        key="sched",
        translation_key="sched",
        value_name="$.schedule",
        id_name=1,
    )
    entity = ReefLedScheduleSensorEntity(cast(Any, device), cast(Any, desc))
    entity._update_val()

    assert entity.native_value == "Prog"
    assert entity.extra_state_attributes == {
        "data": {"auto": True},
        "clouds": {"cloud": True},
    }


@pytest.mark.asyncio
async def test_async_setup_entry_led_g2_branch(monkeypatch: Any, hass: Any) -> None:
    class _G2(_FakeCoordinator):
        pass

    monkeypatch.setattr(sensor_platform, "ReefLedG2Coordinator", _G2)
    monkeypatch.setattr(sensor_platform, "ReefLedCoordinator", type("L", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefVirtualLedCoordinator", type("V", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefMatCoordinator", type("M", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefWaveCoordinator", type("W", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefDoseCoordinator", type("D", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefATOCoordinator", type("A", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefRunCoordinator", type("R", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefBeatCloudCoordinator", type("C", (), {}))

    g2 = ReefBeatSensorEntityDescription(
        key="g2", translation_key="g2", value_fn=lambda _: 1
    )
    led = ReefBeatSensorEntityDescription(
        key="led", translation_key="led", value_fn=lambda _: 1
    )

    monkeypatch.setattr(sensor_platform, "CLOUD_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "G2_LED_SENSORS", (g2,))
    monkeypatch.setattr(sensor_platform, "LED_SENSORS", (led,))
    monkeypatch.setattr(sensor_platform, "MAT_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "WAVE_SCHEDULE_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "LED_SCHEDULES", tuple())
    monkeypatch.setattr(sensor_platform, "COMMON_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "USER_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "ATO_SENSORS", tuple())

    entry = MockConfigEntry(domain=DOMAIN, data={"host": "1.2.3.4"})
    entry.add_to_hass(hass)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = _G2(hass=hass)

    added: list[Any] = []

    def _add_entities(new_entities: Any, update_before_add: bool = False) -> None:
        added.extend(list(new_entities))

    await sensor_platform.async_setup_entry(
        hass, cast(Any, entry), cast(Any, _add_entities)
    )

    assert any(isinstance(e, sensor_platform.ReefBeatSensorEntity) for e in added)


@pytest.mark.asyncio
async def test_async_setup_entry_led_schedule_branch(
    monkeypatch: Any, hass: Any
) -> None:
    class _Led(_FakeCoordinator):
        pass

    monkeypatch.setattr(sensor_platform, "ReefLedCoordinator", _Led)
    monkeypatch.setattr(sensor_platform, "ReefLedG2Coordinator", type("G", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefVirtualLedCoordinator", type("V", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefMatCoordinator", type("M", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefWaveCoordinator", type("W", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefDoseCoordinator", type("D", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefATOCoordinator", type("A", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefRunCoordinator", type("R", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefBeatCloudCoordinator", type("C", (), {}))

    one = ReefBeatSensorEntityDescription(
        key="one", translation_key="one", value_fn=lambda _: 1
    )

    monkeypatch.setattr(sensor_platform, "CLOUD_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "G2_LED_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "LED_SENSORS", (one,))
    monkeypatch.setattr(sensor_platform, "MAT_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "WAVE_SCHEDULE_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "COMMON_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "USER_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "ATO_SENSORS", tuple())

    monkeypatch.setattr(
        sensor_platform,
        "LED_SCHEDULES",
        (
            ReefLedScheduleSensorEntityDescription(
                key="sched",
                translation_key="sched",
                value_name="$.schedule",
                id_name=1,
            ),
        ),
    )

    entry = MockConfigEntry(domain=DOMAIN, data={"host": "1.2.3.4"})
    entry.add_to_hass(hass)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = _Led(hass=hass)

    added: list[Any] = []

    def _add_entities(new_entities: Any, update_before_add: bool = False) -> None:
        added.extend(list(new_entities))

    await sensor_platform.async_setup_entry(
        hass, cast(Any, entry), cast(Any, _add_entities)
    )

    assert any(
        isinstance(e, sensor_platform.ReefLedScheduleSensorEntity) for e in added
    )

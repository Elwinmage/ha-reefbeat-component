from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

import pytest
from homeassistant.helpers.device_registry import DeviceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.sensor as sensor_platform
from custom_components.redsea.const import DOMAIN
from custom_components.redsea.sensor import (
    ReefRunSensorEntity,
    ReefRunSensorEntityDescription,
)


@dataclass
class _FakeCoordinator:
    serial: str = "SERIAL"
    title: str = "Device"
    device_info: DeviceInfo = field(
        default_factory=lambda: DeviceInfo(
            identifiers={("redsea", "SERIAL")}, name="Device"
        )
    )

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:  # noqa: N803
        return None


def test_run_device_info_extends_identifiers_and_name() -> None:
    device = _FakeCoordinator()
    desc = ReefRunSensorEntityDescription(
        key="x",
        translation_key="x",
        value_name="$.v",
        pump=2,
    )
    entity = ReefRunSensorEntity(cast(Any, device), desc)

    di = entity.device_info
    assert cast(str, di.get("name") or "").endswith("_pump_2")
    identifiers = cast(set[Any], di.get("identifiers") or set())
    assert any("pump_2" in cast(tuple[Any, ...], ident) for ident in identifiers)


def test_run_device_info_no_identifiers_still_sets_name() -> None:
    device = _FakeCoordinator()
    device.device_info = DeviceInfo(name="Device")

    desc = ReefRunSensorEntityDescription(
        key="x",
        translation_key="x",
        value_name="$.v",
        pump=1,
    )
    entity = ReefRunSensorEntity(cast(Any, device), desc)

    assert cast(str, entity.device_info.get("name") or "").endswith("_pump_1")


@pytest.mark.asyncio
async def test_async_setup_entry_run_branch(monkeypatch: Any, hass: Any) -> None:
    class _Run(_FakeCoordinator):
        pass

    monkeypatch.setattr(sensor_platform, "ReefRunCoordinator", _Run)
    monkeypatch.setattr(sensor_platform, "ReefLedCoordinator", type("L", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefLedG2Coordinator", type("G", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefVirtualLedCoordinator", type("V", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefMatCoordinator", type("M", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefWaveCoordinator", type("W", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefDoseCoordinator", type("D", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefATOCoordinator", type("A", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefBeatCloudCoordinator", type("C", (), {}))

    monkeypatch.setattr(sensor_platform, "CLOUD_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "G2_LED_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "LED_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "MAT_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "WAVE_SCHEDULE_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "LED_SCHEDULES", tuple())
    monkeypatch.setattr(sensor_platform, "COMMON_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "USER_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "ATO_SENSORS", tuple())

    entry = MockConfigEntry(domain=DOMAIN, data={"host": "1.2.3.4"})
    entry.add_to_hass(hass)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = _Run()

    added: list[Any] = []

    def _add_entities(new_entities: Any, update_before_add: bool = False) -> None:
        added.extend(list(new_entities))

    await sensor_platform.async_setup_entry(
        hass, cast(Any, entry), cast(Any, _add_entities)
    )

    assert any(isinstance(e, sensor_platform.ReefRunSensorEntity) for e in added)

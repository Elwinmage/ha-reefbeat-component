"""Unit tests for ReefRunSensorEntity calibration date conversion."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, cast

from homeassistant.helpers.device_registry import DeviceInfo

from custom_components.redsea.sensor import (
    ReefRunSensorEntity,
    ReefRunSensorEntityDescription,
)
from homeassistant.components.sensor import SensorDeviceClass


@dataclass
class _FakeCoordinator:
    serial: str = "SERIAL"
    title: str = "Device"
    device_info: DeviceInfo = field(
        default_factory=lambda: DeviceInfo(
            identifiers={("redsea", "SERIAL")}, name="Device"
        )
    )
    _data_map: dict[str, Any] = field(default_factory=dict)

    def pump_device_info(self, pump_id: int) -> DeviceInfo:
        return DeviceInfo(
            identifiers={("redsea", f"SERIAL_pump_{pump_id}")},
            name=f"Device_pump_{pump_id}",
            manufacturer="Red Sea",
            model="X",
        )

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:
        return self._data_map.get(name)


def _make_entity(
    device: _FakeCoordinator, translation_key: str, value_name: str
) -> ReefRunSensorEntity:
    desc = ReefRunSensorEntityDescription(
        key=f"test_{translation_key}",
        translation_key=translation_key,
        value_name=value_name,
        icon="mdi:calendar-clock",
        device_class=SensorDeviceClass.DATE,
        pump=0,
    )
    return ReefRunSensorEntity(cast(Any, device), desc)


def test_skim_calibration_date_converts_epoch_to_date() -> None:
    # 1755113717 = 2025-08-13 in UTC
    device = _FakeCoordinator(
        _data_map={
            "$.sources[?(@.name=='/calibration')].data.skim_last_calibration_date": 1755113717
        }
    )
    entity = _make_entity(
        device,
        "skim_last_calibration",
        "$.sources[?(@.name=='/calibration')].data.skim_last_calibration_date",
    )
    result = entity._get_value()
    assert isinstance(result, datetime.date)
    assert result == datetime.datetime.fromtimestamp(1755113717, tz=datetime.UTC).date()


def test_cup_calibration_date_converts_epoch_to_date() -> None:
    device = _FakeCoordinator(
        _data_map={
            "$.sources[?(@.name=='/calibration')].data.cup_last_calibration_date": 1755113746
        }
    )
    entity = _make_entity(
        device,
        "cup_last_calibration",
        "$.sources[?(@.name=='/calibration')].data.cup_last_calibration_date",
    )
    result = entity._get_value()
    assert isinstance(result, datetime.date)
    assert result == datetime.datetime.fromtimestamp(1755113746, tz=datetime.UTC).date()


def test_calibration_date_none_returns_none() -> None:
    device = _FakeCoordinator(_data_map={})
    entity = _make_entity(
        device,
        "skim_last_calibration",
        "$.sources[?(@.name=='/calibration')].data.skim_last_calibration_date",
    )
    result = entity._get_value()
    assert result is None


def test_calibration_date_invalid_value_returns_none() -> None:
    device = _FakeCoordinator(
        _data_map={
            "$.sources[?(@.name=='/calibration')].data.skim_last_calibration_date": "not_a_number"
        }
    )
    entity = _make_entity(
        device,
        "skim_last_calibration",
        "$.sources[?(@.name=='/calibration')].data.skim_last_calibration_date",
    )
    result = entity._get_value()
    assert result is None


def test_non_calibration_sensor_returns_raw_value() -> None:
    device = _FakeCoordinator(
        _data_map={
            "$.sources[?(@.name=='/dashboard')].data.pump_1.name": "Reefrun 1200"
        }
    )
    desc = ReefRunSensorEntityDescription(
        key="test_name",
        translation_key="name",
        value_name="$.sources[?(@.name=='/dashboard')].data.pump_1.name",
        icon="mdi:pump",
        pump=1,
    )
    entity = ReefRunSensorEntity(cast(Any, device), desc)
    result = entity._get_value()
    assert result == "Reefrun 1200"

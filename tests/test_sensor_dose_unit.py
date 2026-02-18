from __future__ import annotations

import datetime
from contextlib import suppress
from copy import deepcopy
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Callable, cast

import pytest
from homeassistant.helpers.device_registry import DeviceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.sensor as sensor_platform
from custom_components.redsea.const import DOMAIN
from custom_components.redsea.sensor import (
    ReefBeatSensorEntity,
    ReefDoseSensorEntity,
    ReefDoseSensorEntityDescription,
)


@dataclass
class _FakeBus:
    fired: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    listeners: list[tuple[str, Callable[[Any], None]]] = field(default_factory=list)

    def fire(self, event_type: str, event_data: dict[str, Any] | None = None) -> None:
        self.fired.append((event_type, dict(event_data or {})))

    def async_listen(
        self, event_type: str, listener: Callable[[Any], None]
    ) -> Callable[[], None]:
        self.listeners.append((event_type, listener))

        def _remove() -> None:
            with suppress(Exception):
                self.listeners.remove((event_type, listener))

        return _remove


@dataclass
class _FakeHass:
    language: str = "en"
    bus: _FakeBus = field(default_factory=_FakeBus)

    @property
    def config(self) -> Any:
        return SimpleNamespace(language=self.language)


@dataclass
class _FakeCoordinator:
    serial: str = "SERIAL"
    title: str = "Device"
    device_info: DeviceInfo = field(
        default_factory=lambda: DeviceInfo(
            identifiers={("redsea", "SERIAL")},
            name="Device",
            manufacturer="Red Sea",
            model="X",
            via_device=("redsea", "hub"),
        )
    )
    hass: Any | None = None

    get_data_map: dict[str, Any] = field(default_factory=dict)
    set_calls: list[tuple[str, Any]] = field(default_factory=list)

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:  # noqa: N803
        return self.get_data_map.get(name)

    def set_data(self, name: str, value: Any) -> None:
        self.set_calls.append((name, value))
        self.get_data_map[name] = value

    def head_device_info(self, head_id):
        """Return device info extended with the head identifier (non-mutating)."""
        if head_id <= 0:
            return self.device_info
        else:
            res = deepcopy(self.device_info)
            res["identifiers"] = {("redsea", f"{self.serial}_head_{head_id}")}
            res["name"] = f"{self.title} head {head_id}"
            return res


def test_update_val_sets_extra_attributes_from_with_attr_fields() -> None:
    device = _FakeCoordinator()
    device.get_data_map["$.value"] = "v"
    device.get_data_map["$.attr"] = {"k": "v"}

    desc = ReefDoseSensorEntityDescription(
        key="x",
        translation_key="x",
        value_name="$.value",
        with_attr_name="extra",
        with_attr_value="$.attr",
        head=0,
    )
    entity = ReefBeatSensorEntity(cast(Any, device), cast(Any, desc))
    entity._update_val()

    assert entity.native_value == "v"
    assert entity.extra_state_attributes == {"extra": {"k": "v"}}


def test_get_value_dosing_queue_non_empty(monkeypatch: Any) -> None:
    device = _FakeCoordinator(hass=_FakeHass(language="en"))
    device.get_data_map["$.queue"] = [{"head": 3}]

    desc = ReefDoseSensorEntityDescription(
        key="dosing_queue",
        translation_key="dosing_queue",
        icon="mdi:tray-full",
        value_name="$.queue",
        head=0,
    )
    entity = ReefBeatSensorEntity(cast(Any, device), cast(Any, desc))

    assert entity._get_value() == 3


def test_get_value_dosing_queue_empty_translates(monkeypatch: Any) -> None:
    device = _FakeCoordinator(hass=_FakeHass(language="fr"))
    device.get_data_map["$.queue"] = []

    desc = ReefDoseSensorEntityDescription(
        key="dosing_queue",
        translation_key="dosing_queue",
        icon="mdi:tray-full",
        value_name="$.queue",
        head=0,
    )
    entity = ReefBeatSensorEntity(cast(Any, device), cast(Any, desc))

    assert entity._get_value() == "empty"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        ("nope", None),
        (0, datetime.date(1970, 1, 1)),
    ],
)
def test_dose_last_calibration_parsing(raw: Any, expected: Any) -> None:
    device = _FakeCoordinator()
    device.get_data_map["$.cal"] = raw

    desc = ReefDoseSensorEntityDescription(
        key="last_calibration",
        translation_key="last_calibration",
        value_name="$.cal",
        head=1,
    )
    entity = ReefDoseSensorEntity(cast(Any, device), desc)

    assert entity._get_value() == expected


def test_dose_container_volume_increase_fires_event() -> None:
    fake_hass = _FakeHass(language="en")
    device = _FakeCoordinator(hass=fake_hass)

    desc = ReefDoseSensorEntityDescription(
        key="container_volume",
        translation_key="container_volume",
        value_name="event.key",
        head=1,
    )
    entity = ReefDoseSensorEntity(cast(Any, device), desc)

    entity._attr_native_value = 10
    device.get_data_map["event.key"] = 12

    entity._update_val()

    assert fake_hass.bus.fired == [("event.key", {"value": 12})]


def test_dose_device_info_head_zero_uses_base() -> None:
    device = _FakeCoordinator()
    desc = ReefDoseSensorEntityDescription(
        key="x",
        translation_key="x",
        value_name="$.v",
        head=0,
    )
    entity = ReefDoseSensorEntity(cast(Any, device), desc)

    assert entity.device_info == device.device_info


def test_dose_device_info_head_extends_identifiers_and_name() -> None:
    device = _FakeCoordinator()

    # Also include a non-string to ensure we don't copy it into the TypedDict.
    device.device_info = DeviceInfo(
        identifiers={("redsea", "SERIAL")},
        name="Device",
        manufacturer="Red Sea",
        model="X",
        sw_version=None,
        hw_version="1",
        # field not expected to be copied
        configuration_url=cast(Any, 123),
        via_device=("redsea", "hub"),
    )

    desc = ReefDoseSensorEntityDescription(
        key="x",
        translation_key="x",
        value_name="$.v",
        head=2,
    )
    entity = ReefDoseSensorEntity(cast(Any, device), desc)

    di = entity.device_info
    identifiers = cast(set[tuple[str, str]], di.get("identifiers") or set())
    assert ("redsea", "SERIAL_head_2") in identifiers
    assert di.get("name") == "Device head 2"
    assert di.get("via_device") == ("redsea", "hub")


@pytest.mark.asyncio
async def test_async_setup_entry_dose_branch(monkeypatch: Any, hass: Any) -> None:
    class _Dose(_FakeCoordinator):
        heads_nb: int = 1

    monkeypatch.setattr(sensor_platform, "ReefDoseCoordinator", _Dose)
    monkeypatch.setattr(sensor_platform, "ReefLedCoordinator", type("L", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefLedG2Coordinator", type("G", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefVirtualLedCoordinator", type("V", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefMatCoordinator", type("M", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefWaveCoordinator", type("W", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefATOCoordinator", type("A", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefRunCoordinator", type("R", (), {}))
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

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = _Dose(hass=hass)

    added: list[Any] = []

    def _add_entities(new_entities: Any, update_before_add: bool = False) -> None:
        added.extend(list(new_entities))

    await sensor_platform.async_setup_entry(
        hass, cast(Any, entry), cast(Any, _add_entities)
    )

    assert any(
        isinstance(
            e,
            (sensor_platform.RestoreSensorEntity, sensor_platform.ReefDoseSensorEntity),
        )
        for e in added
    )

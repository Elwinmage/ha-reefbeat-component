from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Callable, cast

import pytest
from homeassistant.helpers.device_registry import DeviceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.sensor as sensor_platform
from custom_components.redsea.const import DOMAIN
from custom_components.redsea.sensor import (
    ReefWaveSensorEntity,
    ReefWaveSensorEntityDescription,
)


@dataclass
class _FakeBus:
    listeners: list[tuple[str, Callable[[Any], None]]] = field(default_factory=list)

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
class _FakeWaveCoordinator:
    serial: str = "SERIAL"
    title: str = "Device"
    hass: Any | None = None
    current_values: dict[tuple[str, str], Any] = field(default_factory=dict)

    def get_current_value(self, basename: str, name: str) -> Any:
        return self.current_values.get((basename, name))


def test_wave_sensor_translates_type_and_direction(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        sensor_platform, "translate", lambda txt, lang, **_: f"{txt}-{lang}"
    )

    device = _FakeWaveCoordinator(hass=_FakeHass(language="en"))
    device.current_values[("schedule", "type")] = "A"
    device.current_values[("schedule", "direction")] = "X"

    type_desc = ReefWaveSensorEntityDescription(
        key="t",
        translation_key="t",
        value_basename="schedule",
        value_name="type",
    )
    dir_desc = ReefWaveSensorEntityDescription(
        key="d",
        translation_key="d",
        value_basename="schedule",
        value_name="direction",
    )

    type_entity = ReefWaveSensorEntity(cast(Any, device), type_desc)
    dir_entity = ReefWaveSensorEntity(cast(Any, device), dir_desc)

    assert type_entity._get_value() == "A-en"
    assert dir_entity._get_value() == "X-en"


def test_wave_sensor_direction_defaults_fw_when_none() -> None:
    device = _FakeWaveCoordinator(hass=_FakeHass(language="en"))
    device.current_values[("schedule", "direction")] = None

    desc = ReefWaveSensorEntityDescription(
        key="d",
        translation_key="d",
        value_basename="schedule",
        value_name="direction",
    )
    entity = ReefWaveSensorEntity(cast(Any, device), desc)

    assert entity._get_value() == "fw"


def test_wave_sensor_default_return_value() -> None:
    device = _FakeWaveCoordinator(hass=_FakeHass(language="en"))
    device.current_values[("schedule", "fti")] = 7

    desc = ReefWaveSensorEntityDescription(
        key="fti",
        translation_key="fti",
        value_basename="schedule",
        value_name="fti",
    )
    entity = ReefWaveSensorEntity(cast(Any, device), desc)

    assert entity._get_value() == 7


@pytest.mark.asyncio
async def test_async_setup_entry_wave_branch(monkeypatch: Any, hass: Any) -> None:
    @dataclass
    class _Wave:
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

        def get_current_value(self, basename: str, name: str) -> Any:
            return None

    monkeypatch.setattr(sensor_platform, "ReefWaveCoordinator", _Wave)
    monkeypatch.setattr(sensor_platform, "ReefLedG2Coordinator", type("G", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefVirtualLedCoordinator", type("V", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefLedCoordinator", type("L", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefMatCoordinator", type("M", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefDoseCoordinator", type("D", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefATOCoordinator", type("A", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefRunCoordinator", type("R", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefBeatCloudCoordinator", type("C", (), {}))

    one = ReefWaveSensorEntityDescription(
        key="wave_val",
        translation_key="wave_val",
        value_basename="schedule",
        value_name="direction",
    )

    monkeypatch.setattr(sensor_platform, "CLOUD_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "G2_LED_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "LED_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "MAT_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "WAVE_SCHEDULE_SENSORS", (one,))
    monkeypatch.setattr(sensor_platform, "LED_SCHEDULES", tuple())
    monkeypatch.setattr(sensor_platform, "COMMON_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "USER_SENSORS", tuple())

    entry = MockConfigEntry(domain=DOMAIN, data={"host": "1.2.3.4"})
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = _Wave(hass=hass)

    added: list[Any] = []

    def _add_entities(new_entities: Any, update_before_add: bool = False) -> None:
        added.extend(list(new_entities))

    await sensor_platform.async_setup_entry(
        hass, cast(Any, entry), cast(Any, _add_entities)
    )

    assert any(isinstance(e, sensor_platform.ReefWaveSensorEntity) for e in added)

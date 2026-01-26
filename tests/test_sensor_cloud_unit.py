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
    ReefBeatCloudSensorEntity,
    ReefBeatCloudSensorEntityDescription,
    ReefBeatSensorEntityDescription,
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
class _FakeApi:
    data: dict[str, Any] = field(default_factory=dict)

    def get_data(self, path: str) -> Any:
        return self.data.get(path, [])


@dataclass
class _FakeCoordinator:
    serial: str = "SERIAL"
    title: str = "Device"
    device_info: DeviceInfo = field(
        default_factory=lambda: DeviceInfo(
            identifiers={("redsea", "SERIAL")}, name="Device"
        )
    )
    hass: Any | None = None
    my_api: _FakeApi = field(default_factory=_FakeApi)

    get_data_map: dict[str, Any] = field(default_factory=dict)

    def cloud_link(self) -> Any:
        return True

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:  # noqa: N803
        return self.get_data_map.get(name)


def test_cloud_sensor_formats_value_and_sets_attributes() -> None:
    device = _FakeCoordinator(hass=_FakeHass(language="en"))

    value_name = "$.sources[?(@.name=='/cloud/lights')].data[?(@.uid=='1')].name"
    device.get_data_map[value_name.replace("].name", "].aquarium_uid")] = 1
    device.get_data_map[
        "$.sources[?(@.name=='/aquarium')].data[?(@.uid=='1')].name"
    ] = "Tank"
    device.get_data_map[value_name] = "Prog"
    device.get_data_map[value_name.replace("].name", "]")] = {"uid": 1}

    desc = ReefBeatCloudSensorEntityDescription(
        key="prog_1",
        translation_key="led_program",
        value_name=value_name,
    )

    entity = ReefBeatCloudSensorEntity(cast(Any, device), desc)

    assert entity._get_value() == "Prog-Tank"
    assert entity.extra_state_attributes == {"uid": 1}

    di = entity.device_info
    assert di.get("name") == "Tank"


def test_cloud_sensor_supplement_defaults_aquarium_name() -> None:
    device = _FakeCoordinator(hass=_FakeHass(language="en"))

    value_name = "$.sources[?(@.name=='/cloud/supp')].data[?(@.uid=='2')].name"
    device.get_data_map[value_name.replace("].name", "].aquarium_uid")] = None
    device.get_data_map[value_name] = "Supp"
    device.get_data_map[value_name.replace("].name", "]")] = {"uid": 2}

    desc = ReefBeatCloudSensorEntityDescription(
        key="supplement_2",
        translation_key="supplement_program",
        value_name=value_name,
    )

    entity = ReefBeatCloudSensorEntity(cast(Any, device), desc)

    assert entity._get_value() == "Supp-Supplements"
    assert entity.device_info.get("name") == "Supplements"


def test_cloud_sensor_no_aquarium_name_returns_raw_name() -> None:
    device = _FakeCoordinator(hass=_FakeHass(language="en"))

    value_name = "$.sources[?(@.name=='/cloud/waves')].data[?(@.uid=='3')].name"
    device.get_data_map[value_name.replace("].name", "].aquarium_uid")] = None
    device.get_data_map[value_name] = "Wave"

    desc = ReefBeatCloudSensorEntityDescription(
        key="wave_3",
        translation_key="wave_program",
        value_name=value_name,
    )

    entity = ReefBeatCloudSensorEntity(cast(Any, device), desc)

    assert entity._get_value() == "Wave"


@pytest.mark.asyncio
async def test_async_setup_entry_cloud_linked_branch(
    monkeypatch: Any, hass: Any
) -> None:
    class _CloudLinked(_FakeCoordinator):
        pass

    monkeypatch.setattr(
        sensor_platform,
        "CLOUD_SENSORS",
        (
            ReefBeatSensorEntityDescription(
                key="cloud_account",
                translation_key="cloud_account",
                value_fn=lambda _: "x",
            ),
        ),
    )
    monkeypatch.setattr(sensor_platform, "G2_LED_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "LED_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "MAT_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "WAVE_SCHEDULE_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "COMMON_SENSORS", tuple())

    monkeypatch.setattr(sensor_platform, "ReefBeatCloudCoordinator", type("X", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefVirtualLedCoordinator", type("Y", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefLedG2Coordinator", type("Z", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefLedCoordinator", type("A", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefMatCoordinator", type("B", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefWaveCoordinator", type("C", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefDoseCoordinator", type("D", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefATOCoordinator", type("E", (), {}))
    monkeypatch.setattr(sensor_platform, "ReefRunCoordinator", type("F", (), {}))

    entry = MockConfigEntry(domain=DOMAIN, data={"host": "1.2.3.4"})
    entry.add_to_hass(hass)

    device = _CloudLinked(hass=hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[Any] = []

    def _add_entities(new_entities: Any, update_before_add: bool = False) -> None:
        added.extend(list(new_entities))

    await sensor_platform.async_setup_entry(
        hass, cast(Any, entry), cast(Any, _add_entities)
    )

    assert any(isinstance(e, sensor_platform.ReefBeatSensorEntity) for e in added)


@pytest.mark.asyncio
async def test_async_setup_entry_cloud_library_dynamic_descriptions(
    monkeypatch: Any, hass: Any
) -> None:
    class _CloudCoord(_FakeCoordinator):
        pass

    monkeypatch.setattr(sensor_platform, "ReefBeatCloudCoordinator", _CloudCoord)

    monkeypatch.setattr(sensor_platform, "CLOUD_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "G2_LED_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "LED_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "MAT_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "WAVE_SCHEDULE_SENSORS", tuple())
    monkeypatch.setattr(sensor_platform, "COMMON_SENSORS", tuple())

    monkeypatch.setattr(
        sensor_platform,
        "USER_SENSORS",
        (
            ReefBeatCloudSensorEntityDescription(
                key="user_1",
                translation_key="user_sensor",
                value_name="$.user",
            ),
        ),
    )

    device = _CloudCoord(hass=hass)
    device.get_data_map["$.user"] = "U"

    device.my_api.data[
        "$.sources[?(@.name=='" + sensor_platform.LIGHTS_LIBRARY + "')].data"
    ] = [{"uid": 1}]
    device.my_api.data[
        "$.sources[?(@.name=='" + sensor_platform.WAVES_LIBRARY + "')].data"
    ] = [{"uid": 2}]
    device.my_api.data[
        "$.sources[?(@.name=='" + sensor_platform.SUPPLEMENTS_LIBRARY + "')].data"
    ] = [{"uid": 3}]

    device.get_data_map[
        "$.sources[?(@.name=='"
        + sensor_platform.LIGHTS_LIBRARY
        + "')].data[?(@.uid=='1')].name"
    ] = "P"
    device.get_data_map[
        "$.sources[?(@.name=='"
        + sensor_platform.WAVES_LIBRARY
        + "')].data[?(@.uid=='2')].name"
    ] = "W"
    device.get_data_map[
        "$.sources[?(@.name=='"
        + sensor_platform.SUPPLEMENTS_LIBRARY
        + "')].data[?(@.uid=='3')].name"
    ] = "S"

    entry = MockConfigEntry(domain=DOMAIN, data={"host": "1.2.3.4"})
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[Any] = []

    def _add_entities(new_entities: Any, update_before_add: bool = False) -> None:
        added.extend(list(new_entities))

    await sensor_platform.async_setup_entry(
        hass, cast(Any, entry), cast(Any, _add_entities)
    )

    assert any(isinstance(e, sensor_platform.ReefBeatCloudSensorEntity) for e in added)

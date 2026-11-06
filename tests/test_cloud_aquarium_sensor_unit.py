"""Aquarium of a cloud-linked device (coordinator + `aquarium` sensor)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from custom_components.redsea import sensor as sensor_mod
from custom_components.redsea.coordinator import ReefBeatCloudLinkedCoordinator

_DEVICES = "$.sources[?(@.name=='/device')].data"
_AQUARIUMS = "$.sources[?(@.name=='/aquarium')].data"


class _FakeCloud:
    def __init__(self, devices: Any, aquariums: Any, title: str = "me@x") -> None:
        self._data = {_DEVICES: devices, _AQUARIUMS: aquariums}
        self.title = title

    def get_data(self, path: str, is_None_possible: bool = False) -> Any:
        return self._data.get(path)


AQ = {
    "uid": "aq-1",
    "name": "Reef 350",
    "system_model": "G2 350",
    "water_volume": 350,
    "net_water_volume": 280,
}


def _device(cloud: _FakeCloud | None, hwid: str = "hw-1") -> Any:
    dev = SimpleNamespace(_cloud_link=cloud, model_id=hwid)
    dev.cloud_aquarium = lambda: ReefBeatCloudLinkedCoordinator.cloud_aquarium(
        cast(Any, dev)
    )
    dev.cloud_link = lambda: cloud.title if cloud else "none"
    return dev


def _cloud(**kw: Any) -> _FakeCloud:
    devices = kw.get(
        "devices",
        [
            {"hwid": "other", "aquarium_uid": "aq-2"},
            {"hwid": "hw-1", "aquarium_uid": "aq-1"},
        ],
    )
    aquariums = kw.get("aquariums", [{"uid": "aq-2", "name": "Frag"}, AQ])
    return _FakeCloud(devices, aquariums)


def test_aquarium_of_a_linked_device() -> None:
    dev = _device(_cloud())
    assert dev.cloud_aquarium() == AQ
    assert sensor_mod._aquarium_name(dev) == "Reef 350"
    assert sensor_mod._aquarium_attributes(dev) == {
        "aquarium_uid": "aq-1",
        "cloud_account": "me@x",
        "system_model": "G2 350",
        "water_volume": 350,
        "net_water_volume": 280,
    }


def test_no_aquarium_when_not_linked() -> None:
    dev = _device(None)
    assert dev.cloud_aquarium() is None
    assert sensor_mod._aquarium_name(dev) is None
    attrs = sensor_mod._aquarium_attributes(dev)
    assert attrs["aquarium_uid"] is None
    assert attrs["cloud_account"] is None


def test_no_aquarium_when_device_unknown_or_unassigned() -> None:
    assert _device(_cloud(), hwid="missing").cloud_aquarium() is None
    unassigned = _cloud(devices=[{"hwid": "hw-1", "aquarium_uid": None}])
    assert _device(unassigned).cloud_aquarium() is None
    gone = _cloud(aquariums=[{"uid": "aq-2", "name": "Frag"}])
    assert _device(gone).cloud_aquarium() is None


def test_no_aquarium_when_cloud_data_not_loaded() -> None:
    assert _device(_FakeCloud(None, None)).cloud_aquarium() is None
    assert _device(_FakeCloud("", [AQ])).cloud_aquarium() is None


def test_name_falls_back_to_uid() -> None:
    cloud = _cloud(aquariums=[{"uid": "aq-1", "name": ""}])
    assert sensor_mod._aquarium_name(_device(cloud)) == "aq-1"


def test_device_without_cloud_capability() -> None:
    dev = SimpleNamespace()
    assert sensor_mod._aquarium_name(cast(Any, dev)) is None
    assert sensor_mod._aquarium_attributes(cast(Any, dev))["cloud_account"] is None


def test_sensor_description_is_skipped_for_led_groups() -> None:
    desc = next(d for d in sensor_mod.CLOUD_SENSORS if d.key == "aquarium")
    group = object.__new__(sensor_mod.ReefVirtualLedCoordinator)
    assert desc.exists_fn(cast(Any, group)) is False
    assert desc.exists_fn(cast(Any, _device(_cloud()))) is True

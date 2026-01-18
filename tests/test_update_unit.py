from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, cast

import pytest
from homeassistant.const import STATE_UNKNOWN
from homeassistant.helpers.device_registry import DeviceInfo

from custom_components.redsea.update import (
    ReefBeatUpdateEntity,
    ReefBeatUpdateEntityDescription,
)


@dataclass
class _FakeCloudCoordinator:
    get_data_map: dict[str, Any] = field(default_factory=dict)

    def get_data(self, name: str, use_cache: bool = True) -> Any:
        return self.get_data_map.get(name)


@dataclass
class _FakeAPI:
    pressed: list[str] = field(default_factory=list)

    async def press(self, cmd: str) -> None:
        self.pressed.append(cmd)


@dataclass
class _FakeDevice:
    serial: str = "SERIAL"
    device_info: DeviceInfo = field(
        default_factory=lambda: DeviceInfo(identifiers={("redsea", "SERIAL")})
    )

    sw_version: str | None = "1.0"
    latest_firmware_url: str | None = "/latest-fw"
    cloud_coordinator: _FakeCloudCoordinator | None = field(
        default_factory=_FakeCloudCoordinator
    )

    last_update_success: bool = True

    my_api: _FakeAPI = field(default_factory=_FakeAPI)

    get_data_map: dict[str, Any] = field(default_factory=dict)
    set_calls: list[tuple[str, Any]] = field(default_factory=list)

    def async_add_listener(
        self, update_callback: Callable[[], None], _context: Any | None = None
    ) -> Callable[[], None]:
        def _remove() -> None:
            return None

        return _remove

    def get_data(self, name: str, use_cache: bool = True) -> Any:
        return self.get_data_map.get(name)

    def set_data(self, name: str, value: Any) -> None:
        self.set_calls.append((name, value))
        self.get_data_map[name] = value

    @property
    def cloud_link(self) -> Any:
        return True


@dataclass
class _State:
    state: str = STATE_UNKNOWN
    attributes: dict[str, Any] = field(default_factory=dict)


@pytest.mark.asyncio
async def test_update_entity_latest_from_cloud_and_install(hass: Any) -> None:
    dev = _FakeDevice()

    desc = ReefBeatUpdateEntityDescription(
        key="firmware_update",
        translation_key="firmware_update",
        version_path="$.sources[?(@.name=='/firmware')].data.version",
    )

    # installed from cache
    dev.get_data_map[desc.version_path] = "1.1"

    # latest from cloud
    assert dev.cloud_coordinator is not None
    dev.cloud_coordinator.get_data_map[
        "$.sources[?(@.name=='/latest-fw')].data.version"
    ] = "2.0"

    ent = ReefBeatUpdateEntity(cast(Any, dev), desc)
    ent.hass = hass
    ent.async_write_ha_state = lambda: None  # type: ignore[assignment]

    assert ent.installed_version == "1.1"
    assert ent.latest_version == "2.0"

    # install should press firmware and mirror latest into cache
    await ent.async_install(None, False)

    assert dev.my_api.pressed == ["firmware"]
    assert (desc.version_path, "2.0") in dev.set_calls


@pytest.mark.asyncio
async def test_update_entity_async_added_restores_versions(
    monkeypatch: pytest.MonkeyPatch, hass: Any
) -> None:
    # async_added_to_hass ends by calling _handle_device_update(), which will
    # recompute installed_version from cache/sw_version. Keep sw_version aligned
    # with the restored values so this test can assert the end state.
    dev = _FakeDevice(
        latest_firmware_url=None, cloud_coordinator=None, sw_version="9.9"
    )

    desc = ReefBeatUpdateEntityDescription(
        key="firmware_update",
        translation_key="firmware_update",
        version_path="$.sources[?(@.name=='/firmware')].data.version",
    )

    ent = ReefBeatUpdateEntity(cast(Any, dev), desc)
    ent.hass = hass
    ent.async_write_ha_state = lambda: None  # type: ignore[assignment]

    # Force missing so restore path is used
    ent._attr_installed_version = None
    ent._attr_latest_version = None

    async def _fake_last_state() -> _State:
        return _State(
            state="on",
            attributes={"installed_version": "9.9", "latest_version": "9.9"},
        )

    ent.async_get_last_state = cast(Any, _fake_last_state)

    await ent.async_added_to_hass()

    assert ent.installed_version == "9.9"
    assert ent.latest_version == "9.9"

    # Ask-for-latest event should not crash and should hit both branches
    hass.bus.async_fire("request_latest_firmware", {"device_name": "nope"})
    hass.bus.async_fire("request_latest_firmware", {"device_name": ent.unique_id})
    await hass.async_block_till_done()


def test_update_latest_from_cloud_with_no_cloud_coordinator_returns_none() -> None:
    dev = _FakeDevice(latest_firmware_url="/latest", cloud_coordinator=None)

    desc = ReefBeatUpdateEntityDescription(
        key="firmware_update",
        translation_key="firmware_update",
        version_path="$.sources[?(@.name=='/firmware')].data.version",
    )
    ent = ReefBeatUpdateEntity(cast(Any, dev), desc)

    assert ent._get_latest_from_cloud() is None

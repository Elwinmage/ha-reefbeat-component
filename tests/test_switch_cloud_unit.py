from __future__ import annotations


from dataclasses import dataclass, field
from typing import Any, Callable, cast

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo

import custom_components.redsea.switch as platform
from custom_components.redsea.const import DOMAIN
from custom_components.redsea.switch import (
    ReefBeatSwitchEntity,
    ReefCloudSwitchEntity,
    ReefCloudSwitchEntityDescription,
    SaveStateSwitchEntity,
    SaveStateSwitchEntityDescription,
)
from tests._switch_test_fakes import FakeCoordinator


class _CloudLinkedDevice(FakeCoordinator):
    def cloud_link(self) -> Any:
        return True


@dataclass
class _FakeSwitchCoordinator:
    """Fake coordinator pour les tests switch cloud."""

    serial: str = "CLOUD-SERIAL"
    title: str = "Device"
    last_update_success: bool = True
    device_info: DeviceInfo = field(
        default_factory=lambda: DeviceInfo(
            identifiers={("redsea", "CLOUD-SERIAL")},
            name="Device",
            manufacturer="Red Sea",
            model="X",
        )
    )
    get_data_map: dict[str, Any] = field(default_factory=dict)
    set_calls: list[tuple[str, Any]] = field(default_factory=list)
    _listeners: list[Callable[[], None]] = field(default_factory=list)

    def async_add_listener(
        self, update_callback: Callable[[], None], context: Any = None
    ) -> Callable[[], None]:
        self._listeners.append(update_callback)
        return lambda: None

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:  # noqa: N803
        return self.get_data_map.get(name)

    def set_data(self, name: str, value: Any) -> None:
        self.set_calls.append((name, value))
        self.get_data_map[name] = value

    async def async_request_refresh(self, source: str = "", **kwargs: Any) -> None:
        pass


class _FakeCloudAPI:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def http_send(self, *, action: str, method: str = "post") -> None:
        self.sent.append((action, method))


class _CloudDevice(FakeCoordinator):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.my_api = _FakeCloudAPI()


@pytest.mark.asyncio
async def test_save_state_switch_sets_local_cache_and_icons(hass: Any) -> None:
    device = FakeCoordinator()

    desc = SaveStateSwitchEntityDescription(
        key="use_cloud_api",
        translation_key="use_cloud_api",
        icon="mdi:cloud",
        icon_off="mdi:cloud-off",
    )

    entity = SaveStateSwitchEntity(cast(Any, device), desc)
    entity.hass = hass
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await entity.async_turn_off()
    assert device.set_calls[-1] == ("$.local.use_cloud_api", False)
    assert entity.icon == "mdi:cloud-off"

    await entity.async_turn_on()
    assert device.set_calls[-1] == ("$.local.use_cloud_api", True)
    assert entity.icon == "mdi:cloud"

    assert entity.device_info == device.device_info

    device.get_data_map["$.local.use_cloud_api"] = True
    await entity.async_added_to_hass()
    assert entity.is_on is True


@pytest.mark.asyncio
async def test_save_state_switch_async_added_to_hass_sets_available_when_previously_unavailable(
    hass: Any,
) -> None:
    device = FakeCoordinator(last_update_success=False)

    desc = SaveStateSwitchEntityDescription(
        key="use_cloud_api",
        translation_key="use_cloud_api",
        icon="mdi:cloud",
        icon_off="mdi:cloud-off",
    )

    entity = SaveStateSwitchEntity(cast(Any, device), desc)
    entity.hass = hass
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    # Force the first restore/availability branch.
    entity._attr_available = False
    entity._attr_is_on = False

    await entity.async_added_to_hass()

    assert entity.available is True
    assert entity.icon == "mdi:cloud"


@pytest.mark.asyncio
async def test_save_state_switch_async_added_to_hass_uses_restored_state(
    hass: Any,
) -> None:
    device = FakeCoordinator(last_update_success=False)

    desc = SaveStateSwitchEntityDescription(
        key="use_cloud_api",
        translation_key="use_cloud_api",
        icon="mdi:cloud",
        icon_off="mdi:cloud-off",
    )

    entity = SaveStateSwitchEntity(cast(Any, device), desc)
    entity.hass = hass
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    async def _last() -> Any:
        return type("_State", (), {"state": "off"})()

    entity.async_get_last_state = _last  # type: ignore[assignment]

    await entity.async_added_to_hass()
    assert entity.is_on is False


@pytest.mark.asyncio
async def test_switch_async_setup_entry_cloud_linked_adds_save_state_and_common(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Ensure the cloud coordinator isinstance() doesn't short-circuit COMMON switches.
    monkeypatch.setattr(
        platform, "ReefBeatCloudCoordinator", type("_Cloud", (), {}), raising=True
    )

    entry = MockConfigEntry(domain=DOMAIN, title="cloud", data={}, unique_id="cloud")
    entry.add_to_hass(hass)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = _CloudLinkedDevice()

    added: list[list[Any]] = []

    def _add(new_entities: Any, update_before_add: bool = False) -> None:
        added.append(list(new_entities))

    await platform.async_setup_entry(hass, cast(Any, entry), _add)

    assert added
    entities = added[0]

    assert any(isinstance(e, SaveStateSwitchEntity) for e in entities)
    assert any(isinstance(e, ReefBeatSwitchEntity) for e in entities)


def test_cloud_shortcut_recomputes_active_switches_from_aquarium_data() -> None:
    device = _CloudDevice()
    device.get_data_map["$.sources[?(@.name=='/aquarium')].data"] = [
        {
            "uid": "a1",
            "properties": {
                "feeding_1": {"enabled": True},
                "feeding_2": {"enabled": True},
            },
        }
    ]

    ReefCloudSwitchEntity._recompute_active_switches(cast(Any, device))
    assert ReefCloudSwitchEntity._active_switches["a1"] == "feeding_1"


@pytest.mark.asyncio
async def test_cloud_shortcut_switch_turn_on_off_sends_http_and_fires_event_and_refreshes(
    hass: Any,
) -> None:
    device = _CloudDevice(hass=hass)

    aquarium = {"uid": "a1", "name": "A"}
    shortcut_path = "$.shortcut"
    device.get_data_map[shortcut_path] = {"name": "Feed", "enabled": True, "code": "c1"}

    desc = ReefCloudSwitchEntityDescription(
        key="feeding_1",
        translation_key="feeding_1",
        icon="mdi:play",
        icon_off="mdi:stop",
        shortcut=shortcut_path,
        value_name="$.unused",
        aquarium=aquarium,
    )

    ent = ReefCloudSwitchEntity(cast(Any, device), desc)
    ent.hass = hass
    ent.async_write_ha_state = lambda: None  # type: ignore[assignment]

    events: list[dict[str, Any]] = []

    def _on_event(event: Any) -> None:
        events.append(dict(event.data))

    ent.async_on_remove(hass.bus.async_listen("shortcut_state", _on_event))

    await ent.async_turn_on()
    await hass.async_block_till_done()

    assert device.my_api.sent[-1] == ("/aquarium/a1/shortcut/c1/start", "post")
    assert device.refreshed[-1] == "/aquarium"
    assert events[-1] == {"code": "c1", "state": "on"}

    await ent.async_turn_off()
    await hass.async_block_till_done()

    assert device.my_api.sent[-1] == ("/aquarium/a1/shortcut/c1/stop", "post")
    assert device.refreshed[-1] == "/aquarium"
    assert events[-1] == {"code": "c1", "state": "off"}


def test_cloud_switch_compute_is_on_returns_false_when_not_present() -> None:
    """Couvre _compute_is_on() : ligne 1007 (_present == False)."""
    from custom_components.redsea.switch import (
        ReefCloudSwitchEntity,
        ReefCloudSwitchEntityDescription,
    )

    device = _FakeSwitchCoordinator()
    aquarium = {"uid": "a1", "name": "Tank"}
    shortcut_path = "$.shortcut"
    # Pas de shortcut dans get_data_map → _present sera False
    device.get_data_map[shortcut_path] = None

    desc = ReefCloudSwitchEntityDescription(
        key="feeding_1",
        translation_key="feeding_1",
        icon="mdi:play",
        icon_off="mdi:stop",
        shortcut=shortcut_path,
        value_name="$.shortcut.enabled",
        aquarium=aquarium,
    )

    entity = ReefCloudSwitchEntity(cast(Any, device), desc)

    # _present est False car shortcut est None
    assert entity._present is False
    assert entity._compute_is_on() is False


def test_cloud_switch_compute_is_on_returns_false_on_key_error() -> None:
    """Couvre _compute_is_on() : lignes 1011-1013 (KeyError)."""
    from custom_components.redsea.switch import (
        ReefCloudSwitchEntity,
        ReefCloudSwitchEntityDescription,
    )

    device = _FakeSwitchCoordinator()
    aquarium = {"uid": "a1", "name": "Tank"}
    shortcut_path = "$.shortcut"
    device.get_data_map[shortcut_path] = {"name": "Feed", "enabled": True, "code": "c1"}

    desc = ReefCloudSwitchEntityDescription(
        key="feeding_1",
        translation_key="feeding_1",
        icon="mdi:play",
        icon_off="mdi:stop",
        shortcut=shortcut_path,
        value_name="$.shortcut.enabled",
        aquarium=aquarium,
    )

    entity = ReefCloudSwitchEntity(cast(Any, device), desc)
    assert entity._present is True

    # Faire lever un KeyError lors de get_data
    device.get_data_map.clear()

    # Simuler KeyError en remplaçant get_data
    def _raise_key_error(name: str, is_None_possible: bool = False) -> Any:  # noqa: N803
        raise KeyError("shortcut deleted")

    device.get_data = _raise_key_error  # type: ignore[method-assign]

    assert entity._compute_is_on() is False


def test_cloud_switch_compute_is_on_returns_false_on_value_error() -> None:
    """Couvre _compute_is_on() : lignes 1011-1013 (ValueError)."""
    from custom_components.redsea.switch import (
        ReefCloudSwitchEntity,
        ReefCloudSwitchEntityDescription,
    )

    device = _FakeSwitchCoordinator()
    aquarium = {"uid": "a1", "name": "Tank"}
    shortcut_path = "$.shortcut"
    device.get_data_map[shortcut_path] = {"name": "Feed", "enabled": True, "code": "c1"}

    desc = ReefCloudSwitchEntityDescription(
        key="feeding_1",
        translation_key="feeding_1",
        icon="mdi:play",
        icon_off="mdi:stop",
        shortcut=shortcut_path,
        value_name="$.shortcut.enabled",
        aquarium=aquarium,
    )

    entity = ReefCloudSwitchEntity(cast(Any, device), desc)
    assert entity._present is True

    def _raise_value_error(name: str, is_None_possible: bool = False) -> Any:  # noqa: N803
        raise ValueError("invalid data")

    device.get_data = _raise_value_error  # type: ignore[method-assign]

    assert entity._compute_is_on() is False


def test_cloud_switch_shortcut_icons() -> None:
    """Cover shortcuts icons"""
    from custom_components.redsea.switch import (
        ReefCloudSwitchEntity,
        ReefCloudSwitchEntityDescription,
    )

    device = _FakeSwitchCoordinator()
    aquarium = {"uid": "a1", "name": "Tank"}
    shortcut_path = "$.shortcut"
    device.get_data_map[shortcut_path] = {
        "name": "Feed",
        "enabled": True,
        "code": "c1",
        "icon": "personnal",
        "type": "test",
    }

    desc = ReefCloudSwitchEntityDescription(
        key="feeding_1",
        translation_key="feeding_1",
        icon="mdi:play",
        icon_off="mdi:stop",
        shortcut=shortcut_path,
        value_name="$.shortcut.enabled",
        aquarium=aquarium,
    )

    entity = ReefCloudSwitchEntity(cast(Any, device), desc)
    assert entity._present is True

    assert entity.icon == "redsea:personnal"

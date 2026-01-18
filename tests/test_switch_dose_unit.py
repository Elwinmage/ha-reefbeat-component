from __future__ import annotations

from typing import Any, cast

import pytest
from homeassistant.helpers.device_registry import DeviceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.switch as platform
from custom_components.redsea.const import DOMAIN
from custom_components.redsea.switch import (
    ReefBeatSwitchEntity,
    ReefDoseSwitchEntity,
    ReefDoseSwitchEntityDescription,
)
from tests._switch_test_fakes import FakeCoordinator, FakeDoseCoordinator


class _DoseDevice(FakeDoseCoordinator):
    heads_nb: int = 1


@pytest.mark.asyncio
async def test_dose_switch_device_info_adds_head_suffix() -> None:
    device = FakeCoordinator(title="Dose")
    desc = ReefDoseSwitchEntityDescription(
        key="dose",
        translation_key="dose",
        value_name="$.local.x",
        icon="mdi:on",
        head=2,
    )

    entity = ReefDoseSwitchEntity(cast(Any, device), desc)
    info = entity.device_info

    assert info.get("name") == "Dose head 2"
    identifiers = cast(set[tuple[str, str]], info.get("identifiers"))
    assert ("redsea", "SERIAL_head_2") in identifiers


@pytest.mark.asyncio
async def test_dose_switch_device_info_head_zero_returns_base() -> None:
    device = FakeCoordinator(title="Dose")
    desc = ReefDoseSwitchEntityDescription(
        key="dose",
        translation_key="dose",
        value_name="$.local.x",
        icon="mdi:on",
        head=0,
    )
    entity = ReefDoseSwitchEntity(cast(Any, device), desc)
    assert entity.device_info == device.device_info


@pytest.mark.asyncio
async def test_dose_switch_device_info_copies_fields_and_via_device() -> None:
    base = DeviceInfo(
        identifiers={("redsea", "SERIAL")},
        name="Dose",
        manufacturer="Red Sea",
        model="X",
        hw_version=None,
        via_device=("redsea", "PARENT"),
    )
    device = FakeCoordinator(title="Dose", device_info=base)

    # Force a non-string field via a dict cast (TypedDict allows it at runtime).
    device.device_info = cast(DeviceInfo, {**dict(base), "model": 123})

    desc = ReefDoseSwitchEntityDescription(
        key="dose",
        translation_key="dose",
        value_name="$.local.x",
        icon="mdi:on",
        head=1,
    )

    entity = ReefDoseSwitchEntity(cast(Any, device), desc)
    info = entity.device_info

    assert info.get("manufacturer") == "Red Sea"
    assert "model" not in info
    assert info.get("hw_version") is None
    assert info.get("via_device") == ("redsea", "PARENT")


@pytest.mark.asyncio
async def test_dose_switch_notify_and_pushes_head(hass: Any) -> None:
    device = FakeDoseCoordinator()
    device.hass = hass

    events: list[str] = []

    def _on_event(evt: Any) -> None:
        events.append(cast(str, evt.event_type))

    hass.bus.async_listen("event.name", _on_event)

    desc = ReefDoseSwitchEntityDescription(
        key="dose",
        translation_key="dose",
        value_name="event.name",
        icon="mdi:on",
        head=2,
        notify=True,
    )

    entity = ReefDoseSwitchEntity(cast(Any, device), desc)
    entity.hass = hass
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await entity.async_turn_on()
    await hass.async_block_till_done()

    assert events == ["event.name"]
    assert device.head_pushed == [2]
    assert device.refreshed == ["/head/2/settings"]


@pytest.mark.asyncio
async def test_dose_switch_turn_off_notify_and_pushes_head(hass: Any) -> None:
    device = FakeDoseCoordinator()
    device.hass = hass

    events: list[str] = []

    def _on_event(evt: Any) -> None:
        events.append(cast(str, evt.event_type))

    hass.bus.async_listen("event.name", _on_event)

    desc = ReefDoseSwitchEntityDescription(
        key="dose",
        translation_key="dose",
        value_name="event.name",
        icon="mdi:on",
        head=1,
        notify=True,
    )

    entity = ReefDoseSwitchEntity(cast(Any, device), desc)
    entity.hass = hass
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await entity.async_turn_off()
    await hass.async_block_till_done()

    assert events == ["event.name"]
    assert device.head_pushed == [1]
    assert device.refreshed == ["/head/1/settings"]


@pytest.mark.asyncio
async def test_switch_async_setup_entry_dose_adds_dose_and_common(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(platform, "ReefDoseCoordinator", _DoseDevice, raising=True)

    # Ensure the cloud coordinator isinstance() doesn't short-circuit COMMON switches.
    monkeypatch.setattr(
        platform, "ReefBeatCloudCoordinator", type("_Cloud", (), {}), raising=True
    )

    entry = MockConfigEntry(domain=DOMAIN, title="dose", data={}, unique_id="dose")
    entry.add_to_hass(hass)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = _DoseDevice()

    added: list[list[Any]] = []

    def _add(new_entities: Any, update_before_add: bool = False) -> None:
        added.append(list(new_entities))

    await platform.async_setup_entry(hass, cast(Any, entry), _add)

    assert added
    entities = added[0]

    assert any(isinstance(e, ReefDoseSwitchEntity) for e in entities)
    assert any(isinstance(e, ReefBeatSwitchEntity) for e in entities)

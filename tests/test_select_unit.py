from __future__ import annotations

from typing import Any, cast

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from tests._select_test_fakes import FakeCoordinator


@pytest.mark.asyncio
async def test_extract_source_from_value_name_branches() -> None:
    from custom_components.redsea.select import ReefBeatSelectEntity

    assert ReefBeatSelectEntity._restore_value("abc") == "abc"

    assert ReefBeatSelectEntity._extract_source_from_value_name("$.x") is None

    # Marker present but missing closing quote
    assert (
        ReefBeatSelectEntity._extract_source_from_value_name(
            "$.sources[?(@.name=='/pump/settings)].data.foo"
        )
        is None
    )

    assert (
        ReefBeatSelectEntity._extract_source_from_value_name(
            "$.sources[?(@.name=='/pump/settings')].data.foo"
        )
        == "/pump/settings"
    )


@pytest.mark.asyncio
async def test_select_async_select_option_without_source_does_not_push(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    from custom_components.redsea.select import (
        ReefBeatSelectEntity,
        ReefBeatSelectEntityDescription,
    )

    device = FakeCoordinator(hass=hass, _data={"$.x": "old"})
    desc = ReefBeatSelectEntityDescription(
        key="x", translation_key="x", value_name="$.x"
    )
    ent = ReefBeatSelectEntity(cast(Any, device), desc)

    wrote: list[str] = []

    def _write() -> None:
        wrote.append(cast(str, ent.current_option))

    monkeypatch.setattr(ent, "async_write_ha_state", _write, raising=True)

    await ent.async_select_option("new")

    assert device.get_data("$.x") == "new"
    assert device.pushed == []
    assert device.refreshed == 0
    assert wrote == ["new"]


@pytest.mark.asyncio
async def test_select_async_select_option_with_source_pushes_and_refreshes(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    from custom_components.redsea.select import (
        ReefBeatSelectEntity,
        ReefBeatSelectEntityDescription,
    )

    value_name = "$.sources[?(@.name=='/pump/settings')].data.foo"
    device = FakeCoordinator(hass=hass, _data={value_name: "old"})
    desc = ReefBeatSelectEntityDescription(
        key="foo",
        translation_key="foo",
        value_name=value_name,
        method="post",
        options=["a"],
    )
    ent = ReefBeatSelectEntity(cast(Any, device), desc)

    monkeypatch.setattr(ent, "async_write_ha_state", lambda: None, raising=True)

    await ent.async_select_option("a")

    assert device.pushed == [{"source": "/pump/settings", "method": "post"}]
    assert device.refreshed == 1


@pytest.mark.asyncio
async def test_select_async_added_to_hass_sets_attr_available_true(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    from custom_components.redsea.entity import ReefBeatRestoreEntity
    from custom_components.redsea.select import (
        ReefBeatSelectEntity,
        ReefBeatSelectEntityDescription,
    )

    async def _noop_added_to_hass(self: Any) -> None:
        return None

    monkeypatch.setattr(
        ReefBeatRestoreEntity, "async_added_to_hass", _noop_added_to_hass
    )

    device = FakeCoordinator(hass=hass, last_update_success=False, _data={"$.x": "abc"})
    desc = ReefBeatSelectEntityDescription(
        key="x", translation_key="x", value_name="$.x"
    )
    ent = ReefBeatSelectEntity(cast(Any, device), desc)

    # Force the "not available" branch in async_added_to_hass.
    ent._attr_available = False
    assert ent._attr_current_option is not None

    await ent.async_added_to_hass()

    assert ent._attr_available is True


@pytest.mark.asyncio
async def test_select_async_added_to_hass_primes_from_cache_and_calls_handle_update(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    from custom_components.redsea.entity import ReefBeatRestoreEntity
    from custom_components.redsea.select import (
        ReefBeatSelectEntity,
        ReefBeatSelectEntityDescription,
    )

    async def _noop_added_to_hass(self: Any) -> None:
        return None

    monkeypatch.setattr(
        ReefBeatRestoreEntity, "async_added_to_hass", _noop_added_to_hass
    )

    handled: list[bool] = []

    def _noop_handle_update(self: Any) -> None:
        handled.append(True)

    monkeypatch.setattr(
        CoordinatorEntity,
        "_handle_coordinator_update",
        _noop_handle_update,
        raising=True,
    )

    device = FakeCoordinator(hass=hass, last_update_success=True, _data={"$.x": "old"})
    desc = ReefBeatSelectEntityDescription(
        key="x", translation_key="x", value_name="$.x"
    )
    ent = ReefBeatSelectEntity(cast(Any, device), desc)

    device.set_data("$.x", "updated")

    await ent.async_added_to_hass()

    assert ent.current_option == "updated"
    assert handled == [True]


def test_select_device_info_property_returns_coordinator_device_info(
    hass: HomeAssistant,
) -> None:
    from custom_components.redsea.select import (
        ReefBeatSelectEntity,
        ReefBeatSelectEntityDescription,
    )

    base_di = {"identifiers": {("redsea", "X")}, "name": "X"}
    device = FakeCoordinator(
        hass=hass, serial="X", device_info=base_di, _data={"$.x": "a"}
    )
    desc = ReefBeatSelectEntityDescription(
        key="x", translation_key="x", value_name="$.x"
    )

    ent = ReefBeatSelectEntity(cast(Any, device), desc)
    assert ent.device_info == base_di


def test_select_handle_coordinator_update_updates_value_and_calls_super(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    from custom_components.redsea.select import (
        ReefBeatSelectEntity,
        ReefBeatSelectEntityDescription,
    )

    handled: list[bool] = []

    def _noop_handle_update(self: Any) -> None:
        handled.append(True)

    monkeypatch.setattr(
        CoordinatorEntity,
        "_handle_coordinator_update",
        _noop_handle_update,
        raising=True,
    )

    device = FakeCoordinator(hass=hass, _data={"$.x": "old"})
    desc = ReefBeatSelectEntityDescription(
        key="x", translation_key="x", value_name="$.x"
    )
    ent = ReefBeatSelectEntity(cast(Any, device), desc)

    device.set_data("$.x", "new")
    ent._handle_coordinator_update()

    assert ent.current_option == "new"
    assert handled == [True]

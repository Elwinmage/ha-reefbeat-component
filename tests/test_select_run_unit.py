from __future__ import annotations

from typing import Any, cast

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.select as platform
from custom_components.redsea.const import DOMAIN
from tests._select_test_fakes import FakeCoordinator, FakeRunCoordinator


@pytest.mark.asyncio
async def test_async_setup_entry_run_adds_skimmer_model_select_for_matching_pump(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        platform, "ReefRunCoordinator", FakeRunCoordinator, raising=True
    )

    entry = MockConfigEntry(domain=DOMAIN, title="run", data={}, unique_id="run")
    entry.add_to_hass(hass)

    device = FakeRunCoordinator(
        hass=hass,
        serial="RUN",
        _data={
            "$.sources[?(@.name=='/pump/settings')].data.pump_1.type": "skimmer",
            "$.sources[?(@.name=='/pump/settings')].data.pump_2.type": "return",
        },
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[list[Any]] = []

    def _add(new_entities: Any, update_before_add: bool = False) -> None:
        added.append(list(new_entities))

    await platform.async_setup_entry(hass, cast(Any, entry), _add)

    assert added
    assert len(added[0]) == 1


def test_reefrun_select_device_info_extends_identifiers_and_name(
    hass: HomeAssistant,
) -> None:
    from custom_components.redsea.select import (
        ReefRunSelectEntity,
        ReefRunSelectEntityDescription,
    )

    base_di: dict[str, Any] = {
        "identifiers": {("redsea", "BASE")},
        "name": "ReefRun",
    }
    device = FakeCoordinator(
        hass=hass, serial="BASE", title="ReefRun", device_info=base_di
    )

    desc = ReefRunSelectEntityDescription(
        key="model",
        translation_key="model",
        value_name="$.sources[?(@.name=='/pump/settings')].data.pump_2.model",
        pump=2,
    )
    ent = ReefRunSelectEntity(cast(Any, device), desc)

    di = cast(dict[str, Any], ent.device_info)
    assert di["name"].endswith("_pump_2")

    identifiers = di.get("identifiers")
    assert identifiers
    assert ("redsea", "BASE", "pump_2") in identifiers


@pytest.mark.asyncio
async def test_reefrun_select_async_select_option_pushes_pump_scoped_settings(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    from custom_components.redsea.select import (
        ReefRunSelectEntity,
        ReefRunSelectEntityDescription,
    )

    device = FakeCoordinator(hass=hass, _data={"$.v": "old"})
    desc = ReefRunSelectEntityDescription(
        key="model",
        translation_key="model",
        value_name="$.v",
        pump=2,
    )
    ent = ReefRunSelectEntity(cast(Any, device), desc)

    monkeypatch.setattr(ent, "async_write_ha_state", lambda: None, raising=True)

    await ent.async_select_option("new")

    assert device.get_data("$.v") == "new"
    assert device.pushed == [{"source": "/pump/settings", "method": "put", "pump": 2}]

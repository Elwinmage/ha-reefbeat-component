from __future__ import annotations

from typing import Any, cast

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.select as platform
from custom_components.redsea.const import DOMAIN
from tests._select_test_fakes import FakeDoseCoordinator


@pytest.mark.asyncio
async def test_async_setup_entry_dose_adds_per_head_supplement_selects(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        platform, "ReefDoseCoordinator", FakeDoseCoordinator, raising=True
    )

    entry = MockConfigEntry(domain=DOMAIN, title="dose", data={}, unique_id="dose")
    entry.add_to_hass(hass)

    # Known supplement UID so translate(uid -> fullname) succeeds in ReefDoseSelectEntity.__init__
    uid = "0e63ba83-3ec4-445e-a3dd-7f2dbdc7f964"
    data = {
        "$.local.head.1.new_supplement": uid,
        "$.local.head.2.new_supplement": uid,
    }
    device = FakeDoseCoordinator(hass=hass, serial="DOSE", _data=data)
    device.heads_nb = 2
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[list[Any]] = []

    def _add(new_entities: Any, update_before_add: bool = False) -> None:
        added.append(list(new_entities))

    await platform.async_setup_entry(hass, cast(Any, entry), _add)

    assert added
    assert len(added[0]) == 2


def test_reefdose_select_device_info_head_zero_returns_base(
    hass: HomeAssistant,
) -> None:
    from custom_components.redsea.select import (
        ReefDoseSelectEntity,
        ReefDoseSelectEntityDescription,
    )

    uid = "0e63ba83-3ec4-445e-a3dd-7f2dbdc7f964"

    base_di: dict[str, Any] = {
        "identifiers": {("redsea", "BASE")},
        "manufacturer": "Red Sea",
    }
    device = FakeDoseCoordinator(
        hass=hass,
        serial="BASE",
        title="Dose",
        device_info=base_di,
        _data={"$.sup": uid},
    )

    desc = ReefDoseSelectEntityDescription(
        key="sup",
        translation_key="supplements",
        value_name="$.sup",
        head=0,
    )
    ent = ReefDoseSelectEntity(cast(Any, device), desc)

    assert ent.device_info == base_di


def test_reefdose_select_device_info_builds_head_device_and_copies_fields(
    hass: HomeAssistant,
) -> None:
    from custom_components.redsea.select import (
        ReefDoseSelectEntity,
        ReefDoseSelectEntityDescription,
    )

    uid = "0e63ba83-3ec4-445e-a3dd-7f2dbdc7f964"

    base_di: dict[str, Any] = {
        "identifiers": {("redsea", "IDENT")},
        "manufacturer": "Red Sea",
        "model": 123,  # should be excluded (non-str)
        "hw_version": None,  # allowed
        "via_device": ("redsea", "PARENT"),
    }
    device = FakeDoseCoordinator(
        hass=hass,
        serial="IDENT",
        title="Dose",
        device_info=base_di,
        _data={"$.sup": uid},
    )

    desc = ReefDoseSelectEntityDescription(
        key="sup",
        translation_key="supplements",
        value_name="$.sup",
        head=1,
    )
    ent = ReefDoseSelectEntity(cast(Any, device), desc)

    di = cast(DeviceInfo, ent.device_info)
    assert ("redsea", "IDENT_head_1") in (di.get("identifiers") or set())
    assert di.get("name") == "Dose head 1"

    assert di.get("manufacturer") == "Red Sea"
    assert di.get("hw_version") is None
    assert di.get("via_device") == ("redsea", "PARENT")


@pytest.mark.asyncio
async def test_reefdose_select_async_select_option_other_fires_event_and_sets_value(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    from custom_components.redsea.select import (
        ReefDoseSelectEntity,
        ReefDoseSelectEntityDescription,
    )

    uid = "0e63ba83-3ec4-445e-a3dd-7f2dbdc7f964"
    device = FakeDoseCoordinator(hass=hass, _data={"$.sup": uid})
    desc = ReefDoseSelectEntityDescription(
        key="sup",
        translation_key="supplements",
        value_name="$.sup",
        head=1,
    )
    ent = ReefDoseSelectEntity(cast(Any, device), desc)

    fired: list[tuple[str, dict[str, Any]]] = []

    def _fire(
        _bus: Any, event_type: str, event_data: dict[str, Any] | None = None
    ) -> None:
        fired.append((event_type, event_data or {}))

    monkeypatch.setattr(type(hass.bus), "fire", _fire, raising=True)
    monkeypatch.setattr(ent, "async_write_ha_state", lambda: None, raising=True)


@pytest.mark.asyncio
async def test_reefdose_select_async_select_option_known_supplement_translates_to_uid(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    from custom_components.redsea.select import (
        ReefDoseSelectEntity,
        ReefDoseSelectEntityDescription,
    )

    uid = "0e63ba83-3ec4-445e-a3dd-7f2dbdc7f964"
    fullname = "Red Sea - Calcium (Powder)"

    device = FakeDoseCoordinator(hass=hass, _data={"$.sup": uid})
    desc = ReefDoseSelectEntityDescription(
        key="sup",
        translation_key="supplements",
        value_name="$.sup",
        head=1,
    )
    ent = ReefDoseSelectEntity(cast(Any, device), desc)

    fired: list[tuple[str, dict[str, Any]]] = []

    def _fire(
        _bus: Any, event_type: str, event_data: dict[str, Any] | None = None
    ) -> None:
        fired.append((event_type, event_data or {}))

    monkeypatch.setattr(type(hass.bus), "fire", _fire, raising=True)
    monkeypatch.setattr(ent, "async_write_ha_state", lambda: None, raising=True)

    await ent.async_select_option(fullname)

    assert device.get_data("$.sup") == uid
    assert fired == [("$.sup", {"other": False})]


def test_dose_select_handle_coordinator_update_other_branch(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    from custom_components.redsea.select import (
        ReefDoseSelectEntity,
        ReefDoseSelectEntityDescription,
    )

    def _translate(val: Any, *_a: Any, **_k: Any) -> Any:
        return "OTHER" if val == "other" else val

    monkeypatch.setattr(platform, "translate", _translate, raising=True)

    device = FakeDoseCoordinator(
        hass=hass, last_update_success=False, _data={"$.supp": "uid"}
    )
    desc = ReefDoseSelectEntityDescription(
        key="supp",
        translation_key="supp",
        value_name="$.supp",
        head=1,
    )
    entity = ReefDoseSelectEntity(cast(Any, device), desc)
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    device.set_data("$.supp", "other")
    entity._handle_coordinator_update()

    assert entity.current_option == "other"

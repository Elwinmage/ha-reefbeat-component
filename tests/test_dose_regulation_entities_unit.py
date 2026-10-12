"""Tests of the dose regulation entities, service and doser calls."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry
from test_dose_regulation_unit import (
    DD,
    SUPPLEMENT,
    FakeDoser,
    _regulator,
    put_brine,
)

from custom_components.redsea import dose_regulation as R
from custom_components.redsea import dose_regulation_entities as E
from custom_components.redsea.const import DOMAIN
from custom_components.redsea.coordinator import ReefDoseCoordinator
from custom_components.redsea.reefbeat.dose import ReefDoseAPI

R_LOG = f"$.sources[?(@.name=='{R.DAILY_LOG}')].data"


async def _entities(
    hass: HomeAssistant,
) -> tuple[dict[str, Any], R.DoseRegulator, FakeDoser]:
    regulator, doser, _clock = await _regulator(hass, (1,))
    doser.regulation = regulator  # type: ignore[attr-defined]
    found: dict[str, Any] = {}
    for platform in ("select", "number", "button", "sensor", "binary_sensor"):
        for entity in E.regulation_entities(doser, platform):
            entity.hass = hass
            entity.entity_id = f"{platform}.{entity.translation_key}"
            entity.async_write_ha_state = MagicMock()
            found[entity.translation_key] = entity
    return found, regulator, doser


async def test_builder(hass: HomeAssistant) -> None:
    assert E.regulation_entities(object(), "sensor") == []
    found, _, _ = await _entities(hass)
    assert len(found) == 3 + 11 + 3 + 7 + 1
    assert E._head_entities(FakeDoser(), 1, "light") == []
    status = found["regulation_status"]
    assert status.unique_id == "SER_regulation_status_head_1"
    assert status.device_info["name"] == "head 1"
    assert status.options == R.STATUSES


async def test_listener(hass: HomeAssistant) -> None:
    found, regulator, _doser = await _entities(hass)
    entity = found["regulation_mode"]
    await entity.async_added_to_hass()
    regulator.store.notify()
    entity.async_write_ha_state.assert_called_once()
    await entity.async_will_remove_from_hass()
    await entity.async_will_remove_from_hass()
    regulator.store.notify()
    entity.async_write_ha_state.assert_called_once()


async def test_selects(hass: HomeAssistant) -> None:
    found, regulator, doser = await _entities(hass)
    mode = found["regulation_mode"]
    assert mode.current_option == "off" and mode.options == ["off", "assisted"]
    assert mode.entity_category is None
    with pytest.raises(HomeAssistantError):
        await mode.async_select_option("brine")
    put_brine(doser)
    assert mode.options == ["off", "brine"]
    await mode.async_select_option("brine")
    assert regulator.head_state(1).settings.parameter == "salinity"
    parameter = found["regulation_parameter"]
    assert parameter.current_option == "salinity"
    with pytest.raises(HomeAssistantError):
        await parameter.async_select_option("kh")
    # The brine taken off the head: its mode stays shown until changed
    doser.data[SUPPLEMENT(1)] = "null"
    assert mode.options == ["off", "assisted", "brine"]
    await mode.async_select_option("assisted")
    await parameter.async_select_option("mg")
    assert regulator.head_state(1).settings.target == 1350.0
    doser.data["$.sources[?(@.name=='/dashboard')].data.bundled_heads"] = True
    await mode.async_select_option("off")
    with pytest.raises(HomeAssistantError):
        await mode.async_select_option("brine")
    # Bundled: head 1 is regulated on the calcium
    await mode.async_select_option("assisted")
    assert regulator.head_state(1).settings.parameter == "ca"


async def test_salinity_source_select(hass: HomeAssistant) -> None:
    found, regulator, _doser = await _entities(hass)
    hass.states.async_set("sensor.ppt", "35", {"unit_of_measurement": "ppt"})
    hass.states.async_set("sensor.ec", "53", {"unit_of_measurement": "mS/cm"})
    hass.states.async_set("sensor.temp", "25", {"unit_of_measurement": "°C"})
    source = found["brine_salinity_source"]
    assert source.options == [E.NO_SOURCE, "sensor.ec", "sensor.ppt"]
    assert source.current_option == E.NO_SOURCE
    await source.async_select_option("sensor.ppt")
    assert regulator.head_state(1).settings.salinity_source == "sensor.ppt"
    # A sensor gone stays offered while chosen
    hass.states.async_remove("sensor.ppt")
    assert source.options == [E.NO_SOURCE, "sensor.ec", "sensor.ppt"]
    assert source.current_option == "sensor.ppt"
    await source.async_select_option(E.NO_SOURCE)
    assert regulator.head_state(1).settings.salinity_source == ""


async def test_numbers(hass: HomeAssistant) -> None:
    found, regulator, _doser = await _entities(hass)
    target = found["regulation_target"]
    assert target.native_value == 8.0
    assert target.native_unit_of_measurement == "dKH"
    assert target.native_step == 0.01
    await target.async_set_native_value(8.4)
    assert regulator.head_state(1).settings.target == 8.4
    with pytest.raises(HomeAssistantError):
        await target.async_set_native_value(5000)
    assert found["regulation_potency"].native_unit_of_measurement == "dKH/mL/100L"
    assert found["regulation_measurement"].entity_category is None
    concentration = found["brine_concentration"]
    assert concentration.native_unit_of_measurement == "g/L"
    assert (concentration.native_min_value, concentration.native_max_value) == (
        10.0,
        350.0,
    )
    volume = found["regulation_tank_volume"]
    assert volume.extra_state_attributes == {
        "reef_role": "regulation_tank_volume",
        "volume_used": None,
        "volume_source": None,
    }
    await volume.async_set_native_value(150)
    assert volume.extra_state_attributes["volume_source"] == "user"


async def test_buttons(hass: HomeAssistant) -> None:
    found, regulator, doser = await _entities(hass)
    doser.data[DD(1)] = 20
    await regulator.async_set(1, "mode", "assisted")
    await regulator.async_set(1, "potency", 0.1)
    await regulator.async_set(1, "tank_volume", 100)
    await regulator.async_set(1, "target", 8.4)
    await regulator.async_set(1, "measurement", 8.0)
    await found["regulation_record"].async_press()
    assert regulator.head_state(1).proposal is not None
    await found["regulation_dismiss"].async_press()
    assert regulator.head_state(1).proposal is None
    await found["regulation_record"].async_press()
    await found["regulation_apply"].async_press()
    assert doser.pushed == [1]
    # The brine needs a salinity: a plain test of another mode fails cleanly
    regulator.head_state(1).settings.parameter = "zinc"
    with pytest.raises(HomeAssistantError):
        await found["regulation_record"].async_press()


async def test_sensors_assisted(hass: HomeAssistant) -> None:
    found, regulator, doser = await _entities(hass)
    status = found["regulation_status"]
    assert status.native_value == "off"
    assert status.extra_state_attributes == {
        "reef_role": "regulation_status",
        "mode": "off",
        "parameter": "kh",
        "unit": "dKH",
        "target": 8.0,
    }
    assert found["regulation_proposed_dose"].native_value is None
    assert found["regulation_consumption"].native_value is None
    assert found["regulation_last_measurement"].native_value is None
    history = found["regulation_last_measurement"].extra_state_attributes
    assert history["measurements"] == [] and history["measured_at"] is None

    doser.data[DD(1)] = 20
    await regulator.async_set(1, "mode", "assisted")
    await regulator.async_set(1, "potency", 0.1)
    await regulator.async_set(1, "tank_volume", 100)
    await regulator.async_set(1, "target", 8.4)
    regulator.head_state(1).daily = {"2026-09-30": 20.0}
    await regulator.async_record(1, 8.0)
    proposed = found["regulation_proposed_dose"]
    assert proposed.native_value == pytest.approx(21.3)
    assert proposed.native_unit_of_measurement == "mL"
    attrs = proposed.extra_state_attributes
    assert attrs["current_dose"] == 20.0 and "dose" not in attrs
    assert found["regulation_consumption"].native_unit_of_measurement == "dKH/d"
    last = found["regulation_last_measurement"]
    assert last.native_value == 8.0 and last.native_unit_of_measurement == "dKH"
    assert last.extra_state_attributes["daily_volumes"] == {"2026-09-30": 20.0}
    assert found["regulation_tank_volume_used"].native_value == 100.0
    assert found["regulation_tank_volume_used"].extra_state_attributes == {
        "reef_role": "regulation_tank_volume_used",
        "source": "user",
    }
    regulator.head_state(1).details["last_proposal"]["consumption"] = 2.1
    assert found["regulation_consumption"].native_value == 2.1


async def test_sensors_brine_and_alarm(hass: HomeAssistant) -> None:
    found, regulator, doser = await _entities(hass)
    put_brine(doser)
    hass.states.async_set("sensor.ppt", "34.5", {"unit_of_measurement": "ppt"})
    await regulator.async_set(1, "mode", "brine")
    await regulator.async_set(1, "salinity_source", "sensor.ppt")
    await regulator.async_set(1, "tank_volume", 200)
    # Too few samples for an average yet: the current reading
    hass.states.async_set("sensor.ppt", "34.6", {"unit_of_measurement": "ppt"})
    assert found["brine_salinity"].native_value == 34.6
    assert found["brine_daily_volume"].native_value is None
    assert found["brine_salinity"].extra_state_attributes == {
        "reef_role": "brine_salinity",
        "current": 34.6,
        "samples": 1,
        "averaged": False,
    }
    hass.states.async_set("sensor.ppt", "34.5", {"unit_of_measurement": "ppt"})
    for _ in range(R.MIN_SAMPLES - 1):
        regulator.now.advance(minutes=10)  # type: ignore[attr-defined]
        await regulator._async_tick()
    assert found["brine_salinity"].native_value == 34.5
    assert found["brine_salinity"].extra_state_attributes["averaged"] is True
    # 200 L, 0.5 ppt short, default 200 g/L brine
    assert found["brine_daily_volume"].native_value == pytest.approx(170.8)
    assert found["regulation_consumption"].native_value is None
    assert found["regulation_consumption"].native_unit_of_measurement == "ppt/d"
    regulator.head_state(1).day_sums = {
        "2026-09-29": (350.0, 10),
        "2026-09-30": (350.5, 10),
    }
    # 102.5 mL of 200 g/L brine in 200 L: +0.1 ppt, rose by 0.05: 0.05 lost
    regulator.head_state(1).daily = {"2026-09-30": 102.5}
    assert found["regulation_consumption"].native_value == pytest.approx(0.05)
    alarm = found["regulation_alarm"]
    assert alarm.is_on is False
    await regulator.async_record(1, 34.6)
    await regulator.async_record(1, 37.0)
    assert alarm.is_on is True
    assert alarm.extra_state_attributes == {
        "reef_role": "regulation_alarm",
        "reason": "recalibration_required",
    }
    hass.states.async_set("sensor.ppt", "unavailable")
    assert found["brine_salinity"].extra_state_attributes["current"] is None
    # Neither an average nor a reading
    regulator.head_state(1).samples = []
    assert found["brine_salinity"].native_value is None
    last = found["regulation_last_measurement"].extra_state_attributes
    assert last["last_check"] is not None


# =============================================================================
# Doser calls
# =============================================================================


async def test_api_manual_dose(monkeypatch: pytest.MonkeyPatch) -> None:
    api = ReefDoseAPI("192.0.2.1", False, MagicMock(), 2)
    send = AsyncMock(return_value={"ok": True})
    monkeypatch.setattr(api, "_http_send", send)
    assert await api.manual_dose(2, 3.5) is True
    send.assert_awaited_once_with(
        "http://192.0.2.1/head/2/manual",
        {"manual_dose_scheduled": True, "volume": 3.5},
        method="post",
    )
    send.return_value = None
    assert await api.manual_dose(2, 3.5) is False


async def test_coordinator_manual_dose() -> None:
    coordinator = object.__new__(ReefDoseCoordinator)
    coordinator.my_api = MagicMock()
    coordinator.my_api.manual_dose = AsyncMock(return_value=True)
    coordinator.async_request_refresh = AsyncMock()  # type: ignore[method-assign]
    assert await coordinator.manual_dose(1, 2.0) is True
    coordinator.async_request_refresh.assert_awaited_once_with(wait=0)
    coordinator.my_api.manual_dose.return_value = False
    assert await coordinator.manual_dose(1, 2.0) is False
    coordinator.async_request_refresh.assert_awaited_once()


# =============================================================================
# Integration: setup and service
# =============================================================================


async def test_setup_and_record_measurement_service(
    hass: HomeAssistant, local_dose_config_entry: MockConfigEntry
) -> None:
    local_dose_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(local_dose_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][local_dose_config_entry.entry_id]
    regulator = coordinator.regulation
    assert isinstance(regulator, R.DoseRegulator)
    # The daily log was read (its 2025 days are older than the history kept)
    assert isinstance(coordinator.get_data(R_LOG, True), dict)

    ent_reg = er.async_get(hass)
    mode_id = ent_reg.async_get_entity_id(
        "select", DOMAIN, f"{coordinator.serial}_regulation_mode_head_1"
    )
    assert mode_id is not None
    mode_state = hass.states.get(mode_id)
    assert mode_state is not None and mode_state.state == "off"

    dev_reg = dr.async_get(hass)
    entry_id = local_dose_config_entry.entry_id
    head = dev_reg.async_get_device_by_identifier(
        (DOMAIN, f"{coordinator.model_id}_head_1"), entry_id
    )
    assert head is not None

    async def call(data: dict[str, Any]) -> Any:
        return await hass.services.async_call(
            DOMAIN, "record_measurement", data, blocking=True, return_response=True
        )

    response = await call({"device_id": head.id, "value": 8.1, "parameter": "kh"})
    assert response == {"ok": True, "recorded": True, "suspect": False}
    response = await call(
        {
            "device_id": head.id,
            "value": 8.2,
            "measured_at": "2026-10-01T09:00:00+02:00",
        }
    )
    assert response["ok"] is True
    assert regulator.head_state(1).measurements[0].value == 8.2
    assert regulator.head_state(1).measurements[0].at == datetime(
        2026, 10, 1, 7, tzinfo=UTC
    )
    # The datetime selector gives a local time without offset
    response = await call(
        {"device_id": head.id, "value": 8.3, "measured_at": "2026-09-30 08:00:00"}
    )
    assert response["ok"] is True
    first = regulator.head_state(1).measurements[0]
    assert first.value == 8.3
    assert first.at.utcoffset() == dt_util.now().utcoffset()
    assert await call(
        {"device_id": head.id, "value": 8.3, "measured_at": "yesterday"}
    ) == {"ok": False, "error": "invalid measured_at 'yesterday'"}
    response = await call({"device_id": head.id, "value": 8.1, "parameter": "zinc"})
    assert response == {"ok": False, "error": "unknown parameter 'zinc'"}
    assert await call({"device_id": "nope", "value": 1}) == {
        "ok": False,
        "error": "Not a ReefDose head",
    }
    parent = dev_reg.async_get_device_by_identifier(
        (DOMAIN, coordinator.model_id), entry_id
    )
    assert parent is not None
    assert (await call({"device_id": parent.id, "value": 1}))["ok"] is False

    # A doser without regulator
    coordinator.regulation = None
    assert await call({"device_id": head.id, "value": 1}) == {
        "ok": False,
        "error": "Regulation unavailable",
    }
    coordinator.regulation = regulator

    assert await hass.config_entries.async_unload(local_dose_config_entry.entry_id)
    await hass.async_block_till_done()
    assert not regulator._unsubs


async def test_dose_head_resolution(hass: HomeAssistant) -> None:
    from custom_components.redsea import _dose_head

    assert _dose_head(hass, None) is None
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    dev_reg = dr.async_get(hass)
    other = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={("other", "X_head_1")}
    )
    orphan = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "GONE_head_1")}
    )
    hass.data.setdefault(DOMAIN, {})["x"] = object()
    assert _dose_head(hass, other.id) is None
    assert _dose_head(hass, orphan.id) is None

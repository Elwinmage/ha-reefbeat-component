"""History of the doses of a ReefDose, its last dose sensors and the
redsea.get_doses action (poseidon)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.redsea.poseidon import const
from custom_components.redsea.poseidon.doses import DoseHistory, ended_at
from custom_components.redsea.poseidon.keystore import DeviceKeys, KeyStore
from custom_components.redsea.poseidon.manager import Poseidon, get_poseidon
from custom_components.redsea.poseidon.switch_entity import (
    PoseidonLastDoseSensor,
    poseidon_dose_sensors,
)
from tests._poseidon_fakes import HWID, SECRET
from tests.test_poseidon_dose_event_unit import LOG
from tests.test_poseidon_dose_event_unit import _coordinator as _dosing_sources
from tests.test_poseidon_entry_unit import _entry
from tests.test_poseidon_spy_unit import _poseidon

DOMAIN = "redsea"


def _dose(head: int, ended: datetime, volume: float = 1.0) -> dict[str, Any]:
    return {
        "head": head,
        "supplement": "KH",
        "brand": "Red Sea",
        "dose_type": "scheduled",
        "volume": volume,
        "started_at": (ended - timedelta(seconds=10)).isoformat(),
        "ended_at": ended.isoformat(),
        "duration_s": 10.0,
    }


NOW = datetime.now(UTC)


# -- history ---------------------------------------------------------------------------


async def test_history(hass: HomeAssistant) -> None:
    history = DoseHistory(hass)
    await history.async_load()
    history.add(HWID, _dose(2, NOW - timedelta(hours=2), 12.5))
    history.add(HWID, _dose(1, NOW - timedelta(hours=1), 6.9))
    # Out of order: kept in the order of the doses
    history.add(HWID, _dose(2, NOW - timedelta(hours=3), 11.0))
    history.add("other", _dose(2, NOW, 3.0))
    # No end: nothing to keep
    history.add(HWID, dict(_dose(1, NOW), ended_at=None))
    assert [d["volume"] for d in history.entries(HWID)] == [6.9, 12.5, 11.0]
    assert [d["volume"] for d in history.entries(HWID, head=2)] == [12.5, 11.0]
    assert "hwid" not in history.entries(HWID)[0]
    assert history.entries(HWID, head=2, limit=1)[0]["volume"] == 12.5
    assert len(history.entries(HWID, days=0.1)) == 2
    last = history.last(HWID, 2)
    assert last is not None and last["volume"] == 12.5
    assert history.last(HWID, 3) is None


async def test_history_retention(hass: HomeAssistant) -> None:
    history = DoseHistory(hass, days=2, max_entries=3)
    await history.async_load()
    history.add(HWID, _dose(1, NOW - timedelta(days=3)))
    assert history.entries(HWID) == []
    for hour in range(5):
        history.add(HWID, _dose(1, NOW - timedelta(hours=hour), float(hour)))
    assert [d["volume"] for d in history.entries(HWID)] == [0.0, 1.0, 2.0]


async def test_history_persisted(hass: HomeAssistant, hass_storage: Any) -> None:
    hass_storage["redsea_poseidon_doses"] = {
        "version": 1,
        "key": "redsea_poseidon_doses",
        "data": {
            "entries": [
                {"hwid": HWID, **_dose(2, NOW - timedelta(hours=1))},
                {"hwid": HWID, **_dose(2, NOW - timedelta(days=60))},
                {"hwid": 1, **_dose(2, NOW)},
                {"hwid": HWID, "ended_at": "junk"},
                {"hwid": HWID, "ended_at": "2026-10-30T10:00:00"},
                "junk",
            ]
        },
    }
    history = DoseHistory(hass)
    await history.async_load()
    await history.async_load()  # once only
    assert len(history.entries(HWID)) == 1
    # The old one was dropped: written back
    async_fire_time_changed(hass, datetime.now(UTC) + timedelta(seconds=60))
    await hass.async_block_till_done()
    assert len(hass_storage["redsea_poseidon_doses"]["data"]["entries"]) == 1


async def test_history_of_nothing(hass: HomeAssistant, hass_storage: Any) -> None:
    hass_storage["redsea_poseidon_doses"] = {
        "version": 1,
        "key": "redsea_poseidon_doses",
        "data": ["junk"],
    }
    history = DoseHistory(hass)
    await history.async_load()
    assert history.entries(HWID) == []
    assert ended_at({"ended_at": 1}) is None


# -- in the manager ----------------------------------------------------------------------


def _dosing(hass: HomeAssistant) -> tuple[Any, Any]:
    poseidon, coordinator = _poseidon(
        hass, {const.CONF_DEVICE_STRATEGIES: {HWID: const.STRATEGY_SPY}}
    )
    poseidon.keystore.devices[HWID].type = "reef-dosing"
    poseidon._apply_polling()
    cast(Any, coordinator.my_api).data["sources"] = _dosing_sources().my_api.data[
        "sources"
    ]
    return poseidon, coordinator


async def test_doses_are_kept(hass: HomeAssistant) -> None:
    poseidon, _ = _dosing(hass)
    poseidon._fire_dose(HWID, LOG)
    poseidon._fire_dose(HWID, LOG)  # twice: kept once
    last = poseidon.doses.last(HWID, 2)
    assert last is not None and last["duration_s"] == 19.0
    assert len(poseidon.doses.entries(HWID)) == 1


def _registry(hass: HomeAssistant) -> tuple[Any, Any]:
    owner = MockConfigEntry(domain="test", data={})
    owner.add_to_hass(hass)
    registry = dr.async_get(hass)
    doser = registry.async_get_or_create(
        config_entry_id=owner.entry_id,
        identifiers={(DOMAIN, HWID)},
        name="Doser",
        model="RSDOSE2",
    )
    head = registry.async_get_or_create(
        config_entry_id=owner.entry_id,
        identifiers={(DOMAIN, f"{HWID}_head_2")},
        name="Doser head 2",
    )
    return doser, head


async def test_head_devices(hass: HomeAssistant) -> None:
    poseidon, _ = _dosing(hass)
    assert poseidon.head_device_entry(HWID, 2) is None
    doser, head = _registry(hass)
    # Identifiers of another domain are skipped
    dr.async_get(hass).async_update_device(
        doser.id, new_identifiers={(DOMAIN, HWID), ("zz", "y"), ("aa", "x")}
    )
    found = poseidon.head_device_entry(HWID, 2)
    assert found is not None and found.id == head.id
    assert poseidon.head_device_entry(HWID, 1) is None
    assert poseidon.hwid_of_device(head.id) == (HWID, 2)
    assert poseidon.hwid_of_device(doser.id) == (HWID, None)
    assert poseidon.hwid_of_device("nothing") is None
    # The config entry of the device
    hass.data.setdefault(DOMAIN, {})["entry"] = SimpleNamespace(model_id=HWID.upper())
    assert poseidon.hwid_of_device("entry") == (HWID, None)
    other = dr.async_get(hass).async_get_or_create(
        config_entry_id=doser.config_entry_id,
        identifiers={("other", "x")},
    )
    assert poseidon.hwid_of_device(other.id) is None


# -- sensors ---------------------------------------------------------------------------


async def test_last_dose_sensor(hass: HomeAssistant) -> None:
    poseidon, coordinator = _dosing(hass)
    device: Any = SimpleNamespace(id="head2")
    sensor = PoseidonLastDoseSensor(poseidon, HWID, device, 2)
    assert sensor.unique_id == f"poseidon_last_dose_{HWID}_2"
    # In Poseidon mode (its /cloud points at the relay): available
    assert sensor.available
    assert sensor.native_value is None
    assert sensor.extra_state_attributes["volume"] is None
    poseidon._fire_dose(HWID, LOG)
    assert sensor.native_value == datetime.fromisoformat(LOG["local_time"])
    attributes = sensor.extra_state_attributes
    assert attributes["head"] == 2 and attributes["volume"] == 12.487
    assert attributes["started_at"] == "2026-10-30T10:28:45+01:00"
    # Out of Poseidon mode: unavailable
    coordinator.cloud = {"url": "mqtt.reef-beat.com:1883"}
    assert not sensor.available


def test_unreadable_end() -> None:
    poseidon: Any = SimpleNamespace(
        doses=SimpleNamespace(last=lambda hwid, head: {"ended_at": "x"})
    )
    sensor = PoseidonLastDoseSensor(poseidon, HWID, SimpleNamespace(id="d"), 1)  # type: ignore[arg-type]
    assert sensor.native_value is None


async def test_sensors_of_the_doses(hass: HomeAssistant) -> None:
    poseidon, coordinator = _dosing(hass)
    doser, head = _registry(hass)
    coordinator.heads_nb = 2
    sensors = poseidon_dose_sensors(poseidon, {HWID: doser})
    assert [(s._head, cast(Any, s.device_entry).id) for s in sensors] == [
        (1, doser.id),  # no head device: on the doser
        (2, head.id),
    ]
    # Without coordinator: the number of heads of its model
    coordinator.heads_nb = None
    assert len(poseidon_dose_sensors(poseidon, {HWID: doser})) == 2
    odd: Any = SimpleNamespace(id="x", model="RSDOSE")
    assert len(poseidon_dose_sensors(poseidon, {HWID: odd})) == 4
    # Not a ReefDose, not known
    poseidon.keystore.devices[HWID].type = "reef-wave"
    assert poseidon_dose_sensors(poseidon, {HWID: doser}) == []
    assert poseidon_dose_sensors(poseidon, {"unknown": doser}) == []


async def test_sensor_platform_without_poseidon(hass: HomeAssistant) -> None:
    from custom_components.redsea import sensor

    added: list[Any] = []
    await sensor.async_setup_entry(hass, _entry(), added.append)  # type: ignore[arg-type]
    assert added == []


# -- action ------------------------------------------------------------------------------


@pytest.fixture
async def running(hass: HomeAssistant) -> Any:
    """A Poseidon entry set up, with a ReefDose and its head 2 in the registry."""
    doser, head = _registry(hass)
    store = KeyStore(hass)
    await store.async_upsert(
        DeviceKeys(
            hwid=HWID,
            api_key="key",
            api_secret=SECRET,
            ip="192.0.2.10",
            type="reef-dosing",
        )
    )
    entry = _entry()
    entry.add_to_hass(hass)
    with (
        patch.object(Poseidon, "async_start", AsyncMock()),
        patch.object(Poseidon, "async_stop", AsyncMock()),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        poseidon = get_poseidon(hass)
        assert poseidon is not None
        await poseidon.async_load()
        poseidon.async_add_new_switches()
        await hass.async_block_till_done()
        yield poseidon, doser, head


async def test_get_doses(hass: HomeAssistant, running: Any) -> None:
    poseidon, doser, head = running
    poseidon.doses.add(HWID, _dose(1, NOW - timedelta(hours=2), 6.9))
    poseidon.doses.add(HWID, _dose(2, NOW - timedelta(hours=1), 12.5))

    async def _call(**data: Any) -> Any:
        return await hass.services.async_call(
            DOMAIN, const.SERVICE_GET_DOSES, data, blocking=True, return_response=True
        )

    answer = await _call(device_id=head.id)
    assert [d["volume"] for d in answer["doses"]] == [12.5]
    assert answer["retention_days"] == poseidon.doses.days
    answer = await _call(device_id=doser.id)
    assert [d["volume"] for d in answer["doses"]] == [12.5, 6.9]
    answer = await _call(device_id=doser.id, head=1, days=1, limit=5)
    assert [d["volume"] for d in answer["doses"]] == [6.9]
    assert await _call(device_id="nothing") == {"error": "Unknown device", "doses": []}
    # The last dose sensors were created, on the head device
    state = hass.states.get("sensor.doser_head_2_last_dose")
    assert state is not None
    hass.data.pop(const.DATA_POSEIDON)
    with pytest.raises(ServiceValidationError):
        await _call(device_id=head.id)

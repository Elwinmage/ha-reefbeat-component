"""redsea_dose event of a ReefDose (poseidon/events.py)."""

from __future__ import annotations

import copy
from types import SimpleNamespace
from typing import Any

from homeassistant.core import HomeAssistant

from custom_components.redsea.poseidon import const
from custom_components.redsea.poseidon.events import (
    EVENT_DOSE,
    DoseEvents,
    dose_event,
    dose_start,
)
from custom_components.redsea.poseidon.relay import UP
from tests._poseidon_fakes import HWID
from tests.test_poseidon_spy_responses_unit import _state_frame
from tests.test_poseidon_spy_unit import _poseidon

# As pushed and polled on the RSDOSE4 of the spy run of 2026-10-30
LOG = {
    "day": 30,
    "hour": 10,
    "utc_time": "2026-10-30T09:29:04Z",
    "local_time": "2026-10-30T10:29:04+01:00",
    "hwid": HWID,
    "head": 2,
    "supplement_name": "KH/Alkalinity (Foundation B)",
    "custom_supplement": False,
    "brand_name": "Red Sea",
    "custom_brand": False,
    "dose_type": "scheduled",
    "volume": 12.48726,
}
ANSWERS: dict[str, Any] = {
    "/head/2/settings": {"supplement": {"name": "KH/Alkalinity", "short_name": "KH"}},
    "/head/4/settings": {"supplement": {"name": "Potassium", "short_name": "K "}},
    "/dosing-queue": [
        {"head": "KH", "time": 30900, "volume": 12.5, "dose_type": "Auto"},
        {"head": "KH", "time": 37725, "volume": 12.5, "dose_type": "Auto"},
        {"head": "Ca", "time": 37000, "volume": 6.9, "dose_type": "Auto"},
        {"head": "K ", "time": 42300, "volume": 2, "dose_type": "Auto"},
        {"head": "KH", "time": 44550, "volume": 12.5, "dose_type": "Auto"},
        "junk",
    ],
}


def _coordinator(answers: dict[str, Any] | None = None) -> Any:
    polled = copy.deepcopy(ANSWERS if answers is None else answers)
    sources = [{"name": n, "type": "data", "data": d} for n, d in polled.items()]
    return SimpleNamespace(my_api=SimpleNamespace(data={"sources": sources}))


def test_dose_event() -> None:
    event = dose_event(_coordinator(), LOG)
    assert event == {
        "head": 2,
        "supplement": "KH/Alkalinity (Foundation B)",
        "brand": "Red Sea",
        "dose_type": "scheduled",
        "volume": 12.487,
        # 37725 s after the local midnight: the last one before its end
        "started_at": "2026-10-30T10:28:45+01:00",
        "ended_at": "2026-10-30T10:29:04+01:00",
        "duration_s": 19.0,
    }


def test_start_of_a_short_name_with_a_space() -> None:
    log = dict(LOG, head=4, local_time="2026-10-30T11:45:07+01:00")
    event = dose_event(_coordinator(), log)
    assert event is not None and event["started_at"] == "2026-10-30T11:45:00+01:00"


def test_dose_without_start() -> None:
    # A manual dose from the app: not in the queue
    log = dict(LOG, dose_type="manual", local_time="2026-10-30T09:15:19+01:00")
    event = dose_event(_coordinator(), log)
    assert event is not None
    assert event["started_at"] is None and event["duration_s"] is None
    # No queue, no supplement known, a queue that is no list
    assert dose_event(_coordinator({}), LOG)["started_at"] is None  # type: ignore[index]
    answers = copy.deepcopy(ANSWERS)
    answers["/dosing-queue"] = {"x": 1}
    assert dose_event(_coordinator(answers), LOG)["started_at"] is None  # type: ignore[index]
    answers["/head/2/settings"] = {"supplement": None}
    assert dose_start(_coordinator(answers), 2, _ended()) is None


def _ended() -> Any:
    from datetime import datetime

    return datetime.fromisoformat(LOG["local_time"])


def test_not_a_dose() -> None:
    assert dose_event(_coordinator(), "junk") is None
    assert dose_event(_coordinator(), dict(LOG, head="2")) is None
    assert dose_event(_coordinator(), dict(LOG, local_time="junk")) is None
    assert dose_event(_coordinator(), dict(LOG, local_time=None)) is None
    # No offset: not a time of the device
    assert (
        dose_event(_coordinator(), dict(LOG, local_time="2026-10-30T10:29:04")) is None
    )
    event = dose_event(_coordinator(), dict(LOG, volume=None))
    assert event is not None and event["volume"] is None


def test_duplicates() -> None:
    doses = DoseEvents()
    assert doses.first_time(HWID, LOG)
    assert not doses.first_time(HWID, dict(LOG))
    assert doses.first_time("other", LOG)
    assert doses.first_time(HWID, dict(LOG, head=1))


async def test_event_fired_once(hass: HomeAssistant) -> None:
    poseidon, coordinator = _poseidon(
        hass, {const.CONF_DEVICE_STRATEGIES: {HWID: const.STRATEGY_SPY}}
    )
    poseidon.keystore.devices[HWID].type = "reef-dosing"
    poseidon._apply_polling()
    coordinator.my_api.data["sources"] = _coordinator().my_api.data["sources"]  # type: ignore[attr-defined]
    events: list[Any] = []
    hass.bus.async_listen(EVENT_DOSE, events.append)
    topic = f"device/reef-dosing/{HWID}/dosing-log"
    # Pushed twice after a reconnection
    poseidon._on_frame(HWID, UP, _state_frame(LOG, topic))
    poseidon._on_frame(HWID, UP, _state_frame(LOG, topic))
    await hass.async_block_till_done()
    [event] = events
    assert event.data["head"] == 2 and event.data["duration_s"] == 19.0
    assert "device_id" in event.data and event.data["name"]
    # Not a device of the integration, not a dose
    poseidon._fire_dose("unknown", LOG)
    poseidon._fire_dose(HWID, "junk")
    poseidon._fire_dose(HWID, {"head": "x"})
    await hass.async_block_till_done()
    assert len(events) == 1

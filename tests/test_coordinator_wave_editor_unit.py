"""ReefWave program editor: wave library, group checks and program writes."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import timedelta
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

import custom_components.redsea.coordinator as coord
from custom_components.redsea.const import (
    CONFIG_FLOW_CONFIG_TYPE,
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_IP_ADDRESS,
    DOMAIN,
    WAVE_SCHEDULE_PATH,
    WAVES_LIBRARY,
)

HWID_PATH = "$.sources[?(@.name=='/device-info')].data.hwid"
DEVICES_PATH = "$.sources[?(@.name=='/device')].data"
LIBRARY_PATH = "$.sources[?(@.name=='" + WAVES_LIBRARY + "')].data"

LIBRARY = [
    {
        "uid": "rs-random",
        "aquarium_uid": "aq",
        "type": "ra",
        "name": "RS Random",
        "frt": 10,
        "rrt": 2,
        "default": True,
        "pump_settings": [{"hwid": "hw1", "fti": 40, "rti": 60, "sync": True}],
    },
    {
        "uid": "night",
        "aquarium_uid": "aq",
        "type": "re",
        "name": "nuit",
        "frt": 10,
        "rrt": 2,
        "default": False,
        "pump_settings": [
            {"hwid": "hw1", "fti": 100, "rti": 30, "sync": True},
            {"hwid": "other", "fti": 20, "rti": 20, "sync": False},
        ],
    },
    # Another aquarium: never offered
    {"uid": "elsewhere", "aquarium_uid": "aq2", "type": "nw", "name": "No Wave"},
]


def _device(hwid: str, grouped: bool, index: int = 0, **extra: Any) -> dict[str, Any]:
    return {
        "hwid": hwid,
        "name": "RSWAVE45-" + hwid,
        "type": "reef-wave",
        "aquarium_uid": "aq",
        "grouped": grouped,
        "group_index": index,
        **extra,
    }


@dataclass
class _Cloud:
    """Cloud coordinator: device list and library, records the writes."""

    title: str = "Cloud"
    devices: Any = field(default_factory=list)
    library: Any = field(default_factory=lambda: copy.deepcopy(LIBRARY))
    sent: list[tuple[str, Any, str]] = field(default_factory=list)
    fetched: list[str | None] = field(default_factory=list)
    # Aquariums whose wave programs were pushed to the pumps (/sync), apart
    # from the other writes
    synced: list[str] = field(default_factory=list)
    # What the next POST of a wave creates (None: nothing appears)
    created_uid: str | None = "new-uid"

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:
        if name == DEVICES_PATH:
            return self.devices
        if name == LIBRARY_PATH:
            return self.library
        if name.startswith(DEVICES_PATH + "[?(@.hwid=='"):
            hwid = name.split("hwid=='")[1].split("'")[0]
            devices = self.devices if isinstance(self.devices, list) else [self.devices]
            for d in devices:
                if isinstance(d, dict) and d.get("hwid") == hwid:
                    return d.get("aquarium_uid")
            return None
        raise AssertionError(name)

    async def send_cmd(self, action: str, payload: Any, method: str = "post") -> Any:
        if action.startswith("/reef-wave/") and action.endswith("/sync"):
            assert (payload, method) == ({}, "post")
            self.synced.append(action.split("/")[2])
            return None
        self.sent.append((action, copy.deepcopy(payload), method))
        if action.startswith("/reef-wave/schedule/"):
            return {"ok": True, "status": 200}
        if not action.startswith(WAVES_LIBRARY) or method == "delete":
            return None
        # As the cloud: a name has 15 characters at most (else a 400)
        if not 1 <= len(str(payload.get("name", ""))) <= 15:
            return {"ok": False, "status": 400}
        if action == WAVES_LIBRARY:
            # As the cloud: a name is unique in an aquarium (else a 409)
            if not self.created_uid or any(
                w.get("name") == payload.get("name")
                and w.get("aquarium_uid") == payload.get("aquarium_uid")
                for w in self.library
            ):
                return {"ok": False, "status": 409}
            self.library.append({**payload, "uid": self.created_uid})
            return {"ok": True, "status": 200}
        # As the cloud: the type of a wave is kept by a PUT
        uid = action.rsplit("/", 1)[1]
        for w in self.library:
            if w.get("uid") == uid:
                w.update({k: v for k, v in payload.items() if k != "type"})
        return {"ok": True, "status": 200}

    async def fetch_config(self, config_path: str | None = None) -> None:
        self.fetched.append(config_path)


@dataclass
class _Api:
    data: dict[str, Any] = field(default_factory=dict)
    http_calls: list[tuple[str, Any]] = field(default_factory=list)
    fetched: list[str | None] = field(default_factory=list)

    def get_data(
        self, name: str, is_None_possible: bool = False, cached: bool = True
    ) -> Any:
        return self.data.get(name)

    async def http_send(self, path: str, payload: Any) -> None:
        self.http_calls.append((path, copy.deepcopy(payload)))

    def set_data(self, name: str, value: Any) -> None:
        self.data[name] = value

    async def push_values(self, source: str, method: str = "post") -> None:
        self.http_calls.append(("push " + source, method))

    async def delete(self, source: str) -> None:
        self.http_calls.append(("delete " + source, None))

    async def fetch_config(self, config_path: str | None = None) -> None:
        self.fetched.append(config_path)


@pytest.fixture(autouse=True)
def _patch_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        coord, "async_get_clientsession", lambda _hass: object(), raising=True
    )

    class _CtorApi(_Api):
        def __init__(self, *_a: Any, **_k: Any) -> None:
            super().__init__()

    monkeypatch.setattr(coord, "ReefWaveAPI", _CtorApi, raising=True)


def _wave(
    hass: HomeAssistant,
    hwid: str,
    cloud: _Cloud | None,
    program: list[dict[str, Any]] | None = None,
    entry_id: str | None = None,
) -> coord.ReefWaveCoordinator:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="WAVE-" + hwid,
        data={
            CONFIG_FLOW_IP_ADDRESS: "192.0.2.1",
            CONFIG_FLOW_HW_MODEL: "RSWAVE45",
            CONFIG_FLOW_CONFIG_TYPE: False,
        },
        entry_id=entry_id or hwid,
    )
    pump = coord.ReefWaveCoordinator(hass, cast(Any, entry))
    api = cast(_Api, pump.my_api)
    api.data[HWID_PATH] = hwid
    api.data[WAVE_SCHEDULE_PATH] = program
    pump._cloud_link = cast(Any, cloud)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = pump
    return pump


PROGRAM = [
    {
        "st": 0,
        "wave_uid": "night",
        "name": "nuit",
        "type": "re",
        "frt": 10,
        "rrt": 2,
        "fti": 100,
        "rti": 30,
        "direction": "fw",
    },
    {
        "st": 600,
        "wave_uid": "rs-random",
        "name": "RS Random",
        "type": "ra",
        "fti": 40,
        "rti": 60,
        "direction": "alt",
    },
]


# -- Link, library, group -------------------------------------------------------


@pytest.mark.asyncio
async def test_link_and_library(hass: HomeAssistant) -> None:
    alone = _wave(hass, "hw0", None)
    assert alone.wave_link() is None
    assert alone.wave_library() is None

    cloud = _Cloud(devices=[_device("hw1", False)])
    pump = _wave(hass, "hw1", cloud)
    assert pump.wave_link() == (cloud, "aq")
    library = pump.wave_library()
    assert library is not None
    assert [w["uid"] for w in library] == ["rs-random", "night"]
    assert library[1]["fti"] == 100  # this pump's own intensities

    # A device unknown to the cloud, a single device unwrapped, junk
    stranger = _wave(hass, "hw9", cloud)
    assert stranger.wave_link() is None
    cloud.devices = _device("hw1", False)
    assert pump.wave_link() == (cloud, "aq")
    assert pump._cloud_devices(cast(Any, cloud)) == [cloud.devices]
    cloud.library = LIBRARY[1]
    assert [w["uid"] for w in pump.wave_library() or []] == ["night"]
    cloud.library = "junk"
    assert pump.wave_library() == []
    cloud.devices = "junk"
    assert pump._cloud_devices(cast(Any, cloud)) == []


@pytest.mark.asyncio
async def test_group_members_and_availability(hass: HomeAssistant) -> None:
    cloud = _Cloud(
        devices=[
            _device("hw2", True, 1),
            _device("hw1", True, 0),
            _device("hw3", True, 2, in_service=False),
            _device("solo", False),
            {**_device("x", True), "aquarium_uid": "aq2"},
            {**_device("y", True), "type": "reef-lights"},
        ]
    )
    pump = _wave(hass, "hw1", cloud)
    group = pump.wave_group()
    assert [m["hwid"] for m in group] == ["hw1", "hw2", "hw3"]
    assert group[0]["coordinator"] is pump
    assert group[1]["coordinator"] is None
    assert group[1]["name"] == "RSWAVE45-hw2"
    assert group[2]["in_service"] is False
    # hw2 not loaded blocks, hw3 out of service does not
    assert pump.unavailable_wave_members() == ["RSWAVE45-hw2"]
    with pytest.raises(HomeAssistantError) as err:
        pump._check_group_ready()
    assert err.value.translation_key == "wave_group_member_unavailable"

    other = _wave(hass, "hw2", cloud)
    assert pump.wave_group()[1]["name"] == other.title
    other.last_update_success = False
    assert pump.unavailable_wave_members() == [other.title]
    other.last_update_success = True
    assert pump.unavailable_wave_members() == []
    pump._check_group_ready()

    # Not grouped (or not linked): the pump alone
    solo = _wave(hass, "solo", cloud)
    assert [m["hwid"] for m in solo.wave_group()] == ["solo"]
    alone = _wave(hass, "lonely", None)
    assert alone.wave_group()[0]["coordinator"] is alone


@pytest.mark.asyncio
async def test_usage_and_program(hass: HomeAssistant) -> None:
    cloud = _Cloud(devices=[_device("hw1", False)])
    pump = _wave(hass, "hw1", cloud, PROGRAM)
    other = _wave(hass, "hw2", cloud, [{"st": 0, "wave_uid": "night"}, {"st": 5}])
    hass.data[DOMAIN]["junk"] = object()
    assert pump.program_intervals() == PROGRAM
    usage = pump.wave_usage()
    assert sorted(usage["night"]) == sorted([pump.title, other.title])
    assert usage["rs-random"] == [pump.title]
    cast(_Api, other.my_api).data[WAVE_SCHEDULE_PATH] = "junk"
    assert other.program_intervals() == []
    # A pump not registered in hass.data still counts itself
    del hass.data[DOMAIN]["hw1"]
    assert pump.title in pump.wave_usage()["night"]


# -- Library edits --------------------------------------------------------------

SETTINGS = {"type": "re", "frt": 12, "rrt": 3, "fti": 70, "rti": 40, "sync": True}


@pytest.mark.asyncio
async def test_create_wave_gives_intensities_to_the_group(
    hass: HomeAssistant,
) -> None:
    cloud = _Cloud(devices=[_device("hw1", True, 0), _device("hw2", True, 1)])
    pump = _wave(hass, "hw1", cloud)
    _wave(hass, "hw2", cloud)
    uid = await pump.save_wave(" Storm ", dict(SETTINGS))
    assert uid == "new-uid"
    action, payload, method = cloud.sent[-1]
    assert (action, method) == (WAVES_LIBRARY, "post")
    assert payload["aquarium_uid"] == "aq"
    assert payload["name"] == "Storm"
    assert payload["type"] == "re" and payload["frt"] == 12
    assert [s["hwid"] for s in payload["pump_settings"]] == ["hw1", "hw2"]
    assert cloud.fetched == [WAVES_LIBRARY]

    # The new wave cannot be found back
    cloud.created_uid = None
    assert await pump.save_wave("Other", dict(SETTINGS)) is None


@pytest.mark.asyncio
async def test_create_wave_refusals(hass: HomeAssistant) -> None:
    alone = _wave(hass, "hw0", None)
    with pytest.raises(HomeAssistantError) as err:
        await alone.save_wave("A", dict(SETTINGS))
    assert err.value.translation_key == "wave_cloud_required"

    cloud = _Cloud(devices=[_device("hw1", True, 0), _device("hw2", True, 1)])
    pump = _wave(hass, "hw1", cloud)
    for name, settings, key in (
        ("nuit", SETTINGS, "wave_name_taken"),
        ("A", {"type": "zz"}, "wave_bad_type"),
    ):
        with pytest.raises(HomeAssistantError) as err:
            await pump.save_wave(name, dict(settings))
        assert err.value.translation_key == key
    # hw2 not loaded: nothing sent
    with pytest.raises(HomeAssistantError) as err:
        await pump.save_wave("A", dict(SETTINGS))
    assert err.value.translation_key == "wave_group_member_unavailable"
    assert cloud.sent == []


@pytest.mark.asyncio
async def test_update_wave_and_rewrite_programs(hass: HomeAssistant) -> None:
    cloud = _Cloud(
        devices=[
            _device("hw1", True, 0),
            _device("hw2", True, 1),
            _device("hw3", True, 2),
        ]
    )
    pump = _wave(hass, "hw1", cloud, PROGRAM)
    # hw2 does not use the wave, hw3 does
    _wave(hass, "hw2", cloud, [{"st": 0, "wave_uid": "rs-random"}])
    _wave(hass, "hw3", cloud, [{"st": 0, "wave_uid": "night", "direction": "rw"}])
    assert await pump.save_wave("nuit 2", dict(SETTINGS), "night") == "night"

    put = cloud.sent[0]
    assert put[0] == WAVES_LIBRARY + "/night" and put[2] == "put"
    assert "aquarium_uid" not in put[1]
    ps = {s["hwid"]: s for s in put[1]["pump_settings"]}
    # This pump's replaced, other's kept, members without settings filled
    assert ps["hw1"]["fti"] == 70
    assert ps["other"]["fti"] == 20
    assert ps["hw2"]["fti"] == 70 and ps["hw3"]["fti"] == 70

    # Programs using the wave are posted again: hw1 and hw3, not hw2
    posted = [a for a, _p, _m in cloud.sent[1:]]
    assert posted == ["/reef-wave/schedule/hw1", "/reef-wave/schedule/hw3"]
    hw3 = cloud.sent[2][1]["intervals"][0]
    assert hw3["direction"] == "rw"


SURGE = {"type": "su", "pd": 3, "fti": 40, "rti": 60, "sync": True}


@pytest.mark.asyncio
async def test_update_wave_type_replaces_the_wave(hass: HomeAssistant) -> None:
    """The cloud keeps the type of a wave, and a name is unique: the old wave
    is renamed, a new one added under its name, the programs using the old
    one pointed at it, then the old one is deleted."""
    cloud = _Cloud(
        devices=[
            _device("hw1", True, 0),
            _device("hw2", True, 1),
            _device("hw3", True, 2),
        ]
    )
    pump = _wave(hass, "hw1", cloud, PROGRAM)
    _wave(hass, "hw2", cloud, [{"st": 0, "wave_uid": "rs-random"}])
    _wave(hass, "hw3", cloud, [{"st": 0, "wave_uid": "night", "direction": "rw"}])
    assert await pump.save_wave("nuit", dict(SURGE), "night") == "new-uid"

    # The old wave first gets a name of its own, its shape and settings kept
    action, payload, method = cloud.sent[0]
    assert (action, method) == (WAVES_LIBRARY + "/night", "put")
    assert payload["name"] == "~night"
    assert payload["type"] == "re" and payload["frt"] == 10 and payload["rrt"] == 2
    assert payload["pump_settings"] == LIBRARY[1]["pump_settings"]

    action, payload, method = cloud.sent[1]
    assert (action, method) == (WAVES_LIBRARY, "post")
    assert payload["aquarium_uid"] == "aq" and payload["name"] == "nuit"
    assert payload["type"] == "su" and payload["pd"] == 3
    assert "frt" not in payload
    ps = {s["hwid"]: s for s in payload["pump_settings"]}
    assert ps["hw1"]["fti"] == 40 and ps["other"]["fti"] == 20

    # The programs of hw1 and hw3 use the new wave, hw2's is left
    posted = [(a, m) for a, _p, m in cloud.sent[2:4]]
    assert posted == [
        ("/reef-wave/schedule/hw1", "post"),
        ("/reef-wave/schedule/hw3", "post"),
    ]
    hw1 = cloud.sent[2][1]["intervals"]
    assert [i["wave_uid"] for i in hw1] == ["new-uid", "rs-random"]
    assert hw1[0]["type"] == "su"
    assert cloud.sent[3][1]["intervals"][0]["direction"] == "rw"
    # Then the old wave goes
    assert cloud.sent[4] == (WAVES_LIBRARY + "/night", {}, "delete")
    assert len(cloud.sent) == 5
    # Each program posted is pushed to the pumps
    assert cloud.synced == ["aq", "aq"]


@pytest.mark.asyncio
async def test_update_wave_type_keeps_a_wave_still_used(
    hass: HomeAssistant,
) -> None:
    """A loaded pump that cannot be given the new wave keeps the old one."""
    cloud = _Cloud(devices=[_device("hw1", False)])
    pump = _wave(hass, "hw1", cloud, PROGRAM)
    _wave(hass, "hw9", None, [{"st": 0, "wave_uid": "night"}])
    # A pump not registered in hass.data still counts itself
    del hass.data[DOMAIN]["hw1"]
    assert await pump.save_wave("nuit", dict(SURGE), "night") == "new-uid"
    actions = [(a, m) for a, _p, m in cloud.sent]
    assert actions == [
        (WAVES_LIBRARY + "/night", "put"),
        (WAVES_LIBRARY, "post"),
        ("/reef-wave/schedule/hw1", "post"),
    ]
    # Kept under its new name
    assert next(w for w in cloud.library if w["uid"] == "night")["name"] == "~night"

    # The new wave cannot be added: the old one gets its name back
    cloud = _Cloud(devices=[_device("hw1", False)], created_uid=None)
    pump._cloud_link = cast(Any, cloud)
    with pytest.raises(HomeAssistantError) as err:
        await pump.save_wave("nuit", dict(SURGE), "night")
    assert err.value.translation_key == "wave_replace_failed"
    assert [(a, m) for a, _p, m in cloud.sent] == [
        (WAVES_LIBRARY + "/night", "put"),
        (WAVES_LIBRARY, "post"),
        (WAVES_LIBRARY + "/night", "put"),
    ]
    assert cloud.sent[2][1]["name"] == "nuit"
    assert next(w for w in cloud.library if w["uid"] == "night")["name"] == "nuit"

    # The old wave cannot be renamed: nothing else is sent
    cloud = _Cloud(devices=[_device("hw1", False)])
    cloud.library[1]["uid"] = "a-uid-of-more-than-fifteen-characters"
    pump._cloud_link = cast(Any, cloud)
    real = cloud.send_cmd

    async def refuse_put(action: str, payload: Any, method: str = "post") -> Any:
        if method == "put":
            cloud.sent.append((action, payload, method))
            return {"ok": False, "status": 400}
        return await real(action, payload, method)

    cloud.send_cmd = refuse_put  # type: ignore[method-assign]
    with pytest.raises(HomeAssistantError) as err:
        await pump.save_wave(
            "nuit", dict(SURGE), "a-uid-of-more-than-fifteen-characters"
        )
    assert err.value.translation_key == "wave_replace_failed"
    assert [(a, m) for a, _p, m in cloud.sent] == [
        (WAVES_LIBRARY + "/a-uid-of-more-than-fifteen-characters", "put")
    ]
    # The name kept within the cloud's limit
    assert cloud.sent[0][1]["name"] == "~a-uid-of-more-"


@pytest.mark.asyncio
async def test_update_wave_refusals(hass: HomeAssistant) -> None:
    cloud = _Cloud(devices=[_device("hw1", False)])
    pump = _wave(hass, "hw1", cloud)
    with pytest.raises(HomeAssistantError) as err:
        await pump.save_wave("x", dict(SETTINGS), "zz")
    assert err.value.translation_key == "wave_not_found"
    with pytest.raises(HomeAssistantError) as err:
        await pump.save_wave("Mine", dict(SETTINGS), "rs-random")
    assert err.value.translation_key == "wave_default_readonly"
    assert cloud.sent == []


@pytest.mark.asyncio
async def test_delete_wave(hass: HomeAssistant) -> None:
    alone = _wave(hass, "hw0", None)
    with pytest.raises(HomeAssistantError):
        await alone.delete_wave("night")

    cloud = _Cloud(devices=[_device("hw1", False)])
    cloud.library.append(
        {"uid": "spare", "aquarium_uid": "aq", "type": "nw", "name": "Spare"}
    )
    pump = _wave(hass, "hw1", cloud, PROGRAM)
    for uid, key in (
        ("zz", "wave_not_found"),
        ("rs-random", "wave_default_readonly"),
        ("night", "wave_in_use"),
    ):
        with pytest.raises(HomeAssistantError) as err:
            await pump.delete_wave(uid)
        assert err.value.translation_key == key
    assert cloud.sent == []
    assert await pump.delete_wave("spare") is True
    assert cloud.sent == [(WAVES_LIBRARY + "/spare", {}, "delete")]
    assert cloud.fetched == [WAVES_LIBRARY]


# -- Program writes -------------------------------------------------------------

SLOTS = [
    {"st": 0, "wave_uid": "night", "direction": "fw"},
    {"st": 720, "wave_uid": "rs-random", "direction": "alt"},
]


@pytest.mark.asyncio
async def test_save_program_through_the_cloud_for_the_group(
    hass: HomeAssistant,
) -> None:
    cloud = _Cloud(
        devices=[
            _device("hw1", True, 0),
            _device("hw2", True, 1),
            _device("hw3", True, 2, in_service=False),
        ]
    )
    pump = _wave(hass, "hw1", cloud, PROGRAM)
    other = _wave(hass, "hw2", cloud)
    await pump.save_program(copy.deepcopy(SLOTS))
    assert [a for a, _p, _m in cloud.sent] == [
        "/reef-wave/schedule/hw1",
        "/reef-wave/schedule/hw2",
    ]
    # The cloud pushes each program to the pumps, as the app has it do
    assert cloud.synced == ["aq", "aq"]
    mine = cloud.sent[0][1]["intervals"]
    theirs = cloud.sent[1][1]["intervals"]
    assert [i["st"] for i in mine] == [0, 720]
    # Same slots, each pump's own intensities (hw2 has none in "nuit": the
    # default ones)
    assert mine[0]["fti"] == 100 and theirs[0]["fti"] == 50
    assert cast(_Api, pump.my_api).fetched == [None]
    assert cast(_Api, other.my_api).fetched == [None]
    # Nothing on the local API
    assert cast(_Api, pump.my_api).http_calls == []


@pytest.mark.asyncio
async def test_program_posted_is_shown_until_the_pump_runs_it(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The pump gets a program once the cloud pushed it: it is shown at once
    (optimistic), kept over the reads of the pump until it runs it, and the
    pump read back READBACK_S later."""
    cloud = _Cloud(devices=[_device("hw1", False)])
    pump = _wave(hass, "hw1", cloud, copy.deepcopy(PROGRAM))
    told: list[int] = []
    pump.async_update_listeners = lambda: told.append(1)  # type: ignore[method-assign]
    refreshed: list[tuple[Any, Any]] = []

    async def _refresh(source: Any = None, config: bool = False, wait: Any = 2):
        refreshed.append((source, wait))

    pump.async_request_refresh = _refresh  # type: ignore[method-assign]
    await pump.save_program(copy.deepcopy(SLOTS))
    posted = cloud.sent[0][1]["intervals"]
    shown = pump.program_intervals()
    # Shown at once, as the pump will hold it
    assert [i["st"] for i in shown] == [0, 720]
    assert all("start" not in i for i in shown)
    assert shown[0]["fti"] == posted[0]["fti"] and told

    # The pump still runs its old program: the one posted stays shown
    old = copy.deepcopy(PROGRAM)

    async def _read(_self: Any) -> dict[str, Any]:
        cast(_Api, pump.my_api).data[WAVE_SCHEDULE_PATH] = copy.deepcopy(old)
        return {}

    monkeypatch.setattr(
        coord.ReefWaveCoordinator.__mro__[1], "_async_update_data", _read
    )
    await pump._async_update_data()
    assert [i["st"] for i in pump.program_intervals()] == [0, 720]

    # Read back READBACK_S later
    assert refreshed == []
    async_fire_time_changed(
        hass, dt_util.utcnow() + timedelta(seconds=pump.READBACK_S + 1)
    )
    await hass.async_block_till_done()
    assert refreshed == [("/auto", 0)]

    # The pump runs it: nothing kept any more
    old = copy.deepcopy(shown)
    await pump._async_update_data()
    assert pump._pending_program is None
    old = copy.deepcopy(PROGRAM)
    await pump._async_update_data()
    assert pump.program_intervals()[1]["st"] == PROGRAM[1]["st"]

    # Not run after PENDING_S: the pump's own program is shown again
    await pump.save_program(copy.deepcopy(SLOTS))
    assert pump._pending_program is not None
    monkeypatch.setattr(coord, "time", lambda: 1e12)
    await pump._async_update_data()
    assert pump._pending_program is None
    assert pump.program_intervals()[1]["st"] == PROGRAM[1]["st"]

    # Without /auto data yet, nothing is written in it
    pump._pending_program = (shown, 2e12)
    cast(_Api, pump.my_api).data[WAVE_SCHEDULE_PATH] = None
    pump._keep_pending_program()
    assert pump.program_intervals() == []

    # Unloaded: the read back planned is dropped
    cast(_Api, pump.my_api).data[WAVE_SCHEDULE_PATH] = copy.deepcopy(PROGRAM)
    await pump.save_program(copy.deepcopy(SLOTS))
    assert pump._readback is not None
    pump.unload()
    assert pump._readback is None


@pytest.mark.asyncio
async def test_program_refused_by_the_cloud_is_not_shown(
    hass: HomeAssistant,
) -> None:
    cloud = _Cloud(devices=[_device("hw1", False)])
    pump = _wave(hass, "hw1", cloud, copy.deepcopy(PROGRAM))
    real = cloud.send_cmd

    async def refuse(action: str, payload: Any, method: str = "post") -> Any:
        if action.startswith("/reef-wave/schedule/"):
            cloud.sent.append((action, payload, method))
            return {"ok": False, "status": 400}
        return await real(action, payload, method)

    cloud.send_cmd = refuse  # type: ignore[method-assign]
    await pump.save_program(copy.deepcopy(SLOTS))
    assert pump._pending_program is None and pump._readback is None
    assert pump.program_intervals()[1]["st"] == PROGRAM[1]["st"]


@pytest.mark.asyncio
async def test_save_program_refusals(hass: HomeAssistant) -> None:
    cloud = _Cloud(devices=[_device("hw1", True, 0), _device("hw2", True, 1)])
    pump = _wave(hass, "hw1", cloud, PROGRAM)
    with pytest.raises(HomeAssistantError) as err:
        await pump.save_program([{"st": 60, "wave_uid": "night"}])
    assert err.value.translation_key == "wave_program_midnight"
    with pytest.raises(HomeAssistantError) as err:
        await pump.save_program(copy.deepcopy(SLOTS))
    assert err.value.translation_key == "wave_group_member_unavailable"
    _wave(hass, "hw2", cloud)
    with pytest.raises(HomeAssistantError) as err:
        await pump.save_program([{"st": 0, "wave_uid": "elsewhere"}])
    assert err.value.translation_key == "wave_not_found"


@pytest.mark.asyncio
async def test_save_program_locally_without_cloud(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _UUID:
        @staticmethod
        def uuid4() -> str:
            return "u-1"

    monkeypatch.setattr(coord, "uuid", _UUID, raising=True)
    pump = _wave(hass, "hw0", None, PROGRAM)
    await pump.save_program(
        [
            {"st": 0, "wave_uid": "rs-random", "direction": "rw"},
            {"st": 500, "wave_uid": "night", "direction": "alt"},
        ]
    )
    api = cast(_Api, pump.my_api)
    paths = [p for p, _ in api.http_calls]
    assert paths == ["/auto/init", "/auto", "/auto", "/auto/complete", "/auto/apply"]
    first = api.http_calls[1][1]["intervals"][0]
    assert first["wave_uid"] == "rs-random" and first["direction"] == "rw"
    assert "start" not in first
    assert api.http_calls[0][1] == {"uid": "u-1"}
    assert api.fetched == [None]

    # Only the waves of its own program can be used without the library
    with pytest.raises(HomeAssistantError) as err:
        await pump.save_program([{"st": 0, "wave_uid": "elsewhere"}])
    assert err.value.translation_key == "wave_not_found"


# -- Group list, preview, per-pump settings ---------------------------------------


@pytest.mark.asyncio
async def test_linked_waves(hass: HomeAssistant) -> None:
    cloud = _Cloud(devices=[_device("hw1", True, 0), _device("hw2", True, 1)])
    pump = _wave(hass, "hw1", cloud)
    linked = pump.linked_waves()
    assert [w["hwid"] for w in linked] == ["hw1", "hw2"]
    assert linked[0]["entry_id"] == "hw1" and linked[0]["available"] is True
    assert linked[1]["entry_id"] is None and linked[1]["available"] is False
    assert _wave(hass, "solo", None).linked_waves() == []


@pytest.mark.asyncio
async def test_preview(hass: HomeAssistant) -> None:
    pump = _wave(hass, "hw1", None)
    refresh = AsyncMock()
    pump.async_request_refresh = refresh  # type: ignore[method-assign]
    api = cast(_Api, pump.my_api)
    await pump.start_preview(
        {"type": "st", "frt": 5, "rrt": 2, "pd": 3, "sn": 4, "fti": 70, "rti": 20},
        "alt",
        5,
    )
    path = pump.PREVIEW_PATH
    assert api.data[path + "type"] == "st"
    assert api.data[path + "sn"] == 4
    assert api.data[path + "direction"] == "alt"
    # Duration clamped to 1..10 min
    assert api.data[path + "duration"] == 60000
    assert api.http_calls[-1] == ("push /preview", "post")
    refresh.assert_awaited()
    await pump.start_preview(
        {"type": "re", "frt": 5, "rrt": 2, "fti": 70, "rti": 20}, "fw", 10**9
    )
    assert api.data[path + "duration"] == 600000

    for settings, direction, key in (
        ({"type": "zz"}, "fw", "wave_bad_type"),
        ({"type": "nw", "fti": 1, "rti": 1}, "fw", "wave_preview_no_wave"),
        (
            {"type": "re", "frt": 5, "rrt": 2, "fti": 1, "rti": 1},
            "up",
            "wave_program_bad_slot",
        ),
    ):
        with pytest.raises(HomeAssistantError) as err:
            await pump.start_preview(settings, direction, 60000)
        assert err.value.translation_key == key

    await pump.stop_preview()
    assert api.http_calls[-1] == ("delete /preview", None)


@pytest.mark.asyncio
async def test_current_slot(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _At:
        @classmethod
        def now(cls) -> Any:
            return SimpleNamespace(hour=11, minute=0)

    monkeypatch.setattr(coord, "datetime", _At, raising=True)
    pump = _wave(hass, "hw1", None, PROGRAM)
    assert pump.current_slot() == 1
    cast(_Api, pump.my_api).data[WAVE_SCHEDULE_PATH] = PROGRAM + [
        {"st": 900, "wave_uid": "night"}
    ]
    assert pump.current_slot() == 1
    cast(_Api, pump.my_api).data[WAVE_SCHEDULE_PATH] = []
    assert pump.current_slot() == -1


@pytest.mark.asyncio
async def test_set_current_pump_through_the_cloud(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        coord.ReefWaveCoordinator, "current_slot", lambda _s, _i=None: 1
    )
    cloud = _Cloud(devices=[_device("hw1", True, 0), _device("hw2", True, 1)])
    pump = _wave(hass, "hw1", cloud, PROGRAM)
    # hw2 not loaded: a single pump's setting does not need the group
    await pump.set_current_pump("rw", 70, 10)
    put = cloud.sent[0]
    assert put[0] == WAVES_LIBRARY + "/rs-random" and put[2] == "put"
    # A Red Sea wave keeps its shape and default flag, only its settings
    assert put[1]["default"] is True and put[1]["type"] == "ra"
    assert "uid" not in put[1] and "aquarium_uid" not in put[1]
    assert put[1]["pump_settings"] == [
        {"hwid": "hw1", "fti": 70, "rti": 10, "sync": True}
    ]
    post = cloud.sent[1]
    assert post[0] == "/reef-wave/schedule/hw1"
    assert [i["direction"] for i in post[1]["intervals"]] == ["fw", "rw"]
    assert len(cloud.sent) == 2
    assert cloud.synced == ["aq"]

    # A wave the library lost
    cloud.library = []
    with pytest.raises(HomeAssistantError) as err:
        await pump.set_current_pump("fw", 1, 1)
    assert err.value.translation_key == "wave_not_found"


@pytest.mark.asyncio
async def test_set_current_pump_locally_and_refusals(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    slot = {"v": 0}
    monkeypatch.setattr(
        coord.ReefWaveCoordinator, "current_slot", lambda _s, _i=None: slot["v"]
    )
    pump = _wave(hass, "hw0", None, copy.deepcopy(PROGRAM))
    await pump.set_current_pump("alt", 30, 40)
    api = cast(_Api, pump.my_api)
    sent = [p for p, _ in api.http_calls if p == "/auto"]
    assert len(sent) == 2
    first = api.http_calls[1][1]["intervals"][0]
    assert (first["direction"], first["fti"], first["rti"]) == ("alt", 30, 40)
    # The program read stays untouched until the pump answers
    assert PROGRAM[0].get("direction") == "fw"

    for direction, fti, key in (
        ("up", 1, "wave_program_bad_slot"),
        ("fw", 101, "wave_bad_value"),
    ):
        with pytest.raises(HomeAssistantError) as err:
            await pump.set_current_pump(direction, fti, 1)
        assert err.value.translation_key == key
    slot["v"] = -1
    with pytest.raises(HomeAssistantError) as err:
        await pump.set_current_pump("fw", 1, 1)
    assert err.value.translation_key == "wave_program_empty"


# -- Grouping ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wave_grouped_state(hass: HomeAssistant) -> None:
    assert _wave(hass, "hw0", None).wave_grouped() is None
    cloud = _Cloud(devices=[_device("hw1", True), _device("hw2", False)])
    assert _wave(hass, "hw1", cloud).wave_grouped() is True
    assert _wave(hass, "hw2", cloud).wave_grouped() is False


@pytest.mark.asyncio
async def test_group_and_ungroup(hass: HomeAssistant) -> None:
    cloud = _Cloud(
        devices=[
            _device("hw2", True, 1, name="B"),
            _device("hw1", True, 0, name="A"),
            _device("hw3", False),
            {**_device("x", True), "aquarium_uid": "aq2"},
        ]
    )
    pump = _wave(hass, "hw3", cloud)
    other = _wave(hass, "hw1", cloud)
    hass.data[DOMAIN]["junk"] = object()
    listener = AsyncMock()
    other.async_update_listeners = listener  # type: ignore[method-assign]
    await pump.set_wave_grouped(True)
    assert cloud.sent[0] == ("/device/hw3/group", {}, "post")
    action, manage, method = cloud.sent[1]
    assert (action, method) == ("/device/manage", "post")
    # Joins last, after the group in its order
    assert [m["hwid"] for m in manage] == ["hw1", "hw2", "hw3"]
    assert [m["group_index"] for m in manage] == [0, 1, 2]
    assert manage[0] == {
        "hwid": "hw1",
        "name": "A",
        "in_service": True,
        "grouped": True,
        "group_index": 0,
    }
    assert cloud.fetched == ["/device"]
    listener.assert_called()

    cloud.sent.clear()
    await pump.set_wave_grouped(False)
    assert cloud.sent == [("/device/hw3/ungroup", {}, "post")]

    with pytest.raises(HomeAssistantError) as err:
        await _wave(hass, "hw0", None).set_wave_grouped(True)
    assert err.value.translation_key == "wave_cloud_required"


@pytest.mark.asyncio
async def test_group_order(hass: HomeAssistant) -> None:
    cloud = _Cloud(devices=[_device("hw1", True, 0), _device("hw2", True, 1)])
    pump = _wave(hass, "hw1", cloud)
    await pump.set_wave_group_order(["hw2", "hw1"])
    action, manage, _m = cloud.sent[-1]
    assert action == "/device/manage"
    assert [(m["hwid"], m["group_index"]) for m in manage] == [("hw2", 0), ("hw1", 1)]
    assert cloud.fetched == ["/device"]
    for bad in ("x", ["hw1"], ["hw1", "hw3"]):
        with pytest.raises(HomeAssistantError) as err:
            await pump.set_wave_group_order(bad)
        assert err.value.translation_key == "wave_group_bad_order"
    # A pump alone has no order
    solo = _wave(hass, "solo", _Cloud(devices=[_device("solo", False)]))
    with pytest.raises(HomeAssistantError):
        await solo.set_wave_group_order(["solo"])

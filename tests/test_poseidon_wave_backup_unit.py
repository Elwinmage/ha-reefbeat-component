"""Key capture of a ReefWave: its waves and program saved, put back in the
cloud, pushed to the pump (poseidon)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from homeassistant.core import HomeAssistant

from custom_components.redsea.poseidon import capture as capture_mod
from custom_components.redsea.poseidon import const
from custom_components.redsea.poseidon.capture import (
    CaptureReport,
    SnapshotStore,
    acquire_keys,
)
from custom_components.redsea.poseidon.keystore import DeviceKeys, KeyStore
from custom_components.redsea.poseidon.wave_backup import (
    CLOUD_WAVES,
    backup_waves,
    custom_waves,
    program_of,
    renamed_auto,
    restore_waves,
    same_program,
)
from tests._poseidon_fakes import HWID, FakeCloudApi, FakeHttp

AQUARIUM = "aq-1"
OTHER = "0000bbbb0001"
LIBRARY: list[dict[str, Any]] = [
    # Red Sea's: the same for everybody, never saved
    {"uid": "rs-1", "aquarium_uid": AQUARIUM, "name": "RS Regular", "type": "re",
     "default": True, "pump_settings": []},
    {"uid": "w-night", "aquarium_uid": AQUARIUM, "name": "Nuit", "type": "re",
     "frt": 10, "rrt": 2, "default": False,
     "pump_settings": [{"hwid": HWID, "fti": 40, "rti": 60, "sync": True},
                       {"hwid": OTHER, "fti": 30, "rti": 30, "sync": True}]},
    {"uid": "w-day", "aquarium_uid": AQUARIUM, "name": "Journee", "type": "ra",
     "frt": 10, "rrt": 2, "default": False,
     "pump_settings": [{"hwid": HWID, "fti": 100, "rti": 60, "sync": False}]},
    # Another aquarium
    {"uid": "w-x", "aquarium_uid": "aq-2", "name": "X", "type": "re",
     "default": False, "pump_settings": []},
]  # fmt: skip
AUTO = {
    "intervals": [
        {"wave_uid": "rs-1", "type": "re", "name": "RS Regular", "st": 0,
         "fti": 40, "rti": 60, "direction": "fw"},
        {"wave_uid": "w-day", "type": "ra", "name": "Journee", "st": 750,
         "fti": 100, "rti": 60, "direction": "alt"},
        {"wave_uid": "w-night", "type": "re", "name": "Nuit", "st": 1350,
         "fti": 40, "rti": 60, "direction": "fw"},
    ]
}  # fmt: skip


def _library() -> list[dict[str, Any]]:
    return json.loads(json.dumps(LIBRARY))


def _sent(cloud: FakeCloudApi, action: str) -> list[Any]:
    return [c[1] for c in cloud.calls if c[0] == action and c[2] != "get"]


# -- helpers ------------------------------------------------------------------------------


async def test_cloud_answers() -> None:
    cloud = FakeCloudApi(library=_library())

    async def _none(_path: str) -> Any:
        return None

    cloud.http_get = _none  # type: ignore[method-assign]
    assert await backup_waves(cloud, AQUARIUM) is None

    async def _none_send(*_args: Any) -> Any:
        return None

    cloud = FakeCloudApi(library=_library())
    backup = await backup_waves(cloud, AQUARIUM)
    assert backup is not None
    cloud.http_send = _none_send  # type: ignore[method-assign]
    ok, notes, _ = await restore_waves(cloud, HWID, backup, AUTO)
    assert not ok and "program: refused by the cloud" in notes


def test_custom_waves() -> None:
    assert [w["uid"] for w in custom_waves(LIBRARY, AQUARIUM)] == ["w-night", "w-day"]
    assert len(custom_waves(LIBRARY, "")) == 3
    assert custom_waves("junk", AQUARIUM) == []
    assert custom_waves(["junk", {"default": False}], "") == []


def test_program() -> None:
    program = program_of(AUTO["intervals"] + ["junk"], {"w-day": "new-1"})
    assert [i["wave_uid"] for i in program] == ["rs-1", "new-1", "w-night"]
    assert [i["start"] for i in program] == [0, 750, 1350]
    assert program_of(None, {}) == []
    renamed = renamed_auto(AUTO, {"w-day": "new-1"})
    assert renamed["intervals"][1]["wave_uid"] == "new-1"
    assert AUTO["intervals"][1]["wave_uid"] == "w-day"
    assert renamed_auto(AUTO, {}) is AUTO
    assert renamed_auto(None, {"a": "b"}) is None
    assert same_program(AUTO, renamed, {"w-day": "new-1"})
    assert not same_program(AUTO, renamed, {})
    assert not same_program(AUTO, {"intervals": []}, {})
    assert same_program(None, {"intervals": ["junk"]}, {})


async def test_backup() -> None:
    cloud = FakeCloudApi(library=_library())
    backup = await backup_waves(cloud, AQUARIUM)
    assert backup is not None and backup["aquarium_uid"] == AQUARIUM
    assert [w["name"] for w in backup["library"]] == ["Nuit", "Journee"]
    cloud.unreadable = True
    assert await backup_waves(cloud, AQUARIUM) is None


# -- restore -------------------------------------------------------------------------------


async def test_nothing_lost() -> None:
    cloud = FakeCloudApi(library=_library())
    backup = await backup_waves(cloud, AQUARIUM)
    assert backup is not None
    ok, notes, renamed = await restore_waves(cloud, HWID, backup, AUTO)
    assert ok and renamed == {}
    # No wave written; the program posted, the pumps synced
    assert _sent(cloud, "/reef-wave/library") == []
    [program] = _sent(cloud, f"/reef-wave/schedule/{HWID}")
    assert [i["wave_uid"] for i in program["intervals"]] == ["rs-1", "w-day", "w-night"]
    assert _sent(cloud, f"/reef-wave/{AQUARIUM}/sync") == [{}]
    assert notes == ["program: 3 interval(s) posted", "programs pushed to the pumps"]


async def test_settings_of_the_pump_lost() -> None:
    cloud = FakeCloudApi(library=_library())
    backup = await backup_waves(cloud, AQUARIUM)
    assert backup is not None
    # The delete took the pump out of its waves
    for wave in cloud.library:
        wave["pump_settings"] = [s for s in wave["pump_settings"] if s["hwid"] != HWID]
    ok, notes, _ = await restore_waves(cloud, HWID, backup, AUTO)
    assert ok
    [night] = _sent(cloud, "/reef-wave/library/w-night")
    # The other pump keeps its own
    assert night["pump_settings"] == [
        {"hwid": OTHER, "fti": 30, "rti": 30, "sync": True},
        {"hwid": HWID, "fti": 40, "rti": 60, "sync": True},
    ]
    assert (
        night["name"] == "Nuit" and night["frt"] == 10 and "aquarium_uid" not in night
    )
    assert "wave Journee: settings of the pump put back" in notes


async def test_waves_lost() -> None:
    cloud = FakeCloudApi(library=_library())
    backup = await backup_waves(cloud, AQUARIUM)
    assert backup is not None
    cloud.library = [w for w in _library() if w["uid"] not in ("w-day", "w-night")]
    ok, notes, renamed = await restore_waves(cloud, HWID, backup, AUTO)
    assert ok
    created = _sent(cloud, "/reef-wave/library")
    assert [w["name"] for w in created] == ["Nuit", "Journee"]
    assert created[1]["aquarium_uid"] == AQUARIUM and created[1]["type"] == "ra"
    assert created[1]["pump_settings"][0]["fti"] == 100
    # The program uses them under their new uid
    assert set(renamed) == {"w-day", "w-night"}
    [program] = _sent(cloud, f"/reef-wave/schedule/{HWID}")
    assert [i["wave_uid"] for i in program["intervals"]] == [
        "rs-1",
        renamed["w-day"],
        renamed["w-night"],
    ]
    assert "wave Nuit: created again" in notes


async def test_refusals() -> None:
    cloud = FakeCloudApi(library=_library())
    backup = await backup_waves(cloud, AQUARIUM)
    assert backup is not None
    # Unreadable library
    cloud.unreadable = True
    ok, notes, _ = await restore_waves(cloud, HWID, backup, AUTO)
    assert not ok and notes == ["wave library unreadable"]
    # Every write refused
    cloud = FakeCloudApi(
        library=[w for w in _library() if w["uid"] != "w-night"],
        refuse={
            "/reef-wave/library",
            f"/reef-wave/schedule/{HWID}",
            f"/reef-wave/{AQUARIUM}/sync",
        },
    )
    cloud.library[1]["pump_settings"] = []
    cloud.refuse.add("/reef-wave/library/w-day")
    ok, notes, renamed = await restore_waves(cloud, HWID, backup, AUTO)
    assert not ok and renamed == {}
    assert notes == [
        "wave Nuit: not created again",
        "wave Journee: settings of the pump not put back",
        "program: refused by the cloud",
        "sync refused by the cloud",
    ]


async def test_created_wave_not_found() -> None:
    cloud = FakeCloudApi(library=_library())
    backup = await backup_waves(cloud, AQUARIUM)
    assert backup is not None
    cloud.library = [w for w in _library() if w["uid"] != "w-night"]

    async def _created_elsewhere(
        action: str, payload: Any = None, method: str = "post"
    ) -> Any:
        cloud.calls.append((action, payload, method))
        return {"status": 200}

    cloud.http_send = _created_elsewhere  # type: ignore[method-assign]
    ok, notes, renamed = await restore_waves(cloud, HWID, backup, None)
    assert not ok and renamed == {}
    assert "wave Nuit: new uid not found" in notes
    # No program to post
    assert _sent(cloud, f"/reef-wave/schedule/{HWID}") == []
    # No aquarium: nothing to sync
    ok, _, _ = await restore_waves(
        cloud, HWID, {"aquarium_uid": "", "library": []}, None
    )
    assert ok and not any(
        "sync" in c[0]
        for c in cloud.calls
        if c[0].endswith("/sync") and c[0] != f"/reef-wave/{AQUARIUM}/sync"
    )


# -- in the capture -----------------------------------------------------------------------


def _dev() -> DeviceKeys:
    return DeviceKeys(
        hwid=HWID, ip="192.0.2.10", type="reef-wave", model="RSWAVE45",
        name="Wave", aquarium_uid=AQUARIUM,
    )  # fmt: skip


async def _no_sleep(_s: float) -> None:
    return None


async def _capture(
    hass: HomeAssistant, tmp_path: Path, http: FakeHttp, cloud: FakeCloudApi
) -> tuple[CaptureReport, SnapshotStore]:
    snapshots = SnapshotStore(hass, tmp_path)
    report = await acquire_keys(
        cast(Any, cloud),
        cast(Any, http),
        _dev(),
        KeyStore(hass),
        snapshots,
        sleep=_no_sleep,
    )
    return report, snapshots


async def test_capture_saves_the_waves_before_the_delete(
    hass: HomeAssistant, tmp_path: Path
) -> None:
    cloud = FakeCloudApi(library=_library())
    http = FakeHttp({"/mode": {"mode": "auto"}, "/auto": AUTO})
    report, snapshots = await _capture(hass, tmp_path, http, cloud)
    assert report.ok and report.cloud_restored is True and report.restored is True
    # The library read before the delete
    kinds = [(c[0], c[2]) for c in cloud.calls]
    assert kinds.index(("/reef-wave/library", "get")) < kinds.index(
        (f"/device/{HWID}", "delete")
    )
    # The cloud put the program back: the pump is not written
    assert http.writes == []
    assert "programs pushed to the pumps" in report.notes
    assert not snapshots.pending_path(HWID).exists()


async def test_capture_stops_when_the_waves_cannot_be_saved(
    hass: HomeAssistant, tmp_path: Path
) -> None:
    cloud = FakeCloudApi(library=_library())
    cloud.unreadable = True
    http = FakeHttp({"/mode": {"mode": "auto"}, "/auto": AUTO})
    report, snapshots = await _capture(hass, tmp_path, http, cloud)
    assert not report.ok and report.error == "wave_backup_failed"
    # Nothing deleted
    assert not any(c[2] == "delete" for c in cloud.calls)
    # The local snapshot is kept, without waves: saved at the next attempt
    pending = json.loads(snapshots.pending_path(HWID).read_text(encoding="utf-8"))
    assert pending["cloud"] == {}
    cloud.unreadable = False
    report, snapshots = await _capture(hass, tmp_path, http, cloud)
    assert report.ok and report.cloud_restored is True


async def test_capture_writes_the_pump_when_the_cloud_did_not(
    hass: HomeAssistant, tmp_path: Path
) -> None:
    cloud = FakeCloudApi(library=_library(), refuse={f"/reef-wave/{AQUARIUM}/sync"})
    http = FakeHttp({"/mode": {"mode": "auto"}})
    # Before; then wiped by the cloud at the new connection
    http.sequence["/auto"] = [AUTO, {"intervals": []}]
    report, snapshots = await _capture(hass, tmp_path, http, cloud)
    assert report.ok and report.cloud_restored is False
    assert report.restored is True and report.changes == ["/auto"]
    assert any(w[0] == "/auto/apply" for w in http.writes)
    assert report.notes[-1] == "program written on the pump"
    # The cloud copy is not sure: the snapshot is kept
    assert snapshots.pending_path(HWID).exists()
    saved = json.loads(snapshots.pending_path(HWID).read_text(encoding="utf-8"))
    assert [w["name"] for w in saved["cloud"][CLOUD_WAVES]["library"]] == [
        "Nuit",
        "Journee",
    ]


async def test_capture_pump_not_written_and_unreadable(
    hass: HomeAssistant, tmp_path: Path, monkeypatch: Any
) -> None:
    # No real wait between the retries
    monkeypatch.setattr(capture_mod.asyncio, "sleep", _no_sleep)
    cloud = FakeCloudApi(library=_library())
    http = FakeHttp({"/mode": {"mode": "auto"}}, refuse={"/auto/init"})
    http.sequence["/auto"] = [AUTO, {"intervals": []}]
    # Restores retried while the pump rejoins: none
    report, _ = await _capture(hass, tmp_path, http, cloud)
    assert report.restored is False
    assert report.notes[-1] == "program NOT written on the pump"
    # Unreadable after the keys
    http = FakeHttp({"/auto": AUTO, "/mode": {"mode": "auto"}})
    original = http.get_json
    calls = {"n": 0}

    async def _gone(endpoint: str, timeout: float = 5.0) -> Any:
        calls["n"] += 1
        # The first snapshot reads every endpoint once; then the pump is gone
        return await original(endpoint) if calls["n"] <= 9 else None

    http.get_json = _gone  # type: ignore[method-assign]
    report, _ = await _capture(hass, tmp_path / "b", http, cloud)
    assert report.error == "reread_failed"


def test_settle_is_long_enough() -> None:
    assert const.WAVE_SYNC_SETTLE_S >= const.DEVICE_SETTLE_S

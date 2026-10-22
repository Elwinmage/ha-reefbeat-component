"""Poseidon: device HTTP, keystore, snapshots, restore and key capture."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import aiohttp
import pytest
from homeassistant.core import HomeAssistant

from custom_components.redsea.poseidon import capture, const
from custom_components.redsea.poseidon.capture import (
    Snapshot,
    SnapshotStore,
    acquire_keys,
    diff_snapshots,
    endpoints_for,
    restore_device,
    restore_with_retries,
    rsrun_steps,
    rswave_steps,
    run_steps,
    take_snapshot,
)
from custom_components.redsea.poseidon.device_http import DeviceHttp
from custom_components.redsea.poseidon.keystore import DeviceKeys, KeyStore
from tests._poseidon_fakes import HWID, SECRET, FakeCloudApi, FakeHttp


@pytest.fixture(autouse=True)
def _no_waits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(const, "STEP_WAIT_S", 0)
    monkeypatch.setattr(const, "CLOUD_SETTLE_S", 0)
    monkeypatch.setattr(const, "DEVICE_SETTLE_S", 0)


async def _no_sleep(_s: float) -> None:
    return None


def _as_http(fake: FakeHttp) -> DeviceHttp:
    """FakeHttp duck-types DeviceHttp: hand it over where one is expected."""
    return cast(DeviceHttp, fake)


# ── DeviceHttp ──────────────────────────────────────────────────────────────


class _Resp:
    def __init__(self, status: int, body: str) -> None:
        self.status = status
        self._body = body

    async def text(self) -> str:
        return self._body

    async def json(self, content_type: Any = None) -> Any:
        return json.loads(self._body)

    async def __aenter__(self) -> _Resp:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return None


class _Session:
    """Answers by URL path; an exception instance is raised."""

    def __init__(self, answers: dict[str | tuple[str, str], Any]) -> None:
        self.answers = answers
        self.calls: list[tuple[str, str, Any]] = []

    def _answer(self, method: str, url: str, json_body: Any = None) -> _Resp:
        path = url.split("192.0.2.10", 1)[1]
        self.calls.append((method, path, json_body))
        answer = self.answers.get((method, path), self.answers.get(path))
        if isinstance(answer, BaseException):
            raise answer
        status, body = answer if answer is not None else (404, "")
        return _Resp(status, body)

    def get(self, url: str) -> _Resp:
        return self._answer("GET", url)

    def post(self, url: str, json: Any = None) -> _Resp:
        return self._answer("POST", url, json)

    def put(self, url: str, json: Any = None) -> _Resp:
        return self._answer("PUT", url, json)


async def test_device_http_get() -> None:
    session = _Session(
        {
            "/mode": (200, '{"mode": "auto"}'),
            "/text": (200, "plain"),
            "/empty": (200, ""),
            "/err": aiohttp.ClientError("down"),
        }
    )
    http = DeviceHttp(session, "192.0.2.10")  # type: ignore[arg-type]
    assert await http.get_json("/mode") == {"mode": "auto"}
    assert await http.get_json("/text") == "plain"
    assert await http.get_json("/empty") is None
    assert await http.get_json("/missing") is None
    assert await http.get_json("/err") is None


async def test_device_http_write_and_cloud() -> None:
    session = _Session(
        {
            ("POST", "/ok"): (200, "{}"),
            ("PUT", "/ok"): (204, ""),
            ("POST", "/bad"): (400, "nope"),
            ("POST", "/err"): TimeoutError(),
            "/cloud": (200, '{"url": "mqtt.reef-beat.com:1883"}'),
            ("POST", "/cloud"): (200, "{}"),
            ("POST", "/cloud/disable"): (200, "{}"),
            ("POST", "/cloud/enable"): (200, "{}"),
        }
    )
    http = DeviceHttp(session, "192.0.2.10")  # type: ignore[arg-type]
    assert await http.write_json("/ok", {"a": 1}) is True
    assert await http.write_json("/ok", {"a": 1}, "PUT") is True
    assert await http.write_json("/bad") is False
    assert await http.write_json("/err") is False
    assert await http.get_cloud() == {"url": "mqtt.reef-beat.com:1883"}
    assert await http.set_cloud("h:1884", "k", SECRET) is True
    assert [c[1] for c in session.calls[-3:]] == [
        "/cloud/disable",
        "/cloud",
        "/cloud/enable",
    ]
    assert session.calls[-2][2] == {
        "url": "h:1884",
        "api_key": "k",
        "api_secret": SECRET,
    }


async def test_device_http_set_cloud_enables_even_after_refusal() -> None:
    session = _Session(
        {
            ("POST", "/cloud/disable"): (200, "{}"),
            ("POST", "/cloud"): (400, "neither url or api_key"),
            ("POST", "/cloud/enable"): (200, "{}"),
            "/cloud": (200, "[1]"),
        }
    )
    http = DeviceHttp(session, "192.0.2.10")  # type: ignore[arg-type]
    assert await http.set_cloud("h:1884", "k", SECRET) is False
    assert session.calls[-1][1] == "/cloud/enable"
    # Not a dict: no cloud payload
    assert await http.get_cloud() is None


# ── Keystore ────────────────────────────────────────────────────────────────


async def test_keystore_round_trip(hass: HomeAssistant) -> None:
    store = KeyStore(hass)
    await store.async_load()
    assert store.devices == {}
    dev = DeviceKeys(hwid=HWID, api_key="k", api_secret=SECRET, name="Wave")
    assert dev.has_keys
    await store.async_upsert(dev)
    await store.async_upsert(DeviceKeys(hwid="aabbccddeeff"))
    assert dev.updated_at
    assert [d.hwid for d in store.with_keys()] == [HWID]
    assert store.as_json()["devices"][HWID]["api_secret"] == SECRET

    again = KeyStore(hass)
    await again.async_load()
    assert again.get(HWID) == dev
    assert again.get("nope") is None


async def test_keystore_ignores_unknown_fields_and_bad_rows(
    hass: HomeAssistant,
) -> None:
    store = KeyStore(hass)
    await store._store.async_save(
        {"devices": {HWID: {"api_key": "k", "future_field": 1}, "bad": "row"}}
    )
    await store.async_load()
    assert list(store.devices) == [HWID]
    assert store.get(HWID).api_key == "k"  # type: ignore[union-attr]
    assert not store.get(HWID).has_keys  # type: ignore[union-attr]


# ── Snapshots ───────────────────────────────────────────────────────────────


def test_endpoints_for() -> None:
    wave = endpoints_for("reef-wave")
    assert wave[:6] == capture.COMMON_ENDPOINTS
    assert "/auto" in wave and len(wave) == len(set(wave))
    assert "/logging" not in endpoints_for("unknown")
    assert "/configuration" in endpoints_for("unknown")


async def test_snapshot_store(hass: HomeAssistant, tmp_path: Path) -> None:
    store = SnapshotStore(hass, tmp_path)
    assert await store.async_pending(HWID) is None
    snap = Snapshot(
        hwid=HWID,
        taken_at="2026-10-14T21:00:00+02:00",
        ip="192.0.2.10",
        type="reef-wave",
        endpoints={"/mode": {"mode": "off"}},
    )
    path = await store.async_save(snap)
    assert path == store.pending_path(HWID)
    assert len(list((tmp_path / HWID).iterdir())) == 2  # pending + history
    again = await store.async_pending(HWID)
    assert again is not None and again.endpoints == snap.endpoints and again.was_off
    store.pending_path(HWID).write_text("{not json", encoding="utf-8")
    assert await store.async_pending(HWID) is None
    await store.async_drop(HWID)
    await store.async_drop(HWID)  # already gone
    assert not store.pending_path(HWID).exists()


async def test_take_snapshot_and_diff() -> None:
    dev = DeviceKeys(hwid=HWID, ip="192.0.2.10", type="reef-run", model="RSRUN")
    http = FakeHttp({"/mode": {"mode": "auto"}, "/pump/settings": {"pump_1": {}}})
    before = await take_snapshot(http, dev)  # type: ignore[arg-type]
    assert set(before.endpoints) == {"/mode", "/pump/settings"}
    assert not before.was_off
    after = Snapshot(
        hwid=HWID,
        taken_at="t",
        ip="",
        endpoints={"/mode": {"mode": "auto"}, "/cloud": {"x": 1}, "/new": 1},
    )
    assert diff_snapshots(before, after) == ["/new", "/pump/settings"]


# ── Restore ─────────────────────────────────────────────────────────────────


def test_rsrun_steps() -> None:
    snap = Snapshot(
        hwid=HWID,
        taken_at="t",
        ip="",
        type="reef-run",
        endpoints={
            "/pump/settings": {
                "pump_1": {"schedule": [1], "schedule_enabled": False},
                "pump_2": {"schedule": None},
                "pump_3": "not a dict",
                "other": {"schedule": [2]},
            }
        },
    )
    steps = rsrun_steps(snap)
    assert len(steps) == 1
    assert steps[0].payload == {"pump_1": {"schedule_enabled": False, "schedule": [1]}}
    assert steps[0].method == "PUT"
    assert rsrun_steps(Snapshot(hwid=HWID, taken_at="t", ip="")) == []


def test_rswave_steps() -> None:
    snap = Snapshot(
        hwid=HWID,
        taken_at="t",
        ip="",
        type="reef-wave",
        endpoints={"/auto": {"intervals": [{"st": 0}, {"st": 600}, {"st": 900}]}},
    )
    steps = rswave_steps(snap)
    assert [s.endpoint for s in steps] == [
        "/auto/init",
        "/auto",
        "/auto",
        "/auto",
        "/auto/complete",
        "/auto/apply",
    ]
    # One interval per POST, one transaction uid
    assert all(len(s.payload["intervals"]) == 1 for s in steps[1:4])
    uids = {steps[0].payload["uid"], steps[4].payload["uid"], steps[5].payload["uid"]}
    assert len(uids) == 1
    for endpoints in ({}, {"/auto": "x"}, {"/auto": {"intervals": []}}):
        assert (
            rswave_steps(Snapshot(hwid=HWID, taken_at="t", ip="", endpoints=endpoints))
            == []
        )


async def test_run_steps_stops_at_first_refusal() -> None:
    http = FakeHttp(refuse={"/b"})
    steps = [
        capture.RestoreStep("/a", 1, wait=0.0, reread="/a"),
        capture.RestoreStep("/b", 2),
        capture.RestoreStep("/c", 3),
    ]
    assert await run_steps(http, steps) is False  # type: ignore[arg-type]
    assert [w[0] for w in http.writes] == ["/a", "/b"]
    steps[0].wait = 0.001
    assert await run_steps(FakeHttp(), steps[:1]) is True  # type: ignore[arg-type]


async def test_restore_device_switches_back_on_unless_off_before() -> None:
    snap = Snapshot(
        hwid=HWID,
        taken_at="t",
        ip="",
        type="reef-wave",
        endpoints={"/auto": {"intervals": [{"st": 0}]}, "/mode": {"mode": "auto"}},
    )
    http = FakeHttp({"/mode": {"mode": "off"}})
    assert await restore_device(http, snap) is True  # type: ignore[arg-type]
    assert http.writes[-1][0] == "/on"
    # Off before: left off
    snap.endpoints["/mode"] = {"mode": "off"}
    http = FakeHttp({"/mode": {"mode": "off"}})
    assert await restore_device(http, snap) is True  # type: ignore[arg-type]
    assert all(w[0] != "/on" for w in http.writes)
    # On already: nothing to do
    snap.endpoints["/mode"] = {"mode": "auto"}
    http = FakeHttp({"/mode": {"mode": "auto"}})
    await restore_device(http, snap)  # type: ignore[arg-type]
    assert all(w[0] != "/on" for w in http.writes)
    # No handler, or nothing to replay
    assert (
        await restore_device(
            _as_http(FakeHttp()),
            Snapshot(hwid=HWID, taken_at="t", ip="", type="reef-mat"),
        )
        is False
    )
    assert (
        await restore_device(
            _as_http(FakeHttp()),
            Snapshot(hwid=HWID, taken_at="t", ip="", type="reef-run"),
        )
        is False
    )


async def test_restore_with_retries() -> None:
    snap = Snapshot(
        hwid=HWID,
        taken_at="t",
        ip="",
        type="reef-wave",
        endpoints={"/auto": {"intervals": [{"st": 0}]}},
    )
    http = FakeHttp({"/mode": {"mode": "auto"}})
    # Unreachable first, then back
    http.sequence["/mode"] = [None]
    assert await restore_with_retries(http, snap, retries=2, interval=0) is True  # type: ignore[arg-type]
    http = FakeHttp({}, refuse={"/auto/init"})
    assert await restore_with_retries(http, snap, retries=2, interval=0) is False  # type: ignore[arg-type]


# ── Key capture ─────────────────────────────────────────────────────────────


def _dev(device_type: str = "reef-wave") -> DeviceKeys:
    return DeviceKeys(
        hwid=HWID,
        ip="192.0.2.10",
        type=device_type,
        model="RSWAVE45",
        name="Wave",
        aquarium_uid="aq-1",
    )


async def _capture(
    hass: HomeAssistant,
    tmp_path: Path,
    http: FakeHttp,
    cloud: FakeCloudApi | None = None,
    dev: DeviceKeys | None = None,
) -> tuple[capture.CaptureReport, KeyStore, SnapshotStore, FakeCloudApi]:
    keystore = KeyStore(hass)
    snapshots = SnapshotStore(hass, tmp_path)
    cloud = cloud or FakeCloudApi()
    report = await acquire_keys(
        cloud,
        _as_http(http),
        dev or _dev(),
        keystore,
        snapshots,
        sleep=_no_sleep,  # type: ignore[arg-type]
    )
    return report, keystore, snapshots, cloud


async def test_capture_unchanged_device(hass: HomeAssistant, tmp_path: Path) -> None:
    http = FakeHttp({"/mode": {"mode": "auto"}, "/cloud": {"url": "x"}})
    report, keystore, snapshots, cloud = await _capture(hass, tmp_path, http)
    assert report.ok and not report.error and report.changes == []
    keys = keystore.get(HWID)
    assert keys is not None and keys.api_secret == SECRET and keys.mqtt_url
    assert [c[2] for c in cloud.calls] == ["delete", "post"]
    assert cloud.calls[1][1]["aquarium_uid"] == "aq-1"
    # Pushed to the device for the Red Sea broker
    assert http.cloud_writes == [("mqtt.reef-beat.com:1883", "key-1", SECRET)]
    # Nothing changed: the pending snapshot is dropped
    assert not snapshots.pending_path(HWID).exists()


async def test_capture_restores_a_wave(hass: HomeAssistant, tmp_path: Path) -> None:
    http = FakeHttp({"/mode": {"mode": "auto"}})
    http.sequence["/auto"] = [{"intervals": [{"st": 0}]}, {"intervals": []}]
    report, _keystore, snapshots, _cloud = await _capture(hass, tmp_path, http)
    assert report.ok and report.changes == ["/auto"] and report.restored is True
    assert any(w[0] == "/auto/apply" for w in http.writes)
    assert not snapshots.pending_path(HWID).exists()


async def test_capture_reports_other_families(
    hass: HomeAssistant, tmp_path: Path
) -> None:
    http = FakeHttp({"/mode": {"mode": "auto"}})
    http.sequence["/configuration"] = [{"a": 1}, {"a": 2}]
    report, _keystore, snapshots, _cloud = await _capture(
        hass, tmp_path, http, dev=_dev("reef-mat")
    )
    assert (
        report.ok and report.changes == ["/configuration"] and report.restored is None
    )
    # Kept: what changed is to be checked
    assert snapshots.pending_path(HWID).exists()


async def test_capture_reuses_pending_snapshot(
    hass: HomeAssistant, tmp_path: Path
) -> None:
    snapshots = SnapshotStore(hass, tmp_path)
    await snapshots.async_save(
        Snapshot(
            hwid=HWID,
            taken_at="t",
            ip="",
            type="reef-wave",
            endpoints={"/mode": {"mode": "auto"}},
        )
    )
    http = FakeHttp({"/mode": {"mode": "auto"}})
    report = await acquire_keys(
        FakeCloudApi(),
        _as_http(http),
        _dev(),
        KeyStore(hass),
        snapshots,
        sleep=_no_sleep,  # type: ignore[arg-type]
    )
    assert report.ok and report.snapshot == str(snapshots.pending_path(HWID))


@pytest.mark.parametrize(
    ("http", "cloud", "error", "ok"),
    [
        (FakeHttp({}), FakeCloudApi(), "snapshot_failed", False),
        (
            FakeHttp({"/mode": {}}),
            FakeCloudApi(delete_status=500),
            "cloud_delete_failed",
            False,
        ),
        (
            FakeHttp({"/mode": {}}),
            FakeCloudApi(created="none"),
            "cloud_create_failed",
            False,
        ),
        (
            FakeHttp({"/mode": {}}),
            FakeCloudApi(created={"api_key": "k"}),
            "no_credentials",
            False,
        ),
        (
            FakeHttp({"/mode": {}}, cloud={}, set_cloud_ok=False),
            FakeCloudApi(),
            "push_failed",
            True,
        ),
    ],
)
async def test_capture_failures(
    hass: HomeAssistant,
    tmp_path: Path,
    http: FakeHttp,
    cloud: FakeCloudApi,
    error: str,
    ok: bool,
) -> None:
    report, keystore, *_ = await _capture(hass, tmp_path, http, cloud)
    assert report.error == error and report.ok is ok
    # Keys are stored as soon as they are known
    assert (keystore.get(HWID) is not None) is ok


async def test_capture_device_gone_after(hass: HomeAssistant, tmp_path: Path) -> None:
    http = FakeHttp({})
    http.sequence["/mode"] = [{"mode": "auto"}]
    report, *_ = await _capture(hass, tmp_path, http)
    assert report.ok and report.error == "reread_failed"

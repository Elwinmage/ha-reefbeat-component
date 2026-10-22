"""Poseidon manager: devices, statuses, switching, revert and adding."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea.poseidon import const, manager
from custom_components.redsea.poseidon.capture import CaptureReport
from custom_components.redsea.poseidon.keystore import DeviceKeys
from custom_components.redsea.poseidon.manager import (
    STATUS_KEYS_NEEDED,
    STATUS_KEYS_OK,
    STATUS_NO_CLOUD,
    STATUS_NOT_IN_ACCOUNT,
    STATUS_POSEIDON,
    STATUS_UNREACHABLE,
    Poseidon,
    broker_of,
    get_poseidon,
    is_poseidon_entry,
)
from tests._poseidon_fakes import (
    HWID,
    SECRET,
    FakeCoordinator,
    FakeHttp,
    cloud_coordinator,
)

DOMAIN = "redsea"
RELAY_URL = "192.0.2.1:1884"


@pytest.fixture(autouse=True)
def _no_settle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(const, "SWITCH_SETTLE_S", 0)


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Poseidon",
        unique_id="poseidon",
        data={
            "poseidon": True,
            "port": 1884,
            "host": "192.0.2.1",
            "cloud_account": "cloud-entry",
        },
    )


def _poseidon(
    hass: HomeAssistant,
    coordinators: dict[str, Any] | None = None,
    https: dict[str, FakeHttp] | None = None,
) -> Poseidon:
    hass.data[DOMAIN] = coordinators if coordinators is not None else {}
    poseidon = Poseidon(hass, _entry())
    https = https or {}
    poseidon.http = lambda ip: https.setdefault(ip, FakeHttp(ip=ip))  # type: ignore[method-assign]
    return poseidon


def _keys(**kwargs: Any) -> DeviceKeys:
    return DeviceKeys(
        hwid=HWID, api_key="key", api_secret=SECRET, ip="192.0.2.10", **kwargs
    )


def test_helpers(hass: HomeAssistant) -> None:
    assert is_poseidon_entry(_entry())
    assert not is_poseidon_entry(MockConfigEntry(domain=DOMAIN, data={}))
    assert broker_of(None) == ""
    assert broker_of({"url": " MQTT://Host:1884/ "}) == "host:1884"
    assert get_poseidon(hass) is None


def test_local_devices_and_lookup(hass: HomeAssistant) -> None:
    wave = FakeCoordinator()
    cloud = cloud_coordinator()
    virtual = FakeCoordinator(model_id="v", title="virtual_led-1")
    poseidon = _poseidon(
        hass,
        {"w": wave, "c": cloud, "v": virtual, "x": object()},
    )
    assert poseidon.local_devices() == [wave]
    assert poseidon.coordinator(HWID) is wave
    assert poseidon.coordinator("nope") is None
    assert poseidon.advertised_url == RELAY_URL


def test_cloud_device_and_device_keys(hass: HomeAssistant) -> None:
    wave = FakeCoordinator(cloud={"url": "x"})
    cloud = cloud_coordinator(
        devices=[
            "junk",
            {
                "hwid": HWID.upper(),
                "name": "Left",
                "aquarium_uid": "aq",
                "type": "reef-wave",
            },
        ]
    )
    poseidon = _poseidon(hass, {"w": wave, "cloud-entry": cloud})
    assert poseidon.cloud_device(HWID)["name"] == "Left"  # type: ignore[index]
    assert poseidon.cloud_device("other") is None
    dev = poseidon.device_keys(wave)
    assert (dev.name, dev.aquarium_uid, dev.type, dev.ip) == (
        "Left",
        "aq",
        "reef-wave",
        "192.0.2.10",
    )
    assert poseidon.cached_cloud(HWID) == {"url": "x"}
    assert poseidon.cached_cloud("other") is None
    # No cloud account loaded, nor its device list
    alone = _poseidon(hass, {"w": FakeCoordinator(cloud="bad")})  # type: ignore[arg-type]
    assert alone.cloud_device(HWID) is None
    dev = alone.device_keys(alone.coordinator(HWID))
    assert dev.name == "Wave left" and dev.type == "reef-wave"
    assert alone.cached_cloud(HWID) is None
    cloud.devices = None
    assert _poseidon(hass, {"cloud-entry": cloud}).cloud_device(HWID) is None


@pytest.mark.parametrize(
    ("cloud", "keys", "record", "status"),
    [
        (None, False, True, STATUS_UNREACHABLE),
        ({"url": RELAY_URL}, True, True, STATUS_POSEIDON),
        (
            {"url": "mqtt.reef-beat.com:1883", "api_key": "k"},
            True,
            False,
            STATUS_KEYS_OK,
        ),
        (
            {"url": "mqtt.reef-beat.com:1883", "api_key": ""},
            False,
            True,
            STATUS_NO_CLOUD,
        ),
        (
            {"url": "mqtt.reef-beat.com:1883", "api_key": "k"},
            False,
            False,
            STATUS_NOT_IN_ACCOUNT,
        ),
        (
            {"url": "mqtt.reef-beat.com:1883", "api_key": "k"},
            False,
            True,
            STATUS_KEYS_NEEDED,
        ),
    ],
)
async def test_status(
    hass: HomeAssistant, cloud: Any, keys: bool, record: bool, status: str
) -> None:
    wave = FakeCoordinator()
    devices = [{"hwid": HWID, "aquarium_uid": "aq"}] if record else []
    poseidon = _poseidon(
        hass,
        {"w": wave, "cloud-entry": cloud_coordinator(devices=devices)},
        {"192.0.2.10": FakeHttp(cloud=cloud)},
    )
    if keys:
        poseidon.keystore.devices[HWID] = _keys()
    assert await poseidon.async_status(wave) == status


async def test_switch_on_and_off(hass: HomeAssistant) -> None:
    signals: list[Any] = []
    wave = FakeCoordinator(_ip="192.0.2.11")
    http = FakeHttp(cloud={"url": "x"}, ip="192.0.2.11")
    poseidon = _poseidon(hass, {"w": wave}, {"192.0.2.11": http})
    poseidon.keystore.devices[HWID] = _keys(mqtt_url="custom:1883")
    poseidon._signal = lambda force=False: signals.append(force)  # type: ignore[method-assign]
    assert await poseidon.async_switch(HWID, True) is True
    assert http.cloud_writes[-1] == (RELAY_URL, "key", SECRET)
    assert wave.fetched == ["/cloud"] and signals == [True]
    # The device moved: its new address is kept
    assert poseidon.keystore.get(HWID).ip == "192.0.2.11"  # type: ignore[union-attr]
    assert await poseidon.async_switch(HWID, False) is True
    assert http.cloud_writes[-1][0] == "custom:1883"
    # Unknown device or no keys
    assert await poseidon.async_switch("other", True) is False
    poseidon.keystore.devices[HWID].api_secret = ""
    assert await poseidon.async_switch(HWID, True) is False


def test_normal_url(hass: HomeAssistant) -> None:
    poseidon = _poseidon(hass)
    assert poseidon.normal_url(_keys()) == "mqtt.reef-beat.com:1883"
    assert poseidon.normal_url(_keys(mqtt_url=RELAY_URL)) == "mqtt.reef-beat.com:1883"
    assert poseidon.normal_url(_keys(mqtt_url="other:1883")) == "other:1883"


async def test_revert_all(hass: HomeAssistant) -> None:
    https = {
        "192.0.2.10": FakeHttp(cloud={"url": RELAY_URL}),
        "192.0.2.20": FakeHttp(cloud=None),
        "192.0.2.30": FakeHttp(cloud={"url": "mqtt.reef-beat.com:1883"}),
        "192.0.2.40": FakeHttp(cloud={"url": RELAY_URL}, set_cloud_ok=False),
    }
    poseidon = _poseidon(hass, {}, https)
    poseidon.keystore.devices = {
        "a": DeviceKeys(
            hwid="a", name="A", ip="192.0.2.10", api_key="k", api_secret=SECRET
        ),
        "b": DeviceKeys(
            hwid="b", name="B", ip="192.0.2.20", api_key="k", api_secret=SECRET
        ),
        "c": DeviceKeys(hwid="c", ip="192.0.2.30", api_key="k", api_secret=SECRET),
        "d": DeviceKeys(hwid="d", ip="192.0.2.40", api_key="k", api_secret=SECRET),
        "e": DeviceKeys(hwid="e", api_key="k", api_secret=SECRET),  # no address
    }
    assert await poseidon.async_revert_all() == ["B", "d"]
    assert https["192.0.2.10"].cloud_writes == [
        ("mqtt.reef-beat.com:1883", "k", SECRET)
    ]
    assert https["192.0.2.30"].cloud_writes == []


async def test_add_devices(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    ready = FakeCoordinator(model_id="aa", _ip="192.0.2.10", cloud={"url": "x"})
    needs = FakeCoordinator(model_id="bb", _ip="192.0.2.20", title="Run")
    poseidon = _poseidon(
        hass,
        {"r": ready, "n": needs, "cloud-entry": cloud_coordinator()},
        {
            "192.0.2.10": FakeHttp(cloud={"url": "x"}),
            "192.0.2.20": FakeHttp(cloud={"url": "x"}, set_cloud_ok=False),
        },
    )
    poseidon.keystore.devices["aa"] = DeviceKeys(
        hwid="aa", api_key="k", api_secret=SECRET
    )

    async def fake_acquire(
        cloud: Any, http: Any, dev: DeviceKeys, *args: Any
    ) -> CaptureReport:
        dev.api_key, dev.api_secret = "k2", SECRET
        poseidon.keystore.devices[dev.hwid] = dev
        return CaptureReport(hwid=dev.hwid, name=dev.name, ok=True)

    monkeypatch.setattr(manager, "acquire_keys", fake_acquire)
    seen: list[str] = []

    async def on_device(report: CaptureReport) -> None:
        seen.append(report.hwid)

    reports = await poseidon.async_add_devices(["aa", "bb", "zz"], on_device)
    assert [(r.hwid, r.ok, r.error) for r in reports] == [
        ("aa", True, ""),
        ("bb", True, "switch_failed"),
    ]
    assert seen == ["aa", "bb"]
    # A sync callback works too, and no cloud account means no capture
    poseidon.cloud_entry_id = "gone"
    poseidon.keystore.devices.pop("bb")
    reports = await poseidon.async_add_devices(["bb"], lambda r: seen.append(r.error))
    assert reports[0].error == "no_cloud_account" and seen[-1] == "no_cloud_account"


async def test_switch_devices_and_dynamic_switches(hass: HomeAssistant) -> None:
    registry = dr.async_get(hass)
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    device = registry.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, HWID)}
    )
    poseidon = _poseidon(hass)
    # A device of the same identifiers owned by Poseidon is not the one
    assert isinstance(poseidon.entry, MockConfigEntry)
    poseidon.entry.add_to_hass(hass)
    registry.async_get_or_create(
        config_entry_id=poseidon.entry.entry_id, identifiers={(DOMAIN, "owned")}
    )
    poseidon.keystore.devices = {
        HWID: _keys(),
        "unregistered": DeviceKeys(hwid="unregistered", api_key="k", api_secret=SECRET),
        "owned": DeviceKeys(hwid="owned", api_key="k", api_secret=SECRET),
    }
    assert poseidon.switch_devices() == {HWID: device}
    poseidon.async_add_new_switches()  # no platform yet: nothing
    added: list[dict[str, Any]] = []
    poseidon.async_set_switch_adder(added.append)
    poseidon.async_add_new_switches()  # nothing new
    assert added == [{HWID: device}]


async def test_refresh_tick_and_signal(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[str] = []
    monkeypatch.setattr(manager, "async_dispatcher_send", lambda h, s: sent.append(s))
    ok = FakeCoordinator()
    broken = FakeCoordinator(model_id="bb", fail_fetch=True)
    poseidon = _poseidon(hass, {"a": ok, "b": broken})
    poseidon.keystore.devices = {
        HWID: _keys(),
        "bb": DeviceKeys(hwid="bb", api_key="k", api_secret=SECRET),
        "cc": DeviceKeys(hwid="cc", api_key="k", api_secret=SECRET),  # not loaded
    }
    await poseidon._refresh_tick()
    assert ok.fetched == ["/cloud"] and sent == [const.SIGNAL_POSEIDON_UPDATE]
    # Traffic signals are throttled
    poseidon._on_traffic(HWID, "up")
    assert len(sent) == 1
    poseidon._last_signal = 0
    poseidon._on_traffic(HWID, "up")
    assert len(sent) == 2


async def test_on_connect_refreshes_api_key(hass: HomeAssistant) -> None:
    poseidon = _poseidon(hass)
    poseidon.keystore.devices[HWID] = _keys()
    poseidon.keystore.async_upsert = AsyncMock()  # type: ignore[method-assign]
    poseidon._on_connect(HWID, {"password": "key"})
    poseidon._on_connect("unknown", {"password": "x"})
    poseidon._on_connect(HWID, {})
    await hass.async_block_till_done()
    poseidon.keystore.async_upsert.assert_not_called()
    poseidon._on_connect(HWID, {"password": "new-key"})
    await hass.async_block_till_done()
    assert poseidon.keystore.get(HWID).api_key == "new-key"  # type: ignore[union-attr]
    poseidon.keystore.async_upsert.assert_awaited_once()


async def test_traffic_default(hass: HomeAssistant) -> None:
    poseidon = _poseidon(hass)
    assert poseidon.traffic(HWID).last_up is None


async def test_start_and_stop(hass: HomeAssistant) -> None:
    poseidon = _poseidon(hass)
    poseidon.relay.async_start = AsyncMock()  # type: ignore[method-assign]
    poseidon.relay.async_stop = AsyncMock()  # type: ignore[method-assign]
    await poseidon.async_start()
    assert poseidon._unsub_refresh is not None
    await poseidon.async_stop()
    await poseidon.async_stop()
    assert poseidon._unsub_refresh is None
    assert poseidon.relay.async_stop.await_count == 2


def _debug_poseidon(hass: HomeAssistant, **options: Any) -> Poseidon:
    """A Poseidon whose entry carries options."""
    hass.data[DOMAIN] = {}
    base = _entry()
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="poseidon", data=dict(base.data), options=options
    )
    return Poseidon(hass, entry)


async def test_watchdog_key_and_device_http(hass: HomeAssistant) -> None:
    assert _poseidon(hass).watchdog_key == ""
    poseidon = _debug_poseidon(hass, watchdog_key="abcdefghij012345")
    assert poseidon.watchdog_key == "abcdefghij012345"
    http = poseidon.http("192.0.2.9")
    assert isinstance(http, manager.DeviceHttp) and http.ip == "192.0.2.9"


async def test_silent_device_issue(hass: HomeAssistant) -> None:
    from datetime import timedelta

    from homeassistant.helpers import issue_registry as ir
    from homeassistant.util import dt as dt_util

    wave = FakeCoordinator(cloud={"url": RELAY_URL})
    poseidon = _poseidon(hass, {"w": wave})
    poseidon._added["switch"] = {HWID}
    poseidon._started_at = dt_util.utcnow() - timedelta(hours=1)
    issue_id = f"{const.ISSUE_DEVICE_SILENT}_{HWID}"
    registry = ir.async_get(hass)

    # Nothing through the relay since the start: silent, named by its hwid
    poseidon._update_silent_issues()
    issue = registry.async_get_issue(DOMAIN, issue_id)
    assert issue is not None
    assert issue.translation_placeholders == {"name": HWID, "minutes": "10"}
    # Its keys give it a name
    poseidon.keystore.devices = {HWID: _keys(name="Wave")}
    poseidon._update_silent_issues()
    issue = registry.async_get_issue(DOMAIN, issue_id)
    assert issue is not None
    assert issue.translation_placeholders == {"name": "Wave", "minutes": "10"}
    # Traffic again: the issue goes
    poseidon.relay._seen(HWID, "up")
    poseidon._update_silent_issues()
    assert registry.async_get_issue(DOMAIN, issue_id) is None


async def test_is_alive(hass: HomeAssistant) -> None:
    from datetime import timedelta

    from homeassistant.util import dt as dt_util

    from custom_components.redsea.poseidon.relay import Traffic

    wave = FakeCoordinator(cloud={"url": RELAY_URL})
    normal = FakeCoordinator(model_id="bb", cloud={"url": "mqtt.reef-beat.com:1883"})
    poseidon = _poseidon(hass, {"w": wave, "n": normal})
    poseidon.keystore.devices = {
        HWID: _keys(name="Wave", type="reef-wave", mqtt_url="mqtt.example:1883"),
        "bb": DeviceKeys(hwid="bb", api_key="k", api_secret=SECRET),  # not relayed
        "cc": DeviceKeys(hwid="cc", api_key="k", api_secret=SECRET),  # not loaded
    }
    now = dt_util.utcnow()
    poseidon.relay.traffic[HWID] = Traffic(last_up=now, last_down=now)

    # An unreadable delay: the default one
    answer = poseidon.is_alive({"id": "r1", "minutes": "soon"})
    assert answer["id"] == "r1" and answer["ok"] is True
    assert list(answer["devices"]) == [HWID]
    assert answer["devices"][HWID] == {
        "name": "Wave",
        "type": "reef-wave",
        "ip": "192.0.2.10",
        "api_key": "key",
        "api_secret": SECRET,
        "mqtt_url": "mqtt.example:1883",
        "last_up": now.isoformat(),
        "last_down": now.isoformat(),
    }

    # Frames in one direction only, or too old: not alive
    poseidon.relay.traffic[HWID] = Traffic(last_up=now)
    answer = poseidon.is_alive({"id": "r2"})
    assert answer["ok"] is False and answer["devices"][HWID]["last_down"] is None
    old = now - timedelta(minutes=5)
    poseidon.relay.traffic[HWID] = Traffic(last_up=old, last_down=old)
    assert poseidon.is_alive({"id": "r3", "minutes": 1})["ok"] is False
    # 0 reads as unset: the default delay
    assert poseidon.is_alive({"id": "r4", "minutes": 0})["ok"] is True
    assert poseidon.is_alive({"id": "r5", "minutes": 10})["ok"] is True
    # Nothing relayed at all
    poseidon.relay.traffic.clear()
    answer = poseidon.is_alive({"id": "r6"})
    assert answer["ok"] is False and answer["devices"][HWID]["last_up"] is None


async def test_debug_mode_logs_every_frame(hass: HomeAssistant) -> None:
    from custom_components.redsea.poseidon.mqtt import MqttFrame

    poseidon = _debug_poseidon(hass, debug=True)
    records: list[dict[str, Any]] = []
    poseidon.debug_log.write = records.append  # type: ignore[method-assign]
    poseidon._on_frame(HWID, "up", MqttFrame(packet_type=12, flags=0, body=b""))
    assert len(records) == 1
    assert records[0]["hwid"] == HWID and records[0]["packet"] == "PINGREQ"

"""Messages nothing expected (poseidon/anomalies.py)."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from custom_components.redsea.poseidon import anomalies as an
from custom_components.redsea.poseidon import const
from custom_components.redsea.poseidon.relay import UP
from tests._poseidon_fakes import HWID
from tests.test_poseidon_spy_responses_unit import _state_frame
from tests.test_poseidon_spy_unit import _poseidon

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "poseidon" / "rspower_spy.json").read_text(
        encoding="utf-8"
    )
)
TELEMETRY = next(e for e in FIXTURE["events"] if e["kind"] == "telemetry")["payload"]
STATE = FIXTURE["states"][0]["payload"]
PWR = "reef-power"
DOWN = "down"


def _topic(suffix: str, family: str = PWR) -> str:
    return f"device/{family}/{HWID}/{suffix}"


# -- the catalogue against what the devices send ---------------------------------


def test_recorded_run_has_no_anomaly() -> None:
    for event in FIXTURE["events"]:
        if event["kind"] == "dashboard":
            continue
        assert an.check_frame(PWR, UP, 3, _topic(event["kind"]), event["payload"]) == []


def test_known_commands_and_packets() -> None:
    for method, url in (
        ("POST", "/socket/5/toggle"),
        ("PUT", "/socket/5/config/schedule"),
        ("GET", "/socket/1/config/schedule"),
        ("PUT", "/sockets/config"),
        ("GET", "/mode"),
        ("POST", "/off"),
        ("DELETE", "/off"),
    ):
        command = {"method": method, "url": url, "body": None, "hwid": HWID}
        assert an.check_frame(PWR, DOWN, 3, _topic("command"), command) == []
    for packet in (1, 2, 4, 8, 9, 12, 13, 14):
        assert an.check_frame(PWR, UP, packet, None, None) == []
    # A command answer is an HTTP answer: never checked
    assert an.check_frame(PWR, UP, 3, _topic("command-response"), {"x": 1}) == []


# -- levels ------------------------------------------------------------------------------


def test_level1_unknown_packet_and_topic() -> None:
    [packet] = an.check_frame(PWR, UP, 15, None, None)
    assert (packet.level, packet.kind, packet.topic) == (1, "unknown_packet", "type 15")
    [topic] = an.check_frame(PWR, UP, 3, _topic("event"), {"hwid": HWID, "x": 1})
    assert (topic.level, topic.kind, topic.topic) == (1, "unknown_topic", "up event")
    assert topic.details == ("device/<family>/<hwid>/event",)
    assert topic.sample == {"hwid": "<…>", "x": 1}
    # A known suffix the wrong way
    [down] = an.check_frame(PWR, DOWN, 3, _topic("telemetry"), TELEMETRY)
    assert down.topic == "down telemetry"
    # Not even a device topic
    [odd] = an.check_frame(PWR, UP, 3, "firmware/check", None)
    assert odd.topic == "up ?" and odd.details == ("firmware/check",)
    # Any family: the topics are common
    assert an.check_frame("reef-wave", UP, 3, _topic("event", "reef-wave"), None)


def test_level2_unknown_command() -> None:
    command = {"method": "post", "url": "/socket/3/feed?x=1", "hwid": HWID}
    [found] = an.check_frame(PWR, DOWN, 3, _topic("command"), command)
    assert (found.level, found.details) == (2, ("POST /socket/*/feed",))
    assert an.command_key({"method": "GET"}) is None
    assert an.command_key("junk") is None
    assert an.check_frame(PWR, DOWN, 3, _topic("command"), {"url": "/x"}) == []


def test_level3_state_keys() -> None:
    state = copy.deepcopy(STATE)
    state["specific_attributes"]["sockets"]["0"]["timer"] = 30
    state["specific_attributes"]["sockets"]["1"]["enabled"] = "yes"
    state["specific_attributes"]["sockets"]["2"]["sensor"] = {"type": "temp", "min": 24}
    [found] = an.check_frame(PWR, UP, 3, _topic("state"), state)
    assert found.level == 3
    assert found.details == (
        "+specific_attributes.sockets.*.timer:number",
        "~specific_attributes.sockets.*.enabled:str",
    )
    # A partial state is normal: nothing required in a state
    partial = {"specific_attributes": {"feed_schedule": None}}
    assert an.check_frame(PWR, UP, 3, _topic("state"), partial) == []
    # Empty objects and lists where items are known
    empty = {
        "specific_attributes": {
            "sockets": {"0": {}},
            "schedule": {"1": {"intervals": []}},
        }
    }
    assert an.check_frame(PWR, UP, 3, _topic("state"), empty) == []


def test_level4_telemetry_keys() -> None:
    telemetry = copy.deepcopy(TELEMETRY)
    telemetry["sockets"]["0"]["voltage"] = 230
    del telemetry["free_heap"]
    telemetry["wifi_signal"] = "-60"
    del telemetry["metrics"]["ping"]  # optional: missing sometimes
    [found] = an.check_frame(PWR, UP, 3, _topic("telemetry"), telemetry)
    assert found.level == 4
    assert found.details == (
        "+sockets.*.voltage:number",
        "-free_heap",
        "~wifi_signal:str",
    )


def test_no_catalogue_or_payload_no_check() -> None:
    telemetry = {"anything": 1}
    assert (
        an.check_frame("reef-wave", UP, 3, _topic("telemetry", "reef-wave"), telemetry)
        == []
    )
    # Not decrypted: only its topic is checked
    assert an.check_frame(PWR, UP, 3, _topic("telemetry"), None) == []


# -- signature, sample -----------------------------------------------------------------------


def test_signature_is_the_same_for_every_user() -> None:
    def found(hwid: str, name: str, consumption: float) -> an.Anomaly:
        telemetry = copy.deepcopy(TELEMETRY)
        telemetry["hwid"] = hwid
        telemetry["sockets"]["0"]["voltage"] = consumption
        telemetry["sockets"]["0"]["label"] = name
        topic = f"device/reef-power/{hwid}/telemetry"
        return an.check_frame(PWR, UP, 3, topic, telemetry, hwid)[0]

    first = found("aaaa00000001", "Pump", 1.0)
    second = found("bbbb00000002", "Skimmer", 230.5)
    assert first.signature == second.signature
    assert len(first.signature) == 10
    # Another difference, another signature
    telemetry = copy.deepcopy(TELEMETRY)
    telemetry["new_field"] = True
    other = an.check_frame(PWR, UP, 3, _topic("telemetry"), telemetry)[0]
    assert other.signature != first.signature


def test_anonymize() -> None:
    sample = an.anonymize(
        {
            "hwid": HWID,
            "url": f"/device/{HWID.upper()}/x",
            "sockets": [{"name": "Pump", "api_secret": "s", "ip": "192.168.0.2"}],
            "empty_name": {"name": ""},
        },
        HWID,
    )
    assert sample == {
        "hwid": "<…>",
        "url": "/device/<hwid>/x",
        "sockets": [{"name": "<…>", "api_secret": "***", "ip": "<…>"}],
        "empty_name": {"name": ""},
    }


def test_value_type() -> None:
    assert [an.value_type(v) for v in (None, True, 1, 1.5, "a", [], {})] == [
        "null",
        "bool",
        "number",
        "number",
        "str",
        "list",
        "dict",
    ]


# -- GitHub ------------------------------------------------------------------------------------


def _item(state: str, number: int, labels: tuple[str, ...] = ()) -> dict[str, Any]:
    return {
        "state": state,
        "number": number,
        "html_url": f"https://github.com/x/y/issues/{number}",
        "labels": [{"name": n} for n in labels],
    }


def test_parse_search() -> None:
    assert an.parse_search({"items": []}).status == "none"
    assert an.parse_search("junk").status == "none"
    assert an.parse_search({"items": ["junk"]}).status == "none"
    report = an.parse_search(
        {"items": [_item("closed", 3, ("fixed-in-2.8.0",)), _item("open", 7)]}
    )
    assert (report.status, report.number) == ("open", 7)
    report = an.parse_search(
        {"items": [_item("closed", 9), _item("closed", 3, ("bug", "fixed-in-2.8.0"))]}
    )
    assert (report.status, report.number, report.fixed_in) == ("closed", 3, "2.8.0")
    report = an.parse_search({"items": [_item("closed", 9), _item("closed", 4)]})
    assert (report.number, report.fixed_in) == (9, "")


def test_new_issue_url() -> None:
    telemetry = copy.deepcopy(TELEMETRY)
    telemetry["big"] = ["x" * 50] * 300
    anomaly = an.check_frame(PWR, UP, 3, _topic("telemetry"), telemetry, HWID)[0]
    url = an.new_issue_url(anomaly, "RSPOWER6", "1.1.9", "v2.7.1")
    parsed = urlparse(url)
    assert url.startswith(const.GITHUB_NEW_ISSUE_URL)
    query = parse_qs(parsed.query)
    assert query["title"] == [an.issue_title(anomaly)]
    assert f"[poseidon-sig:{anomaly.signature}]" in query["title"][0]
    assert query["labels"] == [const.ANOMALY_LABEL]
    body = query["body"][0]
    assert len(body) <= an.MAX_BODY
    assert "RSPOWER6" in body and "1.1.9" in body and "please attach" in body
    assert HWID not in url
    small = an.check_frame(PWR, UP, 3, _topic("event"), {"a": 1}, HWID)[0]
    assert (
        "please attach"
        not in parse_qs(urlparse(an.new_issue_url(small, "m", "f", "v")).query)["body"][
            0
        ]
    )


# -- monitor -----------------------------------------------------------------------------------


def _monitor(
    hass: HomeAssistant, search: bool = True
) -> tuple[an.AnomalyMonitor, list]:
    written: list[dict[str, Any]] = []
    return an.AnomalyMonitor(hass, written.append, lambda: search, "v2.7.1"), written


def _anomaly(level: int) -> an.Anomaly:
    if level == 4:
        telemetry = copy.deepcopy(TELEMETRY)
        telemetry["new"] = 1
        return an.check_frame(PWR, UP, 3, _topic("telemetry"), telemetry)[0]
    return an.check_frame(PWR, UP, 3, _topic(f"event{level}"), {"a": 1})[0]


async def test_report_logs_once_and_counts(hass: HomeAssistant) -> None:
    monitor, written = _monitor(hass, search=False)
    anomaly = _anomaly(1)
    for _ in range(3):
        monitor.report(HWID, [anomaly], "RSPOWER6", "1.1.9")
    await hass.async_block_till_done()
    assert len(written) == 1
    record = written[0]
    assert record["kind"] == "anomaly" and record["signature"] == anomaly.signature
    assert (record["model"], record["firmware"]) == ("RSPOWER6", "1.1.9")
    assert monitor.seen[anomaly.signature].count == 3


@pytest.mark.parametrize(
    ("level", "report", "issue"),
    [
        (1, an.Report("none"), "new"),
        (1, None, "new"),
        (1, an.Report("open", "https://gh/1", 1), "reported"),
        (2, an.Report("closed", "https://gh/2", 2, "2.8.0"), "fixed"),
        (3, an.Report("closed", "https://gh/3", 3), "closed"),
        (4, an.Report("none"), "new"),
        (4, None, None),
        (4, an.Report("open", "https://gh/4", 4), None),
        (4, an.Report("closed", "https://gh/5", 5, "2.8.0"), None),
    ],
)
async def test_resolve(
    hass: HomeAssistant, monkeypatch: Any, level: int, report: Any, issue: str | None
) -> None:
    monitor, _ = _monitor(hass)

    async def _search(signature: str) -> Any:
        return report

    monkeypatch.setattr(monitor, "async_search", _search)
    anomaly = _anomaly(level)
    monitor.report(HWID, [anomaly], "RSPOWER6", "1.1.9")
    await hass.async_block_till_done()
    registry = ir.async_get(hass)
    found = registry.async_get_issue("redsea", f"poseidon_anomaly_{anomaly.signature}")
    if issue is None:
        assert found is None
        return
    assert found is not None
    assert found.translation_key == f"poseidon_anomaly_{issue}"
    assert (found.translation_placeholders or {})["signature"] == anomaly.signature
    if issue == "new":
        assert (found.learn_more_url or "").startswith(const.GITHUB_NEW_ISSUE_URL)
    else:
        assert found.learn_more_url == report.url
    # Turned off: the issues go
    monitor.clear()
    assert (
        registry.async_get_issue("redsea", f"poseidon_anomaly_{anomaly.signature}")
        is None
    )


async def test_resolve_unknown_signature(hass: HomeAssistant) -> None:
    monitor, _ = _monitor(hass)
    await monitor.async_resolve("nothing")


async def test_search(hass: HomeAssistant, aioclient_mock: Any) -> None:
    monitor, _ = _monitor(hass)
    aioclient_mock.get(const.GITHUB_SEARCH_URL, json={"items": [_item("open", 12)]})
    report = await monitor.async_search("abc")
    assert report is not None and (report.status, report.number) == ("open", 12)
    url = aioclient_mock.mock_calls[0][1]
    assert parse_qs(urlparse(str(url)).query)["q"] == [
        'repo:Elwinmage/ha-reefbeat-component "poseidon-sig:abc" in:title'
    ]
    # Cached
    await monitor.async_search("abc")
    assert aioclient_mock.call_count == 1


async def test_search_failures(hass: HomeAssistant, aioclient_mock: Any) -> None:
    monitor, _ = _monitor(hass)
    aioclient_mock.get(const.GITHUB_SEARCH_URL, status=403)
    assert await monitor.async_search("limited") is None
    aioclient_mock.clear_requests()
    aioclient_mock.get(const.GITHUB_SEARCH_URL, exc=TimeoutError())
    assert await monitor.async_search("down") is None
    off, _ = _monitor(hass, search=False)
    assert await off.async_search("x") is None


# -- in the manager ----------------------------------------------------------------------------


def _power(hass: HomeAssistant, options: dict[str, Any] | None = None) -> Any:
    poseidon, coordinator = _poseidon(hass, options)
    poseidon.keystore.devices[HWID].type = "reef-power"
    poseidon._apply_polling()
    written: list[dict[str, Any]] = []
    poseidon.anomalies.write = written.append
    poseidon.anomalies.search_enabled = lambda: False
    return poseidon, coordinator, written


async def test_manager_reports_frames(hass: HomeAssistant) -> None:
    poseidon, _, written = _power(hass)
    telemetry = copy.deepcopy(TELEMETRY)
    telemetry["new_field"] = 1
    poseidon._on_frame(HWID, UP, _state_frame(telemetry, _topic("telemetry")))
    poseidon._on_frame(
        HWID, "down", _state_frame({"method": "GET", "url": "/x"}, _topic("command"))
    )
    from custom_components.redsea.poseidon.mqtt import MqttFrame

    poseidon._on_frame(HWID, UP, MqttFrame(15, 0, b""))
    await hass.async_block_till_done()
    assert [r["anomaly"] for r in written] == [
        "telemetry_keys",
        "unknown_command",
        "unknown_packet",
    ]
    assert written[0]["model"] == "RSWAVE45"
    # Nothing for a device out of Poseidon mode
    poseidon._on_frame("unknown", UP, MqttFrame(15, 0, b""))
    assert len(written) == 3


async def test_manager_detection_off(hass: HomeAssistant) -> None:
    poseidon, _, written = _power(hass, {const.CONF_ANOMALIES: False})
    assert not poseidon.anomaly_detection and not poseidon.anomaly_search
    from custom_components.redsea.poseidon.mqtt import MqttFrame

    poseidon._on_frame(HWID, UP, MqttFrame(15, 0, b""))
    assert written == []


async def test_manager_check_never_raises(
    hass: HomeAssistant, monkeypatch: Any
) -> None:
    poseidon, _, written = _power(hass)

    def _boom(*args: Any) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr("custom_components.redsea.poseidon.manager.check_frame", _boom)
    poseidon._check_anomalies(HWID, UP, 15, None, None)
    assert written == []


async def test_manager_options(hass: HomeAssistant) -> None:
    poseidon, _, _ = _power(hass, {const.CONF_ANOMALY_SEARCH: False})
    assert poseidon.anomaly_detection and not poseidon.anomaly_search
    poseidon, _, _ = _power(hass)
    assert poseidon.anomaly_search


def test_empty_container_at_a_typed_path_with_known_items() -> None:
    # A path typed as a scalar whose items the catalogue also knows: an empty
    # list or object there stands for "no items", not for another type
    catalog = {
        "a": frozenset({"number"}),
        "a.*.b": frozenset({"number"}),
        "c": frozenset({"str"}),
        "c.d": frozenset({"number"}),
    }
    assert an._key_differences({"a": [], "c": {}}, catalog) == ()
    assert an._key_differences({"a": "x"}, catalog) == ("~a:str",)


async def test_manager_detection_turned_off_clears(hass: HomeAssistant) -> None:
    poseidon, _, _ = _power(hass, {const.CONF_ANOMALIES: False})
    cleared: list[bool] = []
    poseidon.anomalies.clear = lambda: cleared.append(True)
    await poseidon.async_apply_options()
    assert cleared == [True]

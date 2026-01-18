from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.coordinator as coord
from custom_components.redsea.const import (
    CONFIG_FLOW_CLOUD_PASSWORD,
    CONFIG_FLOW_CLOUD_USERNAME,
    CONFIG_FLOW_CONFIG_TYPE,
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_IP_ADDRESS,
    DOMAIN,
)


def _make_cloud_entry(
    *, title: str = "Cloud", ip: str = "192.0.2.10"
) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title=title,
        data={
            CONFIG_FLOW_IP_ADDRESS: ip,
            CONFIG_FLOW_HW_MODEL: "ReefBeat",
            CONFIG_FLOW_CONFIG_TYPE: False,
            CONFIG_FLOW_CLOUD_USERNAME: "u",
            CONFIG_FLOW_CLOUD_PASSWORD: "p",
        },
    )


@dataclass
class _FakeCloudAPI:
    data: dict[str, Any] = field(default_factory=lambda: {"sources": []})
    connected: int = 0
    initial: int = 0
    fetched: int = 0
    sent: list[tuple[str, Any, str]] = field(default_factory=list)

    async def connect(self) -> None:
        self.connected += 1

    async def get_initial_data(self) -> None:
        self.initial += 1

    async def fetch_data(self) -> dict[str, Any] | None:
        self.fetched += 1
        return self.data

    async def http_send(self, action: str, payload: Any, method: str = "post") -> Any:
        self.sent.append((action, payload, method))
        return {"ok": True}


class _QueryResult:
    def __init__(self, value: Any):
        self.value = value


@pytest.fixture(autouse=True)
def _patch_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        coord, "async_get_clientsession", lambda _hass: object(), raising=True
    )

    def _cloud_ctor(*_a: Any, **_k: Any) -> _FakeCloudAPI:
        return _FakeCloudAPI(
            data={
                "sources": [
                    {"name": "/device", "type": "data", "data": []},
                    {"name": "/reef-wave/library", "type": "data", "data": []},
                ]
            }
        )

    monkeypatch.setattr(coord, "ReefBeatCloudAPI", _cloud_ctor, raising=True)


@pytest.mark.asyncio
async def test_cloud_async_setup_connects_and_fires_ready(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = _make_cloud_entry(title="MyCloud")
    cloud = coord.ReefBeatCloudCoordinator(hass, cast(Any, entry))

    api = cast(_FakeCloudAPI, cloud.my_api)

    listened: list[str] = []
    fired: list[tuple[str, dict[str, Any]]] = []

    def _fake_listen(self: Any, event_type: str, _cb: Any) -> Any:
        listened.append(event_type)
        return lambda: None

    def _fake_fire(
        self: Any, event_type: str, event_data: dict[str, Any] | None = None
    ) -> None:
        fired.append((event_type, dict(event_data or {})))

    monkeypatch.setattr(type(hass.bus), "async_listen", _fake_listen, raising=True)
    monkeypatch.setattr(type(hass.bus), "fire", _fake_fire, raising=True)

    await cloud.async_setup()
    await cloud.async_setup()

    assert api.connected == 1
    assert api.initial == 1
    assert "redsea_ask_for_cloud_link" in listened
    assert ("redsea_ask_for_cloud_link_ready", {}) in fired


@pytest.mark.asyncio
async def test_cloud_handle_link_requests_links_device_when_present(
    hass: HomeAssistant,
) -> None:
    entry = _make_cloud_entry(title="MyCloud")
    cloud = coord.ReefBeatCloudCoordinator(hass, cast(Any, entry))

    # Provide a minimal get_data implementation via API map.
    class _FakeDevice:
        model_id = "hwid-1"
        linked: int = 0

        async def set_cloud_link(self, _cloud: Any) -> None:
            self.linked += 1

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["dev1"] = _FakeDevice()

    # Patch cloud.get_data to return a non-None device record.
    cloud.get_data = lambda *_a, **_k: {"hwid": "hwid-1"}  # type: ignore[assignment]

    class _Evt:
        def __init__(self, data: dict[str, Any]):
            self.data = data

    await cloud._handle_link_requests(_Evt({"device_id": "dev1"}))  # type: ignore[attr-defined]
    assert hass.data[DOMAIN]["dev1"].linked == 1

    # Missing device_id -> no-op.
    await cloud._handle_link_requests(_Evt({}))  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_cloud_get_no_wave_and_send_cmd_and_unload(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = _make_cloud_entry(title="MyCloud")
    cloud = coord.ReefBeatCloudCoordinator(hass, cast(Any, entry))

    # Monkeypatch parse() to return a query object that finds two candidate waves.
    class _FakeQuery:
        def __init__(self, results: list[Any]):
            self._results = results

        def find(self, _data: Any) -> list[Any]:
            return [_QueryResult(v) for v in self._results]

    def _fake_parse(_expr: str) -> _FakeQuery:
        return _FakeQuery(
            [
                {"type": "nw", "aquarium_uid": "aq-1", "uid": "nw-1"},
                {"type": "nw", "aquarium_uid": "aq-2", "uid": "nw-2"},
            ]
        )

    monkeypatch.setattr(coord, "parse", _fake_parse, raising=True)

    # Make cloud.get_data return aquarium_uid for the target device.
    cloud.get_data = lambda *_a, **_k: "aq-2"  # type: ignore[assignment]

    device = type("D", (), {"model_id": "hwid-1"})()
    assert cloud.get_no_wave(device) == {
        "type": "nw",
        "aquarium_uid": "aq-2",
        "uid": "nw-2",
    }

    cloud.get_data = lambda *_a, **_k: "missing"  # type: ignore[assignment]
    assert cloud.get_no_wave(device) is None

    res = await cloud.send_cmd("/x", {"a": 1}, "put")
    assert res == {"ok": True}

    fired: list[tuple[str, dict[str, Any]]] = []

    def _fake_fire(
        self: Any, event_type: str, event_data: dict[str, Any] | None = None
    ) -> None:
        fired.append((event_type, dict(event_data or {})))

    monkeypatch.setattr(type(hass.bus), "fire", _fake_fire, raising=True)

    cloud.unload()
    assert fired == [
        ("redsea_ask_for_cloud_link_ready", {"state": "off", "account": "MyCloud"})
    ]


@pytest.mark.asyncio
async def test_cloud_listen_for_firmware_adds_source_and_fetches(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = _make_cloud_entry(title="MyCloud")
    cloud = coord.ReefBeatCloudCoordinator(hass, cast(Any, entry))

    api = cast(_FakeCloudAPI, cloud.my_api)

    fired: list[tuple[str, dict[str, Any]]] = []

    def _fake_fire(
        self: Any, event_type: str, event_data: dict[str, Any] | None = None
    ) -> None:
        fired.append((event_type, dict(event_data or {})))

    monkeypatch.setattr(type(hass.bus), "fire", _fake_fire, raising=True)

    await cloud.listen_for_firmware(None, "Dev")
    assert api.fetched == 0

    await cloud.listen_for_firmware("/firmware/latest", "Dev")
    assert api.fetched == 1
    assert any(s.get("name") == "/firmware/latest" for s in api.data["sources"])
    assert fired == [("request_latest_firmware", {"device_name": "Dev"})]


def test_cloud_identity_properties_and_device_info(hass: HomeAssistant) -> None:
    entry = _make_cloud_entry(title="MyCloud")
    cloud = coord.ReefBeatCloudCoordinator(hass, cast(Any, entry))

    assert cloud.title == "MyCloud"
    assert cloud.serial == "MyCloud"
    assert cloud.model == "ReefBeat"
    assert cloud.model_id == "ReefBeat"
    assert cloud.detected_id == "MyCloud"

    di = cloud.device_info
    assert (DOMAIN, "MyCloud") in cast(
        set[tuple[str, str]], di.get("identifiers") or set()
    )

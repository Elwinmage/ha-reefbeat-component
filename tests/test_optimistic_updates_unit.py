"""Optimistic updates: an accepted write shows before the device read-back.

Once a device acknowledges a command, the cached data is changed to the
expected outcome and the entities are refreshed at once; the read-back that
follows (after its settle delay) replaces it with what the device reports,
so a command that did not take effect is corrected on the next poll.

Covers the RSCONTROL port and pairing writes (including what the card sends
through ``redsea.request``), the RSPower local probe and pairing, and the
coordinators updating both ends of a hub / power center pairing.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.redsea.coordinator import (
    ReefControlCoordinator,
    ReefPowerCoordinator,
    _accepted,
)
from custom_components.redsea.reefbeat.api import ReefBeatAPI
from custom_components.redsea.reefbeat.control import ReefControlAPI
from custom_components.redsea.reefbeat.power import ReefPowerAPI
from custom_components.redsea.sensor import _power_temperature_attributes

OK: Any = {"ok": True, "status": 200}


def _control_api(extra: list[dict[str, Any]] | None = None) -> Any:
    api = ReefControlAPI.__new__(ReefControlAPI)
    api.data = {
        "sources": [
            {
                "name": "/dashboard",
                "type": "data",
                "data": {
                    "connected_device": {"hwid": "pw1"},
                    "ports": [
                        {"number": 0, "mode": "on", "type": "other", "name": "A"},
                        {"number": 1, "mode": "sensor", "type": "other", "name": "B"},
                    ],
                },
            },
            {
                "name": "/ports/config",
                "type": "config",
                "data": [
                    {"number": 0, "mode": "on", "type": "other", "name": "A"},
                    {
                        "number": 1,
                        "mode": "sensor",
                        "type": "other",
                        "name": "B",
                        "power_on_percent": 60,
                    },
                ],
            },
            {
                "name": "/subscription-info",
                "type": "data",
                "data": {
                    "internal": [
                        {"number": 1, "type": "ato", "uid": "0xA"},
                        "junk",
                    ],
                    "external": [{"number": 3, "type": "ph"}],
                },
            },
            *(extra or []),
        ]
    }
    api._data_db = {}
    api._base_url = "http://test"
    return api


def _dash(api: Any) -> dict[str, Any]:
    return api.data["sources"][0]["data"]


def _config(api: Any, number: int) -> dict[str, Any]:
    return api.data["sources"][1]["data"][number]


def _info(api: Any) -> dict[str, Any]:
    return api.data["sources"][2]["data"]


# ── Base hook ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_http_send_mirrors_only_accepted_writes() -> None:
    api = ReefBeatAPI.__new__(ReefBeatAPI)
    api._base_url = "http://test"
    api._mirror_write = MagicMock()  # type: ignore[method-assign]
    api._http_send = AsyncMock(return_value=OK)  # type: ignore[method-assign]
    assert await api.http_send("/x", {"a": 1}, "PUT") == OK
    api._mirror_write.assert_called_once_with("/x", {"a": 1}, "put", OK)

    api._mirror_write.reset_mock()
    api._http_send = AsyncMock(return_value={"ok": False})  # type: ignore[method-assign]
    await api.http_send("/x", None, "post")
    api._http_send = AsyncMock(return_value=None)  # type: ignore[method-assign]
    await api.http_send("/x", None, "post")
    api._mirror_write.assert_not_called()
    # The base hook itself does nothing
    ReefBeatAPI._mirror_write(api, "/x", None, "post", OK)


def test_accepted() -> None:
    assert _accepted(OK) is True
    assert _accepted({"ok": False}) is False
    assert _accepted(None) is False


# ── RSCONTROL ────────────────────────────────────────────────────────────────


def test_ports_config_write_sets_mode_everywhere() -> None:
    api = _control_api()
    api._mirror_write(
        "/ports/config",
        [{"number": 1, "mode": "on", "name": "Fan"}, {"mode": "x"}, "junk"],
        "put",
        OK,
    )
    assert _config(api, 1)["mode"] == "on"
    assert _config(api, 1)["power_on_percent"] == 60
    port = _dash(api)["ports"][1]
    assert (port["mode"], port["user_config_mode"], port["name"]) == (
        "on",
        "on",
        "Fan",
    )
    # A payload that is not a list changes nothing
    api._mirror_write("/ports/config", {"number": 1}, "put", OK)
    assert _config(api, 1)["mode"] == "on"


def test_ports_config_write_without_dashboard_entry() -> None:
    api = _control_api()
    _dash(api)["ports"] = "junk"
    api._mirror_write("/ports/config", [{"number": 0, "type": "ato"}], "put", OK)
    assert _config(api, 0)["type"] == "ato"
    # An unknown port in neither source
    api._mirror_write("/ports/config", [{"number": 5, "mode": "on"}], "put", OK)


def test_ports_subscribe_replaces_the_rule() -> None:
    api = _control_api()
    rule = {"number": 1, "type": "ph", "uid": "0xB"}
    api._mirror_write("/ports/subscribe", {"ports": [rule, "junk"]}, "put", OK)
    assert _info(api)["internal"] == ["junk", rule]
    # Shapes that carry no rule
    api._mirror_write("/ports/subscribe", {"ports": None}, "put", OK)
    api._mirror_write("/ports/subscribe", ["x"], "put", OK)
    assert _info(api)["internal"] == ["junk", rule]


def test_rules_without_subscription_info() -> None:
    api = _control_api()
    api.data["sources"][2]["data"] = None
    api._mirror_write("/ports/subscribe", {"ports": [{"number": 0}]}, "put", OK)
    api.data["sources"][2]["data"] = {"internal": None}
    api._mirror_write("/ports/subscribe", {"ports": [{"number": 0}]}, "put", OK)
    assert _info(api)["internal"] == [{"number": 0}]


def test_unpair_and_unsubscribe() -> None:
    api = _control_api()
    api._mirror_write("/socket/3/unsubscribe", {}, "put", OK)
    assert _info(api)["external"] == []
    api._mirror_write("/power/unpair", {}, "post", OK)
    assert _dash(api)["connected_device"] is None


def test_unpair_without_dashboard() -> None:
    api = _control_api()
    api.data["sources"][0]["data"] = None
    api._mirror_write("/power/unpair", {}, "post", OK)


def test_port_install_and_delete() -> None:
    api = _control_api()
    api._mirror_write("/port/0/install", {"type": "other"}, "post", OK)
    api._mirror_write("/port/0/install", {"type": 3}, "post", OK)
    api._mirror_write("/port/0/install", None, "post", OK)
    assert _config(api, 0)["type"] == "other"

    api._mirror_write("/port/1", None, "delete", OK)
    entry = _config(api, 1)
    assert entry["type"] == "unknown"
    assert entry["mode"] == "setup"
    assert entry["name"] == "S2"
    assert entry["power_on_percent"] == 100
    assert entry["sensor"] is None
    assert _dash(api)["ports"][1]["type"] == "unknown"
    assert _info(api)["internal"] == ["junk"]


def test_unrelated_writes_change_nothing() -> None:
    api = _control_api()
    before = repr(api.data)
    api._mirror_write("/port/0/schedule", {"intervals": []}, "put", OK)
    api._mirror_write("/port/0", None, "post", OK)
    api._mirror_write("/port/0/install", {"type": "other"}, "put", OK)
    api._mirror_write("/socket/0/unsubscribe", {}, "post", OK)
    assert repr(api.data) == before


# ── RSPower ──────────────────────────────────────────────────────────────────


def _power_api(temperature: Any = None) -> Any:
    api = ReefPowerAPI.__new__(ReefPowerAPI)
    api.data = {
        "sources": [
            {
                "name": "/dashboard",
                "type": "data",
                "data": {"temperature": temperature, "connected_device": {"hwid": "h"}},
            }
        ]
    }
    api._data_db = {}
    api._base_url = "http://test"
    return api


def test_power_local_probe_and_unpair() -> None:
    api = _power_api()
    board = api.data["sources"][0]["data"]
    api._mirror_write("/sensor/install", {}, "post", {"ok": True, "json": {}})
    assert board["temperature"] is None
    api._mirror_write("/sensor/install", {}, "post", {"ok": True, "json": "x"})
    api._mirror_write(
        "/sensor/install", {}, "post", {"ok": True, "json": {"uid": "0xT"}}
    )
    assert board["temperature"] == {"uid": "0xT"}
    # A known reading is kept
    board["temperature"] = {"uid": "0xT", "value": 25}
    api._mirror_write(
        "/sensor/install", {}, "post", {"ok": True, "json": {"uid": "0xU"}}
    )
    assert board["temperature"]["value"] == 25

    api._mirror_write("/sensor", None, "delete", OK)
    assert board["temperature"] is None
    api._mirror_write("/paired-device", None, "delete", OK)
    assert board["connected_device"] is None
    api._mirror_write("/other", None, "delete", OK)


def test_power_without_dashboard() -> None:
    api = _power_api()
    api.data["sources"][0]["data"] = None
    api._mirror_write("/sensor", None, "delete", OK)


def test_power_temperature_attributes() -> None:
    device = MagicMock()
    config = {
        "acceptable_range_low": 24,
        "desired_range_low": 25,
        "desired_range_high": 26.5,
        "acceptable_range_high": 28,
    }
    device.get_data.side_effect = lambda path, is_None_possible=False: (
        config if "config" in path else {"value": 25.2, "level": "desired"}
    )
    assert _power_temperature_attributes(device) == {
        "ranges": [24.0, 25.0, 26.5, 28.0],
        "level": "desired",
    }
    # A missing bound, no reading
    partial = {**config, "desired_range_high": None}
    device.get_data.side_effect = lambda path, is_None_possible=False: (
        partial if "config" in path else None
    )
    assert _power_temperature_attributes(device) == {"ranges": None, "level": None}
    device.get_data.side_effect = lambda path, is_None_possible=False: None
    assert _power_temperature_attributes(device) == {"ranges": None, "level": None}


# ── Coordinators ─────────────────────────────────────────────────────────────


def _hub(dashboard: Any, hass_data: dict[str, Any]) -> Any:
    coord = ReefControlCoordinator.__new__(ReefControlCoordinator)
    coord.my_api = MagicMock(
        power_discover=AsyncMock(return_value=OK),
        power_unpair=AsyncMock(return_value=OK),
    )
    coord.my_api.get_data.side_effect = lambda path, *a, **k: _read(dashboard, path)
    coord._title = "HUB"  # model_id/serial fall back on the title
    coord._hass = MagicMock(data={"redsea": hass_data})
    coord.async_request_refresh = AsyncMock()  # type: ignore[method-assign]
    coord.async_update_listeners = MagicMock()  # type: ignore[method-assign]
    return coord


def _power(dashboard: Any, hwid: str = "PW") -> Any:
    coord = ReefPowerCoordinator.__new__(ReefPowerCoordinator)
    coord.my_api = MagicMock(unpair_control=AsyncMock(return_value=OK))
    coord.my_api.get_data.side_effect = lambda path, *a, **k: _read(dashboard, path)
    coord.async_request_refresh = AsyncMock()  # type: ignore[method-assign]
    coord.async_update_listeners = MagicMock()  # type: ignore[method-assign]
    coord._title = hwid  # model_id falls back on the title
    return coord


def _read(dashboard: Any, path: str) -> Any:
    """Tiny resolver for the /dashboard paths the coordinators read."""
    if not path.startswith("$.sources[?(@.name=='/dashboard')].data"):
        return None
    node: Any = dashboard
    rest = path[len("$.sources[?(@.name=='/dashboard')].data") :]
    for key in [k for k in rest.split(".") if k]:
        node = node.get(key) if isinstance(node, dict) else None
    return node


@pytest.mark.asyncio
async def test_pair_power_links_both_ends() -> None:
    power_dash: dict[str, Any] = {"connected_device": None, "temperature": None}
    power = _power(power_dash)
    hub_dash: dict[str, Any] = {"connected_device": None}
    hub = _hub(hub_dash, {"p": power})
    await hub.pair_power()
    assert hub_dash["connected_device"]["hwid"] == "PW"
    assert power_dash["connected_device"]["hwid"] == "HUB"
    hub.async_update_listeners.assert_called()
    power.async_update_listeners.assert_called()
    hub.async_request_refresh.assert_awaited_once_with(config=True)


@pytest.mark.asyncio
async def test_pair_power_without_a_single_candidate() -> None:
    free = _power({"connected_device": None, "temperature": None}, "A")
    other = _power({"connected_device": None, "temperature": None}, "B")
    paired = _power({"connected_device": {"hwid": "x"}}, "C")
    with_probe = _power({"connected_device": None, "temperature": {"v": 1}}, "D")
    hub_dash: dict[str, Any] = {"connected_device": None}
    hub = _hub(hub_dash, {"a": free, "b": other, "c": paired, "d": with_probe})
    await hub.pair_power()
    assert hub_dash["connected_device"] is None
    # Refused by the hub: nothing shown either
    hub = _hub(hub_dash, {"a": free})
    hub.my_api.power_discover = AsyncMock(return_value={"ok": False})
    await hub.pair_power()
    assert hub_dash["connected_device"] is None


@pytest.mark.asyncio
async def test_unpair_power_clears_the_power_center() -> None:
    power_dash: dict[str, Any] = {"connected_device": {"hwid": "HUB"}}
    power = _power(power_dash)
    hub = _hub({"connected_device": {"hwid": "PW"}}, {"p": power, "x": object()})
    assert hub.connected_power() is power
    await hub.unpair_power()
    assert power_dash["connected_device"] is None
    hub.async_update_listeners.assert_called_once()

    # No pairing known, or refused: the other end is left alone
    lone = _hub({"connected_device": None}, {})
    assert lone.connected_power() is None
    await lone.unpair_power()
    refused = _hub({"connected_device": {"hwid": "PW"}}, {"p": power})
    refused.my_api.power_unpair = AsyncMock(return_value=None)
    power_dash["connected_device"] = {"hwid": "HUB"}
    await refused.unpair_power()
    assert power_dash["connected_device"] == {"hwid": "HUB"}
    refused.async_update_listeners.assert_not_called()


@pytest.mark.asyncio
async def test_unpair_control_clears_the_hub() -> None:
    hub_dash: dict[str, Any] = {"connected_device": {"hwid": "PW"}}
    hub = _hub(hub_dash, {})
    power = _power({"connected_device": {"hwid": "X"}})
    power.connected_control = MagicMock(return_value=hub)  # type: ignore[method-assign]
    await power.unpair_control()
    assert hub_dash["connected_device"] is None
    power.async_update_listeners.assert_called_once()

    # Without a hub set up here, or refused
    power.connected_control = MagicMock(return_value=None)  # type: ignore[method-assign]
    await power.unpair_control()
    power.async_update_listeners.reset_mock()
    power.my_api.unpair_control = AsyncMock(return_value=None)
    await power.unpair_control()
    power.async_update_listeners.assert_not_called()


def test_set_connected_device_needs_a_dashboard() -> None:
    hub = _hub(None, {})
    hub.set_connected_device(None)
    hub.async_update_listeners.assert_not_called()
    power = _power(None)
    power.set_connected_device(None)
    power.async_update_listeners.assert_not_called()


@pytest.mark.asyncio
async def test_delete_port_shows_at_once() -> None:
    hub = _hub({}, {})
    hub.port_count = 1  # type: ignore[attr-defined]
    hub.my_api.delete_port = AsyncMock(return_value=OK)
    await hub.delete_port(0)
    hub.async_update_listeners.assert_called_once()

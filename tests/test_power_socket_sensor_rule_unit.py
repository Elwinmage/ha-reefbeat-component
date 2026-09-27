"""Sensor-mode rule of a RSPOWER socket: local probe or paired RSCONTROL hub.

A socket in sensor mode follows either the power center's own temperature
probe — rule in its ``/temperature/subscriptions`` — or a probe of the paired
RSCONTROL hub, where the power center only keeps the probe type
(``sensor.app_cache``) and the hub holds the rule in ``/subscription-info``
(``external``, keyed by socket number). ``socket_N_mode`` exposes it as
``sensor_config`` plus ``sensor_source``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.sensor as sensor_platform
from custom_components.redsea.const import DOMAIN
from custom_components.redsea.coordinator import (
    ReefControlCoordinator,
    ReefPowerCoordinator,
)

HWID_PATH = "$.sources[?(@.name=='/dashboard')].data.connected_device.hwid"
HUB_RULES_PATH = "$.sources[?(@.name=='/subscription-info')].data.external"
HUB_HWID_PATH = "$.sources[?(@.name=='/device-info')].data.hwid"


def _local_path(socket: int) -> str:
    return (
        "$.sources[?(@.name=='/temperature/subscriptions')]"
        f".data.sockets[?(@.number=={socket})]"
    )


class _Api:
    def __init__(self, data: dict[str, Any]) -> None:
        self.map = data

    def get_data(
        self, name: str, is_None_possible: bool = False, cached: bool = True
    ) -> Any:
        return self.map.get(name)


def _power(hass: Any, data: dict[str, Any]) -> ReefPowerCoordinator:
    power = ReefPowerCoordinator.__new__(ReefPowerCoordinator)
    power._hass = hass
    power.my_api = cast(Any, _Api(data))
    return power


def _hub(hwid: str, rules: Any) -> ReefControlCoordinator:
    hub = ReefControlCoordinator.__new__(ReefControlCoordinator)
    hub.my_api = cast(Any, _Api({HUB_HWID_PATH: hwid, HUB_RULES_PATH: rules}))
    return hub


# Rule shape returned by a real RSCONTROLPRO's /subscription-info.
HUB_RULE = {
    "number": 1,
    "type": "orp",
    "uid": "0x0071F",
    "sensor": "value",
    "is_above": True,
    "value": 250,
    "hysteresis": 5,
    "trigger_op": "off",
    "last_sock_op": "on",
}


# ===========================================================================
# ReefPowerCoordinator.socket_sensor_config
# ===========================================================================


@pytest.mark.asyncio
async def test_local_temperature_rule_wins(hass: Any) -> None:
    local = {"number": 1, "value": 24.2, "is_above": True, "turn_on": False}
    power = _power(hass, {_local_path(1): local, HWID_PATH: "hub1"})
    hass.data.setdefault(DOMAIN, {})["hub"] = _hub("hub1", [HUB_RULE])

    assert power.socket_sensor_config(1) == ("local", local)


@pytest.mark.asyncio
async def test_hub_rule_for_socket(hass: Any) -> None:
    power = _power(hass, {HWID_PATH: "hub1"})
    other_rule = {**HUB_RULE, "number": 4, "type": "ato"}
    data = hass.data.setdefault(DOMAIN, {})
    data["unrelated"] = object()
    data["other-hub"] = _hub("hub2", [{**HUB_RULE, "type": "ph"}])
    data["hub"] = _hub("hub1", ["garbage", other_rule, HUB_RULE])

    assert power.socket_sensor_config(1) == ("control", HUB_RULE)
    assert power.socket_sensor_config(4) == ("control", other_rule)
    assert power.connected_control() is data["hub"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("hwid", "hub_hwid", "rules"),
    [
        (None, "hub1", [HUB_RULE]),  # not paired
        ("hub1", "hub2", [HUB_RULE]),  # paired hub not set up here
        ("hub1", "hub1", None),  # hub subscriptions not fetched yet
        ("hub1", "hub1", [{**HUB_RULE, "number": 3}]),  # no rule for socket
    ],
)
async def test_no_rule(hass: Any, hwid: Any, hub_hwid: str, rules: Any) -> None:
    power = _power(hass, {HWID_PATH: hwid})
    hass.data.setdefault(DOMAIN, {})["hub"] = _hub(hub_hwid, rules)

    assert power.socket_sensor_config(1) == (None, None)


# ===========================================================================
# socket_N_mode attributes
# ===========================================================================


@dataclass
class _Power:
    serial: str = "SERIAL"
    title: str = "Power"
    hass: Any | None = None
    socket_count: int = 6
    last_update_success: bool = True
    get_data_map: dict[str, Any] = field(default_factory=dict)
    rules: dict[int, tuple[str | None, Any]] = field(default_factory=dict)

    @property
    def device_info(self) -> Any:
        return {"identifiers": {(DOMAIN, "SERIAL")}}

    def async_add_listener(self, update_callback: Any) -> Any:
        return lambda: None

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:
        return self.get_data_map.get(name)

    def socket_sensor_config(self, socket: int) -> tuple[str | None, Any]:
        return self.rules.get(socket, (None, None))


@pytest.mark.asyncio
async def test_socket_mode_sensor_exposes_rule_and_source(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sensor_platform, "ReefPowerCoordinator", _Power)
    for name in (
        "ReefATOCoordinator",
        "ReefBeatCloudCoordinator",
        "ReefControlCoordinator",
        "ReefDoseCoordinator",
        "ReefLedCoordinator",
        "ReefLedG2Coordinator",
        "ReefMatCoordinator",
        "ReefRunCoordinator",
        "ReefVirtualLedCoordinator",
        "ReefWaveCoordinator",
    ):
        monkeypatch.setattr(sensor_platform, name, type(f"_Stub{name}", (), {}))

    device = _Power(rules={1: ("control", HUB_RULE)})
    entry = MockConfigEntry(domain=DOMAIN, title="power", unique_id="p-rule")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[Any] = []
    await sensor_platform.async_setup_entry(
        hass, cast(Any, entry), cast(Any, lambda new, _u=False: added.extend(new))
    )
    by_key = {e.entity_description.key: e.entity_description for e in added}

    attrs = by_key["socket_1_mode"].attributes_fn(device)
    assert attrs["sensor_config"] == HUB_RULE
    assert attrs["sensor_source"] == "control"
    assert "schedule" in attrs

    attrs = by_key["socket_0_mode"].attributes_fn(device)
    assert attrs["sensor_config"] is None
    assert attrs["sensor_source"] is None

"""Coverage for RSCONTROL port entities across the platforms.

Each test mounts the platform's `async_setup_entry` on a synthetic
ReefControl device reporting its ports in its /dashboard payload. The
per-port ATO entities once built for a port of type "ato" are gone: the hub
never reports those fields (see test_no_ato_port_entities).
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from homeassistant.helpers.device_registry import DeviceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea.const import DOMAIN

# ---------------------------------------------------------------------------
# Shared fake coordinator
# ---------------------------------------------------------------------------


@dataclass
class _FakeControlDevice:
    """Just enough surface for the RSCONTROL platforms.

    The `get_data_map` mirrors the `/dashboard.ports` structure the real
    firmware ships. Each test injects the ports array it needs before
    invoking `async_setup_entry`.
    """

    serial: str = "CTL123"
    title: str = "RSCONTROL"
    port_count: int = 2
    hass: Any | None = None
    last_update_success: bool = True
    device_info: DeviceInfo = field(
        default_factory=lambda: DeviceInfo(identifiers={("redsea", "CTL123")})
    )
    get_data_map: dict[str, Any] = field(default_factory=dict)
    my_api: Any = None
    _listeners: list[Any] = field(default_factory=list)

    def async_add_listener(self, cb: Any) -> Any:
        self._listeners.append(cb)

        def _remove() -> None:
            with suppress(Exception):
                self._listeners.remove(cb)

        return _remove

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:
        return self.get_data_map.get(name)

    def set_data(self, name: str, value: Any) -> None:
        self.get_data_map[name] = value

    async def async_request_refresh(self) -> None:
        return None

    # Temperature-fusion surface used by the RSCONTROL branch of the platform
    # dispatchers. Defaults keep fusion inert (fewer than two sources) so these
    # setup-only tests see just the base ATO/port entities.
    def temperature_source_count(self) -> int:
        return 0

    def temperature_incoherent(self) -> bool | None:
        return None

    def fusion_attributes(self) -> dict[str, Any]:
        return {}


def _one_ato_port() -> list[dict[str, Any]]:
    return [
        {
            "number": 0,
            "name": "ATO",
            "type": "ato",
            "mode": "auto",
            "auto_fill": True,
            "today_volume": 42,
            "volume_left": 13000,
            "is_pump_on": False,
            "last_pump_on_cause": "unknown",
            "consumption": 0,
        }
    ]


def _two_ato_ports() -> list[dict[str, Any]]:
    ports = _one_ato_port()
    ports.append(
        {
            "number": 1,
            "name": "ATO2",
            "type": "ato",
            "mode": "auto",
            "auto_fill": False,
            "today_volume": 0,
            "volume_left": 5000,
            "is_pump_on": True,
            "last_pump_on_cause": "manual",
            "consumption": 0,
        }
    )
    return ports


def _one_ato_one_other() -> list[dict[str, Any]]:
    ports = _one_ato_port()
    ports.append(
        {
            "number": 1,
            "name": "Ozone1",
            "type": "other",
            "mode": "off",
            "state": "unknown",
            "consumption": 0,
        }
    )
    return ports


def _neutralise_other_coordinators(
    module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Replace unrelated coordinator symbols so only the RSCONTROL branch fires."""
    for name in (
        "ReefATOCoordinator",
        "ReefBeatCloudCoordinator",
        "ReefDoseCoordinator",
        "ReefLedCoordinator",
        "ReefLedG2Coordinator",
        "ReefMatCoordinator",
        "ReefPowerCoordinator",
        "ReefRunCoordinator",
        "ReefVirtualLedCoordinator",
        "ReefWaveCoordinator",
    ):
        monkeypatch.setattr(module, name, type(f"_S{name}", (), {}), raising=False)


# ---------------------------------------------------------------------------
# No per-port ATO entities
# ---------------------------------------------------------------------------
#
# The hub's `/dashboard.ports` entries never carry the RSATO+ fields these
# entities read (`is_pump_on`, `today_volume_usage`, `leak_sensor`, …), nor do
# the `/ato/…` endpoints their buttons, switch and number wrote to exist on
# it: a port linked to an ATO probe stays `type: "other"`. Even a port
# reporting `type: "ato"` builds none of them.

_REMOVED_ATO_KEYS = (
    "ato_manual_pump",
    "ato_stop",
    "ato_resume",
    "ato_volume_left",
    "ato_auto_fill",
    "check_sensor",
    "is_advancing",
    "is_pump_on",
    "leak_sensor",
    "last_fill_date",
    "last_pump_on_cause",
    "today_volume",
    "leak_status",
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "platform", ["sensor", "binary_sensor", "button", "switch", "number"]
)
async def test_no_ato_port_entities(
    hass: Any, monkeypatch: pytest.MonkeyPatch, platform: str
) -> None:
    import importlib

    module = importlib.import_module(f"custom_components.redsea.{platform}")

    class _Ctl(_FakeControlDevice):
        pass

    monkeypatch.setattr(module, "ReefControlCoordinator", _Ctl, raising=True)
    _neutralise_other_coordinators(module, monkeypatch)

    device = _Ctl(port_count=2)
    device.my_api = type("_FakeApi", (), {"live_config_update": True})()
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports"] = (
        _two_ato_ports()
    )
    entry = MockConfigEntry(
        domain=DOMAIN, title="ctl", data={}, unique_id=f"ctl-noato-{platform}"
    )
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[Any] = []
    await module.async_setup_entry(
        hass,
        cast(Any, entry),
        cast(Any, lambda new, update_before_add=False: added.extend(list(new))),
    )
    # Something was built, so the absence below is meaningful
    assert added
    # Every entity is keyed `{serial}_{key}`
    unique_ids = {str(getattr(e, "_attr_unique_id", "")) for e in added}
    for port_idx in (0, 1):
        for suffix in _REMOVED_ATO_KEYS:
            assert f"CTL123_port_{port_idx}_{suffix}" not in unique_ids


# ---------------------------------------------------------------------------
# button.py — uninstalled-port install buttons (ReefControl)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_button_platform_builds_delete_buttons_for_every_port(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Delete buttons are always created (one per port_count) — mirrors
    ReefPower's socket_N_delete — and disabled while a port is unconfigured
    or has already been erased (type unknown/absent). Installing a port's
    type is not exposed here at all: it is as involved as configuring an
    RSPower socket's sensor mode, so it is configured from ha-reef-card via
    the generic ``redsea.request`` service instead (mirrors the removal of
    RSPower's socket_N_mode select and RSCONTROL's port_N_mode select).
    """
    import custom_components.redsea.button as button_platform

    class _Ctl(_FakeControlDevice):
        pass

    monkeypatch.setattr(button_platform, "ReefControlCoordinator", _Ctl, raising=True)
    _neutralise_other_coordinators(button_platform, monkeypatch)

    device = _Ctl(port_count=2)
    device.my_api = type(
        "_FakeApi",
        (),
        {
            "ato_manual_pump": AsyncMock(return_value=None),
            "ato_stop": AsyncMock(return_value=None),
            "ato_resume": AsyncMock(return_value=None),
            "live_config_update": True,
        },
    )()
    # Port 0 is installed (ato); port 1 is unknown (never configured, or
    # just erased — same "nothing to delete" state either way).
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports"] = [
        {"number": 0, "type": "ato", "mode": "auto"},
        {"number": 1, "type": "unknown"},
    ]
    device.get_data_map[
        "$.sources[?(@.name=='/dashboard')].data.ports[?(@.number==0)].type"
    ] = "ato"
    device.get_data_map[
        "$.sources[?(@.name=='/dashboard')].data.ports[?(@.number==1)].type"
    ] = "unknown"

    entry = MockConfigEntry(domain=DOMAIN, title="ctl", data={}, unique_id="ctl-del")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[Any] = []
    await button_platform.async_setup_entry(
        hass,
        cast(Any, entry),
        cast(Any, lambda new_entities, _u=False: added.extend(list(new_entities))),
    )

    by_key = {e.entity_description.key: e for e in added}
    # Both ports get the button, regardless of install state.
    assert "port_0_delete" in by_key
    assert "port_1_delete" in by_key
    assert by_key["port_0_delete"].available is True
    assert by_key["port_1_delete"].available is False

    # A port with no `type` field at all (missing, not just "unknown") is
    # the same "nothing installed" state and must also read as unavailable.
    device.get_data_map.pop(
        "$.sources[?(@.name=='/dashboard')].data.ports[?(@.number==1)].type"
    )
    assert by_key["port_1_delete"].available is False


# ---------------------------------------------------------------------------
# button.py — subscription-info unsubscribe buttons (ReefControl)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_button_platform_builds_unsubscribe_buttons(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """External socket subscriptions get an unsubscribe button each."""
    import custom_components.redsea.button as button_platform

    class _Ctl(_FakeControlDevice):
        pass

    monkeypatch.setattr(button_platform, "ReefControlCoordinator", _Ctl, raising=True)
    _neutralise_other_coordinators(button_platform, monkeypatch)

    device = _Ctl(port_count=1)
    device.my_api = type(
        "_FakeApi",
        (),
        {
            "ato_manual_pump": AsyncMock(return_value=None),
            "ato_stop": AsyncMock(return_value=None),
            "ato_resume": AsyncMock(return_value=None),
            "live_config_update": True,
        },
    )()
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports"] = []
    device.get_data_map["$.sources[?(@.name=='/subscription-info')].data.external"] = [
        {"number": 0},
        {"number": 2},
    ]

    entry = MockConfigEntry(domain=DOMAIN, title="ctl", data={}, unique_id="ctl-unsub")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[Any] = []
    await button_platform.async_setup_entry(
        hass,
        cast(Any, entry),
        cast(Any, lambda new_entities, _u=False: added.extend(list(new_entities))),
    )

    keys = {e.entity_description.key for e in added}
    assert "socket_0_unsubscribe" in keys
    assert "socket_2_unsubscribe" in keys


# ---------------------------------------------------------------------------
# button.py — socket delete buttons (ReefPower)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_button_platform_builds_socket_delete_for_power(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Configured sockets on ReefPower get a delete button each."""
    import custom_components.redsea.button as button_platform

    @dataclass
    class _PowerDevice(_FakeControlDevice):
        socket_count: int = 6

    _neutralise_other_coordinators(button_platform, monkeypatch)
    # Override *after* neutralise so the elif chain hits the Power branch.
    monkeypatch.setattr(
        button_platform, "ReefPowerCoordinator", _PowerDevice, raising=True
    )

    device = _PowerDevice()
    device.my_api = type("_FakeApi", (), {"live_config_update": True})()
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.sockets"] = [
        {"number": 0, "mode": "manual"},
        {"number": 1, "mode": "setup"},  # still in setup → no delete
        {"number": 2, "mode": "schedule"},
    ]

    entry = MockConfigEntry(domain=DOMAIN, title="pwr", data={}, unique_id="pwr-del")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[Any] = []
    await button_platform.async_setup_entry(
        hass,
        cast(Any, entry),
        cast(Any, lambda new_entities, _u=False: added.extend(list(new_entities))),
    )

    keys = {e.entity_description.key for e in added}
    assert "socket_0_delete" in keys
    assert "socket_2_delete" in keys
    # Socket in setup mode still gets a button entity (stable entities)
    # but it will be unavailable at runtime via dependency_reverse.
    assert "socket_1_delete" in keys


# ---------------------------------------------------------------------------
# binary_sensor.py — leak probe entities (ReefControl)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_binary_sensor_platform_builds_leak_probe_entities(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Leak probes in the dashboard payload produce moisture binary sensors."""
    import custom_components.redsea.binary_sensor as bs_platform

    class _Ctl(_FakeControlDevice):
        pass

    monkeypatch.setattr(bs_platform, "ReefControlCoordinator", _Ctl, raising=True)
    _neutralise_other_coordinators(bs_platform, monkeypatch)

    device = _Ctl(port_count=1)
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports"] = []
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.probes"] = [
        {"uid": "AB-12", "name": "Sump leak", "type": "leak", "detected": False},
        {"uid": "CD-34", "name": "Cabinet", "type": "leak", "detected": True},
        {"uid": "XX-99", "name": "Temp", "type": "temperature"},  # not leak
    ]

    entry = MockConfigEntry(domain=DOMAIN, title="ctl", data={}, unique_id="ctl-leak")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[Any] = []
    await bs_platform.async_setup_entry(
        hass,
        cast(Any, entry),
        cast(Any, lambda new_entities, _u=False: added.extend(list(new_entities))),
    )

    keys = {e.entity_description.key for e in added}
    assert "probe_leak_ab12_detected" in keys
    assert "probe_leak_cd34_detected" in keys
    # Temperature probe must NOT produce a leak entity.
    assert "probe_leak_xx99_detected" not in keys


@pytest.mark.asyncio
async def test_button_platform_pair_unpair_availability_follows_link_state(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ "Pair" is only available while no power center is linked; "unpair"
    only once one is — mirrors the port delete buttons' always-created,
    dependency-gated pattern.
    """
    import custom_components.redsea.button as button_platform

    class _Ctl(_FakeControlDevice):
        pass

    monkeypatch.setattr(button_platform, "ReefControlCoordinator", _Ctl, raising=True)
    _neutralise_other_coordinators(button_platform, monkeypatch)

    device = _Ctl(port_count=0)
    device.my_api = type(
        "_FakeApi",
        (),
        {"live_config_update": True},
    )()
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports"] = []

    entry = MockConfigEntry(domain=DOMAIN, title="ctl", data={}, unique_id="ctl-pair")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[Any] = []
    await button_platform.async_setup_entry(
        hass,
        cast(Any, entry),
        cast(Any, lambda new_entities, _u=False: added.extend(list(new_entities))),
    )
    by_key = {e.entity_description.key: e for e in added}
    assert "pair_power" in by_key
    assert "unpair_power" in by_key

    # No power center linked yet -> can pair, can't unpair.
    assert by_key["pair_power"].available is True
    assert by_key["unpair_power"].available is False

    # A power center is now linked -> can unpair, can't pair again.
    device.get_data_map[
        "$.sources[?(@.name=='/dashboard')].data.connected_device.hwid"
    ] = "004b12eaacc0"
    assert by_key["pair_power"].available is False
    assert by_key["unpair_power"].available is True

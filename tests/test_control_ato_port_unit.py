"""Coverage for RSCONTROL port entities across the platforms.

Each test mounts the platform's `async_setup_entry` on a synthetic
ReefControl device reporting its ports in its /dashboard payload. A port of
type "ato" holds the ATO module (Red Sea ATO kit), which gets its own
entities (see test_ato_port_entities and test_control_ato_module_unit.py).
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

    def async_add_listener(self, cb: Any, context: Any = None) -> Any:
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

    # ATO module surface, read off the ports injected in `get_data_map`
    ato_cfg: dict[str, Any] = field(default_factory=dict)
    ato_calls: list[tuple[str, Any]] = field(default_factory=list)

    def _ports(self) -> list[dict[str, Any]]:
        return (
            self.get_data_map.get("$.sources[?(@.name=='/dashboard')].data.ports") or []
        )

    def ato_port_number(self) -> int | None:
        for port in self._ports():
            if port.get("type") == "ato":
                return int(port["number"])
        return None

    def ato_is_port(self, number: int) -> bool:
        return self.ato_port_number() == number

    def ato_port_value(self, number: int, field_name: str) -> Any:
        if not self.ato_is_port(number):
            return None
        for port in self._ports():
            if port.get("number") == number:
                return port.get(field_name)
        return None

    def ato_status(self, number: int) -> str | None:
        from custom_components.redsea.coordinator import ReefControlCoordinator

        return ReefControlCoordinator.ato_status(cast(Any, self), number)

    def ato_config_value(self, *keys: str) -> Any:
        value: Any = self.ato_cfg
        for key in keys:
            value = value.get(key) if isinstance(value, dict) else None
        return value

    async def async_set_ato_config(self, fields: dict[str, Any]) -> None:
        self.ato_calls.append(("config", fields))

    async def async_set_ato_hose(
        self, length_cm: float | None = None, height_cm: float | None = None
    ) -> None:
        self.ato_calls.append(("hose", (length_cm, height_cm)))

    async def async_set_ato_flow_rate(self, liters_per_minute: float) -> None:
        self.ato_calls.append(("flow_rate", liters_per_minute))

    async def async_update_ato_volume(self, volume_ml: float) -> None:
        self.ato_calls.append(("volume", volume_ml))

    async def async_ato_resume(self) -> None:
        self.ato_calls.append(("resume", None))

    async def async_ato_manual_pump(self) -> None:
        self.ato_calls.append(("manual_pump", None))

    async def async_ato_stop(self) -> None:
        self.ato_calls.append(("stop", None))

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
# Per-port ATO module entities
# ---------------------------------------------------------------------------
#
# Captured from the app installing the Red Sea ATO kit: the port becomes of
# type "ato" and its `/dashboard.ports` entry carries `auto_fill`,
# `today_volume`, `volume_left`, `is_pump_on`, `last_pump_on_cause`; its mode
# reports the module's faults. Only that port gets the module's entities.

_ATO_KEYS: dict[str, tuple[str, ...]] = {
    "sensor": ("ato_status", "today_volume", "volume_left", "last_pump_on_cause"),
    "binary_sensor": ("is_pump_on", "ato_fault"),
    "switch": (
        "ato_auto_fill",
        "ato_volume_monitor",
        "ato_notify",
        "ato_temp_log",
    ),
    "number": (
        "ato_volume_left",
        "ato_hose_length",
        "ato_hose_height",
        "ato_flow_rate",
    ),
    "button": ("ato_resume", "ato_manual_pump", "ato_stop"),
}

# Keys of the entities once built from RSATO+ fields the hub never reports
_GONE_KEYS = ("check_sensor", "is_advancing", "leak_sensor", "leak_status")


async def _setup(
    hass: Any, monkeypatch: pytest.MonkeyPatch, platform: str, ports: Any
) -> tuple[Any, list[Any]]:
    import importlib

    module = importlib.import_module(f"custom_components.redsea.{platform}")

    class _Ctl(_FakeControlDevice):
        pass

    monkeypatch.setattr(module, "ReefControlCoordinator", _Ctl, raising=True)
    _neutralise_other_coordinators(module, monkeypatch)

    device = _Ctl(port_count=2)
    device.my_api = type("_FakeApi", (), {"live_config_update": True})()
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports"] = ports
    entry = MockConfigEntry(
        domain=DOMAIN, title="ctl", data={}, unique_id=f"ctl-ato-{platform}"
    )
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[Any] = []
    await module.async_setup_entry(
        hass,
        cast(Any, entry),
        cast(Any, lambda new, update_before_add=False: added.extend(list(new))),
    )
    return device, added


@pytest.mark.asyncio
@pytest.mark.parametrize("platform", list(_ATO_KEYS))
async def test_ato_port_entities(
    hass: Any, monkeypatch: pytest.MonkeyPatch, platform: str
) -> None:
    _device, added = await _setup(hass, monkeypatch, platform, _one_ato_one_other())
    assert added
    unique_ids = {str(getattr(e, "_attr_unique_id", "")) for e in added}
    for suffix in _ATO_KEYS[platform]:
        # The module's port only
        assert f"CTL123_port_0_{suffix}" in unique_ids
        assert f"CTL123_port_1_{suffix}" not in unique_ids
    for suffix in _GONE_KEYS:
        assert f"CTL123_port_0_{suffix}" not in unique_ids


@pytest.mark.asyncio
@pytest.mark.parametrize("platform", list(_ATO_KEYS))
async def test_no_ato_entities_without_module(
    hass: Any, monkeypatch: pytest.MonkeyPatch, platform: str
) -> None:
    ports = [p for p in _one_ato_one_other() if p["type"] != "ato"]
    _device, added = await _setup(hass, monkeypatch, platform, ports)
    unique_ids = {str(getattr(e, "_attr_unique_id", "")) for e in added}
    assert not any("_ato_" in uid for uid in unique_ids)


@pytest.mark.asyncio
async def test_ato_port_sensor_values(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    ports = _one_ato_one_other()
    device, added = await _setup(hass, monkeypatch, "sensor", ports)
    by_key = {e.entity_description.key: e for e in added}

    def value(key: str) -> Any:
        return by_key[key].entity_description.value_fn(device)

    assert value("port_0_ato_status") == "ok"
    assert value("port_0_today_volume") == 42
    assert value("port_0_volume_left") == 13000
    assert value("port_0_last_pump_on_cause") == "unknown"
    assert by_key["port_0_ato_status"].entity_description.attributes_fn(device) == {
        "port": 0
    }
    # The port reports no `state`: its pump drives it
    assert value("port_0_state") == "standby"
    ports[0]["is_pump_on"] = True
    assert value("port_0_state") == "on"
    ports[0]["mode"] = "missing_pump"
    assert value("port_0_ato_status") == "missing_pump"
    # Not the module's port: its own state, from its mode
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports[1].mode"] = "off"
    assert value("port_1_state") == "off"


@pytest.mark.asyncio
async def test_ato_port_binary_sensor_values(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    ports = _one_ato_one_other()
    device, added = await _setup(hass, monkeypatch, "binary_sensor", ports)
    by_key = {e.entity_description.key: e for e in added}
    pump = by_key["port_0_is_pump_on"].entity_description
    fault = by_key["port_0_ato_fault"].entity_description
    assert pump.value_fn(device) is False
    assert fault.value_fn(device) is False
    assert fault.attributes_fn(device) == {"port": 0}
    ports[0]["mode"] = "empty"
    assert fault.value_fn(device) is True
    ports[0]["mode"] = None
    assert fault.value_fn(device) is None


@pytest.mark.asyncio
async def test_ato_port_switches(hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    ports = _one_ato_one_other()
    device, added = await _setup(hass, monkeypatch, "switch", ports)
    by_key = {e.entity_description.key: e for e in added}
    auto_fill = by_key["port_0_ato_auto_fill"]
    monitor = by_key["port_0_ato_volume_monitor"]
    # Not read yet: the dashboard carries auto_fill, not rvm_enabled
    assert auto_fill._read_fn() is True
    assert monitor._read_fn() is None
    device.ato_cfg = {"auto_fill": False, "rvm_enabled": True}
    assert auto_fill._read_fn() is False
    assert monitor._read_fn() is True
    await auto_fill._write_fn(True)
    await by_key["port_0_ato_temp_log"]._write_fn(False)
    assert device.ato_calls == [
        ("config", {"auto_fill": True}),
        ("config", {"temp_log_enabled": False}),
    ]


@pytest.mark.asyncio
async def test_ato_port_numbers(hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    ports = _one_ato_one_other()
    device, added = await _setup(hass, monkeypatch, "number", ports)
    by_key = {e._description.key: e for e in added}
    volume = by_key["port_0_ato_volume_left"]
    length = by_key["port_0_ato_hose_length"]
    height = by_key["port_0_ato_hose_height"]
    rate = by_key["port_0_ato_flow_rate"]

    assert volume._read_fn() == 13000.0
    assert length._read_fn() is None
    assert rate._read_fn() is None
    assert rate.available is False
    device.ato_cfg = {
        "hose": {"length": 459, "height": 220},
        "pump_override": {"speed_override": 0, "flow_rate_override": 500},
    }
    assert length._read_fn() == 459.0
    assert height._read_fn() == 220.0
    assert rate._read_fn() == 0.5
    device.ato_cfg["pump_override"]["flow_rate_override"] = -1
    assert rate._read_fn() == 0.0
    device.ato_cfg["pump_override"]["flow_rate_override"] = True
    assert rate._read_fn() is None

    await volume._write_fn(50000)
    await length._write_fn(300)
    await height._write_fn(100)
    await rate._write_fn(1.5)
    await rate._write_fn(0.1)
    assert device.ato_calls == [
        ("volume", 50000),
        ("hose", (300, None)),
        ("hose", (None, 100)),
        ("flow_rate", 1.5),
        ("flow_rate", 0),
    ]


@pytest.mark.asyncio
async def test_ato_number_entity_lifecycle(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    ports = _one_ato_one_other()
    device, added = await _setup(hass, monkeypatch, "number", ports)
    volume = next(e for e in added if e._description.key == "port_0_ato_volume_left")
    volume.hass = hass
    volume.entity_id = "number.ato_volume_left"
    volume.async_write_ha_state = lambda: None
    await volume.async_added_to_hass()
    assert volume.native_value == 13000.0
    assert volume.available is True
    ports[0]["volume_left"] = 1000
    volume._handle_coordinator_update()
    assert volume.native_value == 1000.0
    await volume.async_set_native_value(2000)
    assert volume.native_value == 2000
    assert device.ato_calls == [("volume", 2000)]


@pytest.mark.asyncio
async def test_ato_port_buttons(hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    ports = _one_ato_one_other()
    device, added = await _setup(hass, monkeypatch, "button", ports)
    by_key = {e.entity_description.key: e for e in added}
    resume = by_key["port_0_ato_resume"]
    # Nothing to resume from while the module is fine
    assert resume.available is False
    ports[0]["mode"] = "stalled"
    assert resume.available is True
    for key in ("port_0_ato_resume", "port_0_ato_manual_pump", "port_0_ato_stop"):
        await by_key[key].entity_description.press_fn(device)
    assert [c[0] for c in device.ato_calls] == ["resume", "manual_pump", "stop"]


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

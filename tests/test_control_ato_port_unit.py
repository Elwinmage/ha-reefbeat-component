"""Coverage for RSCONTROL ATO port entities across every platform.

Covers the new per-port ATO entities added on top of the existing RSCONTROL
port infrastructure:

- sensor.py     -> ATO-only per-port sensors (today_volume, volume_left,
                   last_pump_on_cause)
- binary_sensor -> per-port `is_pump_on`
- button.py     -> per-port manual_pump / stop / resume
- switch.py     -> per-port auto_fill toggle
- number.py     -> per-port volume_left input (in mL)

Each test mounts the platform's `async_setup_entry` on a synthetic
ReefControl device that reports 1 or 2 ATO ports in its /dashboard payload.
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
# sensor.py — per-ATO-port sensors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sensor_platform_builds_ato_port_sensors(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """1 ATO port + 1 generic port -> 3 ATO-only sensors on the ATO port only."""
    import custom_components.redsea.sensor as sensor_platform

    class _Ctl(_FakeControlDevice):
        pass

    monkeypatch.setattr(sensor_platform, "ReefControlCoordinator", _Ctl, raising=True)
    _neutralise_other_coordinators(sensor_platform, monkeypatch)

    device = _Ctl(port_count=2)
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports"] = (
        _one_ato_one_other()
    )

    entry = MockConfigEntry(domain=DOMAIN, title="ctl", data={}, unique_id="ctl-ato")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[Any] = []

    def _add(new_entities: Any, update_before_add: bool = False) -> None:
        added.extend(list(new_entities))

    await sensor_platform.async_setup_entry(hass, cast(Any, entry), cast(Any, _add))

    keys = {e.entity_description.key for e in added}
    # ATO-only entities on port 0. Note: `port_N_volume_left` used to be a
    # sensor but is now exposed only as the editable `number` entity — the
    # sensor was a duplicate.
    assert "port_0_today_volume" in keys
    assert "port_0_last_pump_on_cause" in keys
    # Not created on the generic port
    assert "port_1_today_volume" not in keys
    assert "port_1_last_pump_on_cause" not in keys


@pytest.mark.asyncio
async def test_sensor_platform_builds_two_ato_ports_when_both_are_ato(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RSCONTROLPRO with two ATO probes -> ATO sensors on both ports."""
    import custom_components.redsea.sensor as sensor_platform

    class _Ctl(_FakeControlDevice):
        pass

    monkeypatch.setattr(sensor_platform, "ReefControlCoordinator", _Ctl, raising=True)
    _neutralise_other_coordinators(sensor_platform, monkeypatch)

    device = _Ctl(port_count=2)
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports"] = (
        _two_ato_ports()
    )

    entry = MockConfigEntry(domain=DOMAIN, title="ctl", data={}, unique_id="ctl-2ato")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[Any] = []
    await sensor_platform.async_setup_entry(
        hass,
        cast(Any, entry),
        cast(Any, lambda new_entities, _u=False: added.extend(list(new_entities))),
    )

    keys = {e.entity_description.key for e in added}
    for port_idx in (0, 1):
        for suffix in ("today_volume", "last_pump_on_cause"):
            assert f"port_{port_idx}_{suffix}" in keys


# ---------------------------------------------------------------------------
# binary_sensor.py — per-ATO-port is_pump_on
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_binary_sensor_platform_builds_ato_pump_on(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`port_{n}_is_pump_on` binary_sensor is emitted for every ATO port."""
    import custom_components.redsea.binary_sensor as bs_platform

    class _Ctl(_FakeControlDevice):
        pass

    monkeypatch.setattr(bs_platform, "ReefControlCoordinator", _Ctl, raising=True)
    _neutralise_other_coordinators(bs_platform, monkeypatch)

    device = _Ctl(port_count=2)
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports"] = (
        _two_ato_ports()
    )

    entry = MockConfigEntry(domain=DOMAIN, title="ctl", data={}, unique_id="ctl-bs")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[Any] = []
    await bs_platform.async_setup_entry(
        hass,
        cast(Any, entry),
        cast(Any, lambda new_entities, _u=False: added.extend(list(new_entities))),
    )

    keys = {e.entity_description.key for e in added}
    assert "port_0_is_pump_on" in keys
    assert "port_1_is_pump_on" in keys


# ---------------------------------------------------------------------------
# button.py — per-ATO-port buttons
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_button_platform_builds_ato_buttons(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One manual_pump / stop / resume button per ATO port."""
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
            # `live_config_update` is read at the very end of
            # button.py::async_setup_entry (a top-level `if`, not inside
            # any coordinator branch) — so every fake API must expose it,
            # even when we only care about the ReefControl branch.
            "live_config_update": True,
        },
    )()
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports"] = (
        _one_ato_one_other()
    )

    entry = MockConfigEntry(domain=DOMAIN, title="ctl", data={}, unique_id="ctl-btn")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[Any] = []
    await button_platform.async_setup_entry(
        hass,
        cast(Any, entry),
        cast(Any, lambda new_entities, _u=False: added.extend(list(new_entities))),
    )

    keys = {e.entity_description.key for e in added}
    for suffix in ("manual_pump", "stop", "resume"):
        assert f"port_0_ato_{suffix}" in keys
    # None on the "other" port
    for suffix in ("manual_pump", "stop", "resume"):
        assert f"port_1_ato_{suffix}" not in keys


# ---------------------------------------------------------------------------
# switch.py — per-ATO-port auto_fill toggle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_switch_platform_builds_ato_auto_fill(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`port_{n}_ato_auto_fill` switch is emitted for every ATO port."""
    import custom_components.redsea.switch as switch_platform

    class _Ctl(_FakeControlDevice):
        pass

    monkeypatch.setattr(switch_platform, "ReefControlCoordinator", _Ctl, raising=True)
    _neutralise_other_coordinators(switch_platform, monkeypatch)

    device = _Ctl(port_count=2)
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports"] = (
        _one_ato_one_other()
    )

    entry = MockConfigEntry(domain=DOMAIN, title="ctl", data={}, unique_id="ctl-sw")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[Any] = []
    await switch_platform.async_setup_entry(
        hass,
        cast(Any, entry),
        cast(Any, lambda new_entities, _u=False: added.extend(list(new_entities))),
    )

    keys = {e.entity_description.key for e in added}
    assert "port_0_ato_auto_fill" in keys
    assert "port_1_ato_auto_fill" not in keys


@pytest.mark.asyncio
async def test_ato_auto_fill_switch_toggle_writes_configuration() -> None:
    """turn_on/off call push_ato_configuration on the coordinator API."""
    from custom_components.redsea.switch import (
        ReefControlATOSwitchEntity,
        ReefControlATOSwitchEntityDescription,
    )

    device = _FakeControlDevice()
    device.my_api = type(
        "_Api",
        (),
        {"push_ato_configuration": AsyncMock(return_value=None)},
    )()
    desc = ReefControlATOSwitchEntityDescription(
        key="port_0_ato_auto_fill",
        translation_key="ato_auto_fill",
        icon="mdi:waves-arrow-up",
        icon_off="mdi:waves",
        port=0,
    )
    entity = ReefControlATOSwitchEntity(cast(Any, device), desc)
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await entity.async_turn_on()
    device.my_api.push_ato_configuration.assert_awaited_with(0, True)
    assert entity._attr_is_on is True

    await entity.async_turn_off()
    device.my_api.push_ato_configuration.assert_awaited_with(0, False)
    assert entity._attr_is_on is False


# ---------------------------------------------------------------------------
# number.py — per-ATO-port volume_left input
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_number_platform_builds_ato_volume_left(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`port_{n}_ato_volume_left` number is emitted for every ATO port."""
    import custom_components.redsea.number as number_platform

    class _Ctl(_FakeControlDevice):
        pass

    monkeypatch.setattr(number_platform, "ReefControlCoordinator", _Ctl, raising=True)
    _neutralise_other_coordinators(number_platform, monkeypatch)

    device = _Ctl(port_count=2)
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports"] = (
        _two_ato_ports()
    )

    entry = MockConfigEntry(domain=DOMAIN, title="ctl", data={}, unique_id="ctl-num")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[Any] = []
    # number.py calls async_add_entities(entities, update_before_add=True) — a
    # kwarg — while the other platforms use a positional arg. Accept both.
    await number_platform.async_setup_entry(
        hass,
        cast(Any, entry),
        cast(
            Any,
            lambda new_entities, *_a, **_k: added.extend(list(new_entities)),
        ),
    )

    # ReefBeatNumberEntity stores its description as `_description` (see
    # number.py:741), not the HA-standard `entity_description` — access
    # accordingly.
    keys = {e._description.key for e in added}
    assert "port_0_ato_volume_left" in keys
    assert "port_1_ato_volume_left" in keys


@pytest.mark.asyncio
async def test_ato_volume_left_set_native_value_writes_to_api() -> None:
    """Writing a new value goes through ato_set_volume_left(port, mL)."""
    from custom_components.redsea.number import (
        ReefBeatNumberEntityDescription,
        ReefControlATOVolumeLeftNumberEntity,
    )

    device = _FakeControlDevice()
    device.my_api = type(
        "_Api",
        (),
        {"ato_set_volume_left": AsyncMock(return_value=None)},
    )()

    desc = ReefBeatNumberEntityDescription(
        key="port_0_ato_volume_left",
        translation_key="ato_volume_left",
        native_min_value=0,
        native_max_value=200000,
        native_step=1,
        value_name=("$.sources[?(@.name=='/dashboard')].data.ports[0].volume_left"),
        icon="mdi:cup-water",
    )
    entity = ReefControlATOVolumeLeftNumberEntity(cast(Any, device), desc, port=0)
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    await entity.async_set_native_value(12345.0)
    device.my_api.ato_set_volume_left.assert_awaited_with(0, 12345)
    # And the local cache was primed with the same value.
    assert (
        device.get_data_map[
            "$.sources[?(@.name=='/dashboard')].data.ports[0].volume_left"
        ]
        == 12345
    )


# ---------------------------------------------------------------------------
# Coverage top-up: ReefControlATOSwitchEntity restore / added_to_hass /
# _handle_coordinator_update / device_info
#
# NOTE ON TEARDOWN SAFETY:
#   These tests patch `_handle_coordinator_update` on the CoordinatorEntity
#   base and `async_added_to_hass` on ReefBeatRestoreEntity. We always go
#   through pytest's `monkeypatch.setattr` (never a plain class-level
#   assignment) so the teardown correctly restores the original inheritance
#   graph — a plain `Class.attr = orig` in a `finally` block would inject the
#   attribute directly into the subclass `__dict__` (shadowing the base),
#   which then breaks unrelated tests that patch the base method.
# ---------------------------------------------------------------------------


def test_ato_switch_restore_is_on_helper() -> None:
    """The static helper decodes the persisted state string back into a bool."""
    from custom_components.redsea.switch import ReefControlATOSwitchEntity

    assert ReefControlATOSwitchEntity._restore_is_on("on") is True
    assert ReefControlATOSwitchEntity._restore_is_on("off") is False
    assert ReefControlATOSwitchEntity._restore_is_on("anything_else") is False


@pytest.mark.asyncio
async def test_ato_switch_handle_coordinator_update_reads_auto_fill(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_handle_coordinator_update pulls auto_fill from the payload and drives is_on."""
    from homeassistant.helpers.update_coordinator import CoordinatorEntity

    from custom_components.redsea.switch import (
        ReefControlATOSwitchEntity,
        ReefControlATOSwitchEntityDescription,
    )

    # Stub the CoordinatorEntity's own _handle_coordinator_update so the
    # super() call in our override doesn't try to write state to a real hass.
    def _noop(self: Any) -> None:
        return None

    monkeypatch.setattr(
        CoordinatorEntity, "_handle_coordinator_update", _noop, raising=True
    )

    device = _FakeControlDevice()
    desc = ReefControlATOSwitchEntityDescription(
        key="port_0_ato_auto_fill",
        translation_key="ato_auto_fill",
        icon="mdi:waves-arrow-up",
        icon_off="mdi:waves",
        port=0,
    )
    entity = ReefControlATOSwitchEntity(cast(Any, device), desc)
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    # Case A: firmware reports auto_fill = True -> entity ON, icon = "on"
    device.get_data_map[
        "$.sources[?(@.name=='/dashboard')].data.ports[0].auto_fill"
    ] = True
    entity._handle_coordinator_update()
    assert entity._attr_available is True
    assert entity._attr_is_on is True
    assert entity._attr_icon == "mdi:waves-arrow-up"

    # Case B: firmware reports False -> entity OFF, icon flips to icon_off
    device.get_data_map[
        "$.sources[?(@.name=='/dashboard')].data.ports[0].auto_fill"
    ] = False
    entity._handle_coordinator_update()
    assert entity._attr_is_on is False
    assert entity._attr_icon == "mdi:waves"

    # Case C: firmware payload missing the field (None) -> is_on unchanged
    device.get_data_map.pop(
        "$.sources[?(@.name=='/dashboard')].data.ports[0].auto_fill", None
    )
    entity._attr_is_on = True  # simulate a prior known-on state
    entity._handle_coordinator_update()
    assert entity._attr_is_on is True  # non-bool value should not overwrite


@pytest.mark.asyncio
async def test_ato_switch_added_to_hass_restores_from_last_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After HA reboot, the persisted state string is used to prime is_on."""
    from unittest.mock import AsyncMock

    from homeassistant.helpers.update_coordinator import CoordinatorEntity

    from custom_components.redsea.entity import ReefBeatRestoreEntity
    from custom_components.redsea.switch import (
        ReefControlATOSwitchEntity,
        ReefControlATOSwitchEntityDescription,
    )

    async def _noop_added(self: Any) -> None:
        return None

    def _noop_upd(self: Any) -> None:
        return None

    monkeypatch.setattr(
        ReefBeatRestoreEntity, "async_added_to_hass", _noop_added, raising=True
    )
    monkeypatch.setattr(
        CoordinatorEntity, "_handle_coordinator_update", _noop_upd, raising=True
    )

    device = _FakeControlDevice()
    desc = ReefControlATOSwitchEntityDescription(
        key="port_0_ato_auto_fill",
        translation_key="ato_auto_fill",
        icon="mdi:waves-arrow-up",
        icon_off="mdi:waves",
        port=0,
    )
    entity = ReefControlATOSwitchEntity(cast(Any, device), desc)
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]

    class _LastState:
        state = "on"

    entity.async_get_last_state = AsyncMock(  # type: ignore[assignment]
        return_value=_LastState()
    )

    await entity.async_added_to_hass()

    # Restore path took: last_state.state == "on" -> is_on True, available True
    assert entity._attr_is_on is True
    assert entity._attr_available is True


@pytest.mark.asyncio
async def test_ato_switch_added_to_hass_no_last_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without a persisted state, is_on is seeded from the coordinator payload."""
    from unittest.mock import AsyncMock

    from homeassistant.helpers.update_coordinator import CoordinatorEntity

    from custom_components.redsea.entity import ReefBeatRestoreEntity
    from custom_components.redsea.switch import (
        ReefControlATOSwitchEntity,
        ReefControlATOSwitchEntityDescription,
    )

    async def _noop_added(self: Any) -> None:
        return None

    def _noop_upd(self: Any) -> None:
        return None

    monkeypatch.setattr(
        ReefBeatRestoreEntity, "async_added_to_hass", _noop_added, raising=True
    )
    monkeypatch.setattr(
        CoordinatorEntity, "_handle_coordinator_update", _noop_upd, raising=True
    )

    device = _FakeControlDevice()
    device.get_data_map[
        "$.sources[?(@.name=='/dashboard')].data.ports[0].auto_fill"
    ] = True
    desc = ReefControlATOSwitchEntityDescription(
        key="port_0_ato_auto_fill",
        translation_key="ato_auto_fill",
        icon="mdi:waves-arrow-up",
        icon_off="mdi:waves",
        port=0,
    )
    entity = ReefControlATOSwitchEntity(cast(Any, device), desc)
    entity.async_write_ha_state = lambda: None  # type: ignore[assignment]
    entity.async_get_last_state = AsyncMock(return_value=None)  # type: ignore[assignment]

    await entity.async_added_to_hass()

    # The coordinator-update path took the payload's auto_fill == True
    assert entity._attr_is_on is True
    assert entity._attr_available is True


def test_ato_switch_device_info_delegates_to_coordinator() -> None:
    """device_info property returns the coordinator's DeviceInfo unchanged."""
    from custom_components.redsea.switch import (
        ReefControlATOSwitchEntity,
        ReefControlATOSwitchEntityDescription,
    )

    device = _FakeControlDevice()
    desc = ReefControlATOSwitchEntityDescription(
        key="port_0_ato_auto_fill",
        translation_key="ato_auto_fill",
        icon="mdi:waves-arrow-up",
        icon_off="mdi:waves",
        port=0,
    )
    entity = ReefControlATOSwitchEntity(cast(Any, device), desc)

    assert entity.device_info == device.device_info


# ---------------------------------------------------------------------------
# Coverage top-up: ReefControlAPI payload construction
# (ato_set_volume_left / push_ato_configuration)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_control_api_ato_write_methods_build_expected_payloads() -> None:
    """The two ATO write helpers build correct URL / body / method triples.

    Bypasses ``__init__`` (which would spin up an aiohttp session) — we only
    need ``_base_url`` set on the instance for URL construction.
    """
    from custom_components.redsea.reefbeat.control import ReefControlAPI

    api = object.__new__(ReefControlAPI)
    api._base_url = "http://192.0.2.42"  # type: ignore[attr-defined]

    sent: list[tuple[str, Any, str]] = []

    async def _spy(url: str, payload: Any, method: str) -> None:
        sent.append((url, payload, method))

    api._http_send = _spy  # type: ignore[assignment]

    await api.ato_set_volume_left(port=1, volume_ml=12345)
    await api.push_ato_configuration(port=0, auto_fill=True)

    assert sent[0] == (
        "http://192.0.2.42/ato/update-volume",
        {"port_index": 1, "volume": 12345},
        "post",
    )
    assert sent[1] == (
        "http://192.0.2.42/ato/configuration",
        {"port_index": 0, "auto_fill": True},
        "put",
    )


# ---------------------------------------------------------------------------
# Coverage top-up: ReefControlAPI action endpoints
# (ato_manual_pump / ato_stop / ato_resume)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_control_api_ato_action_methods_build_expected_payloads() -> None:
    """The three ATO action helpers POST `port_index` to their own endpoint.

    Unlike the two write helpers above, these pass `payload` and `method` as
    keyword arguments, so the spy has to accept them that way — a positional
    spy would pass here while the real call signature drifted.
    """
    from custom_components.redsea.reefbeat.control import ReefControlAPI

    api = object.__new__(ReefControlAPI)
    api._base_url = "http://192.0.2.42"  # type: ignore[attr-defined]

    sent: list[tuple[str, Any, str]] = []

    async def _spy(url: str, payload: Any = None, method: str = "get") -> None:
        sent.append((url, payload, method))

    api._http_send = _spy  # type: ignore[assignment]

    await api.ato_manual_pump(0)
    await api.ato_stop(1)
    await api.ato_resume(1)

    assert sent == [
        ("http://192.0.2.42/ato/manual-pump", {"port_index": 0}, "post"),
        ("http://192.0.2.42/ato/stop", {"port_index": 1}, "post"),
        ("http://192.0.2.42/ato/resume", {"port_index": 1}, "post"),
    ]


@pytest.mark.asyncio
async def test_control_api_ato_actions_coerce_the_port_to_int() -> None:
    """A port arriving as a string from a service call must not reach the wire.

    The firmware rejects a non-integer `port_index`, and the entities build it
    from an entity key suffix, so the `int()` coercion is load-bearing.
    """
    from custom_components.redsea.reefbeat.control import ReefControlAPI

    api = object.__new__(ReefControlAPI)
    api._base_url = "http://192.0.2.42"  # type: ignore[attr-defined]

    sent: list[Any] = []

    async def _spy(url: str, payload: Any = None, method: str = "get") -> None:
        sent.append(payload)

    api._http_send = _spy  # type: ignore[assignment]

    await api.ato_manual_pump(cast(Any, "1"))
    assert sent == [{"port_index": 1}]
    assert isinstance(sent[0]["port_index"], int)


# ---------------------------------------------------------------------------
# button.py — uninstalled-port install buttons (ReefControl)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_button_platform_builds_install_buttons_for_unknown_ports(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ports with type=unknown get install_other + install_ato buttons."""
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
    # Port 0 is ATO (installed), port 1 is unknown (uninstalled).
    device.get_data_map["$.sources[?(@.name=='/dashboard')].data.ports"] = [
        {"number": 0, "type": "ato", "mode": "auto"},
        {"number": 1, "type": "unknown"},
    ]

    entry = MockConfigEntry(domain=DOMAIN, title="ctl", data={}, unique_id="ctl-inst")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device

    added: list[Any] = []
    await button_platform.async_setup_entry(
        hass,
        cast(Any, entry),
        cast(Any, lambda new_entities, _u=False: added.extend(list(new_entities))),
    )

    keys = {e.entity_description.key for e in added}
    assert "port_1_install_other" in keys
    assert "port_1_install_ato" in keys
    # Installed port must NOT get install buttons.
    assert "port_0_install_other" not in keys


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
        pass

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
    # Socket still in setup must NOT get a delete button.
    assert "socket_1_delete" not in keys


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
    assert "probe_ab12_detected" in keys
    assert "probe_cd34_detected" in keys
    # Temperature probe must NOT produce a leak entity.
    assert "probe_xx99_detected" not in keys

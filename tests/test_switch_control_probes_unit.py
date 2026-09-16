"""Coverage for the RSCONTROL per-probe switches in `switch.py`.

Two families are built in the ``ReefControlCoordinator`` branch of
``async_setup_entry``:

- a **maintenance** toggle per temperature-capable probe
  (:class:`ReefControlProbeMaintenanceSwitchEntity`), local-only, backed by a
  set of uids on the coordinator;
- **buzzer / notify / enabled** toggles per probe
  (:class:`ReefControlProbeConfigSwitchEntity`) — buzzer/notify are stateful
  (a ``read_fn`` tracks the device), enabled is optimistic (no ``read_fn``).

The setup builds them from ``/dashboard`` probes; the entity methods are then
driven directly with ``async_write_ha_state`` stubbed out.
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from homeassistant.helpers.device_registry import DeviceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.switch as switch_platform
from custom_components.redsea.const import DOMAIN

_PROBES_PATH = "$.sources[?(@.name=='/dashboard')].data.probes"


@dataclass
class _Ctl:
    """RSCONTROL surface for the probe-switch setup + entity methods."""

    serial: str = "CTL123"
    title: str = "RSCONTROL"
    port_count: int = 0  # no port switches -> keep the setup focused on probes
    hass: Any | None = None
    last_update_success: bool = True
    device_info: DeviceInfo = field(
        default_factory=lambda: DeviceInfo(identifiers={("redsea", "CTL123")})
    )
    get_data_map: dict[str, Any] = field(default_factory=dict)
    maint: set[str] = field(default_factory=set)
    buzzer: dict[str, bool | None] = field(default_factory=dict)
    notify: dict[str, bool | None] = field(default_factory=dict)
    calls: list[tuple[str, Any]] = field(default_factory=list)
    _listeners: list[Any] = field(default_factory=list)

    def async_add_listener(self, cb: Any) -> Any:
        self._listeners.append(cb)

        def _remove() -> None:
            with suppress(Exception):
                self._listeners.remove(cb)

        return _remove

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:
        return self.get_data_map.get(name)

    # -- maintenance ------------------------------------------------------
    def probe_in_maintenance(self, uid: str) -> bool:
        return uid in self.maint

    def set_probe_maintenance(self, uid: str, on: bool) -> None:
        (self.maint.add if on else self.maint.discard)(uid)
        self.calls.append(("maint", (uid, on)))

    # -- buzzer / notify / enable ----------------------------------------
    def probe_buzzer(self, ptype: str, uid: str) -> bool | None:
        return self.buzzer.get(uid, True)

    def probe_notify(self, ptype: str, uid: str) -> bool | None:
        return self.notify.get(uid, False)

    async def set_probe_buzzer(self, ptype: str, uid: str, on: bool) -> None:
        self.calls.append(("buzzer", (ptype, uid, on)))

    async def set_probe_notify(self, ptype: str, uid: str, on: bool) -> None:
        self.calls.append(("notify", (ptype, uid, on)))

    async def set_probe_enabled(self, ptype: str, uid: str, on: bool) -> None:
        self.calls.append(("enabled", (ptype, uid, on)))


def _probes() -> list[dict[str, Any]]:
    return [
        {"type": "temperature", "uid": "0xT", "name": "Sump Temp"},
        {"type": "ph", "uid": "0xP", "name": "pH"},
        {"type": "leak", "uid": "0xL", "name": "Leak"},  # not temp-capable
    ]


async def _setup(hass: Any, monkeypatch: pytest.MonkeyPatch, device: _Ctl) -> list[Any]:
    monkeypatch.setattr(switch_platform, "ReefControlCoordinator", _Ctl)
    device.get_data_map[_PROBES_PATH] = _probes()
    entry = MockConfigEntry(domain=DOMAIN, title="ctl", data={}, unique_id="ctl-sw")
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device
    added: list[Any] = []
    await switch_platform.async_setup_entry(
        hass,
        cast(Any, entry),
        cast(Any, lambda new, update_before_add=False: added.extend(list(new))),
    )
    return added


def _by_key(added: list[Any]) -> dict[str, Any]:
    return {e.entity_description.key: e for e in added}


# ---------------------------------------------------------------------------
# setup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_setup_builds_maintenance_and_config_switches(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    added = await _setup(hass, monkeypatch, _Ctl())
    keys = set(_by_key(added))

    # Maintenance only on temperature-capable probes (temperature + ph).
    assert "probe_temperature_0xt_maintenance" in keys
    assert "probe_ph_0xp_maintenance" in keys
    assert "probe_leak_0xl_maintenance" not in keys

    # Buzzer / notify / enabled on every probe (leak included).
    for uid_key in ("temperature_0xt", "ph_0xp", "leak_0xl"):
        assert f"probe_{uid_key}_buzzer" in keys
        assert f"probe_{uid_key}_notify" in keys
        assert f"probe_{uid_key}_enabled" in keys


# ---------------------------------------------------------------------------
# maintenance switch entity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_maintenance_switch_methods(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    device = _Ctl()
    added = await _setup(hass, monkeypatch, device)
    ent = _by_key(added)["probe_temperature_0xt_maintenance"]
    monkeypatch.setattr(ent, "async_write_ha_state", lambda: None, raising=False)

    await ent.async_turn_on()
    assert ent.is_on is True
    assert device.probe_in_maintenance("0xT") is True

    await ent.async_turn_off()
    assert ent.is_on is False
    assert device.probe_in_maintenance("0xT") is False

    # Coordinator update mirrors the coordinator's maintenance set.
    device.maint.add("0xT")
    ent._handle_coordinator_update()
    assert ent.is_on is True

    # device_info passes through.
    assert ent.device_info == device.device_info


@pytest.mark.asyncio
async def test_maintenance_switch_added_to_hass_syncs_restore(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    device = _Ctl()
    added = await _setup(hass, monkeypatch, device)
    ent = _by_key(added)["probe_ph_0xp_maintenance"]

    # Neutralise the RestoreEntity plumbing in the base and the state write.
    monkeypatch.setattr(
        switch_platform.ReefBeatRestoreEntity,
        "async_added_to_hass",
        AsyncMock(),
        raising=False,
    )
    monkeypatch.setattr(ent, "async_write_ha_state", lambda: None, raising=False)

    # A restored "on" state must be pushed back into the coordinator.
    ent._attr_is_on = True
    await ent.async_added_to_hass()
    assert device.probe_in_maintenance("0xP") is True


# ---------------------------------------------------------------------------
# config switch entity (buzzer/notify stateful, enabled optimistic)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_config_switch_stateful_buzzer(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    device = _Ctl()
    added = await _setup(hass, monkeypatch, device)
    ent = _by_key(added)["probe_ph_0xp_buzzer"]
    monkeypatch.setattr(ent, "async_write_ha_state", lambda: None, raising=False)

    # Initial state read from the device (buzzer defaults to True).
    assert ent.is_on is True
    assert ent.available is True

    await ent.async_turn_off()
    assert ent.is_on is False
    assert ("buzzer", ("ph", "0xP", False)) in device.calls

    await ent.async_turn_on()
    assert ("buzzer", ("ph", "0xP", True)) in device.calls

    # Coordinator update re-reads the device state.
    device.buzzer["0xP"] = False
    ent._handle_coordinator_update()
    assert ent.is_on is False

    # Unavailable when the config read comes back None.
    device.buzzer["0xP"] = None
    ent._handle_coordinator_update()
    assert ent.available is False
    assert ent.device_info == device.device_info


@pytest.mark.asyncio
async def test_config_switch_optimistic_enabled(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    device = _Ctl()
    added = await _setup(hass, monkeypatch, device)
    ent = _by_key(added)["probe_leak_0xl_enabled"]
    monkeypatch.setattr(ent, "async_write_ha_state", lambda: None, raising=False)

    # No read_fn -> optimistic default-on, always available.
    assert ent.is_on is True
    assert ent.available is True

    await ent.async_turn_off()
    assert ("enabled", ("leak", "0xL", False)) in device.calls
    await ent.async_turn_on()
    assert ("enabled", ("leak", "0xL", True)) in device.calls


# ---------------------------------------------------------------------------
# probe-list helpers — non-list dashboard payloads
# ---------------------------------------------------------------------------


def test_probe_helpers_tolerate_missing_dashboard() -> None:
    device = _Ctl()  # get_data returns None for the probes path
    assert switch_platform._all_probes(cast(Any, device)) == []
    assert switch_platform._temperature_capable_probes(cast(Any, device)) == []

"""Coverage for the probe registry-maintenance helpers in ``__init__``.

``_rename_probe_entities`` moves a replaced probe's registry entities onto the
new uid (so history carries over); ``_purge_orphan_probe_entities`` drops the
registry entities of probes the hub no longer reports. Both run against the
real entity registry, driven here with a fake RSCONTROL coordinator.
"""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea as integration
from custom_components.redsea.const import CONFIG_FLOW_HW_MODEL, DOMAIN


class _FakeControl:
    def __init__(self, probes: list[dict[str, str]], dashboard: Any) -> None:
        self.serial = "CTL123"
        self._probes = probes
        self._dashboard = dashboard

    def list_probes(self) -> list[dict[str, str]]:
        return self._probes

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:
        return self._dashboard


def _entry(hass: Any) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="ctl",
        data={CONFIG_FLOW_HW_MODEL: "RSCONTROLPRO"},
        unique_id="ctl-reg",
    )
    entry.add_to_hass(hass)
    return entry


def _mk(reg: er.EntityRegistry, entry: MockConfigEntry, unique_id: str) -> str:
    ent = reg.async_get_or_create(
        "sensor", DOMAIN, unique_id, config_entry=cast(Any, entry)
    )
    return ent.entity_id


@pytest.mark.asyncio
async def test_rename_probe_entities_moves_and_skips_collisions(hass: Any) -> None:
    entry = _entry(hass)
    reg = er.async_get(hass)

    moved = _mk(reg, entry, "CTL123_probe_temperature_0xab_value")
    # Collision: the target unique_id for this one already exists -> skipped.
    _mk(reg, entry, "CTL123_probe_temperature_0xab_status")
    _mk(reg, entry, "CTL123_probe_temperature_0xcd_status")
    # Unrelated entity -> untouched.
    other = _mk(reg, entry, "CTL123_socket_0_on_off")

    coordinator = _FakeControl(probes=[], dashboard={})
    renamed = integration._rename_probe_entities(
        hass, cast(Any, entry), cast(Any, coordinator), "temperature", "0xAB", "0xCD"
    )

    assert renamed == 1
    moved_entry = reg.async_get(moved)
    assert moved_entry is not None
    assert moved_entry.unique_id == "CTL123_probe_temperature_0xcd_value"
    other_entry = reg.async_get(other)
    assert other_entry is not None
    assert other_entry.unique_id == "CTL123_socket_0_on_off"


@pytest.mark.asyncio
async def test_purge_orphan_probe_entities_removes_only_orphans(hass: Any) -> None:
    entry = _entry(hass)
    reg = er.async_get(hass)

    kept = _mk(reg, entry, "CTL123_probe_temperature_0xab_value")
    orphan = _mk(reg, entry, "CTL123_probe_ph_0xdead_value")
    non_probe = _mk(reg, entry, "CTL123_socket_0_on_off")
    foreign = _mk(reg, entry, "OTHER_probe_temperature_0xff_value")

    coordinator = _FakeControl(
        probes=[
            {"type": "temperature", "uid": "0xAB", "name": "Temp"},
            # A non-hex uid exercises the probe_sub_id() except branch.
            {"type": "ph", "uid": "GARBAGE", "name": "pH"},
        ],
        dashboard={
            "probes": [
                {"type": "temperature", "uid": "0xAB"},
                {"type": "ph", "uid": "GARBAGE"},
            ]
        },
    )
    integration._purge_orphan_probe_entities(
        hass, cast(Any, entry), cast(Any, coordinator)
    )

    assert reg.async_get(kept) is not None  # current probe kept
    assert reg.async_get(orphan) is None  # removed
    assert reg.async_get(non_probe) is not None  # not a probe entity
    assert reg.async_get(foreign) is not None  # different serial prefix


@pytest.mark.asyncio
async def test_purge_bails_without_reliable_probe_snapshot(hass: Any) -> None:
    entry = _entry(hass)
    reg = er.async_get(hass)
    ent = _mk(reg, entry, "CTL123_probe_ph_0xdead_value")

    # Dashboard missing the "probes" key -> refuse to purge (would wipe all).
    coordinator = _FakeControl(probes=[], dashboard={"other": 1})
    integration._purge_orphan_probe_entities(
        hass, cast(Any, entry), cast(Any, coordinator)
    )

    assert reg.async_get(ent) is not None


@pytest.mark.asyncio
async def test_async_setup_entry_purges_control_orphans(
    hass: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A successful RSCONTROL setup purges leftover probe entities."""
    from custom_components.redsea.coordinator import ReefControlCoordinator

    entry = _entry(hass)
    reg = er.async_get(hass)
    orphan = _mk(reg, entry, "CTL123_probe_ph_0xdead_value")

    # A real ReefControlCoordinator instance (so the isinstance gate passes),
    # built without network I/O.
    fake: Any = ReefControlCoordinator.__new__(ReefControlCoordinator)
    fake._title = "CTL123"  # `serial` property returns _title
    fake.async_setup = AsyncMock()
    fake.get_data = lambda name, is_None_possible=False: {
        "probes": [{"type": "temperature", "uid": "0xAB"}]
    }
    fake.list_probes = lambda: [{"type": "temperature", "uid": "0xAB", "name": "T"}]

    monkeypatch.setattr(integration, "_build_coordinator", lambda h, e: fake)
    monkeypatch.setattr(hass.config_entries, "async_forward_entry_setups", AsyncMock())
    monkeypatch.setattr(integration, "_migrate_head_device_names", AsyncMock())

    ok = await integration.async_setup_entry(hass, cast(Any, entry))
    assert ok is True
    assert reg.async_get(orphan) is None  # purged during setup


def _mk_bs(reg: er.EntityRegistry, entry: MockConfigEntry, unique_id: str) -> str:
    ent = reg.async_get_or_create(
        "binary_sensor", DOMAIN, unique_id, config_entry=cast(Any, entry)
    )
    return ent.entity_id


_LEAK = {"type": "leak", "uid": "0x0032B", "name": "Fuite 32B"}


@pytest.mark.asyncio
async def test_purge_keeps_a_current_leak_probe(hass: Any) -> None:
    """The leak sensor's typed key is recognised as a live probe entity."""
    entry = _entry(hass)
    reg = er.async_get(hass)
    leak = _mk_bs(reg, entry, "CTL123_probe_leak_0x0032b_detected")
    coordinator = _FakeControl(probes=[_LEAK], dashboard={"probes": [_LEAK]})
    integration._purge_orphan_probe_entities(
        hass, cast(Any, entry), cast(Any, coordinator)
    )
    assert reg.async_get(leak) is not None


@pytest.mark.asyncio
async def test_migrate_leak_unique_ids_keeps_the_entity_id(hass: Any) -> None:
    entry = _entry(hass)
    reg = er.async_get(hass)
    legacy = _mk_bs(reg, entry, "CTL123_probe_0x0032b_detected")
    other = _mk(reg, entry, "CTL123_probe_temperature_0xab_value")
    foreign = _mk_bs(reg, entry, "OTHER_probe_0x0032b_detected")
    coordinator = _FakeControl(
        probes=[_LEAK, {"type": "temperature", "uid": "0xAB", "name": "T"}],
        dashboard={},
    )
    integration._migrate_leak_unique_ids(hass, cast(Any, entry), cast(Any, coordinator))
    moved = reg.async_get(legacy)
    assert moved is not None
    assert moved.unique_id == "CTL123_probe_leak_0x0032b_detected"
    kept = reg.async_get(other)
    assert kept is not None
    assert kept.unique_id == "CTL123_probe_temperature_0xab_value"
    untouched = reg.async_get(foreign)
    assert untouched is not None
    assert untouched.unique_id == "OTHER_probe_0x0032b_detected"


@pytest.mark.asyncio
async def test_migrate_leak_unique_ids_drops_a_duplicate(hass: Any) -> None:
    entry = _entry(hass)
    reg = er.async_get(hass)
    legacy = _mk_bs(reg, entry, "CTL123_probe_0x0032b_detected")
    current = _mk_bs(reg, entry, "CTL123_probe_leak_0x0032b_detected")
    coordinator = _FakeControl(probes=[_LEAK], dashboard={})
    integration._migrate_leak_unique_ids(hass, cast(Any, entry), cast(Any, coordinator))
    assert reg.async_get(legacy) is None
    assert reg.async_get(current) is not None


@pytest.mark.asyncio
async def test_migrate_leak_unique_ids_without_leak_probe(hass: Any) -> None:
    entry = _entry(hass)
    reg = er.async_get(hass)
    ent = _mk_bs(reg, entry, "CTL123_probe_0x0032b_detected")
    coordinator = _FakeControl(probes=[], dashboard={})
    integration._migrate_leak_unique_ids(hass, cast(Any, entry), cast(Any, coordinator))
    entry_after = reg.async_get(ent)
    assert entry_after is not None
    assert entry_after.unique_id == "CTL123_probe_0x0032b_detected"

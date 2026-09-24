"""Cloud shortcut switches: per-aquarium unique ids and their migration.

The shortcut keys (``shortcut_feeding_1``...) repeat in every aquarium of a
ReefBeat account. They used to be the whole unique id, so with two aquariums
Home Assistant dropped the second aquarium's shortcuts as duplicates.
"""

from __future__ import annotations

from typing import Any, cast

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.redsea.switch as platform
from custom_components.redsea.const import DOMAIN
from custom_components.redsea.switch import ReefCloudSwitchEntityDescription

SERIAL = "me@example.com"
TANK_A = {"uid": "uid-a", "name": "Salon"}
TANK_B = {"uid": "uid-b", "name": "Bureau"}


class _FakeCloud:
    serial = SERIAL

    def aquarium_device_info(self, name: str | None) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, f"cloud_{name}")}, name=name)


def _desc(key: str, aquarium: dict[str, Any]) -> ReefCloudSwitchEntityDescription:
    return ReefCloudSwitchEntityDescription(
        key=key, translation_key="shortcut_feeding", aquarium=aquarium
    )


def _entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="cloud", unique_id="cloud-sc")
    entry.add_to_hass(hass)
    return entry


def _old_switch(
    hass: HomeAssistant, entry: MockConfigEntry, key: str, tank: dict[str, Any] | None
) -> str:
    device_id = None
    if tank is not None:
        device_id = (
            dr.async_get(hass)
            .async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, f"cloud_{tank['name']}")},
            )
            .id
        )
    return (
        er.async_get(hass)
        .async_get_or_create(
            "switch",
            DOMAIN,
            f"{SERIAL}_{key}",
            config_entry=cast(Any, entry),
            device_id=device_id,
        )
        .entity_id
    )


def _unique_id(hass: HomeAssistant, entity_id: str) -> str:
    entry = er.async_get(hass).async_get(entity_id)
    assert entry is not None
    return entry.unique_id


# ===========================================================================
# Unique id
# ===========================================================================


def test_unique_id_includes_aquarium_uid() -> None:
    a = platform._cloud_shortcut_unique_id(SERIAL, _desc("shortcut_feeding_1", TANK_A))
    b = platform._cloud_shortcut_unique_id(SERIAL, _desc("shortcut_feeding_1", TANK_B))
    assert a == f"{SERIAL}_uid-a_shortcut_feeding_1"
    assert b == f"{SERIAL}_uid-b_shortcut_feeding_1"


def test_unique_id_without_aquarium_uid_keeps_legacy_form() -> None:
    desc = _desc("shortcut_feeding_1", {})
    assert platform._cloud_shortcut_unique_id(SERIAL, desc) == (
        f"{SERIAL}_shortcut_feeding_1"
    )


# ===========================================================================
# Migration
# ===========================================================================


@pytest.mark.asyncio
async def test_single_aquarium_migrates_without_device(hass: HomeAssistant) -> None:
    entry = _entry(hass)
    entity_id = _old_switch(hass, entry, "shortcut_feeding_1", None)

    platform._migrate_cloud_shortcut_unique_ids(
        hass,
        cast(Any, entry),
        cast(Any, _FakeCloud()),
        [_desc("shortcut_feeding_1", TANK_A)],
    )

    assert _unique_id(hass, entity_id) == f"{SERIAL}_uid-a_shortcut_feeding_1"


@pytest.mark.asyncio
async def test_several_aquariums_migrate_onto_owner_only(hass: HomeAssistant) -> None:
    entry = _entry(hass)
    # The legacy entity was registered for the second aquarium ("Bureau").
    entity_id = _old_switch(hass, entry, "shortcut_feeding_1", TANK_B)

    platform._migrate_cloud_shortcut_unique_ids(
        hass,
        cast(Any, entry),
        cast(Any, _FakeCloud()),
        [_desc("shortcut_feeding_1", TANK_A), _desc("shortcut_feeding_1", TANK_B)],
    )

    assert _unique_id(hass, entity_id) == f"{SERIAL}_uid-b_shortcut_feeding_1"


@pytest.mark.asyncio
async def test_several_aquariums_without_device_are_left_alone(
    hass: HomeAssistant,
) -> None:
    # Owner unknown: guessing could hand one aquarium's history to another.
    entry = _entry(hass)
    entity_id = _old_switch(hass, entry, "shortcut_feeding_1", None)

    platform._migrate_cloud_shortcut_unique_ids(
        hass,
        cast(Any, entry),
        cast(Any, _FakeCloud()),
        [_desc("shortcut_feeding_1", TANK_A), _desc("shortcut_feeding_1", TANK_B)],
    )

    assert _unique_id(hass, entity_id) == f"{SERIAL}_shortcut_feeding_1"


@pytest.mark.asyncio
async def test_migration_skips_collisions_other_entries_and_missing(
    hass: HomeAssistant,
) -> None:
    entry = _entry(hass)
    reg = er.async_get(hass)

    # Target id already present: no collision.
    old = _old_switch(hass, entry, "shortcut_feeding_1", None)
    reg.async_get_or_create(
        "switch",
        DOMAIN,
        f"{SERIAL}_uid-a_shortcut_feeding_1",
        config_entry=cast(Any, entry),
    )

    # Same unique id owned by another config entry: not ours to move.
    other = MockConfigEntry(domain=DOMAIN, title="other", unique_id="other-sc")
    other.add_to_hass(hass)
    foreign = reg.async_get_or_create(
        "switch",
        DOMAIN,
        f"{SERIAL}_shortcut_feeding_2",
        config_entry=cast(Any, other),
    ).entity_id

    platform._migrate_cloud_shortcut_unique_ids(
        hass,
        cast(Any, entry),
        cast(Any, _FakeCloud()),
        [
            _desc("shortcut_feeding_1", TANK_A),
            _desc("shortcut_feeding_2", TANK_A),
            _desc("shortcut_feeding_3", TANK_A),  # never registered
            _desc("shortcut_emergency_1", {}),  # no aquarium uid
        ],
    )

    assert _unique_id(hass, old) == f"{SERIAL}_shortcut_feeding_1"
    assert _unique_id(hass, foreign) == f"{SERIAL}_shortcut_feeding_2"

"""Unit tests for the device group helpers (groups.py) and the entry migration."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea import async_migrate_entry
from custom_components.redsea.const import (
    CONF_GROUP_MEMBERS,
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_IP_ADDRESS,
    DOMAIN,
    LED_BLUE_INTERNAL_NAME,
    LED_WHITE_INTERNAL_NAME,
    LINKED_LED,
    VIRTUAL_LED,
)
from custom_components.redsea.groups import (
    find_group,
    group_dispatch,
    group_error,
    in_group_dispatch,
    led_group_path,
    led_path_is_shared,
    led_source_is_shared,
    members_from_legacy,
)

KI = "$.local.manual_trick $.sources[?(@.name=='/manual')].data"


def test_group_dispatch_is_scoped_and_nests() -> None:
    assert in_group_dispatch() is False
    with group_dispatch():
        assert in_group_dispatch() is True
        with group_dispatch():
            assert in_group_dispatch() is True
        assert in_group_dispatch() is True
    assert in_group_dispatch() is False


def test_group_dispatch_is_reset_on_error() -> None:
    with pytest.raises(RuntimeError), group_dispatch():
        raise RuntimeError("boom")
    assert in_group_dispatch() is False


def test_find_group(hass: HomeAssistant) -> None:
    class _Group:
        member_ids = ["a", "b"]

    class _Led:
        pass

    class _BadGroup:
        member_ids = ("c",)  # not a list: not a group

    assert find_group(hass, "a") is None  # nothing loaded
    group = _Group()
    hass.data[DOMAIN] = {"g": group, "a": _Led(), "x": _BadGroup()}
    assert find_group(hass, "a") is group
    assert find_group(hass, "b") is group
    assert find_group(hass, "c") is None
    assert find_group(hass, "z") is None


def test_members_from_legacy() -> None:
    linked = {
        "LED-RSLED90-: Salon LED (e1)": True,
        "LED-RSLED60-: Bac - droite (1) (e2)": True,
        "LED-RSLED60-: again (e1)": True,  # duplicate entry id
        "not a key": True,
    }
    assert members_from_legacy(linked) == ["e1", "e2"]
    assert members_from_legacy([]) == []


@pytest.mark.parametrize(
    ("source", "shared"),
    [
        ("/manual", True),
        ("/mode", True),
        ("/timer", True),
        ("/acclimation", True),
        ("/moonphase", True),
        ("/auto", True),
        ("/auto/3", True),
        ("/preset_name/1", True),
        ("/clouds/7", True),
        ("/autox", False),
        ("/device-settings", False),
        ("/cloud", False),
        ("/firmware", False),
        ("/configuration", False),
    ],
)
def test_led_source_is_shared(source: str, shared: bool) -> None:
    assert led_source_is_shared(source) is shared


@pytest.mark.parametrize(
    ("path", "shared"),
    [
        ("$.sources[?(@.name=='/manual')].data.white", True),
        ('$.sources[?(@.name=="/mode")].data.mode', True),
        ("$.sources[?(@.name=='/auto/2')].data", True),
        ("$.sources[?(@.name=='/device-settings')].data.name", False),
        ("$.sources[?(@.name=='/firmware')].data.version", False),
        ("$.local.manual_trick.kelvin", True),
        ("$.local.manual_duration", True),
        ("$.local.acclimation.duration", True),
        ("$.local.moonphase.moon_day", True),
        ("$.local.use_cloud_api", False),
        ("$.local.status", False),
        ("$.anything_else", False),
    ],
)
def test_led_path_is_shared(path: str, shared: bool) -> None:
    assert led_path_is_shared(path) is shared


def test_led_group_path() -> None:
    # Kelvin/intensity: the group's "g1 g2" form, from a G1 or a G2 lamp
    for key in ("kelvin", "intensity"):
        expected = f"{KI}.{key}"
        assert led_group_path(f"$.local.manual_trick.{key}", True) == expected
        assert (
            led_group_path(f"$.sources[?(@.name=='/manual')].data.{key}", False)
            == expected
        )
    # White/blue: only on a group of G1 lamps
    for path in (LED_WHITE_INTERNAL_NAME, LED_BLUE_INTERNAL_NAME):
        assert led_group_path(path, True) == path
        assert led_group_path(path, False) is None
    # Anything else is the same on both generations
    moon = "$.sources[?(@.name=='/manual')].data.moon"
    assert led_group_path(moon, False) == moon


def test_group_error_is_translated() -> None:
    err = group_error("group_member_unavailable", group="G", members="A, B")
    assert isinstance(err, HomeAssistantError)
    assert err.translation_domain == DOMAIN
    assert err.translation_key == "group_member_unavailable"
    assert err.translation_placeholders == {"group": "G", "members": "A, B"}


# -----------------------------------------------------------------------------
# Config entry migration 1.1 -> 1.2
# -----------------------------------------------------------------------------


def _entry(
    hass: HomeAssistant, data: dict[str, Any], version: int = 1, minor: int = 1
) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"{VIRTUAL_LED}-1",
        data=data,
        version=version,
        minor_version=minor,
    )
    entry.add_to_hass(hass)
    return entry


async def test_migrate_virtual_led_members(hass: HomeAssistant) -> None:
    entry = _entry(
        hass,
        {
            CONFIG_FLOW_IP_ADDRESS: VIRTUAL_LED,
            CONFIG_FLOW_HW_MODEL: VIRTUAL_LED,
            LINKED_LED: {"LED-RSLED90-: A (e1)": True, "LED-RSLED60-: B (e2)": True},
        },
    )
    assert await async_migrate_entry(hass, cast(Any, entry)) is True
    assert entry.minor_version == 2
    assert LINKED_LED not in entry.data
    assert entry.data[CONF_GROUP_MEMBERS] == ["e1", "e2"]


async def test_migrate_virtual_led_without_leds(hass: HomeAssistant) -> None:
    entry = _entry(
        hass,
        {
            CONFIG_FLOW_IP_ADDRESS: VIRTUAL_LED,
            CONFIG_FLOW_HW_MODEL: VIRTUAL_LED,
            LINKED_LED: None,
        },
    )
    assert await async_migrate_entry(hass, cast(Any, entry)) is True
    assert entry.data[CONF_GROUP_MEMBERS] == []


async def test_migrate_other_entries_only_bump_the_version(
    hass: HomeAssistant,
) -> None:
    data = {CONFIG_FLOW_IP_ADDRESS: "192.0.2.1", CONFIG_FLOW_HW_MODEL: "RSLED90"}
    entry = _entry(hass, dict(data))
    assert await async_migrate_entry(hass, cast(Any, entry)) is True
    assert entry.minor_version == 2
    assert dict(entry.data) == data

    # Already current: untouched
    current = _entry(hass, dict(data), minor=2)
    assert await async_migrate_entry(hass, cast(Any, current)) is True
    assert current.minor_version == 2


async def test_migrate_refuses_a_newer_version(hass: HomeAssistant) -> None:
    entry = _entry(hass, {}, version=2)
    assert await async_migrate_entry(hass, cast(Any, entry)) is False


# -----------------------------------------------------------------------------
# Staggered sunrise: offsets and the group's store
# -----------------------------------------------------------------------------


def test_staggered_offsets() -> None:
    from custom_components.redsea.groups import staggered_offsets

    assert staggered_offsets(["a", "b", "c"], True, 10) == {"a": 0, "b": 10, "c": 20}
    assert staggered_offsets(["a", "b"], False, 10) == {"a": 0, "b": 0}
    assert staggered_offsets([], True, 10) == {}


async def test_group_store_load_save_and_listeners(hass: HomeAssistant) -> None:
    from custom_components.redsea.groups import GroupStore

    store = GroupStore(hass, "g1")
    await store.async_load()
    assert (store.staggered, store.delay, store.applied) == (False, 10, {})

    told: list[int] = []
    remove = store.async_add_listener(lambda: told.append(1))
    await store.async_set(staggered=True, delay=0)
    assert (store.staggered, store.delay) == (True, 1)
    store.applied = {"a": 0, "b": 1}
    await store.async_set(delay=7.6)
    assert store.delay == 8
    assert told == [1, 1]
    remove()
    remove()  # twice: harmless
    await store.async_set()
    assert told == [1, 1]

    again = GroupStore(hass, "g1")
    await again.async_load()
    assert (again.staggered, again.delay, again.applied) == (True, 8, {"a": 0, "b": 1})


async def test_group_store_ignores_invalid_stored_values(hass: HomeAssistant) -> None:
    from custom_components.redsea.groups import GroupStore

    store = GroupStore(hass, "g2")
    store._store.async_load = AsyncMock(  # type: ignore[method-assign]
        return_value={"staggered": 1, "delay": "x", "applied": {"a": "no", "b": 5}}
    )
    await store.async_load()
    assert (store.staggered, store.delay, store.applied) == (True, 10, {"b": 5})

    store._store.async_load = AsyncMock(  # type: ignore[method-assign]
        return_value={"delay": 99, "applied": []}
    )
    await store.async_load()
    assert (store.delay, store.applied) == (15, {})


# -----------------------------------------------------------------------------
# Group entities (virtual LED): staggered sunrise switch and delay
# -----------------------------------------------------------------------------


async def test_group_entities(hass: HomeAssistant) -> None:
    from custom_components.redsea.group_entities import (
        StaggeredDelayNumber,
        StaggeredSunriseSwitch,
        group_entities,
    )
    from custom_components.redsea.groups import GroupStore

    class _Group:
        serial = "VLED"
        device_info: dict[str, Any] = {}

        def __init__(self) -> None:
            self.group_store = GroupStore(hass, "g3")
            self.calls: list[dict[str, Any]] = []

        async def async_set_staggered(self, **kwargs: Any) -> None:
            self.calls.append(kwargs)
            await self.group_store.async_set(**kwargs)

    assert group_entities(object(), "switch") == []
    group = _Group()
    assert group_entities(group, "sensor") == []
    (switch,) = group_entities(group, "switch")
    (number,) = group_entities(group, "number")
    assert isinstance(switch, StaggeredSunriseSwitch)
    assert isinstance(number, StaggeredDelayNumber)
    assert switch.unique_id == "VLED_staggered_sunrise"
    assert switch.extra_state_attributes == {"reef_role": "staggered_sunrise"}

    writes: list[str] = []
    for entity in (switch, number):
        entity.hass = hass
        entity.entity_id = f"x.{entity.unique_id}".lower()
        entity.async_write_ha_state = lambda e=entity: writes.append(e.unique_id)  # type: ignore[method-assign]
        await entity.async_added_to_hass()

    assert switch.is_on is False
    assert number.native_value == 10
    await switch.async_turn_on()
    await number.async_set_native_value(5)
    await switch.async_turn_off()
    assert group.calls == [{"staggered": True}, {"delay": 5}, {"staggered": False}]
    assert number.native_value == 5 and switch.is_on is False
    assert writes.count("VLED_staggered_sunrise") == 3

    for entity in (switch, number):
        await entity.async_will_remove_from_hass()
        await entity.async_will_remove_from_hass()  # twice: harmless
    await group.group_store.async_set(delay=3)
    assert writes.count("VLED_staggered_sunrise") == 3


def test_group_state_and_sync_action() -> None:
    from custom_components.redsea.groups import (
        SYNC_ADOPT,
        SYNC_CONFLICT,
        SYNC_NONE,
        SYNC_PUSH,
        GroupState,
        sync_action,
    )

    a = GroupState(("h1", "h2"), True, 10)
    b = GroupState(("h2", "h1"), True, 10)
    empty = GroupState((), False, 10)
    assert GroupState.from_dict(a.as_dict()) == a
    assert GroupState.from_dict(None) is None
    assert GroupState.from_dict({"members": "h1"}) is None
    other = GroupState(("h1", "h3"), True, 10)
    assert sync_action(a, a, None) == SYNC_NONE
    assert sync_action(a, empty, None) == SYNC_PUSH
    # A new group of the lamps the app already groups: the app's taken
    assert sync_action(a, b, None) == SYNC_ADOPT
    assert sync_action(a, other, None) == SYNC_CONFLICT
    assert sync_action(b, a, a) == SYNC_PUSH
    assert sync_action(a, b, a) == SYNC_ADOPT
    assert sync_action(b, empty, a) == SYNC_CONFLICT


def test_cloud_group_state() -> None:
    from custom_components.redsea.groups import GroupState, cloud_group_state

    devices = [
        {
            "hwid": "h1",
            "model": "M",
            "aquarium_uid": "a",
            "grouped": True,
            "group_index": 1,
        },
        {
            "hwid": "h2",
            "model": "M",
            "aquarium_uid": "a",
            "grouped": True,
            "group_index": 0,
        },
        {"hwid": "h3", "model": "M", "aquarium_uid": "a", "grouped": False},
        {"hwid": "h4", "model": "X", "aquarium_uid": "a", "grouped": True},
        {"hwid": "h5", "model": "M", "aquarium_uid": "b", "grouped": True},
        {"hwid": "h6", "model": "M", "aquarium_uid": "a", "grouped": True},
        "junk",
    ]
    aquarium = {
        "properties": {
            "groups": [
                "junk",
                {"name": "X", "properties": {"staggered": True}},
                # The app names the group of a model in lower case
                {"name": "m", "properties": {"staggered": True, "staggered_delay": 0}},
            ]
        }
    }
    known = {"h1", "h2", "h3", "h4", "h5"}
    assert cloud_group_state(devices, aquarium, "a", "M", known) == GroupState(
        ("h2", "h1"), True, 10
    )
    assert cloud_group_state(None, None, "a", "M", known) == GroupState((), False, 10)


def test_cloud_group_name() -> None:
    from custom_components.redsea.groups import cloud_group_name

    aquarium = {"properties": {"groups": ["junk", {"name": "rsled160"}]}}
    assert cloud_group_name(aquarium, "RSLED160") == "rsled160"
    assert cloud_group_name(aquarium, "RSLED90") == "rsled90"
    assert cloud_group_name(None, "RSLED90") == "rsled90"

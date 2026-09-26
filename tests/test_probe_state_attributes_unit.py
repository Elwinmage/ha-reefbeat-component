"""Unit tests for the probe identity attributes exposed to the card.

Every probe of a given type shares the same translation keys, so the card
cannot group a hub's entities per probe from the registry alone. Each probe
entity therefore carries `probe_uid` / `probe_type` / `probe_index`, and the
measurement entities also carry the `ranges` their reading is judged against.

Covers: custom_components/redsea/probe_entities.py (probe_index,
        probe_ranges, probe_state_attributes) and the attributes_fn wiring in
        sensor.py (_build_probe_descriptions).
"""

from __future__ import annotations

import re
from typing import Any

from custom_components.redsea.probe_entities import (
    probe_index,
    probe_ranges,
    probe_state_attributes,
    tag_probe_entities,
)
from custom_components.redsea.sensor import _build_probe_descriptions

_CONFIG_RE = re.compile(r"@\.type=='([^']*)' & @\.uid=='([^']*)'")


class FakeHub:
    """Answer the two JSONPath lookups the helpers issue."""

    def __init__(self, probes: Any, config: dict[tuple[str, str], Any]) -> None:
        self.probes = probes
        self.config = config

    def get_data(self, path: str, is_None_possible: bool = False) -> Any:
        if "/probe/config" in path:
            match = _CONFIG_RE.search(path)
            assert match is not None
            return self.config.get((match.group(1), match.group(2)))
        assert path.endswith(".data.probes")
        return self.probes


PROBES = [
    {"type": "temperature", "uid": "0x001"},
    "garbage",
    {"type": "ph", "uid": "0x002"},
    {"type": "ph", "uid": "0x003"},
]
CONFIG = {
    ("ph", "0x002"): {
        "ranges": [7.6, 7.9, 8.4, 8.6],
        "temp": {"ranges": [21, 23, 26, 28]},
    },
    ("ph", "0x003"): {"ranges": [1, 2, 3], "temp": "bad"},
    ("orp", "0x004"): {"ranges": [100, 200, True, 480]},
    ("ec", "0x005"): {"temp": {"ranges": "nope"}},
}


def _hub() -> Any:
    # Typed Any: the helpers under test take a coordinator, of which the
    # fake only implements get_data
    return FakeHub(PROBES, CONFIG)


# ---------------------------------------------------------------------------
# probe_index
# ---------------------------------------------------------------------------


def test_probe_index_is_the_dashboard_position() -> None:
    hub = _hub()
    assert probe_index(hub, "temperature", "0x001") == 0
    # Non-dict entries still count as a position
    assert probe_index(hub, "ph", "0x003") == 3


def test_probe_index_needs_type_and_uid() -> None:
    # Same uid, other type: not the same probe
    assert probe_index(_hub(), "orp", "0x002") is None


def test_probe_index_without_probe_list() -> None:
    assert probe_index(FakeHub(None, {}), "ph", "0x002") is None


# ---------------------------------------------------------------------------
# probe_ranges
# ---------------------------------------------------------------------------


def test_probe_ranges_primary_and_temp() -> None:
    hub = _hub()
    assert probe_ranges(hub, "ph", "0x002") == [7.6, 7.9, 8.4, 8.6]
    assert probe_ranges(hub, "ph", "0x002", is_temp=True) == [21.0, 23.0, 26.0, 28.0]


def test_probe_ranges_rejects_unusable_entries() -> None:
    hub = _hub()
    # Not cached yet
    assert probe_ranges(hub, "ph", "0x999") is None
    # Wrong length, temp not an object
    assert probe_ranges(hub, "ph", "0x003") is None
    assert probe_ranges(hub, "ph", "0x003", is_temp=True) is None
    # A boolean is not a bound
    assert probe_ranges(hub, "orp", "0x004") is None
    # Temp ranges not a list
    assert probe_ranges(hub, "ec", "0x005", is_temp=True) is None


# ---------------------------------------------------------------------------
# probe_state_attributes
# ---------------------------------------------------------------------------


def test_probe_state_attributes_identity_only() -> None:
    assert probe_state_attributes(_hub(), "ph", "0x002") == {
        "probe_uid": "0x002",
        "probe_type": "ph",
        "probe_index": 2,
    }


def test_probe_state_attributes_with_ranges() -> None:
    hub = _hub()
    assert probe_state_attributes(hub, "ph", "0x002", "primary")["ranges"] == [
        7.6,
        7.9,
        8.4,
        8.6,
    ]
    assert probe_state_attributes(hub, "ph", "0x002", "temp")["ranges"] == [
        21.0,
        23.0,
        26.0,
        28.0,
    ]


# ---------------------------------------------------------------------------
# _build_probe_descriptions wiring
# ---------------------------------------------------------------------------


def test_every_probe_sensor_carries_its_probe() -> None:
    descs = _build_probe_descriptions({"uid": "0x002", "type": "ph", "name": "pH"})
    hub = _hub()
    for desc in descs:
        assert desc.attributes_fn is not None
        attrs = desc.attributes_fn(hub)
        assert attrs["probe_uid"] == "0x002"
        assert attrs["probe_type"] == "ph"
        assert attrs["probe_index"] == 2


def test_measurement_sensors_carry_their_ranges() -> None:
    descs = {
        d.key: d
        for d in _build_probe_descriptions({"uid": "0x002", "type": "ph", "name": "pH"})
    }
    hub = _hub()
    value = descs["probe_ph_0x002_value"].attributes_fn(hub)  # type: ignore[misc]
    temp = descs["probe_ph_0x002_temp_value"].attributes_fn(hub)  # type: ignore[misc]
    level = descs["probe_ph_0x002_level"].attributes_fn(hub)  # type: ignore[misc]
    assert value["ranges"] == [7.6, 7.9, 8.4, 8.6]
    assert temp["ranges"] == [21.0, 23.0, 26.0, 28.0]
    # Not a measurement: no ranges attribute at all
    assert "ranges" not in level


# ---------------------------------------------------------------------------
# tag_probe_entities
# ---------------------------------------------------------------------------


class _Entity:
    """Just what tagging reads and writes."""

    def __init__(self, unique_id: Any, attrs: dict[str, Any] | None = None) -> None:
        self._attr_unique_id = unique_id
        if attrs is not None:
            self._attr_extra_state_attributes = attrs


class _TaggedHub(FakeHub):
    serial = "SER"


def test_tag_probe_entities_by_unique_id() -> None:
    hub = _TaggedHub(
        [
            {"type": "PH", "uid": "0x001"},
            {"type": "ph", "uid": "0x0012"},
            {"type": "ec", "uid": "0xE"},
            {"type": "orp"},  # no uid: ignored
            "garbage",
        ],
        {},
    )
    buzzer = _Entity("SER_probe_ph_0x001_buzzer")
    longer = _Entity("SER_probe_ph_0x0012_enabled", {"keep": 1})
    ec_range = _Entity("SER_probe_ec_0xe_ppt_desired_range_low")
    hub_level = _Entity("SER_power_link")
    other_hub = _Entity("OTHER_probe_ph_0x001_buzzer")
    no_id = _Entity(None)

    tag_probe_entities(hub, [buzzer, longer, ec_range, hub_level, other_hub, no_id])

    assert buzzer._attr_extra_state_attributes == {
        "probe_uid": "0x001",
        "probe_type": "ph",
    }
    # A uid that merely starts like another one is not confused with it,
    # and existing attributes are kept
    assert longer._attr_extra_state_attributes == {
        "keep": 1,
        "probe_uid": "0x0012",
        "probe_type": "ph",
    }
    assert ec_range._attr_extra_state_attributes["probe_uid"] == "0xE"
    # No index: it would go stale on attributes set once
    assert "probe_index" not in buzzer._attr_extra_state_attributes
    for entity in (hub_level, other_hub, no_id):
        assert not hasattr(entity, "_attr_extra_state_attributes")


def test_tag_probe_entities_without_probe_list() -> None:
    entity = _Entity("SER_probe_ph_0x001_buzzer")
    tag_probe_entities(_TaggedHub(None, {}), [entity])
    assert not hasattr(entity, "_attr_extra_state_attributes")


def test_legacy_leak_key() -> None:
    from custom_components.redsea.probe_entities import legacy_leak_key

    assert legacy_leak_key("probe_0x0032b_detected", {"0x0032b"}) == (
        "probe_leak_0x0032b_detected"
    )
    assert legacy_leak_key("probe_leak_0x0032b_detected", {"0x0032b"}) is None
    assert legacy_leak_key("probe_0x0032b_detected", set()) is None

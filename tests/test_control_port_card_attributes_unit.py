"""What the card needs to draw and edit the RSCONTROL 12V ports.

Both ports share their translation keys (``port_on_off``, ``port_name``…), so
every port entity carries a ``port`` attribute; and the ``port_N_mode`` sensor
carries what the card's port editor reads, as ``socket_N_mode`` does on a
power center: the whole ``/ports/config`` entry, the schedule and the hub's
probe rule for the port.

Covers: probe_entities.tag_port_entities,
        ReefControlCoordinator.port_mode_attributes and the per-port schedule
        sources registered by the coordinator.
"""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import MagicMock

from custom_components.redsea.probe_entities import tag_port_entities

_PORT0: dict[str, Any] = {
    "number": 0,
    "type": "other",
    "mode": "sensor",
    "power_on_percent": 80,
    "sensor": None,
}
_PORT1: dict[str, Any] = {
    "number": 1,
    "type": "ato",
    "mode": "on",
    "power_on_percent": 100,
    "sensor": {"uid": "0xA", "type": "ph", "value": 8.3},
}


class _Entity:
    def __init__(self, unique_id: Any, attrs: dict[str, Any] | None = None) -> None:
        self._attr_unique_id = unique_id
        if attrs is not None:
            self._attr_extra_state_attributes = attrs


class _Hub:
    serial = "SER"


# ---------------------------------------------------------------------------
# tag_port_entities
# ---------------------------------------------------------------------------


def test_tag_port_entities_reads_the_port_from_the_unique_id() -> None:
    on_off = _Entity("SER_port_1_on_off")
    name = _Entity("SER_port_0_name", {"keep": True})
    others = [
        _Entity("SER_power_link"),
        _Entity("OTHER_port_0_on_off"),
        _Entity("SER_port_x_on_off"),
        _Entity("SER_port_1"),
        _Entity(None),
    ]
    tag_port_entities(_Hub(), [on_off, name, *others])
    assert on_off._attr_extra_state_attributes == {"port": 1}
    assert name._attr_extra_state_attributes == {"keep": True, "port": 0}
    for entity in others:
        assert not hasattr(entity, "_attr_extra_state_attributes")


# ---------------------------------------------------------------------------
# port_mode_attributes
# ---------------------------------------------------------------------------


def _coordinator(sources: list[dict[str, Any]]) -> Any:
    from custom_components.redsea.coordinator import ReefControlCoordinator
    from custom_components.redsea.reefbeat.control import ReefControlAPI

    coord = ReefControlCoordinator.__new__(ReefControlCoordinator)
    api = ReefControlAPI("10.0.0.7", False, cast(Any, MagicMock(name="session")))
    for source in api.data["sources"]:
        for extra in sources:
            if source["name"] == extra["name"]:
                source["data"] = extra["data"]
    for extra in sources:
        if extra["name"] not in [s["name"] for s in api.data["sources"]]:
            api.data["sources"].append(extra)
    coord.my_api = api
    return coord


def test_port_mode_attributes_from_the_hub_rules() -> None:
    rule = {"number": 0, "uid": "0xB", "type": "orp", "value": 400}
    coord = _coordinator(
        [
            {"name": "/ports/config", "type": "config", "data": [_PORT0, _PORT1]},
            {
                "name": "/subscription-info",
                "type": "data",
                "data": {"internal": ["junk", {"number": 1, "uid": "x"}, rule]},
            },
            {
                "name": "/port/0/schedule",
                "type": "config",
                "data": {"intervals": [{"time": 60, "duration": 30}]},
            },
        ]
    )
    attrs = coord.port_mode_attributes(0)
    assert attrs["config"] == _PORT0
    assert attrs["sensor_config"] == rule
    assert attrs["sensor_source"] == "control"
    assert attrs["schedule"] == {"intervals": [{"time": 60, "duration": 30}]}


def test_port_mode_attributes_falls_back_to_the_port_entry() -> None:
    coord = _coordinator(
        [
            {"name": "/ports/config", "type": "config", "data": [_PORT0, _PORT1]},
            {"name": "/subscription-info", "type": "data", "data": {"internal": 3}},
        ]
    )
    # The rule sits in the port's own entry
    attrs = coord.port_mode_attributes(1)
    assert attrs["sensor_config"] == _PORT1["sensor"]
    # No schedule fetched yet: nothing rather than an empty string
    assert attrs["schedule"] is None
    # A port following no probe
    assert coord.port_mode_attributes(0)["sensor_config"] is None


def test_port_mode_attributes_without_any_config() -> None:
    coord = _coordinator([])
    attrs = coord.port_mode_attributes(0)
    assert attrs["config"] is None
    assert attrs["sensor_config"] is None


def test_coordinator_polls_each_port_schedule() -> None:
    """One schedule source per port: 1 on a Lite, 2 on a Pro."""
    from custom_components.redsea.coordinator import ReefControlCoordinator

    for model, expected in (("RSCONTROLLITE", 1), ("RSCONTROLPRO", 2)):
        entry = MagicMock()
        entry.data = {
            "hw_model": model,
            "ip": "10.0.0.7",
        }
        coord = ReefControlCoordinator.__new__(ReefControlCoordinator)
        coord._ip = "10.0.0.7"  # type: ignore[attr-defined]
        coord._live_config_update = False  # type: ignore[attr-defined]
        coord._session = MagicMock()  # type: ignore[attr-defined]
        # Run only this class's own __init__ body, not the HA coordinator's
        from custom_components.redsea import coordinator as coord_mod

        orig = coord_mod.ReefBeatCloudLinkedCoordinator.__init__
        coord_mod.ReefBeatCloudLinkedCoordinator.__init__ = lambda self, h, e: None  # type: ignore[method-assign]
        try:
            ReefControlCoordinator.__init__(coord, MagicMock(), entry)
        finally:
            coord_mod.ReefBeatCloudLinkedCoordinator.__init__ = orig  # type: ignore[method-assign]
        names = [s["name"] for s in coord.my_api.data["sources"]]
        schedules = [n for n in names if n.startswith("/port/")]
        assert schedules == [f"/port/{n}/schedule" for n in range(expected)]


def test_port_mode_sensor_attributes() -> None:
    """The mode sensor carries the port number and the editor's attributes."""
    from custom_components.redsea.sensor import _port_mode_attributes_fn

    device = MagicMock()
    device.port_mode_attributes.return_value = {"config": {"type": "other"}}
    assert _port_mode_attributes_fn(1)(device) == {
        "port": 1,
        "config": {"type": "other"},
    }
    device.port_mode_attributes.assert_called_once_with(1)

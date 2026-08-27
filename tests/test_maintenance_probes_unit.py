"""Coverage for the RSCONTROLPRO probe-scoped maintenance path.

`iter_maintenance_probes` and everything it feeds — the per-probe interval
number and the notify switch — had no test at all. That was invisible until
now: the helper's multi-line signature matched an `exclude_also` pattern in
`.coveragerc`, so coverage reported the whole function as non-executable
rather than as missed.

Covered here:

- maintenance.py -> `probe_sub_id`, `iter_maintenance_probes` and every one of
                    its skip branches
- number.py     -> the `PROBE_SCOPES` branch of `_add_maintenance_numbers` and
                    the `placeholders` argument it passes
- button.py     -> the same branch of `_add_maintenance_buttons`
- switch.py     -> the same branch of `_add_maintenance_notify_switches`
- switch.py     -> the empty-catalogue early return, the RSRUN `get_data`
                    failure guard, and the notify switch's turn_on/turn_off
"""

from __future__ import annotations

from typing import Any, cast

import pytest
from homeassistant.core import HomeAssistant

import custom_components.redsea.maintenance as maint

PROBES_PATH = "$.sources[?(@.name=='/dashboard')].data.probes"


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _ProbeDevice:
    """Coordinator stand-in reporting a fixed `/dashboard.probes` array."""

    _hw = "RSCONTROLPRO"

    def __init__(self, probes: Any, serial: str = "CTL-PROBE") -> None:
        self.serial = serial
        self._probes = probes
        # Read by MaintenanceIntervalNumberEntity for UI grouping.
        self.device_info = None

    def get_data(self, name: str, is_None_possible: bool = False) -> Any:
        if name == PROBES_PATH:
            return self._probes
        return None


def _task(applies_to_sub: str) -> maint.MaintenanceTask:
    """Fetch the real RSCONTROLPRO task for a given probe scope."""
    return next(
        t for t in maint.TASKS["RSCONTROLPRO"] if t.applies_to_sub == applies_to_sub
    )


def _probe(uid: str, ptype: str, name: str | None = None) -> dict[str, Any]:
    probe: dict[str, Any] = {"uid": uid, "type": ptype}
    if name is not None:
        probe["name"] = name
    return probe


# ---------------------------------------------------------------------------
# probe_sub_id
# ---------------------------------------------------------------------------


class TestProbeSubId:
    """Hex uid -> integer sub_id, the key used by the maintenance store."""

    def test_parses_a_hex_uid(self) -> None:
        assert maint.probe_sub_id("0x0032B") == 0x32B

    def test_is_case_insensitive(self) -> None:
        assert maint.probe_sub_id("0xabc") == maint.probe_sub_id("0xABC")

    def test_accepts_a_bare_hex_string(self) -> None:
        # The firmware has been seen reporting uids with and without the 0x
        # prefix; both must land on the same integer namespace.
        assert maint.probe_sub_id("32B") == 0x32B

    def test_distinct_uids_do_not_collide(self) -> None:
        # Collisions would silently merge two probes' maintenance history.
        uids = ["0x0032B", "0x0032C", "0xFFFF", "0x1"]
        assert len({maint.probe_sub_id(u) for u in uids}) == len(uids)

    def test_raises_on_a_non_hex_uid(self) -> None:
        # The caller catches this; it must be a ValueError, not something else.
        with pytest.raises(ValueError):
            maint.probe_sub_id("not-hex")


# ---------------------------------------------------------------------------
# iter_maintenance_probes
# ---------------------------------------------------------------------------


class TestIterMaintenanceProbes:
    """One entry per probe a task applies to, skipping anything malformed."""

    def test_returns_empty_for_a_non_probe_task(self) -> None:
        # A head-scoped RSDOSE task must not pick up RSCONTROL probes.
        task = next(t for t in maint.TASKS["RSDOSE4"] if t.applies_to_sub == "head")
        device = _ProbeDevice([_probe("0x1", "ph")])
        assert maint.iter_maintenance_probes(cast(Any, device), task) == []

    def test_unscoped_task_matches_every_probe_type(self) -> None:
        # PROBE_SCOPES["probe"] is None: cleaning applies to anything wet.
        device = _ProbeDevice(
            [_probe("0x1", "ph"), _probe("0x2", "ec"), _probe("0x3", "temperature")]
        )
        got = maint.iter_maintenance_probes(cast(Any, device), _task("probe"))
        assert [sub_id for sub_id, _ in got] == [1, 2, 3]

    def test_scoped_task_filters_on_probe_type(self) -> None:
        device = _ProbeDevice([_probe("0x1", "ph"), _probe("0x2", "orp")])
        assert maint.iter_maintenance_probes(cast(Any, device), _task("probe_ph")) == [
            (1, "0x1")
        ]
        assert maint.iter_maintenance_probes(cast(Any, device), _task("probe_orp")) == [
            (2, "0x2")
        ]

    def test_wear_task_covers_ph_and_orp_but_not_ec(self) -> None:
        # Documents the deliberate EC exclusion: its 4-pole cell has no
        # electrolyte to deplete, so it has no replacement schedule.
        device = _ProbeDevice(
            [_probe("0x1", "ph"), _probe("0x2", "orp"), _probe("0x3", "ec")]
        )
        got = maint.iter_maintenance_probes(cast(Any, device), _task("probe_wear"))
        assert [sub_id for sub_id, _ in got] == [1, 2]

    def test_uses_the_probe_name_when_present(self) -> None:
        device = _ProbeDevice([_probe("0x2A", "ph", name="Sump pH")])
        assert maint.iter_maintenance_probes(cast(Any, device), _task("probe")) == [
            (0x2A, "Sump pH")
        ]

    def test_falls_back_to_the_uid_when_the_name_is_blank(self) -> None:
        device = _ProbeDevice([_probe("0x2A", "ph", name="")])
        assert maint.iter_maintenance_probes(cast(Any, device), _task("probe")) == [
            (0x2A, "0x2A")
        ]

    def test_falls_back_to_the_uid_when_the_name_is_not_a_string(self) -> None:
        device = _ProbeDevice([{"uid": "0x2A", "type": "ph", "name": 42}])
        assert maint.iter_maintenance_probes(cast(Any, device), _task("probe")) == [
            (0x2A, "0x2A")
        ]

    @pytest.mark.parametrize(
        "probes",
        [
            None,
            "not-a-list",
            {"uid": "0x1"},
            42,
        ],
        ids=["none", "string", "dict", "int"],
    )
    def test_returns_empty_when_probes_is_not_a_list(self, probes: Any) -> None:
        device = _ProbeDevice(probes)
        assert maint.iter_maintenance_probes(cast(Any, device), _task("probe")) == []

    def test_skips_non_dict_entries(self) -> None:
        device = _ProbeDevice(["junk", None, _probe("0x1", "ph")])
        assert maint.iter_maintenance_probes(cast(Any, device), _task("probe")) == [
            (1, "0x1")
        ]

    @pytest.mark.parametrize(
        "probe",
        [
            {"type": "ph"},
            {"uid": "", "type": "ph"},
            {"uid": 42, "type": "ph"},
            {"uid": None, "type": "ph"},
        ],
        ids=["missing", "empty", "int", "none"],
    )
    def test_skips_probes_without_a_usable_uid(self, probe: dict[str, Any]) -> None:
        # A half-paired probe must not break entity setup for the whole hub.
        device = _ProbeDevice([probe, _probe("0x1", "ph")])
        assert maint.iter_maintenance_probes(cast(Any, device), _task("probe")) == [
            (1, "0x1")
        ]

    def test_skips_a_probe_whose_uid_is_not_hex(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        device = _ProbeDevice([_probe("ZZZ", "ph"), _probe("0x1", "ph")])
        with caplog.at_level("DEBUG"):
            got = maint.iter_maintenance_probes(cast(Any, device), _task("probe"))
        assert got == [(1, "0x1")]
        assert any("unparsable uid" in r.message for r in caplog.records)

    def test_returns_empty_when_get_data_raises(self) -> None:
        class _Exploding(_ProbeDevice):
            def get_data(self, name: str, is_None_possible: bool = False) -> Any:
                raise RuntimeError("boom")

        device = _Exploding(None)
        assert maint.iter_maintenance_probes(cast(Any, device), _task("probe")) == []


# ---------------------------------------------------------------------------
# number.py — the PROBE_SCOPES branch
# ---------------------------------------------------------------------------


def test_add_maintenance_numbers_creates_one_entity_per_matching_probe() -> None:
    """The probe branch fans out and passes the probe name as a placeholder."""
    from custom_components.redsea.number import _add_maintenance_numbers

    device = _ProbeDevice(
        [_probe("0x1", "ph", name="Sump pH"), _probe("0x2", "orp", name="Sump ORP")]
    )

    entities: list[Any] = []
    _add_maintenance_numbers(cast(Any, device), entities)

    by_uid = {e._attr_unique_id: e for e in entities}

    # Cleaning is unscoped -> both probes. pH calibration -> pH only.
    clean = _task("probe")
    assert f"CTL-PROBE_{clean.key}_interval_1" in by_uid
    assert f"CTL-PROBE_{clean.key}_interval_2" in by_uid

    ph_cal = _task("probe_ph")
    assert f"CTL-PROBE_{ph_cal.key}_interval_1" in by_uid
    assert f"CTL-PROBE_{ph_cal.key}_interval_2" not in by_uid

    # The probe name reaches the entity as a translation placeholder, which is
    # what disambiguates two identically-named tasks in the UI.
    entity = by_uid[f"CTL-PROBE_{ph_cal.key}_interval_1"]
    assert entity._attr_translation_placeholders == {"probe": "Sump pH"}


def test_add_maintenance_numbers_creates_nothing_without_probes() -> None:
    """A hub reporting no probe yields no probe-scoped entity."""
    from custom_components.redsea.number import _add_maintenance_numbers

    entities: list[Any] = []
    _add_maintenance_numbers(cast(Any, _ProbeDevice([])), entities)
    assert entities == []


# ---------------------------------------------------------------------------
# button.py — the PROBE_SCOPES branch
# ---------------------------------------------------------------------------


def test_add_maintenance_buttons_creates_one_entity_per_matching_probe() -> None:
    """The action button fans out per probe and carries the `{probe}` label.

    Without the placeholder Home Assistant logs a name/placeholder mismatch
    and renders the raw `{probe}` in the UI.
    """
    from custom_components.redsea.button import _add_maintenance_buttons

    device = _ProbeDevice(
        [_probe("0x1", "ph", name="Sump pH"), _probe("0x2", "orp", name="Sump ORP")]
    )

    entities: list[Any] = []
    _add_maintenance_buttons(cast(Any, device), entities)

    by_uid = {e._attr_unique_id: e for e in entities}

    clean = _task("probe")
    assert f"CTL-PROBE_{clean.key}_1" in by_uid
    assert f"CTL-PROBE_{clean.key}_2" in by_uid

    ph_cal = _task("probe_ph")
    assert f"CTL-PROBE_{ph_cal.key}_1" in by_uid
    assert f"CTL-PROBE_{ph_cal.key}_2" not in by_uid

    entity = by_uid[f"CTL-PROBE_{ph_cal.key}_1"]
    assert entity._attr_translation_placeholders == {"probe": "Sump pH"}


def test_add_maintenance_buttons_creates_nothing_without_probes() -> None:
    """A hub reporting no probe yields no probe-scoped button."""
    from custom_components.redsea.button import _add_maintenance_buttons

    entities: list[Any] = []
    _add_maintenance_buttons(cast(Any, _ProbeDevice([])), entities)
    assert entities == []


# ---------------------------------------------------------------------------
# switch.py — early return, RSRUN guard, and the notify toggle
# ---------------------------------------------------------------------------


def test_add_maintenance_notify_switches_one_entity_per_matching_probe() -> None:
    """The notify switch follows the button and the interval slider."""
    from custom_components.redsea.switch import _add_maintenance_notify_switches

    device = _ProbeDevice(
        [_probe("0x1", "ph", name="Sump pH"), _probe("0x2", "orp", name="Sump ORP")]
    )

    entities: list[Any] = []
    _add_maintenance_notify_switches(cast(Any, device), entities)

    by_uid = {e._attr_unique_id: e for e in entities}

    ph_cal = _task("probe_ph")
    assert f"CTL-PROBE_{ph_cal.key}_notify_1" in by_uid
    assert f"CTL-PROBE_{ph_cal.key}_notify_2" not in by_uid

    entity = by_uid[f"CTL-PROBE_{ph_cal.key}_notify_1"]
    assert entity._attr_translation_placeholders == {"probe": "Sump pH"}


def test_add_maintenance_notify_switches_returns_when_hw_unknown() -> None:
    """An unknown model has no task catalogue: the function exits early."""
    from custom_components.redsea.switch import _add_maintenance_notify_switches

    class _UnknownHwDevice:
        _hw = "RS-NOT-A-REAL-MODEL"

    entities: list[Any] = []
    _add_maintenance_notify_switches(cast(Any, _UnknownHwDevice()), entities)
    assert entities == []


def test_add_maintenance_notify_switches_survives_a_failing_get_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An RSRUN whose `/dashboard.pump_N` lookup raises still builds switches.

    The "common parts" pseudo-device has no pump_N data at all, so the guard
    is the normal path there, not an edge case.
    """
    import custom_components.redsea.switch as switch_mod

    class _Run:
        _hw = "RSRUN"
        serial = "RUN-1"

        def get_data(self, name: str, is_None_possible: bool = False) -> Any:
            raise RuntimeError("boom")

    monkeypatch.setattr(switch_mod, "ReefRunCoordinator", _Run, raising=True)

    entities: list[Any] = []
    switch_mod._add_maintenance_notify_switches(cast(Any, _Run()), entities)

    # No pump survived the exception, so only the device-level tasks remain.
    assert all(e._sub_id == 0 for e in entities)


@pytest.mark.asyncio
async def test_notify_switch_turn_on_and_off_persist_to_the_store(
    hass: HomeAssistant,
) -> None:
    """turn_on / turn_off write straight through to the MaintenanceStore."""
    from custom_components.redsea.switch import MaintenanceNotifySwitchEntity

    class _Device:
        serial = "NOTIFY-1"

        def __init__(self) -> None:
            self._hass = hass
            self.maintenance = maint.MaintenanceStore(hass, "notify-toggle")
            self.device_info = None

    device = _Device()
    await device.maintenance.async_load()

    task = maint.TASKS["RSRUN"][0]
    entity = MaintenanceNotifySwitchEntity(cast(Any, device), task, sub_id=1)

    await entity.async_turn_off()
    assert device.maintenance.get_notify(device.serial, 1, task.key) is False

    await entity.async_turn_on()
    assert device.maintenance.get_notify(device.serial, 1, task.key) is True

    # The sibling instance is untouched: the store is keyed per sub_id.
    assert device.maintenance.get_notify(device.serial, 2, task.key) is True

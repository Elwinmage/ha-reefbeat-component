"""Tests for the RSCONTROL probe maintenance tasks.

Unlike RSDOSE heads and RSRUN pumps — fixed in number and addressed by index —
hub probes are discovered at runtime from ``/dashboard.probes`` and identified
by a hex uid. These tests cover the mapping from that payload to maintenance
instances, and the type filter that keeps calibration/replacement reminders off
probes that never need them.
"""

from __future__ import annotations

from typing import Any

from custom_components.redsea.maintenance import (
    PROBE_SCOPES,
    TASKS,
    iter_maintenance_probes,
    probe_sub_id,
    tasks_for,
)

_PROBES: list[dict[str, Any]] = [
    {"type": "leak", "uid": "0x0032B", "name": "Fuite 32B", "detected": False},
    {"type": "ph", "uid": "0x00A1F", "name": "pH bac"},
    {"type": "temperature", "uid": "0x00B22", "name": "Temp"},
    {"type": "ec", "uid": "0x00D44", "name": "Salinite"},
    {"type": "orp", "uid": "0x00C33"},  # no name -> falls back to the uid
]


class _FakeDevice:
    """Minimal stand-in exposing only the get_data() the helper needs."""

    def __init__(self, probes: Any = None) -> None:
        self._probes = probes

    def get_data(self, path: str, is_None_possible: bool = False) -> Any:
        assert "probes" in path
        return self._probes


def _task(key: str) -> Any:
    return next(t for t in tasks_for("RSCONTROLPRO") if t.key == key)


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------


def test_control_tasks_registered_for_both_models() -> None:
    """Lite and Pro share the same probe hardware, hence the same tasks."""
    assert TASKS["RSCONTROLLITE"] == TASKS["RSCONTROLPRO"]
    keys = {t.key for t in tasks_for("RSCONTROLPRO")}
    assert keys == {
        "control_probe_clean",
        "control_probe_calibration_ph",
        "control_probe_calibration_orp",
        "control_probe_replace",
    }


def test_only_cleaning_applies_to_every_probe() -> None:
    """Calibration and replacement are for drifting/wearing probes only."""
    assert _task("control_probe_clean").applies_to_sub == "probe"
    assert _task("control_probe_calibration_ph").applies_to_sub == "probe_ph"
    assert _task("control_probe_calibration_orp").applies_to_sub == "probe_orp"
    assert _task("control_probe_replace").applies_to_sub == "probe_wear"


def test_ph_and_orp_calibration_intervals_differ() -> None:
    """Red Sea: pH recalibrates monthly, ORP is validated every 2 months.

    Averaging both into one task would either over-remind on ORP or let pH
    drift for a month too long.
    """
    assert _task("control_probe_calibration_ph").default_days == 30
    assert _task("control_probe_calibration_orp").default_days == 60


def test_ec_probe_has_no_calibration_or_replacement_task() -> None:
    """The 4-pole conductivity cell has no electrolyte to deplete.

    Red Sea gives it a 24-month warranty, no routine recalibration (only
    after a cleaning) and no replacement schedule — unlike pH and ORP, which
    are both ~12-month wear items.
    """
    assert "ec" not in (PROBE_SCOPES["probe_ph"] or set())
    assert "ec" not in (PROBE_SCOPES["probe_orp"] or set())
    assert "ec" not in (PROBE_SCOPES["probe_wear"] or set())
    # ...but it still needs cleaning like every other wet probe.
    assert PROBE_SCOPES["probe"] is None


def test_wear_replacement_is_about_twelve_months() -> None:
    """Both consumable electrodes are rated ~12 months of continuous use."""
    assert _task("control_probe_replace").default_days == 365
    assert PROBE_SCOPES["probe_wear"] == frozenset({"ph", "orp"})


def test_default_interval_within_bounds() -> None:
    """A default outside its own slider range would be unreachable in the UI."""
    for task in tasks_for("RSCONTROLPRO"):
        assert task.min_days <= task.default_days <= task.max_days


# ---------------------------------------------------------------------------
# probe_sub_id
# ---------------------------------------------------------------------------


def test_probe_sub_id_parses_hex_uid() -> None:
    assert probe_sub_id("0x0032B") == 811


def test_probe_sub_id_is_stable_and_distinct() -> None:
    """Distinct probes must not collide in the storage key."""
    ids = {probe_sub_id(p["uid"]) for p in _PROBES}
    assert len(ids) == len(_PROBES)
    assert probe_sub_id("0x0032B") == probe_sub_id("0x0032B")


def test_probe_sub_id_is_positive() -> None:
    """sub_id == 0 means "device level" — a probe must never land there."""
    assert all(probe_sub_id(p["uid"]) > 0 for p in _PROBES)


# ---------------------------------------------------------------------------
# iter_maintenance_probes
# ---------------------------------------------------------------------------


def test_cleaning_covers_all_probes() -> None:
    got = iter_maintenance_probes(_FakeDevice(_PROBES), _task("control_probe_clean"))
    assert [name for _, name in got] == [
        "Fuite 32B",
        "pH bac",
        "Temp",
        "Salinite",
        "0x00C33",
    ]


def test_ph_calibration_targets_only_the_ph_probe() -> None:
    got = iter_maintenance_probes(
        _FakeDevice(_PROBES), _task("control_probe_calibration_ph")
    )
    assert [name for _, name in got] == ["pH bac"]


def test_orp_validation_targets_only_the_orp_probe() -> None:
    got = iter_maintenance_probes(
        _FakeDevice(_PROBES), _task("control_probe_calibration_orp")
    )
    assert [name for _, name in got] == ["0x00C33"]


def test_replacement_covers_ph_and_orp_but_not_ec() -> None:
    """The EC probe outlives both: no replacement reminder for it."""
    got = iter_maintenance_probes(_FakeDevice(_PROBES), _task("control_probe_replace"))
    names = [name for _, name in got]
    assert names == ["pH bac", "0x00C33"]
    assert "Salinite" not in names


def test_unnamed_probe_falls_back_to_uid() -> None:
    got = iter_maintenance_probes(_FakeDevice(_PROBES), _task("control_probe_clean"))
    assert (3123, "0x00C33") in got


def test_malformed_uid_is_skipped_not_raised() -> None:
    """A half-paired probe must not break setup for the whole device."""
    probes = [*_PROBES, {"type": "ph", "uid": "NOTHEX", "name": "Broken"}]
    got = iter_maintenance_probes(_FakeDevice(probes), _task("control_probe_clean"))
    assert "Broken" not in [name for _, name in got]
    assert len(got) == len(_PROBES)


def test_probe_without_uid_is_skipped() -> None:
    probes = [{"type": "ph", "name": "No uid"}, *_PROBES]
    got = iter_maintenance_probes(_FakeDevice(probes), _task("control_probe_clean"))
    assert "No uid" not in [name for _, name in got]


def test_missing_probes_payload_yields_nothing() -> None:
    assert (
        iter_maintenance_probes(_FakeDevice(None), _task("control_probe_clean")) == []
    )


def test_non_dict_entries_are_ignored() -> None:
    got = iter_maintenance_probes(
        _FakeDevice(["junk", None, *_PROBES]), _task("control_probe_clean")
    )
    assert len(got) == len(_PROBES)


def test_non_probe_task_returns_nothing() -> None:
    """Head/pump tasks keep their existing code path untouched."""
    got = iter_maintenance_probes(_FakeDevice(_PROBES), _task("control_probe_clean"))
    assert got  # sanity: the fixture does produce probes
    dose_task = next(t for t in tasks_for("RSDOSE4") if t.applies_to_sub == "head")
    assert iter_maintenance_probes(_FakeDevice(_PROBES), dose_task) == []

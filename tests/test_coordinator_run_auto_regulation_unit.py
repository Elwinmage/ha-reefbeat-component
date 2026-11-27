"""Auto regulation of a ReefRun skimmer: the segment in force, the intensity
it asks for, and the warning raised when the pump runs under it."""

from __future__ import annotations

from typing import Any

import pytest

from custom_components.redsea.coordinator import ReefRunCoordinator

DASH = "$.sources[?(@.name=='/dashboard')].data.pump_1."
SETTINGS = "$.sources[?(@.name=='/pump/settings')].data.pump_1.schedule"

SCHEDULE = [
    {"st": 0, "ti": 100, "pd": 0},
    {"st": 600, "ti": 80, "pd": 0},
    {"st": 1200, "ti": 60, "pd": 0},
]

# The pump of the warning tests keeps one segment all day long, so that what is
# scheduled does not depend on the hour the suite runs at.
FLAT_SCHEDULE = [{"st": 0, "ti": 100, "pd": 0}]


class _FakeRun(ReefRunCoordinator):
    """A ReefRun coordinator reduced to its data: no HA, no API."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._map = data

    def get_data(
        self, name: str, is_None_possible: bool = False, cached: bool = True
    ) -> Any:
        return self._map.get(name)


def _run(**pump: Any) -> _FakeRun:
    """A skimmer, operational, driven by its sensor, at 100% as scheduled."""
    data: dict[str, Any] = {
        SETTINGS: FLAT_SCHEDULE,
        DASH + "type": "skimmer",
        DASH + "state": "operational",
        DASH + "schedule_enabled": True,
        DASH + "sensor_controlled": True,
        DASH + "intensity": 100,
    }
    data.update({DASH + key: value for key, value in pump.items()})
    return _FakeRun(data)


# -- The segment in force -----------------------------------------------------


@pytest.mark.parametrize(
    ("minutes", "expected"),
    [
        (0, 100),  # first segment, from midnight
        (599, 100),  # one minute before the second one starts
        (601, 80),  # the second one took over
        (1439, 60),  # last segment, until midnight
    ],
)
def test_active_schedule_entry(minutes: int, expected: int) -> None:
    entry = ReefRunCoordinator.active_schedule_entry(SCHEDULE, minutes)
    assert entry is not None
    assert entry["ti"] == expected


def test_active_schedule_entry_without_schedule() -> None:
    assert ReefRunCoordinator.active_schedule_entry([]) is None
    assert ReefRunCoordinator.active_schedule_entry(None) is None


def test_active_schedule_entry_skips_unusable_segments() -> None:
    schedule = [{"st": 0, "ti": 100}, "junk", {"st": "?", "ti": 50}]
    entry = ReefRunCoordinator.active_schedule_entry(schedule, 720)
    assert entry is not None
    assert entry["ti"] == 100


def test_scheduled_intensity() -> None:
    assert _run().scheduled_intensity(1) == pytest.approx(100)


def test_scheduled_intensity_without_schedule() -> None:
    assert _FakeRun({}).scheduled_intensity(1) is None


# -- The warning itself -------------------------------------------------------


def test_following_its_schedule_is_not_a_warning() -> None:
    assert _run(intensity=100).auto_regulation(1) is False


def test_running_under_the_schedule_is_a_warning() -> None:
    """The water column rose: the pump lowered its own speed to 79%."""
    run = _run(intensity=79)
    assert run.auto_regulation(1) is True
    attributes = run.auto_regulation_attributes(1)
    assert attributes["scheduled_intensity"] == 100
    assert attributes["running_intensity"] == 79
    assert attributes["deviation"] == pytest.approx(-21)
    assert attributes["pump"] == 1


def test_the_deadband_absorbs_a_rounding() -> None:
    assert _run(intensity=99).auto_regulation(1) is False


def test_the_over_skimming_state_is_enough() -> None:
    assert _run(state="over-skimming", intensity=100).auto_regulation(1) is True


@pytest.mark.parametrize("state", ["feeding", "preview", "maintenance", "full-cup"])
def test_another_state_lowers_the_speed_for_its_own_reason(state: str) -> None:
    assert _run(state=state, intensity=40).auto_regulation(1) is False


def test_a_pump_left_to_itself_is_not_regulated() -> None:
    assert _run(intensity=40, schedule_enabled=False).auto_regulation(1) is False
    assert _run(intensity=40, sensor_controlled=False).auto_regulation(1) is False


def test_a_return_pump_has_no_auto_regulation() -> None:
    assert _run(type="return", intensity=40).auto_regulation(1) is None


def test_an_unreadable_intensity_says_nothing() -> None:
    assert _run(intensity=None).auto_regulation(1) is None


# -- What the device says badly ----------------------------------------------


def test_active_schedule_entry_of_an_unusable_schedule() -> None:
    assert ReefRunCoordinator.active_schedule_entry(["junk"], 720) is None


def test_a_segment_without_an_intensity_says_nothing() -> None:
    run = _FakeRun({SETTINGS: [{"st": 0}]})
    assert run.scheduled_intensity(1) is None


def test_an_intensity_that_is_not_a_number_says_nothing() -> None:
    assert _run(intensity="--").running_intensity(1) is None


def test_a_pump_without_a_schedule_says_nothing() -> None:
    run = _run(intensity=40)
    run._map[SETTINGS] = []
    assert run.auto_regulation(1) is None


def test_the_attributes_of_a_pump_that_says_nothing() -> None:
    run = _run(intensity=None)
    run._map[SETTINGS] = []
    assert run.auto_regulation_attributes(1) == {
        "scheduled_intensity": None,
        "running_intensity": None,
        "deviation": None,
        "pump": 1,
    }

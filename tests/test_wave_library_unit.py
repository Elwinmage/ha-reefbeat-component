"""Pure helpers of the ReefWave wave library and day program."""

from __future__ import annotations

import pytest

from custom_components.redsea.wave_library import (
    DEFAULT_FTI,
    DEFAULT_RTI,
    WAVE_TYPE_FIELDS,
    WaveLibraryError,
    check_name,
    check_settings,
    check_slots,
    library_payload,
    library_wave,
    merge_pump_settings,
    program_waves,
    pump_settings_of,
    schedule_intervals,
    uses_wave,
)

# Real cloud library entries (ReefBeat account, sanitised)
STEP = {
    "uid": "f760",
    "aquarium_uid": "aq",
    "type": "st",
    "name": "Nettoyage",
    "frt": 10,
    "rrt": 2,
    "pd": 3.0,
    "sn": 6,
    "default": False,
    "pump_settings": [
        {"hwid": "083a", "fti": 100, "rti": 60, "sync": True},
        {"hwid": "bcdd", "fti": 40, "rti": 30, "sync": False},
    ],
}
SURFACE = {
    "uid": "774a",
    "aquarium_uid": "aq",
    "type": "su",
    "name": "RS Surface",
    "pd": 1.0,
    "default": True,
    "pump_settings": [],
}


def test_pump_settings_of() -> None:
    assert pump_settings_of(STEP, "bcdd") == {
        "hwid": "bcdd",
        "fti": 40,
        "rti": 30,
        "sync": False,
    }
    assert pump_settings_of(STEP, "zzzz") is None
    assert pump_settings_of({"pump_settings": None}, "x") is None
    assert pump_settings_of({"pump_settings": ["junk"]}, "x") is None


def test_library_wave_with_and_without_pump_settings() -> None:
    assert library_wave(STEP, "083a") == {
        "uid": "f760",
        "name": "Nettoyage",
        "type": "st",
        "default": False,
        "frt": 10,
        "rrt": 2,
        "pd": 3.0,
        "sn": 6,
        "fti": 100,
        "rti": 60,
        "sync": True,
    }
    surface = library_wave(SURFACE, "083a")
    # Only the fields the type uses, default intensities
    assert surface["pd"] == 1.0
    assert surface["frt"] is None and surface["sn"] is None
    assert (surface["fti"], surface["rti"], surface["sync"]) == (
        DEFAULT_FTI,
        DEFAULT_RTI,
        False,
    )
    assert surface["default"] is True
    # Junk values and missing type
    odd = library_wave({"uid": "x", "frt": True, "pump_settings": []}, "h")
    assert odd["type"] == "nw" and odd["frt"] is None


def test_check_settings() -> None:
    out = check_settings(
        {"type": "st", "frt": 10, "rrt": 2, "pd": 3, "sn": 6, "fti": 80, "rti": 0}
    )
    assert out == {
        "shape": {"type": "st", "frt": 10, "rrt": 2, "pd": 3, "sn": 6},
        "pump": {"sync": False, "fti": 80, "rti": 0},
    }
    # Fields of other types are dropped
    su = check_settings({"type": "su", "pd": 1, "frt": 9, "fti": 50, "rti": 50})
    assert su["shape"] == {"type": "su", "pd": 1}
    assert check_settings({"type": "nw", "fti": 0, "rti": 0, "sync": True})["pump"][
        "sync"
    ]
    with pytest.raises(WaveLibraryError) as err:
        check_settings({"type": "zz"})
    assert err.value.key == "wave_bad_type"
    assert err.value.placeholders == {"type": "zz"}
    for bad in (
        {"type": "re", "frt": 0, "rrt": 2, "fti": 1, "rti": 1},
        {"type": "re", "frt": "a", "rrt": 2, "fti": 1, "rti": 1},
        {"type": "re", "frt": 1, "rrt": 2, "fti": 101, "rti": 1},
        {"type": "re", "frt": 1, "rrt": 2, "fti": 1},
    ):
        with pytest.raises(WaveLibraryError) as err:
            check_settings(bad)
        assert err.value.key == "wave_bad_value"


def test_merge_pump_settings() -> None:
    merged = merge_pump_settings(
        STEP["pump_settings"] + ["junk"],
        ["083a", "083a", "new1"],
        {"fti": 10, "rti": 20, "sync": False},
    )
    assert merged == [
        {"hwid": "bcdd", "fti": 40, "rti": 30, "sync": False},
        {"hwid": "083a", "fti": 10, "rti": 20, "sync": False},
        {"hwid": "new1", "fti": 10, "rti": 20, "sync": False},
    ]
    assert merge_pump_settings(None, [], {}) == []  # type: ignore[arg-type]


def test_library_payload() -> None:
    shape = {"type": "re", "frt": 10, "rrt": 2}
    ps = [{"hwid": "h", "fti": 1, "rti": 2, "sync": True}]
    assert library_payload("A", shape, ps) == {
        "name": "A",
        "type": "re",
        "frt": 10,
        "rrt": 2,
        "default": False,
        "pump_settings": ps,
    }
    created = library_payload("A", shape, ps, "aq")
    assert next(iter(created)) == "aquarium_uid"
    assert created["aquarium_uid"] == "aq"


def test_check_name() -> None:
    lib = [STEP, SURFACE]
    assert check_name("  Storm ", lib) == "Storm"
    # Its own name does not clash on an update
    assert check_name("Nettoyage", lib, "f760") == "Nettoyage"
    with pytest.raises(WaveLibraryError) as err:
        check_name("Nettoyage ", lib)
    assert err.value.key == "wave_name_taken"
    for bad in ("", "  ", None, 3):
        with pytest.raises(WaveLibraryError) as err:
            check_name(bad, lib)
        assert err.value.key == "wave_name_required"


def test_check_slots() -> None:
    out = check_slots(
        [
            {"st": 600, "wave_uid": "b", "direction": "alt"},
            {"st": 0, "wave_uid": "a"},
        ]
    )
    assert out == [
        {"st": 0, "wave_uid": "a", "direction": "fw"},
        {"st": 600, "wave_uid": "b", "direction": "alt"},
    ]
    cases = [
        ([], "wave_program_empty"),
        ("x", "wave_program_empty"),
        (["junk"], "wave_program_bad_slot"),
        ([{"st": "0", "wave_uid": "a"}], "wave_program_bad_slot"),
        ([{"st": True, "wave_uid": "a"}], "wave_program_bad_slot"),
        ([{"st": 1440, "wave_uid": "a"}], "wave_program_bad_slot"),
        ([{"st": 0, "wave_uid": ""}], "wave_program_bad_slot"),
        ([{"st": 0, "wave_uid": "a", "direction": "up"}], "wave_program_bad_slot"),
        ([{"st": 60, "wave_uid": "a"}], "wave_program_midnight"),
        (
            [{"st": 0, "wave_uid": "a"}, {"st": 0, "wave_uid": "b"}],
            "wave_program_same_start",
        ),
    ]
    for slots, key in cases:
        with pytest.raises(WaveLibraryError) as err:
            check_slots(slots)
        assert err.value.key == key


def test_schedule_intervals() -> None:
    waves = {
        "f760": library_wave(STEP, "083a"),
        "774a": library_wave(SURFACE, "083a"),
        "nw": library_wave({"uid": "nw", "type": "nw", "name": "No Wave"}, "083a"),
    }
    slots = [
        {"st": 0, "wave_uid": "nw", "direction": "alt"},
        {"st": 600, "wave_uid": "f760", "direction": "alt"},
        {"st": 900, "wave_uid": "774a", "direction": "rw"},
    ]
    nw, step, surface = schedule_intervals(slots, waves)
    # No wave always forward, no shape
    assert nw["direction"] == "fw"
    assert "frt" not in nw
    assert step == {
        "wave_uid": "f760",
        "type": "st",
        "name": "Nettoyage",
        "frt": 10,
        "rrt": 2,
        "pd": 3.0,
        "sn": 6,
        "fti": 100,
        "rti": 60,
        "sync": True,
        "st": 600,
        "start": 600,
        "direction": "alt",
    }
    assert "sync" not in surface and surface["pd"] == 1.0
    with pytest.raises(WaveLibraryError) as err:
        schedule_intervals([{"st": 0, "wave_uid": "zz", "direction": "fw"}], waves)
    assert err.value.key == "wave_not_found"
    # A shape field the cloud left empty is not sent
    waves["f760"]["sn"] = None
    assert "sn" not in schedule_intervals(slots, waves)[1]


def test_program_waves_and_uses_wave() -> None:
    intervals = [
        {
            "st": 0,
            "wave_uid": "a",
            "name": "A",
            "type": "re",
            "frt": 10,
            "rrt": 2,
            "fti": 70,
            "rti": 30,
            "sync": True,
            "direction": "alt",
        },
        {"st": 300, "wave_uid": "a", "name": "A", "type": "re"},
        {"st": 600, "wave_uid": "b", "name": "B", "type": "su", "pd": 1},
        {"st": 700},
        "junk",
    ]
    waves = program_waves(intervals)
    assert [w["uid"] for w in waves] == ["a", "b"]
    assert waves[0]["fti"] == 70 and waves[0]["sync"] is True
    assert waves[1]["fti"] == 0 and waves[1]["pd"] == 1
    assert program_waves(None) == []
    assert uses_wave(intervals, "b") is True
    assert uses_wave(intervals, "c") is False
    assert uses_wave(None, "a") is False


def test_every_type_has_fields() -> None:
    assert set(WAVE_TYPE_FIELDS) == {"nw", "ra", "re", "st", "su", "un"}

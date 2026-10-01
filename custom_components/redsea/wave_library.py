"""ReefWave cloud wave library and day program: pure helpers.

As in the ReefBeat app, the waves of an aquarium are kept in the cloud
library `/reef-wave/library`. A wave holds its shape, shared by every pump:

    {uid, aquarium_uid, name, type, frt, rrt, pd, sn, default,
     pump_settings: [{hwid, fti, rti, sync}, ...]}

and, per pump (`pump_settings`, by hwid), the forward / reverse intensities
and the sync flag.

The day program of a pump is `/reef-wave/schedule/<hwid>`: intervals that
copy the wave they use (its shape and this pump's intensities) and add their
own start (`st`, minute of the day) and direction (`fw`, `rw`, `alt`).

Nothing here does I/O: the coordinator reads the cloud, calls these helpers
to check and build the payloads, then writes.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .const import WAVE_DIRECTIONS, WAVE_TYPES

# Shape fields each wave type uses (the others are left out of its payload).
WAVE_TYPE_FIELDS: dict[str, tuple[str, ...]] = {
    "nw": (),
    "ra": ("frt", "rrt"),
    "re": ("frt", "rrt"),
    "st": ("frt", "rrt", "pd", "sn"),
    "su": ("pd",),
    "un": ("frt", "rrt", "pd"),
}

# Intensities of a pump that has no settings of its own in a wave yet.
DEFAULT_FTI = 50
DEFAULT_RTI = 50

MINUTES_PER_DAY = 24 * 60


class WaveLibraryError(ValueError):
    """A refused edit; `key` is the translation key of the message."""

    def __init__(self, key: str, **placeholders: str) -> None:
        super().__init__(key)
        self.key = key
        self.placeholders = placeholders


def _num(value: Any) -> int | float | None:
    """A number from the cloud, None when absent or not a number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def pump_settings_of(entry: Mapping[str, Any], hwid: str) -> dict[str, Any] | None:
    """Settings of one pump in a library wave, None when it has none."""
    for settings in entry.get("pump_settings") or []:
        if isinstance(settings, Mapping) and settings.get("hwid") == hwid:
            return dict(settings)
    return None


def library_wave(entry: Mapping[str, Any], hwid: str) -> dict[str, Any]:
    """A library wave as the card uses it, with this pump's intensities.

    {uid, name, type, default, frt, rrt, pd, sn, fti, rti, sync}: the shape
    fields the type does not use are None; a pump without settings of its
    own in the wave gets the default intensities.
    """
    wave_type = str(entry.get("type") or "nw")
    fields = WAVE_TYPE_FIELDS.get(wave_type, ())
    settings = pump_settings_of(entry, hwid) or {}
    fti = _num(settings.get("fti"))
    rti = _num(settings.get("rti"))
    return {
        "uid": entry.get("uid"),
        "name": entry.get("name"),
        "type": wave_type,
        "default": entry.get("default") is True,
        **{
            key: (_num(entry.get(key)) if key in fields else None)
            for key in ("frt", "rrt", "pd", "sn")
        },
        "fti": DEFAULT_FTI if fti is None else fti,
        "rti": DEFAULT_RTI if rti is None else rti,
        "sync": settings.get("sync") is True,
    }


def check_settings(settings: Mapping[str, Any]) -> dict[str, Any]:
    """Check the settings of a wave sent by the card.

    @return the shape ({type, frt, rrt, pd, sn} limited to the type's
            fields) and the pump settings ({fti, rti, sync})
    @raise WaveLibraryError on an unknown type or a missing / bad value
    """
    wave_type = settings.get("type")
    if wave_type not in WAVE_TYPES:
        raise WaveLibraryError("wave_bad_type", type=str(wave_type))
    shape: dict[str, Any] = {"type": wave_type}
    for key in WAVE_TYPE_FIELDS[wave_type]:
        value = _num(settings.get(key))
        if value is None or value <= 0:
            raise WaveLibraryError("wave_bad_value", field=key)
        shape[key] = value
    pump: dict[str, Any] = {"sync": settings.get("sync") is True}
    for key in ("fti", "rti"):
        value = _num(settings.get(key))
        if value is None or not 0 <= value <= 100:
            raise WaveLibraryError("wave_bad_value", field=key)
        pump[key] = value
    return {"shape": shape, "pump": pump}


def merge_pump_settings(
    existing: Iterable[Any], hwids: Iterable[str], pump: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Pump settings of a wave with these pumps' replaced, the others kept.

    @param existing: the wave's current pump_settings
    @param hwids: the pumps the edit applies to (the pump, or its group)
    @param pump: {fti, rti, sync}
    """
    targets = list(dict.fromkeys(hwids))
    kept = [
        dict(s)
        for s in existing or []
        if isinstance(s, Mapping) and s.get("hwid") not in targets
    ]
    return kept + [{"hwid": hwid, **pump} for hwid in targets]


def library_payload(
    name: str,
    shape: Mapping[str, Any],
    pump_settings: list[dict[str, Any]],
    aquarium: str | None = None,
) -> dict[str, Any]:
    """Body of a library wave, as the ReefBeat app sends it.

    The aquarium is only given on creation (POST).
    """
    payload: dict[str, Any] = {"name": name, **shape, "default": False}
    payload["pump_settings"] = pump_settings
    if aquarium is not None:
        payload = {"aquarium_uid": aquarium, **payload}
    return payload


def check_name(
    name: Any, library: Iterable[Mapping[str, Any]], uid: str | None = None
) -> str:
    """A wave name, trimmed, unique in the aquarium's library.

    The new wave is found back by its name after its creation: two waves
    with the same name would make the program point at the wrong one.
    @param uid: the wave being renamed (its own name does not clash)
    @raise WaveLibraryError on an empty or taken name
    """
    if not isinstance(name, str) or not name.strip():
        raise WaveLibraryError("wave_name_required")
    clean = name.strip()
    for entry in library:
        if entry.get("uid") != uid and str(entry.get("name", "")).strip() == clean:
            raise WaveLibraryError("wave_name_taken", name=clean)
    return clean


def check_slots(slots: Any) -> list[dict[str, Any]]:
    """Check the slots of a day program sent by the card.

    Each slot is {st, wave_uid, direction}. The program starts at midnight,
    each start is a distinct minute of the day.
    @return the slots, sorted by start
    @raise WaveLibraryError on a malformed program
    """
    if not isinstance(slots, list) or not slots:
        raise WaveLibraryError("wave_program_empty")
    clean: list[dict[str, Any]] = []
    for slot in slots:
        if not isinstance(slot, Mapping):
            raise WaveLibraryError("wave_program_bad_slot")
        st = slot.get("st")
        if isinstance(st, bool) or not isinstance(st, int):
            raise WaveLibraryError("wave_program_bad_slot")
        if not 0 <= st < MINUTES_PER_DAY:
            raise WaveLibraryError("wave_program_bad_slot")
        uid = slot.get("wave_uid")
        if not isinstance(uid, str) or not uid:
            raise WaveLibraryError("wave_program_bad_slot")
        direction = slot.get("direction", "fw")
        if direction not in WAVE_DIRECTIONS:
            raise WaveLibraryError("wave_program_bad_slot")
        clean.append({"st": st, "wave_uid": uid, "direction": direction})
    clean.sort(key=lambda s: s["st"])
    if clean[0]["st"] != 0:
        raise WaveLibraryError("wave_program_midnight")
    starts = [s["st"] for s in clean]
    if len(set(starts)) != len(starts):
        raise WaveLibraryError("wave_program_same_start")
    return clean


def schedule_intervals(
    slots: list[dict[str, Any]],
    waves: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Intervals of a pump's program, as the ReefBeat app posts them.

    Each interval copies its wave (shape and this pump's intensities), its
    start and its direction. A "no wave" interval always runs forward.
    @param slots: checked slots
    @param waves: the waves by uid, in library_wave() form (this pump's)
    @raise WaveLibraryError when a slot uses a wave the library lacks
    """
    intervals: list[dict[str, Any]] = []
    for slot in slots:
        wave = waves.get(slot["wave_uid"])
        if wave is None:
            raise WaveLibraryError("wave_not_found", uid=slot["wave_uid"])
        interval: dict[str, Any] = {
            "wave_uid": wave["uid"],
            "type": wave["type"],
            "name": wave["name"],
        }
        for key in WAVE_TYPE_FIELDS.get(wave["type"], ()):
            if wave.get(key) is not None:
                interval[key] = wave[key]
        interval["fti"] = wave["fti"]
        interval["rti"] = wave["rti"]
        if wave.get("sync"):
            interval["sync"] = True
        interval["st"] = slot["st"]
        # Some firmwares read the start from "start" in the cloud payload
        interval["start"] = slot["st"]
        interval["direction"] = "fw" if wave["type"] == "nw" else slot["direction"]
        intervals.append(interval)
    return intervals


def program_waves(intervals: Any) -> list[dict[str, Any]]:
    """Waves of a program without the library (local mode): one per uid.

    Without a cloud account the pump only knows the waves of its own day
    program; they are the choices of the program editor.
    """
    waves: dict[str, dict[str, Any]] = {}
    for interval in intervals if isinstance(intervals, list) else []:
        if not isinstance(interval, Mapping):
            continue
        uid = interval.get("wave_uid")
        if not isinstance(uid, str) or uid in waves:
            continue
        entry = {
            "uid": uid,
            "name": interval.get("name"),
            "type": interval.get("type"),
            "frt": interval.get("frt"),
            "rrt": interval.get("rrt"),
            "pd": interval.get("pd"),
            "sn": interval.get("sn"),
            "default": False,
            "pump_settings": [],
        }
        wave = library_wave(entry, "")
        wave["fti"] = _num(interval.get("fti")) or 0
        wave["rti"] = _num(interval.get("rti")) or 0
        wave["sync"] = interval.get("sync") is True
        waves[uid] = wave
    return list(waves.values())


def uses_wave(intervals: Any, uid: str) -> bool:
    """Whether a day program uses a wave."""
    return any(
        isinstance(i, Mapping) and i.get("wave_uid") == uid
        for i in (intervals if isinstance(intervals, list) else [])
    )

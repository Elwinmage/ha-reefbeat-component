"""Cloud side of a ReefWave key capture: its waves and its program.

A ReefWave is the only family whose configuration lives in the Red Sea
cloud: the waves of an aquarium (``/reef-wave/library``, with the
intensities of each pump in ``pump_settings``) and the program of each pump
(``/reef-wave/schedule/<hwid>``). The cloud pushes its copy to the pump at
every connection (``POST /group``, ``/auto/init``, ``/auto``...,
``/auto/apply``, seen on the spy run of 2026-11-01): a pump whose cloud copy
was lost by the delete / create of the capture gets its program wiped at its
next connection, whatever was put back on the pump itself.

So, for a ReefWave:

1. before the delete, the custom waves of its aquarium (the Red Sea ones,
   ``default``, are the same for everybody) go into the snapshot, with its
   program (``/auto`` of the pump, as the cloud pushes it);
2. after the keys, the waves are put back in the cloud: a wave gone is
   created again (its new uid replaces the old one in the program), a wave
   that lost the settings of this pump gets them back; the others are left
   alone;
3. the program is posted to the cloud, then the cloud is asked to push the
   programs of the aquarium to its pumps (``/reef-wave/<aquarium>/sync``).

The pump is read again afterwards: what the cloud did not put back is
restored on the pump itself (``capture.rswave_steps``).
"""

from __future__ import annotations

import copy
import logging
from typing import Any

from ..const import WAVES_LIBRARY
from ..wave_library import WAVE_TYPE_FIELDS, library_payload, pump_settings_of

_LOGGER = logging.getLogger(__name__)

# Key of the cloud backup in a snapshot
CLOUD_WAVES = "waves"


def _json(result: Any) -> Any:
    """The JSON body of a successful cloud answer, None otherwise."""
    if not isinstance(result, dict):
        return None
    status = int(result.get("status", 0) or 0)
    return result.get("json") if 200 <= status < 300 else None


def _ok(result: Any) -> bool:
    if not isinstance(result, dict):
        return False
    return 200 <= int(result.get("status", 0) or 0) < 300


def custom_waves(library: Any, aquarium: str) -> list[dict[str, Any]]:
    """The waves of the aquarium that are not Red Sea's."""
    if not isinstance(library, list):
        return []
    return [
        copy.deepcopy(entry)
        for entry in library
        if isinstance(entry, dict)
        and entry.get("default") is not True
        and entry.get("uid")
        and (not aquarium or entry.get("aquarium_uid") == aquarium)
    ]


async def read_library(cloud: Any) -> list[Any] | None:
    """The wave library of the account, None when it cannot be read."""
    library = _json(await cloud.http_get(WAVES_LIBRARY))
    return library if isinstance(library, list) else None


async def backup_waves(cloud: Any, aquarium: str) -> dict[str, Any] | None:
    """The cloud backup of a pump: the custom waves of its aquarium; None
    when the library cannot be read (the capture must not go on then)."""
    library = await read_library(cloud)
    if library is None:
        return None
    return {"aquarium_uid": aquarium, "library": custom_waves(library, aquarium)}


def _shape(entry: dict[str, Any]) -> dict[str, Any]:
    wave_type = str(entry.get("type") or "nw")
    return {
        "type": wave_type,
        **{
            key: entry[key]
            for key in WAVE_TYPE_FIELDS.get(wave_type, ())
            if entry.get(key) is not None
        },
    }


def program_of(intervals: Any, renamed: dict[str, str]) -> list[dict[str, Any]]:
    """The program of a pump as the cloud takes it, the waves created again
    under their new uid."""
    program: list[dict[str, Any]] = []
    for interval in intervals if isinstance(intervals, list) else []:
        if not isinstance(interval, dict):
            continue
        item = dict(interval)
        uid = str(item.get("wave_uid", ""))
        item["wave_uid"] = renamed.get(uid, uid)
        # The cloud payload carries the start under both names
        item["start"] = item.get("st")
        program.append(item)
    return program


async def restore_waves(
    cloud: Any, hwid: str, backup: dict[str, Any], auto: Any
) -> tuple[bool, list[str], dict[str, str]]:
    """Put the waves and the program of a pump back in the cloud, then have
    it push them (see the module docstring).

    @param backup: from backup_waves
    @param auto: the /auto of the pump before the capture
    @return whether everything was accepted, what was done, and the new uid
            of each wave created again
    """
    aquarium = str(backup.get("aquarium_uid") or "")
    notes: list[str] = []
    renamed: dict[str, str] = {}
    ok = True
    library = await read_library(cloud)
    if library is None:
        return False, ["wave library unreadable"], renamed
    current = {str(e.get("uid")): e for e in custom_waves(library, aquarium)}
    for saved in backup.get("library") or []:
        uid = str(saved.get("uid"))
        name = str(saved.get("name") or "")
        mine = pump_settings_of(saved, hwid)
        now = current.get(uid)
        if now is None:
            payload = library_payload(
                name,
                _shape(saved),
                copy.deepcopy(saved.get("pump_settings") or []),
                aquarium,
            )
            if not _ok(await cloud.http_send(WAVES_LIBRARY, payload, "post")):
                ok = False
                notes.append(f"wave {name}: not created again")
                continue
            notes.append(f"wave {name}: created again")
            renamed[uid] = ""
            continue
        if mine is None or pump_settings_of(now, hwid) == mine:
            continue
        settings = [
            dict(s)
            for s in now.get("pump_settings") or []
            if isinstance(s, dict) and s.get("hwid") != hwid
        ] + [mine]
        payload = library_payload(name, _shape(now), settings)
        if _ok(await cloud.http_send(f"{WAVES_LIBRARY}/{uid}", payload, "put")):
            notes.append(f"wave {name}: settings of the pump put back")
        else:
            ok = False
            notes.append(f"wave {name}: settings of the pump not put back")
    if renamed:
        # The uid of the waves created again: by name, among the new ones
        library = await read_library(cloud) or []
        fresh = [
            e
            for e in custom_waves(library, aquarium)
            if str(e.get("uid")) not in current
        ]
        names = {
            str(s.get("uid")): str(s.get("name") or "")
            for s in backup.get("library") or []
        }
        for old in list(renamed):
            found = next(
                (str(e["uid"]) for e in fresh if e.get("name") == names.get(old)),
                "",
            )
            if found:
                renamed[old] = found
            else:
                del renamed[old]
                ok = False
                notes.append(f"wave {names.get(old)}: new uid not found")
    intervals = auto.get("intervals") if isinstance(auto, dict) else None
    program = program_of(intervals, renamed)
    if program:
        res = await cloud.http_send(
            f"/reef-wave/schedule/{hwid}", {"intervals": program}, "post"
        )
        if _ok(res):
            notes.append(f"program: {len(program)} interval(s) posted")
        else:
            ok = False
            notes.append("program: refused by the cloud")
    if aquarium:
        if _ok(await cloud.http_send(f"/reef-wave/{aquarium}/sync", {}, "post")):
            notes.append("programs pushed to the pumps")
        else:
            ok = False
            notes.append("sync refused by the cloud")
    _LOGGER.debug("Poseidon: waves of %s put back: %s", hwid, notes)
    return ok, notes, renamed


def renamed_auto(auto: Any, renamed: dict[str, str]) -> Any:
    """/auto with the waves created again under their new uid."""
    if not isinstance(auto, dict) or not renamed:
        return auto
    result = copy.deepcopy(auto)
    for interval in result.get("intervals") or []:
        if isinstance(interval, dict):
            uid = str(interval.get("wave_uid", ""))
            interval["wave_uid"] = renamed.get(uid, uid)
    return result


def same_program(before: Any, after: Any, renamed: dict[str, str]) -> bool:
    """Whether the pump runs the program it had (waves created again under
    their new uid)."""

    def key(auto: Any) -> list[tuple[Any, ...]]:
        intervals = auto.get("intervals") if isinstance(auto, dict) else None
        return [
            tuple(i.get(k) for k in ("st", "wave_uid", "direction", "fti", "rti"))
            for i in intervals or []
            if isinstance(i, dict)
        ]

    return key(renamed_auto(before, renamed)) == key(after)

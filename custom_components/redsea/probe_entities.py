"""Pure helpers for probe-scoped entity registry maintenance.

Two operations need to reason about which registry entities belong to a probe:

- **purge** — after a probe is deleted, drop its leftover entities (the
  per-probe sensors/switches/numbers *and* the per-probe maintenance
  button/number/switch instances);
- **rename** — when a probe is *replaced*, move the old probe's entities onto
  the new probe's uid so their ``entity_id`` (hence history/statistics) carries
  over instead of starting fresh.

A probe's entities come in two unique_id shapes (all prefixed ``{serial}_``):

- direct probe entities: ``probe_{type}_{sanitised_uid}_{field}``;
- per-probe maintenance instances: ``{task_key}[_interval|_date|…]_{sub_id}``,
  where ``sub_id = int(uid, 16)`` and ``task_key`` is a probe-scoped task.

Everything here is pure (no Home Assistant imports) so it is unit-testable.
"""

from __future__ import annotations

import re
from typing import Any, cast

_TRAILING_INT = re.compile(r"_(\d+)$")


def sanitise_uid(uid: str) -> str:
    """Lower-case alphanumerics of a uid, as used in entity keys."""
    return "".join(c for c in uid.lower() if c.isalnum())


def probe_sub_id(uid: str) -> int:
    """Integer sub_id a maintenance instance uses for a probe uid."""
    return int(uid, 16)


def probe_display_name(probe: dict[str, Any], probes: list[Any]) -> str:
    """A probe's label for entity friendly names (the ``{probe}`` placeholder).

    Uses the probe's own name if set, falling back to its type. Two probes of
    the same type usually still share the same *default* name (e.g. two ATO
    probes both named "ATO" until the user renames them) — indistinguishable
    entity names otherwise — so the 2nd and later same-type probes (in the
    order the device lists them) get a " #N" suffix; the 1st stays plain.
    """
    label = str(probe.get("name") or probe.get("type") or "probe")
    ptype = probe.get("type")
    same_type = [
        p
        for p in (cast(dict[str, Any], x) for x in probes if isinstance(x, dict))
        if p.get("type") == ptype
    ]
    if len(same_type) <= 1:
        return label
    uid = probe.get("uid")
    for rank, p in enumerate(same_type, start=1):
        if p.get("uid") == uid:
            return label if rank == 1 else f"{label} #{rank}"
    return label


_DASHBOARD_PROBES = "$.sources[?(@.name=='/dashboard')].data.probes"


def probe_index(device: Any, ptype: str, uid: str) -> int | None:
    """Position of a probe in the hub's ``/dashboard.probes`` array.

    The array order is the order the hub lists its probes in, which is what a
    card needs to lay them out. It is looked up on every call rather than
    frozen at setup: probes can be plugged or unplugged, which reorders the
    array. A probe is identified by its ``(type, uid)`` pair, since uids are
    only unique within a type.
    """
    probes = device.get_data(_DASHBOARD_PROBES, is_None_possible=True)
    if not isinstance(probes, list):
        return None
    for idx, raw in enumerate(cast(list[Any], probes)):
        if not isinstance(raw, dict):
            continue
        entry = cast(dict[str, Any], raw)
        if str(entry.get("uid")) == uid and str(entry.get("type", "")).lower() == ptype:
            return idx
    return None


def probe_ranges(
    device: Any, ptype: str, uid: str, *, is_temp: bool = False
) -> list[float] | None:
    """Acceptable/desired bounds of a probe, from its ``/probe/config`` entry.

    Returns ``[acceptable_low, desired_low, desired_high, acceptable_high]``
    for the probe's primary reading, or for its embedded temperature
    (``temp.ranges``) when ``is_temp`` is set. ``None`` when the entry is not
    cached yet or does not carry four numbers.
    """
    entry = device.get_data(
        "$.sources[?(@.name=='/probe/config')]"
        f".data[?(@.type=='{ptype}' & @.uid=='{uid}')]",
        is_None_possible=True,
    )
    if not isinstance(entry, dict):
        return None
    config = cast(dict[str, Any], entry)
    if is_temp:
        temp: Any = config.get("temp")
        raw: Any = (
            cast(dict[str, Any], temp).get("ranges") if isinstance(temp, dict) else None
        )
    else:
        raw = config.get("ranges")
    if not isinstance(raw, list):
        return None
    values = cast(list[Any], raw)
    if len(values) != 4 or not all(
        isinstance(v, (int, float)) and not isinstance(v, bool) for v in values
    ):
        return None
    return [float(v) for v in values]


def probe_state_attributes(
    device: Any, ptype: str, uid: str, ranges: str | None = None
) -> dict[str, Any]:
    """State attributes tying an entity to the probe it belongs to.

    Every probe of a given type shares the same translation keys, so a card
    cannot tell two pH probes' entities apart from the registry alone. These
    attributes carry the probe's identity and position; a measurement entity
    also carries the bounds its reading is judged against.

    ``ranges`` is ``"primary"`` for the probe's own reading, ``"temp"`` for
    its embedded temperature, ``None`` for entities without a range.
    """
    attrs: dict[str, Any] = {
        "probe_uid": uid,
        "probe_type": ptype,
        "probe_index": probe_index(device, ptype, uid),
    }
    if ranges is not None:
        attrs["ranges"] = probe_ranges(device, ptype, uid, is_temp=ranges == "temp")
    return attrs


def tag_probe_entities(device: Any, entities: list[Any]) -> None:
    """Tag a hub's probe-scoped entities with the probe they belong to.

    Covers the platforms whose entities carry no computed attributes
    (number, switch, select, button): a probe's settings share their
    translation keys with every other probe of its type, so without this a
    card cannot tell whose buzzer or range bound an entity is. The probe is
    recognised from the entity's unique_id (``{serial}_probe_{type}_{uid}_…``,
    see ``probe_key_prefix``).

    Only the identity is set, not ``probe_index``: these attributes are set
    once here, and a position frozen at setup would go stale when probes are
    reordered. The measurement sensors carry the live index.
    """
    probes = device.get_data(_DASHBOARD_PROBES, is_None_possible=True)
    if not isinstance(probes, list):
        return
    scopes: list[tuple[str, str, str]] = []
    for raw in cast(list[Any], probes):
        if not isinstance(raw, dict):
            continue
        entry = cast(dict[str, Any], raw)
        uid = entry.get("uid")
        ptype = str(entry.get("type", "")).lower()
        if uid and ptype:
            prefix = f"{device.serial}_{probe_key_prefix(ptype, str(uid))}"
            scopes.append((prefix, ptype, str(uid)))

    for entity in entities:
        unique_id = getattr(entity, "_attr_unique_id", None)
        if not isinstance(unique_id, str):
            continue
        for prefix, ptype, uid in scopes:
            if unique_id.startswith(prefix):
                current = getattr(entity, "_attr_extra_state_attributes", None)
                entity._attr_extra_state_attributes = {
                    **(current or {}),
                    "probe_uid": uid,
                    "probe_type": ptype,
                }
                break


def tag_port_entities(device: Any, entities: list[Any]) -> None:
    """Tag a hub's 12V port entities with their port number (0-based).

    Both ports share their translation keys (``port_on_off``, ``port_name``…),
    so this attribute is what tells a card which port an entity drives. The
    port is read from the unique_id, ``{serial}_port_{n}_…``. Covers the
    platforms without computed attributes; the sensors set it themselves.
    """
    prefix = f"{device.serial}_port_"
    for entity in entities:
        unique_id = getattr(entity, "_attr_unique_id", None)
        if not isinstance(unique_id, str) or not unique_id.startswith(prefix):
            continue
        number, sep, _rest = unique_id[len(prefix) :].partition("_")
        if not sep or not number.isdigit():
            continue
        current = getattr(entity, "_attr_extra_state_attributes", None)
        entity._attr_extra_state_attributes = {
            **(current or {}),
            "port": int(number),
        }


def probe_key_prefix(ptype: str, uid: str) -> str:
    """Unique_id key prefix (after ``{serial}_``) of a probe's direct entities."""
    return f"probe_{ptype.lower()}_{sanitise_uid(uid)}_"


def is_orphan_probe_entity(key: str, valid_prefixes: set[str]) -> bool:
    """Whether ``key`` is a ``probe_*`` entity of a probe that no longer exists."""
    if not key.startswith("probe_"):
        return False
    return not any(key.startswith(prefix) for prefix in valid_prefixes)


def maintenance_probe_sub_id(key: str, probe_task_keys: set[str]) -> int | None:
    """Return the trailing sub_id if ``key`` is a probe-scoped maintenance
    entity, else None.

    Matches ``{task_key}`` optionally followed by ``_interval`` / ``_date`` /
    other suffixes and a trailing ``_{sub_id}``.
    """
    for task_key in probe_task_keys:
        if key == task_key or key.startswith(task_key + "_"):
            match = _TRAILING_INT.search(key)
            if match:
                return int(match.group(1))
    return None


def rename_unique_id(
    unique_id: str,
    serial: str,
    old_type: str,
    old_uid: str,
    new_uid: str,
    probe_task_keys: set[str],
) -> str | None:
    """New unique_id if this entity belongs to ``old_uid``, else None.

    Handles both direct probe entities and per-probe maintenance instances,
    swapping the old uid/sub_id for the new probe's.
    """
    prefix = f"{serial}_"
    if not unique_id.startswith(prefix):
        return None
    key = unique_id[len(prefix) :]

    old_pp = probe_key_prefix(old_type, old_uid)
    if key.startswith(old_pp):
        new_pp = probe_key_prefix(old_type, new_uid)
        return prefix + new_pp + key[len(old_pp) :]

    sub = maintenance_probe_sub_id(key, probe_task_keys)
    if sub is not None and sub == probe_sub_id(old_uid):
        suffix = f"_{sub}"
        new_key = key[: -len(suffix)] + f"_{probe_sub_id(new_uid)}"
        return prefix + new_key
    return None

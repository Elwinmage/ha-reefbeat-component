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
from typing import Any

_TRAILING_INT = re.compile(r"_(\d+)$")


def sanitise_uid(uid: str) -> str:
    """Lower-case alphanumerics of a uid, as used in entity keys."""
    return "".join(c for c in uid.lower() if c.isalnum())


def probe_sub_id(uid: str) -> int:
    """Integer sub_id a maintenance instance uses for a probe uid."""
    return int(uid, 16)


def probe_display_name(probe: dict[str, Any], probes: list[dict[str, Any]]) -> str:
    """A probe's label for entity friendly names (the ``{probe}`` placeholder).

    Uses the probe's own name if set, falling back to its type. Two probes of
    the same type usually still share the same *default* name (e.g. two ATO
    probes both named "ATO" until the user renames them) — indistinguishable
    entity names otherwise — so the 2nd and later same-type probes (in the
    order the device lists them) get a " #N" suffix; the 1st stays plain.
    """
    label = str(probe.get("name") or probe.get("type") or "probe")
    ptype = probe.get("type")
    same_type = [p for p in probes if isinstance(p, dict) and p.get("type") == ptype]
    if len(same_type) <= 1:
        return label
    uid = probe.get("uid")
    for rank, p in enumerate(same_type, start=1):
        if p.get("uid") == uid:
            return label if rank == 1 else f"{label} #{rank}"
    return label


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

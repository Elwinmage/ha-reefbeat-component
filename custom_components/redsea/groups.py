"""Device groups: the ReefBeat app's "grouped" devices, driven from Home Assistant.

Like in the ReefBeat app, grouped devices do not talk to each other: the
group writes the same shared values to every member, in turn. The only
per-member values are the ones that must differ (e.g. the staggered sunrise
offset of each lamp).

A group (the virtual LED) keeps the ordered list of the config entries of its
members. A member finds its group through `find_group`: a write made on a
member entity, when shared by the group, is routed to the group, which checks
that every member is there and applies it to all of them.

Presence: each device entry announces itself when loaded
(``SIGNAL_GROUP_MEMBER_READY``) and when unloaded (``SIGNAL_GROUP_MEMBER_GONE``);
a group re-resolves its members on these signals, so a member that is
reloaded on its own is never driven through a stale coordinator.

Loops: the group drives its members inside ``group_dispatch()``; a member
never routes a write made while the group is dispatching, so a routed write
cannot come back to the group.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN,
    GROUP_MIN_MEMBERS,
    GROUP_STORE_KEY_TPL,
    GROUP_STORE_VERSION,
    LED_BLUE_INTERNAL_NAME,
    LED_G1_KI_PATH,
    LED_G2_KI_PATH,
    LED_GROUP_LOCAL_KEYS,
    LED_GROUP_SOURCES,
    LED_KI_KEYS,
    LED_WHITE_INTERNAL_NAME,
    STAGGERED_DELAY_DEFAULT,
    STAGGERED_DELAY_MAX,
    STAGGERED_DELAY_MIN,
    VIRTUAL_LED,
)

# -----------------------------------------------------------------------------
# Dispatch guard
# -----------------------------------------------------------------------------

# True while a group is writing to its members (per asyncio task: a
# ContextVar follows the awaits of the task that set it).
_DISPATCHING: ContextVar[bool] = ContextVar("redsea_group_dispatching", default=False)


@contextmanager
def group_dispatch() -> Iterator[None]:
    """Mark the writes made inside the block as coming from a group."""
    token = _DISPATCHING.set(True)
    try:
        yield
    finally:
        _DISPATCHING.reset(token)


def in_group_dispatch() -> bool:
    """Whether the current write comes from a group (must not be routed)."""
    return _DISPATCHING.get()


# -----------------------------------------------------------------------------
# Membership
# -----------------------------------------------------------------------------


def find_group(hass: HomeAssistant, entry_id: str) -> Any | None:
    """The loaded group coordinator whose members include ``entry_id``.

    A group is any coordinator of the integration exposing ``member_ids``;
    a device belongs to one group at most (enforced by the options flow).
    """
    for coordinator in hass.data.get(DOMAIN, {}).values():
        members = getattr(coordinator, "member_ids", None)
        if isinstance(members, list) and entry_id in members:
            return coordinator
    return None


_LEGACY_ENTRY_ID_RE = re.compile(r"\((?P<entry_id>[^()]+)\)\s*$")


def members_from_legacy(linked: Iterable[Any]) -> list[str]:
    """Entry ids of the legacy ``linked`` mapping, in its order.

    The keys were built as ``"LED-<model>-: <title> (<entry_id>)"``; the
    title may hold spaces or dashes, only the trailing parenthesis is used.
    """
    res: list[str] = []
    for key in linked:
        match = _LEGACY_ENTRY_ID_RE.search(str(key))
        if match is not None and match.group("entry_id") not in res:
            res.append(match.group("entry_id"))
    return res


# -----------------------------------------------------------------------------
# Scope of a write (LED)
# -----------------------------------------------------------------------------

_SOURCE_PATH_RE = re.compile(
    r"""^\$\.sources\[\?\(@\.name==['"](?P<source>[^'"]+)['"]\)\]"""
)
_LOCAL_PREFIX = "$.local."


def led_source_is_shared(source: str) -> bool:
    """Whether a LED source (``/auto/3``, ``/manual``...) is driven by the group."""
    return any(
        source == shared or source.startswith(shared + "/")
        for shared in LED_GROUP_SOURCES
    )


def led_path_is_shared(path: str) -> bool:
    """Whether a LED data path is shared by the group.

    Covers device sources (``$.sources[?(@.name=='/manual')]...``) and the
    local values later pushed to them (``$.local.acclimation...``). Anything
    else (restored sensor values, firmware version, HA-side settings) stays
    on the member.
    """
    match = _SOURCE_PATH_RE.match(path)
    if match is not None:
        return led_source_is_shared(match.group("source"))
    if path.startswith(_LOCAL_PREFIX):
        return path[len(_LOCAL_PREFIX) :].split(".")[0] in LED_GROUP_LOCAL_KEYS
    return False


def led_group_path(path: str, only_g1: bool) -> str | None:
    """Translate a member's LED path into the group's path.

    Kelvin/intensity live in different places on G1 and G2 lamps: the group
    uses its "g1_path g2_path" form, resolved per lamp when applied. The
    white/blue channels only exist on G1 lamps: in a group holding a G2 they
    cannot be set (None).
    """
    for key in LED_KI_KEYS:
        if path in (f"{LED_G1_KI_PATH}.{key}", f"{LED_G2_KI_PATH}.{key}"):
            return f"{LED_G1_KI_PATH} {LED_G2_KI_PATH}.{key}"
    if not only_g1 and path in (LED_WHITE_INTERNAL_NAME, LED_BLUE_INTERNAL_NAME):
        return None
    return path


# -----------------------------------------------------------------------------
# Errors
# -----------------------------------------------------------------------------


def group_error(translation_key: str, **placeholders: str) -> HomeAssistantError:
    """A translated error, shown to the user when a group action is refused."""
    return HomeAssistantError(
        translation_domain=DOMAIN,
        translation_key=translation_key,
        translation_placeholders=placeholders,
    )


# -----------------------------------------------------------------------------
# Persistent state of a group
# -----------------------------------------------------------------------------


def staggered_offsets(
    member_ids: list[str], enabled: bool, delay: int
) -> dict[str, int]:
    """Offset (minutes) of each member: ``delay * position``, 0 when off.

    As the ReefBeat app (Aquarium.updateDevicesOffsets): the first lamp of
    the group keeps its program, each next one starts ``delay`` later.
    """
    return {
        entry_id: delay * position if enabled else 0
        for position, entry_id in enumerate(member_ids)
    }


class GroupStore:
    """Staggered sunrise of a group, and the offsets last written to its lamps.

    ``applied`` (entry id -> offset) tells what the lamps hold: the offsets
    are written again only when the group, its order or the settings no
    longer match it, and a lamp leaving the group gets its offset back to 0.
    """

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, GROUP_STORE_VERSION, GROUP_STORE_KEY_TPL.format(entry_id=entry_id)
        )
        self.staggered: bool = False
        self.delay: int = STAGGERED_DELAY_DEFAULT
        self.applied: dict[str, int] = {}
        # The user chose to keep the group in Home Assistant only (no cloud)
        self.local_only: bool = False
        # Group state last synchronized with the cloud (GroupState.as_dict)
        self.snapshot: dict[str, Any] | None = None
        self._listeners: list[Callable[[], None]] = []

    @staticmethod
    def _delay(value: Any) -> int:
        """A delay within the app's range (1..15 minutes)."""
        return max(STAGGERED_DELAY_MIN, min(STAGGERED_DELAY_MAX, round(float(value))))

    async def async_load(self) -> None:
        """Read the stored state (defaults for anything missing or invalid)."""
        raw = await self._store.async_load() or {}
        self.staggered = bool(raw.get("staggered", False))
        try:
            self.delay = self._delay(raw.get("delay", STAGGERED_DELAY_DEFAULT))
        except (TypeError, ValueError):
            self.delay = STAGGERED_DELAY_DEFAULT
        applied = raw.get("applied")
        self.applied = (
            {str(k): int(v) for k, v in applied.items() if isinstance(v, int)}
            if isinstance(applied, dict)
            else {}
        )
        self.local_only = bool(raw.get("local_only", False))
        snapshot = raw.get("snapshot")
        self.snapshot = snapshot if isinstance(snapshot, dict) else None

    async def async_save(self) -> None:
        """Store the state and tell the listeners (entities)."""
        await self._store.async_save(
            {
                "staggered": self.staggered,
                "delay": self.delay,
                "applied": self.applied,
                "local_only": self.local_only,
                "snapshot": self.snapshot,
            }
        )
        for listener in list(self._listeners):
            listener()

    async def async_set(
        self, staggered: bool | None = None, delay: Any | None = None
    ) -> None:
        """Change the staggered sunrise settings (saved)."""
        if staggered is not None:
            self.staggered = bool(staggered)
        if delay is not None:
            self.delay = self._delay(delay)
        await self.async_save()

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Be told of every change; returns the function removing it."""
        self._listeners.append(listener)

        def _remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _remove


# -----------------------------------------------------------------------------
# Synchronization with the ReefBeat cloud
# -----------------------------------------------------------------------------
#
# The cloud keeps, as the ReefBeat app writes them: per device ``grouped`` and
# ``group_index`` (the group of a model is its grouped lamps, in that order),
# and per model the staggered sunrise (aquarium ``properties.groups``). Home
# Assistant and the cloud are compared with the state last synchronized (the
# snapshot): the side that changed since wins, both changed is a conflict
# the user settles (Repairs).

SYNC_NONE = "none"
SYNC_PUSH = "push"
SYNC_ADOPT = "adopt"
SYNC_CONFLICT = "conflict"


@dataclass(frozen=True)
class GroupState:
    """A group as both sides can hold it: lamps (hwid, in order), staggered sunrise."""

    members: tuple[str, ...]
    staggered: bool
    delay: int

    def as_dict(self) -> dict[str, Any]:
        """Stored form (the snapshot)."""
        return {
            "members": list(self.members),
            "staggered": self.staggered,
            "delay": self.delay,
        }

    @classmethod
    def from_dict(cls, data: Any) -> GroupState | None:
        """A stored state, None when there is none (or it is unreadable)."""
        if not isinstance(data, dict):
            return None
        members = data.get("members")
        if not isinstance(members, list):
            return None
        return cls(
            tuple(str(m) for m in members),
            bool(data.get("staggered", False)),
            GroupStore._delay(data.get("delay", STAGGERED_DELAY_DEFAULT)),
        )


def sync_action(
    local: GroupState, cloud: GroupState, snapshot: GroupState | None
) -> str:
    """What to do to bring Home Assistant and the cloud together.

    First synchronization (no snapshot): a cloud without this group gets it;
    a cloud already grouping the same lamps is taken (their order and the
    staggered sunrise of the app: the group was just made in Home
    Assistant); other lamps grouped in the cloud are a conflict.
    """
    if local == cloud:
        return SYNC_NONE
    if snapshot is None:
        if not cloud.members:
            return SYNC_PUSH
        if set(cloud.members) == set(local.members):
            return SYNC_ADOPT
        return SYNC_CONFLICT
    local_changed = local != snapshot
    cloud_changed = cloud != snapshot
    if local_changed and cloud_changed:
        return SYNC_CONFLICT
    return SYNC_PUSH if local_changed else SYNC_ADOPT


def same_name(name: Any, model: str) -> bool:
    """Whether a cloud group is the one of a model (the app writes it in
    lower case: "rsled160")."""
    return isinstance(name, str) and name.lower() == model.lower()


def cloud_group_name(aquarium: Any, model: str) -> str:
    """Name of the cloud group of a model: the one the aquarium already has,
    else the model in lower case, as the ReefBeat app names it."""
    props = aquarium.get("properties") if isinstance(aquarium, dict) else None
    groups = props.get("groups") if isinstance(props, dict) else None
    for group in groups if isinstance(groups, list) else []:
        if isinstance(group, dict) and same_name(group.get("name"), model):
            return str(group["name"])
    return model.lower()


def cloud_group_state(
    devices: Any, aquarium: Any, aquarium_uid: str, model: str, known: set[str]
) -> GroupState:
    """The group of a model in an aquarium, as the cloud holds it.

    Only the lamps Home Assistant knows (``known`` hwids) are considered: it
    cannot drive the others, nor put them in a group.
    """
    grouped = [
        d
        for d in (devices if isinstance(devices, list) else [])
        if isinstance(d, dict)
        and d.get("grouped")
        and d.get("model") == model
        and d.get("aquarium_uid") == aquarium_uid
        and str(d.get("hwid")) in known
    ]
    grouped.sort(key=lambda d: int(d.get("group_index") or 0))
    staggered, delay = False, STAGGERED_DELAY_DEFAULT
    props = aquarium.get("properties") if isinstance(aquarium, dict) else None
    groups = props.get("groups") if isinstance(props, dict) else None
    for group in groups if isinstance(groups, list) else []:
        if isinstance(group, dict) and same_name(group.get("name"), model):
            gprops = group.get("properties") or {}
            staggered = bool(gprops.get("staggered", False))
            # The app stores 0 until a delay is chosen: its default is 10
            delay = GroupStore._delay(
                gprops.get("staggered_delay") or STAGGERED_DELAY_DEFAULT
            )
    return GroupState(tuple(str(d["hwid"]) for d in grouped), staggered, delay)


def cloud_groups(
    devices: Any, known: dict[str, str]
) -> dict[tuple[str, str], list[str]]:
    """The groups of lamps a cloud account holds, by (aquarium uid, model).

    Only the lamps Home Assistant knows (``known``: hwid -> entry id) are
    kept, in the group order of the app (group_index); a group needs at
    least two of them to be driven from Home Assistant.
    """
    found: dict[tuple[str, str], list[tuple[int, str]]] = {}
    for device in devices if isinstance(devices, list) else []:
        if not isinstance(device, dict) or not device.get("grouped"):
            continue
        entry_id = known.get(str(device.get("hwid")))
        if entry_id is None:
            continue
        key = (str(device.get("aquarium_uid")), str(device.get("model")))
        found.setdefault(key, []).append(
            (int(device.get("group_index") or 0), entry_id)
        )
    return {
        key: [entry_id for _, entry_id in sorted(members)]
        for key, members in found.items()
        if len(members) >= GROUP_MIN_MEMBERS
    }


def discovery_unique_id(aquarium_uid: str, model: str) -> str:
    """Unique id of a discovered group (one per model in an aquarium)."""
    return f"{VIRTUAL_LED}-{aquarium_uid}-{model}".lower()


# -----------------------------------------------------------------------------
# Repairs
# -----------------------------------------------------------------------------

# No cloud account holds the lamps of the group: it is kept in HA only
ISSUE_NO_CLOUD = "group_no_cloud"
# A group of several models, some of its lamps grouped in the ReefBeat app
ISSUE_MIXED = "group_mixed_models"
# The group changed both in Home Assistant and in the ReefBeat app
ISSUE_CONFLICT = "group_conflict"


def issue_id(kind: str, entry_id: str) -> str:
    """Repairs issue of a group."""
    return f"{kind}_{entry_id}"


@callback
def set_issue(
    hass: HomeAssistant,
    kind: str,
    entry_id: str,
    active: bool,
    placeholders: dict[str, str] | None = None,
) -> None:
    """Raise or clear a Repairs issue of a group."""
    if not active:
        ir.async_delete_issue(hass, DOMAIN, issue_id(kind, entry_id))
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id(kind, entry_id),
        is_fixable=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key=kind,
        translation_placeholders=placeholders or {},
        data={"kind": kind, "entry_id": entry_id},
    )

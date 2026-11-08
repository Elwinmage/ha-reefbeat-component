# Generated from reeftech-catalog/client/catalog_pack.py by scripts/sync_client.py: do not edit this copy.
"""ReefTech catalog client: download, check and read a section of reeftech-catalog.

Canonical copy: reeftech-catalog/client/. Integrations get a copy through
`scripts/sync_client.py`; edit it here, never in a copy.

This module has no Home Assistant dependency (catalog_runtime.py holds the
Home Assistant side). A section release holds a `manifest.json`:

    {
      "format": 1,
      "section": "equipment",
      "version": "2026.11.0",
      "min_integration": {"reef_maintenance": "0.3.0"},
      "notes": "# equipment 2026.11.0 ...",
      "entries": {
        "item.eheim-thermocontrol-200": {
          "kind": "item", "category": "heater", "scopes": ["aquarium"],
          "content_hash": "<hex>", "archive": "equipment-2026.11.0/item.eheim-thermocontrol-200.zip",
          "sha256": "<hex>", "size": 196, "since": "2026.11.0"
        }
      }
    }

Installed packs, the built-in snapshot shipped with an integration and the
user folder share the repository layout of the section:

    tasks/<task_id>.json                                 (equipment)
    categories/<id>/category.json [+ image.webp, ...]   (equipment)
    items/<id>/item.json | supplement.json [+ ...]      (both)
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import shutil
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from pathlib import Path, PurePosixPath
from typing import Any

import aiohttp
from awesomeversion import AwesomeVersion, AwesomeVersionException

_LOGGER = logging.getLogger(__name__)

MANIFEST_FILE = "manifest.json"
MANIFEST_FORMAT = 1
REPO = "Elwinmage/reeftech-catalog"

#: Folder and descriptor of each entry kind (tasks: one json per task)
KIND_LAYOUT: dict[str, tuple[str, str | None]] = {
    "tasks": ("tasks", None),
    "category": ("categories", "category.json"),
    "item": ("items", "item.json"),
    "supplement": ("items", "supplement.json"),
}
SECTION_KINDS: dict[str, frozenset[str]] = {
    "equipment": frozenset({"tasks", "category", "item"}),
    "supplements": frozenset({"supplement"}),
}
IMAGE_FILES = ("image.webp", "image.png")
THUMB_FILE = "thumb.webp"
ALLOWED_SUFFIXES = (".json", ".webp", ".png")
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_ENTRY_BYTES = 4 * 1024 * 1024
MAX_ENTRY_FILES = 256
MAX_JSON_BYTES = 256 * 1024
DOWNLOAD_TIMEOUT_S = 120

_ID_RE = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")
_FILE_RE = re.compile(r"^[A-Za-z0-9_@.-]{1,120}$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_VERSION_RE = re.compile(r"^[0-9A-Za-z._+-]{1,40}$")
_ARCHIVE_RE = re.compile(r"^[a-z]+-[0-9A-Za-z._+-]{1,40}/[A-Za-z0-9_.-]{1,120}\.zip$")


class PackError(Exception):
    """A manifest or an archive that cannot be used."""


# -- manifest -----------------------------------------------------------------


@dataclass(frozen=True)
class PackEntry:
    """One entry of a manifest."""

    name: str
    kind: str
    sha256: str
    size: int
    archive: str
    since: str
    scopes: tuple[str, ...] | None = None

    @property
    def entry_id(self) -> str:
        """Id of the entry (its folder name), `tasks` for the task library."""
        return self.name.split(".", 1)[1] if "." in self.name else self.name

    @property
    def rel_dir(self) -> PurePosixPath:
        """Folder of the entry inside a pack."""
        folder, _ = KIND_LAYOUT[self.kind]
        if self.kind == "tasks":
            return PurePosixPath(folder)
        return PurePosixPath(folder) / self.entry_id


@dataclass
class Manifest:
    """A parsed manifest."""

    section: str
    version: str
    min_integration: dict[str, str] = field(default_factory=dict)
    notes: str = ""
    entries: dict[str, PackEntry] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


def _check_version(value: Any, what: str) -> str:
    if not isinstance(value, str) or not _VERSION_RE.match(value):
        raise PackError(f"bad {what} {value!r}")
    return value


def _parse_entry(name: str, item: Any, section: str) -> PackEntry:
    if not isinstance(item, dict):
        raise PackError(f"entry {name} is not an object")
    kind = item.get("kind")
    if kind not in SECTION_KINDS[section]:
        raise PackError(f"entry {name}: kind {kind!r} not in section {section}")
    if kind == "tasks":
        if name != "tasks":
            raise PackError(f"bad entry name {name!r}")
    else:
        prefix, _, entry_id = name.partition(".")
        if prefix != kind or not _ID_RE.match(entry_id):
            raise PackError(f"bad entry name {name!r}")
    sha = item.get("sha256")
    size = item.get("size")
    archive = item.get("archive")
    if not isinstance(sha, str) or not _SHA_RE.match(sha):
        raise PackError(f"entry {name}: bad sha256")
    if (
        not isinstance(size, int)
        or isinstance(size, bool)
        or not 0 < size <= MAX_ENTRY_BYTES
    ):
        raise PackError(f"entry {name}: bad size")
    if (
        not isinstance(archive, str)
        or not _ARCHIVE_RE.match(archive)
        or not archive.startswith(f"{section}-")
    ):
        raise PackError(f"entry {name}: bad archive {archive!r}")
    since = _check_version(item.get("since"), f"entry {name} version")
    scopes = item.get("scopes")
    if scopes is not None:
        if not isinstance(scopes, list) or not all(isinstance(s, str) for s in scopes):
            raise PackError(f"entry {name}: bad scopes")
        scopes = tuple(scopes)
    return PackEntry(name, kind, sha, size, archive, since, scopes)


def parse_manifest(data: Any, section: str) -> Manifest:
    """Check and parse the manifest of a section. Raises PackError."""
    if section not in SECTION_KINDS:
        raise PackError(f"unknown section {section!r}")
    if not isinstance(data, dict):
        raise PackError("manifest is not an object")
    if data.get("format") != MANIFEST_FORMAT:
        raise PackError(f"unsupported manifest format {data.get('format')!r}")
    if data.get("section") != section:
        raise PackError(
            f"manifest of section {data.get('section')!r}, expected {section!r}"
        )
    version = _check_version(data.get("version"), "manifest version")
    minimum = data.get("min_integration", {})
    if not isinstance(minimum, dict):
        raise PackError("min_integration must be an object")
    for consumer, value in minimum.items():
        _check_version(value, f"min_integration of {consumer}")
    notes = data.get("notes", "")
    if not isinstance(notes, str):
        raise PackError("notes must be a text")
    raw_entries = data.get("entries")
    if not isinstance(raw_entries, dict):
        raise PackError("entries must be an object")
    entries = {
        name: _parse_entry(str(name), item, section)
        for name, item in raw_entries.items()
    }
    return Manifest(section, version, dict(minimum), notes, entries, data)


def select(manifest: Manifest, scopes: Iterable[str] | None) -> Manifest:
    """The manifest restricted to the entries a consumer keeps.

    Entries without scopes (task library, supplements) are always kept; the
    others when one of their scopes is wanted. `None` keeps everything.
    """
    if scopes is None:
        return manifest
    wanted = set(scopes)
    kept = {
        name: entry
        for name, entry in manifest.entries.items()
        if entry.scopes is None or wanted.intersection(entry.scopes)
    }
    raw = dict(manifest.raw)
    raw["entries"] = {name: manifest.raw["entries"][name] for name in kept}
    return replace(manifest, entries=kept, raw=raw)


def is_compatible(manifest: Manifest, consumer: str, integration_version: str) -> bool:
    """True when this integration can use the manifest's entries."""
    minimum = manifest.min_integration.get(consumer)
    if not minimum:
        return True
    try:
        return AwesomeVersion(integration_version.lstrip("v")) >= AwesomeVersion(
            minimum.lstrip("v")
        )
    except AwesomeVersionException:
        return False


# -- installed pack -----------------------------------------------------------


def _entry_present(root: Path, entry: PackEntry) -> bool:
    folder = root / entry.rel_dir
    _, descriptor = KIND_LAYOUT[entry.kind]
    if descriptor is None:
        return folder.is_dir() and any(folder.glob("*.json"))
    return (folder / descriptor).is_file()


def read_installed(root: Path, section: str) -> Manifest | None:
    """Manifest of the installed pack, or None.

    None too when an entry it lists is missing on disk (a restored backup
    without the pack, a folder deleted by hand): the pack is then installed
    again.
    """
    try:
        manifest = parse_manifest(
            json.loads((root / MANIFEST_FILE).read_text(encoding="utf-8")), section
        )
    except (OSError, ValueError, PackError):
        return None
    if not all(_entry_present(root, entry) for entry in manifest.entries.values()):
        return None
    return manifest


def plan(
    installed: Manifest | None, latest: Manifest
) -> tuple[list[PackEntry], list[PackEntry]]:
    """Entries to keep from the installed pack, and entries to download."""
    keep: list[PackEntry] = []
    fetch: list[PackEntry] = []
    current = installed.entries if installed else {}
    for name, entry in sorted(latest.entries.items()):
        old = current.get(name)
        if old is not None and old.sha256 == entry.sha256:
            keep.append(entry)
        else:
            fetch.append(entry)
    return keep, fetch


def verify(blob: bytes, entry: PackEntry) -> None:
    """Check a downloaded archive against its manifest entry."""
    if len(blob) != entry.size:
        raise PackError(f"{entry.name}: {len(blob)} bytes, expected {entry.size}")
    if hashlib.sha256(blob).hexdigest() != entry.sha256:
        raise PackError(f"{entry.name}: checksum mismatch")


def extract_entry(blob: bytes, entry: PackEntry, dest: Path) -> None:
    """Extract an entry archive into `dest` (flat), after checking it."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(blob))
    except zipfile.BadZipFile as err:
        raise PackError(f"{entry.name}: not a zip archive") from err
    with archive:
        infos = [i for i in archive.infolist() if not i.is_dir()]
        if not infos or len(infos) > MAX_ENTRY_FILES:
            raise PackError(f"{entry.name}: {len(infos)} files")
        total = 0
        for info in infos:
            name = info.filename
            if (
                PurePosixPath(name).name != name
                or not _FILE_RE.match(name)
                or not name.endswith(ALLOWED_SUFFIXES)
            ):
                raise PackError(f"{entry.name}: unexpected file {name!r}")
            total += info.file_size
        if total > 4 * MAX_ENTRY_BYTES:
            raise PackError(f"{entry.name}: too big once extracted")
        names = {i.filename for i in infos}
        _, descriptor = KIND_LAYOUT[entry.kind]
        if descriptor is not None and descriptor not in names:
            raise PackError(f"{entry.name}: no {descriptor}")
        for name in sorted(names):
            if not name.endswith(".json"):
                continue
            try:
                parsed = json.loads(archive.read(name).decode("utf-8"))
            except (UnicodeDecodeError, ValueError) as err:
                raise PackError(f"{entry.name}: unreadable {name}") from err
            if not isinstance(parsed, dict):
                raise PackError(f"{entry.name}: {name} is not an object")
        dest.mkdir(parents=True, exist_ok=True)
        for info in infos:
            (dest / info.filename).write_bytes(archive.read(info))


def staging_dir(root: Path) -> Path:
    """Folder an update is prepared in, next to the pack."""
    return root.with_name(root.name + ".new")


def prepare_staging(root: Path, keep: list[PackEntry]) -> Path:
    """A fresh staging folder holding the kept entries of the pack."""
    staging = staging_dir(root)
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    for entry in keep:
        shutil.copytree(root / entry.rel_dir, staging / entry.rel_dir)
    return staging


def commit(root: Path, staging: Path, manifest: Manifest) -> None:
    """Write the manifest, then put the staging folder in place of the pack."""
    (staging / MANIFEST_FILE).write_text(
        json.dumps(manifest.raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    old = root.with_name(root.name + ".old")
    shutil.rmtree(old, ignore_errors=True)
    if root.exists():
        root.rename(old)
    staging.rename(root)
    shutil.rmtree(old, ignore_errors=True)


# -- network ------------------------------------------------------------------


async def download(session: aiohttp.ClientSession, url: str, limit: int) -> bytes:
    """Body of a URL, refusing more than `limit` bytes. Raises PackError."""
    try:
        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT_S)
        ) as response:
            if response.status != 200:
                raise PackError(f"{url}: HTTP {response.status}")
            body = bytearray()
            async for chunk in response.content.iter_chunked(64 * 1024):
                body += chunk
                if len(body) > limit:
                    raise PackError(f"{url}: more than {limit} bytes")
            return bytes(body)
    except (aiohttp.ClientError, TimeoutError) as err:
        raise PackError(f"{url}: {err}") from err


class PackClient:
    """Reads the releases of one section of the catalog repository."""

    def __init__(
        self, session: aiohttp.ClientSession, section: str, repo: str = REPO
    ) -> None:
        """Bind to a section of a `owner/name` GitHub repository."""
        self._session = session
        self.section = section
        self.base_url = f"https://github.com/{repo}/releases"

    @property
    def manifest_url(self) -> str:
        """Fixed URL of the current manifest (rolling '<section>-latest' release)."""
        return f"{self.base_url}/download/{self.section}-latest/{MANIFEST_FILE}"

    def release_url(self, version: str) -> str:
        """Page of a release."""
        return f"{self.base_url}/tag/{self.section}-{version}"

    async def latest(self) -> Manifest:
        """Manifest of the current release."""
        blob = await download(self._session, self.manifest_url, MAX_MANIFEST_BYTES)
        try:
            return parse_manifest(json.loads(blob.decode("utf-8")), self.section)
        except (UnicodeDecodeError, ValueError) as err:
            raise PackError(f"unreadable manifest: {err}") from err

    async def entry(self, entry: PackEntry) -> bytes:
        """Checked archive of an entry."""
        blob = await download(
            self._session, f"{self.base_url}/download/{entry.archive}", entry.size
        )
        verify(blob, entry)
        return blob


# -- merged view --------------------------------------------------------------


@dataclass(frozen=True)
class Layer:
    """A folder holding catalog entries, and how its files are served."""

    name: str  # builtin | pack | user
    root: Path
    url: str  # URL the folder is served at
    stamp: str  # appended to file URLs so that browsers reload changed files


def _read_object(path: Path) -> dict[str, Any] | None:
    try:
        if path.stat().st_size > MAX_JSON_BYTES:
            raise ValueError("too big")
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        _LOGGER.warning("Catalog file %s ignored: %s", path, err)
        return None
    if not isinstance(data, dict):
        _LOGGER.warning("Catalog file %s ignored: not an object", path)
        return None
    return data


def _with_files(
    data: dict[str, Any], folder: Path, layer: Layer, rel: str
) -> dict[str, Any]:
    result = dict(data)
    image = next((name for name in IMAGE_FILES if (folder / name).is_file()), None)
    result["image"] = f"{layer.url}/{rel}/{image}?v={layer.stamp}" if image else None
    thumb = (folder / THUMB_FILE).is_file()
    result["thumb"] = (
        f"{layer.url}/{rel}/{THUMB_FILE}?v={layer.stamp}" if thumb else result["image"]
    )
    result["source"] = layer.name
    return result


def read_layer(layer: Layer, section: str) -> dict[str, dict[str, dict[str, Any]]]:
    """Entries of one layer, by group (tasks, categories, items)."""
    groups: dict[str, dict[str, dict[str, Any]]] = {}
    kinds = SECTION_KINDS[section]
    if "tasks" in kinds:
        tasks = groups.setdefault("tasks", {})
        folder = layer.root / "tasks"
        if folder.is_dir():
            for path in sorted(folder.glob("*.json")):
                data = _read_object(path)
                if data is not None and _ID_RE.match(path.stem):
                    tasks[path.stem] = data
    for kind in sorted(kinds - {"tasks"}):
        folder_name, descriptor = KIND_LAYOUT[kind]
        group = groups.setdefault(folder_name, {})
        base = layer.root / folder_name
        if not base.is_dir():
            continue
        for folder in sorted(base.iterdir()):
            if not folder.is_dir() or not _ID_RE.match(folder.name):
                continue
            data = (
                _read_object(folder / str(descriptor))
                if (folder / str(descriptor)).is_file()
                else None
            )
            if data is not None:
                group[folder.name] = _with_files(
                    data, folder, layer, f"{folder_name}/{folder.name}"
                )
    return groups


def _in_scopes(data: dict[str, Any], scopes: set[str] | None) -> bool:
    entry_scopes = data.get("scopes")
    return (
        scopes is None
        or not isinstance(entry_scopes, list)
        or bool(scopes.intersection(entry_scopes))
    )


def build_view(
    layers: list[Layer], section: str, scopes: Iterable[str] | None = None
) -> dict[str, Any]:
    """Merged catalog: later layers override earlier ones on identical ids.

    Entries outside `scopes` are dropped; an item takes the scopes of its
    category when it has none, and is dropped when its category is unknown.
    """
    wanted = set(scopes) if scopes is not None else None
    view: dict[str, dict[str, dict[str, Any]]] = {}
    for layer in layers:
        for group, entries in read_layer(layer, section).items():
            view.setdefault(group, {}).update(entries)
    if section == "equipment":
        categories = {
            cid: c
            for cid, c in view.get("categories", {}).items()
            if _in_scopes(c, wanted)
        }
        items = {}
        for iid, item in view.get("items", {}).items():
            category = categories.get(item.get("category"))  # type: ignore[arg-type]
            if category is None:
                continue
            resolved = dict(item)
            resolved.setdefault("scopes", category.get("scopes"))
            if _in_scopes(resolved, wanted):
                items[iid] = resolved
        view["categories"] = categories
        view["items"] = items
    return view


def resolve_maintenance(
    view: dict[str, Any], item_id: str | None = None, category_id: str | None = None
) -> list[dict]:
    """Tasks to create for an equipment: category tasks overridden by the item ones.

    Each task: `task` (id), `name`, `description`, `icon`, `schedule`,
    `regulatory`. Unknown tasks are skipped.
    """
    tasks: dict[str, dict[str, Any]] = view.get("tasks", {})
    item = view.get("items", {}).get(item_id) if item_id else None
    if item is not None:
        category_id = item.get("category")
    category = view.get("categories", {}).get(category_id) if category_id else None

    refs: dict[str, dict[str, Any]] = {}
    if category is not None and (item is None or item.get("inherit_maintenance", True)):
        refs.update(
            {
                ref["task"]: ref
                for ref in category.get("maintenance", [])
                if isinstance(ref, dict)
            }
        )
    if item is not None:
        refs.update(
            {
                ref["task"]: ref
                for ref in item.get("maintenance", [])
                if isinstance(ref, dict)
            }
        )

    result = []
    for task_id, ref in refs.items():
        template = tasks.get(task_id)
        if template is None:
            continue
        result.append(
            {
                "task": task_id,
                "name": template.get("name", {}),
                "description": template.get("description", {}),
                "icon": template.get("icon"),
                "schedule": ref.get("schedule", template.get("schedule")),
                "regulatory": ref.get("regulatory", template.get("regulatory", False)),
            }
        )
    return result

# Generated from reeftech-catalog/client/catalog_runtime.py by scripts/sync_client.py: do not edit this copy.
"""ReefTech catalog client: Home Assistant side.

Canonical copy: reeftech-catalog/client/. Integrations get a copy through
`scripts/sync_client.py`; edit it here, never in a copy.

One updater per integration domain, shared by all its config entries:

    # __init__.py
    SPEC = CatalogSpec(DOMAIN, "supplements", "ReefBeat supplements catalog")
    async def async_setup_entry(hass, entry):
        await async_setup_catalog(hass, entry, SPEC)
    async def async_unload_entry(hass, entry):
        ...
        await async_unload_catalog(hass, entry, SPEC)

    # update.py / switch.py
    async_add_entities([*catalog_entities(hass, entry, DOMAIN, "update"), ...])

The downloaded pack of a section is common to every reader of that section: a
`SharedPack` keeps `<config>/reeftech_catalog/pack/<section>/` up to date (check
at start-up then every 12 hours, automatic install unless every reader switched
it off) and tells the updaters when it changes. Each updater merges it with the
built-in snapshot (`catalog_builtin/` next to this file) and the user folders,
serves the visuals at `/<domain>_catalog/{builtin,shared,user}/...` (the pack at
`/reeftech_catalog_pack/<section>/...`) and answers the cards on the websocket
(`<domain>/catalog`, `<domain>/catalog/subscribe`, and for the equipment section
`<domain>/catalog/maintenance`).

An integration too old for the current release (`min_integration`) does not use
the shared pack: it keeps the pack of its own folder `<config>/<domain>/catalog/`,
a copy of the previous shared pack made when the incompatible release was
installed. Once the integration is compatible again it switches to the shared
pack and its own folder is removed.

It also reads the user layer shared by every integration,
`<config>/reeftech_catalog/user/<section>/` (written by catalog editors), between
the pack and the user folder of the domain. A writer tells the integrations to
reload it by sending the dispatcher signal `SIGNAL_USER_CATALOG_CHANGED`
(argument: the section changed, or None).

A tool that is not a reader of the catalog (an editor) takes the shared pack with
`async_acquire_pack` and gives it back with `async_release_pack`.

Translation keys expected in the integration: the exceptions
`catalog_unknown`, `catalog_incompatible` (placeholders `version`, `minimum`)
and `catalog_install_failed` (placeholder `error`), and the entity name
`entity.switch.catalog_auto_update`.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.components.websocket_api import async_register_command
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.decorators import (
    async_response,
    websocket_command,
)
from homeassistant.components.websocket_api.messages import event_message
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.loader import async_get_integration

# Home Assistant validates with probatio since 2026.9: schemas must come from it
if TYPE_CHECKING:
    import probatio as vol  # pyright: ignore[reportMissingImports]
else:
    try:
        import probatio as vol
    except ImportError:  # pragma: no cover - depends on the installed HA version
        import voluptuous as vol

try:
    # Home Assistant 2025.2+ exposes it from the http.server submodule
    from homeassistant.components.http.server import (  # pyright: ignore[reportMissingImports]
        StaticPathConfig,
    )
except ImportError:  # pragma: no cover - depends on the installed HA version
    from homeassistant.components.http import (
        StaticPathConfig,  # pyright: ignore[reportPrivateImportUsage]
    )

from .catalog_pack import (
    MANIFEST_FORMAT,
    REPO,
    Layer,
    Manifest,
    PackClient,
    PackError,
    build_view,
    commit,
    copy_pack,
    extract_entry,
    is_compatible,
    plan,
    prepare_staging,
    read_installed,
    resolve_maintenance,
    shared_pack_parts,
    shared_user_parts,
)

_LOGGER = logging.getLogger(__name__)

DATA_KEY = "reeftech_catalog"
BUILTIN_DIR = Path(__file__).parent / "catalog_builtin"
#: Version shown while no pack is installed
NOT_INSTALLED = "0"
MANUFACTURER = "ReefTech"
#: Where the visuals of the shared packs are served: <url>/<section>/...
SHARED_PACK_URL = "/reeftech_catalog_pack"
#: Hours between two checks of the releases (the shortest asked by a holder wins)
CHECK_HOURS = 12
#: Sent by whoever writes in the shared user layer, with the section changed
#: (or None for all of them): every updater of that section reloads its view.
SIGNAL_USER_CATALOG_CHANGED = "reeftech_catalog_user_changed"


@dataclass(frozen=True)
class CatalogSpec:
    """What an integration reads from the catalog."""

    domain: str
    section: str  # equipment | supplements | parameters | water_tests
    title: str  # name of the catalog device
    scopes: tuple[str, ...] | None = None  # None keeps every scope
    repo: str = REPO
    check_hours: int = CHECK_HOURS
    #: Folders and URLs of the domain carry the section (`catalog_user_<section>`,
    #: `/<domain>_catalog_<section>/...`): needed from the second section of a
    #: domain on. The first one keeps the plain names, so that nothing moves for
    #: an integration that already reads a section.
    by_section: bool = False
    #: Name of the catalog device when the first section of the domain gives it
    #: a name that fits all of them (default: its own title)
    device_title: str | None = None

    @property
    def suffix(self) -> str:
        """What the folders and URLs of this section add to the plain names."""
        return f"_{self.section}" if self.by_section else ""


def signal_catalog_changed(domain: str, section: str | None = None) -> str:
    """Dispatcher signal sent each time the catalog of a domain changes.

    For entities of other config entries (they may be set up before the
    entry hosting the catalog): connect with async_dispatcher_connect. Without
    a section, the signal comes for a change of any section of the domain.
    """
    if section is None:
        return f"{domain}_catalog_changed"
    return f"{domain}_catalog_changed_{section}"


def builtin_dir(spec: CatalogSpec) -> Path:
    """Folder of the built-in snapshot of a section."""
    return BUILTIN_DIR.with_name(f"{BUILTIN_DIR.name}{spec.suffix}")


def _registry(hass: HomeAssistant) -> dict[str, Any]:
    return hass.data.setdefault(DATA_KEY, {})


def _updater_key(domain: str, section: str) -> str:
    return f"{domain}/{section}"


def get_updaters(hass: HomeAssistant, domain: str) -> list[CatalogUpdater]:
    """The running updaters of a domain, the first one set up first."""
    return [
        value
        for value in _registry(hass).values()
        if isinstance(value, CatalogUpdater) and value.spec.domain == domain
    ]


def get_updater(
    hass: HomeAssistant, domain: str, section: str | None = None
) -> CatalogUpdater | None:
    """The running updater of a section of a domain, if any.

    Without a section: the first one set up (the only one for a domain that
    reads a single section).
    """
    if section is not None:
        return _registry(hass).get(_updater_key(domain, section))
    updaters = get_updaters(hass, domain)
    return updaters[0] if updaters else None


def get_shared_pack(hass: HomeAssistant, section: str) -> SharedPack | None:
    """The shared pack of a section, if some holder has taken it."""
    return _registry(hass).get(f"pack_{section}")


# -- shared pack ----------------------------------------------------------------


class SharedPack:
    """The downloaded pack of a section: checks, installs, shared by its holders.

    Holders (an integration reading the section, an editor) keep it alive; the
    updaters among them are told to reload their view when a release is
    installed. It installs a release even when some holder is too old for it:
    such an updater keeps the previous pack as its own (see `_preserve`).
    """

    def __init__(self, hass: HomeAssistant, section: str, repo: str = REPO) -> None:
        """Bind to the shared folder of the section."""
        self.hass = hass
        self.section = section
        self.root = Path(hass.config.path(*shared_pack_parts(section)))
        self.url = f"{SHARED_PACK_URL}/{section}"
        self.client = PackClient(async_get_clientsession(hass), section, repo)
        self.installed: Manifest | None = None
        self.latest: Manifest | None = None
        self.last_error: str | None = None
        self.in_progress = False
        self.progress: int | None = None
        #: holder -> (installs new releases by itself, hours between two checks)
        self.holders: dict[str, tuple[bool, int]] = {}
        #: Updaters reading the pack, by domain
        self.updaters: dict[str, CatalogUpdater] = {}
        self._listeners: list[Callable[[], None]] = []
        self._unsub_timer: CALLBACK_TYPE | None = None

    # -- state ----------------------------------------------------------------

    @property
    def update_available(self) -> bool:
        """A release different from the installed pack (or no pack at all)."""
        if self.latest is None:
            return False
        if self.installed is None:
            return True
        return self.latest.raw != self.installed.raw

    @property
    def wants_auto(self) -> bool:
        """At least one holder wants new releases installed as they come."""
        return any(auto for auto, _ in self.holders.values())

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> CALLBACK_TYPE:
        """Be told when the state changes (check, progress, install done)."""
        self._listeners.append(listener)

        @callback
        def _remove() -> None:
            self._listeners.remove(listener)

        return _remove

    @callback
    def _notify(self) -> None:
        for updater in list(self.updaters.values()):
            updater.notify()
        for listener in list(self._listeners):
            listener()

    @callback
    def set_auto(self, holder: str, auto: bool) -> None:
        """A holder turned automatic installs on or off."""
        _, hours = self.holders[holder]
        self.holders[holder] = (auto, hours)

    # -- life cycle -----------------------------------------------------------

    async def async_prepare(self) -> None:
        """Create the folder and read the installed pack."""
        self.installed = await self.hass.async_add_executor_job(self._prepare_folder)

    @callback
    def async_begin(self) -> None:
        """Start the periodic checks, with a first one in the background.

        A first check that fails (offline) must not delay nor fail the set-up.
        """
        self._schedule()
        # Not started eagerly: the caller still has to register its updater
        self.hass.async_create_background_task(
            self.async_check(), f"{self.section} catalog check", eager_start=False
        )

    def _prepare_folder(self) -> Manifest | None:
        self.root.mkdir(parents=True, exist_ok=True)
        return read_installed(self.root, self.section)

    @callback
    def _schedule(self) -> None:
        """(Re)start the periodic check, at the pace of the most demanding holder."""
        self.async_stop()
        if self.holders:
            hours = min(hours for _, hours in self.holders.values())
            self._unsub_timer = async_track_time_interval(
                self.hass, self._async_timer, timedelta(hours=hours)
            )

    @callback
    def async_stop(self) -> None:
        """Stop the periodic checks."""
        if self._unsub_timer is not None:
            self._unsub_timer()
            self._unsub_timer = None

    async def _async_timer(self, _now: Any) -> None:
        await self.async_check()

    # -- checks ---------------------------------------------------------------

    async def async_check(self, force: bool = False) -> None:
        """Read the current manifest; install it when asked or when a holder wants it.

        Errors are kept in `last_error`, never raised: offline or GitHub down
        keeps the installed pack, quietly.
        """
        try:
            latest = await self.client.latest()
        except PackError as err:
            self.last_error = str(err)
            _LOGGER.debug("%s catalog check failed: %s", self.section, err)
            self._notify()
            return
        self.last_error = None
        self.latest = latest
        for updater in self.updaters.values():
            if not is_compatible(
                latest, updater.spec.domain, updater.integration_version
            ):
                _LOGGER.warning(
                    "%s catalog %s needs %s %s or newer: it keeps its previous catalog",
                    self.section,
                    latest.version,
                    updater.spec.domain,
                    latest.min_integration.get(updater.spec.domain),
                )
        self._notify()
        if not (force or self.wants_auto) or not self.update_available:
            return
        try:
            await self.async_install()
        except (PackError, OSError) as err:
            self.last_error = str(err)
            _LOGGER.warning("%s catalog update failed: %s", self.section, err)
            self._notify()

    # -- install --------------------------------------------------------------

    async def async_install(self) -> None:
        """Install the latest release. Raises PackError or OSError."""
        latest = self.latest
        if latest is None:
            raise PackError("the catalog has not been checked yet")
        if self.in_progress:
            return
        self.in_progress = True
        self.progress = 0
        self._notify()
        try:
            installed = await self.hass.async_add_executor_job(
                read_installed, self.root, self.section
            )
            keep, fetch = plan(installed, latest)
            staging = await self.hass.async_add_executor_job(
                prepare_staging, self.root, keep
            )
            for done, item in enumerate(fetch, start=1):
                blob = await self.client.entry(item)
                await self.hass.async_add_executor_job(
                    extract_entry, blob, item, staging / item.rel_dir
                )
                self.progress = round(100 * done / len(fetch))
                self._notify()
            await self.hass.async_add_executor_job(self._preserve, installed, latest)
            await self.hass.async_add_executor_job(commit, self.root, staging, latest)
            # Set before the final notification, so listeners see the new version
            self.installed = latest
            for updater in list(self.updaters.values()):
                await updater.async_reload()
        finally:
            self.in_progress = False
            self.progress = None
            self._notify()
        _LOGGER.info(
            "%s catalog %s installed (%d entries downloaded, %d kept)",
            self.section,
            latest.version,
            len(fetch),
            len(keep),
        )

    def _preserve(self, previous: Manifest | None, latest: Manifest) -> None:
        """Give the previous pack to the updaters too old for the new release.

        They would otherwise be left with nothing but their built-in snapshot.
        Runs before the new pack replaces the previous one.
        """
        if previous is None:
            return
        for updater in self.updaters.values():
            domain, version = updater.spec.domain, updater.integration_version
            if is_compatible(previous, domain, version) and not is_compatible(
                latest, domain, version
            ):
                copy_pack(self.root, updater.root)


async def async_acquire_pack(
    hass: HomeAssistant,
    section: str,
    holder: str,
    *,
    auto: bool = False,
    check_hours: int = CHECK_HOURS,
    repo: str = REPO,
) -> SharedPack:
    """Take the shared pack of a section for a holder, starting it with the first one.

    `auto`: the holder wants new releases installed as they are published.
    """
    registry = _registry(hass)
    # One holder at a time: the others find the pack read and checking
    async with registry.setdefault("pack_lock", asyncio.Lock()):
        pack: SharedPack | None = registry.get(f"pack_{section}")
        if pack is not None:
            pack.holders[holder] = (auto, check_hours)
            pack._schedule()
            return pack
        pack = SharedPack(hass, section, repo)
        pack.holders[holder] = (auto, check_hours)
        await pack.async_prepare()
        await _async_register_pack_path(hass, pack)
        registry[f"pack_{section}"] = pack
        # No `await` between here and the registration of the caller's updater
        # (the first check must find it)
        pack.async_begin()
        return pack


@callback
def async_release_pack(hass: HomeAssistant, section: str, holder: str) -> None:
    """Give the shared pack back; the last holder stops its checks."""
    registry = _registry(hass)
    pack: SharedPack | None = registry.get(f"pack_{section}")
    if pack is None or holder not in pack.holders:
        return
    del pack.holders[holder]
    pack.updaters.pop(holder, None)
    if pack.holders:
        pack._schedule()
    else:
        pack.async_stop()
        del registry[f"pack_{section}"]


async def _async_register_pack_path(hass: HomeAssistant, pack: SharedPack) -> None:
    """Serve the visuals of a shared pack (public catalog data), once per run."""
    key = f"pack_paths_{pack.section}"
    registry = _registry(hass)
    if registry.get(key) or getattr(hass, "http", None) is None:
        return
    registry[key] = True
    await hass.http.async_register_static_paths(
        [StaticPathConfig(pack.url, str(pack.root), cache_headers=False)]
    )


# -- updater --------------------------------------------------------------------


class CatalogUpdater:
    """State of a domain's catalog: its source pack and the merged view."""

    def __init__(
        self,
        hass: HomeAssistant,
        spec: CatalogSpec,
        integration_version: str,
        shared: SharedPack,
        auto_update: bool = True,
    ) -> None:
        """Bind to the shared pack and the folders of the domain."""
        self.hass = hass
        self.spec = spec
        self.integration_version = integration_version
        self.shared = shared
        #: Pack of the domain's own folder: the previous shared pack, for an
        #: integration too old for the current release
        self.root = Path(hass.config.path(spec.domain, f"catalog{spec.suffix}"))
        self.user_root = Path(
            hass.config.path(spec.domain, f"catalog_user{spec.suffix}")
        )
        self.shared_root = Path(hass.config.path(*shared_user_parts(spec.section)))
        #: Counts the reloads asked by writers; stamps the visuals of the shared layer
        self.user_revision = 0
        self.legacy_installed: Manifest | None = None
        self.auto_update = auto_update
        self.entry_ids: list[str] = []
        self._store: Store[dict[str, Any]] = Store(hass, 1, f"{spec.domain}.catalog")
        self._view: dict[str, Any] | None = None
        self._listeners: list[Callable[[], None]] = []
        self._unsub_user: CALLBACK_TYPE | None = None
        # Registered at once, so that an install cannot miss this updater
        shared.updaters[spec.domain] = self

    # -- state ----------------------------------------------------------------

    @property
    def owner_entry_id(self) -> str | None:
        """Config entry hosting the catalog entities."""
        return self.entry_ids[0] if self.entry_ids else None

    @property
    def client(self) -> PackClient:
        """Client reading the releases of the section."""
        return self.shared.client

    @property
    def latest(self) -> Manifest | None:
        """Current release, once a check succeeded."""
        return self.shared.latest

    @property
    def last_error(self) -> str | None:
        """Why the last check or install failed, if it did."""
        return self.shared.last_error

    @property
    def in_progress(self) -> bool:
        """The pack is being installed."""
        return self.shared.in_progress

    @property
    def progress(self) -> int | None:
        """Percentage of the install in progress."""
        return self.shared.progress

    def _shared_manifest(self) -> Manifest | None:
        """The shared pack when this integration can use it, else None."""
        pack = self.shared.installed
        if pack is not None and is_compatible(
            pack, self.spec.domain, self.integration_version
        ):
            return pack
        return None

    @property
    def uses_shared(self) -> bool:
        """The view is built on the shared pack (not on the folder of the domain)."""
        return self._shared_manifest() is not None

    @property
    def installed(self) -> Manifest | None:
        """Manifest of the pack the view is built on."""
        return self._shared_manifest() or self.legacy_installed

    @property
    def compatible(self) -> bool:
        """The latest release can be used by this integration."""
        return self.latest is None or is_compatible(
            self.latest, self.spec.domain, self.integration_version
        )

    @property
    def update_available(self) -> bool:
        """A release different from the pack in use (or no pack at all)."""
        if self.latest is None:
            return False
        installed = self.installed
        if installed is None:
            return True
        return self.latest.raw != installed.raw

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> CALLBACK_TYPE:
        """Be told when the state changes (check, progress, install done)."""
        self._listeners.append(listener)

        @callback
        def _remove() -> None:
            self._listeners.remove(listener)

        return _remove

    @callback
    def notify(self) -> None:
        """Tell the listeners and the dispatcher that the state changed."""
        for listener in list(self._listeners):
            listener()
        domain, section = self.spec.domain, self.spec.section
        async_dispatcher_send(self.hass, signal_catalog_changed(domain))
        async_dispatcher_send(self.hass, signal_catalog_changed(domain, section))

    # -- life cycle -----------------------------------------------------------

    async def async_start(self) -> None:
        """Read the packs and the folders, then listen to the shared user layer."""
        await self.async_reload()
        self.notify()
        self._unsub_user = async_dispatcher_connect(
            self.hass, SIGNAL_USER_CATALOG_CHANGED, self._on_user_changed
        )

    def _prepare_folders(self) -> Manifest | None:
        """Create the folders; read the own pack, or drop it once the shared one serves."""
        self.user_root.mkdir(parents=True, exist_ok=True)
        self.shared_root.mkdir(parents=True, exist_ok=True)
        if self.uses_shared:
            shutil.rmtree(self.root, ignore_errors=True)
        self.root.mkdir(parents=True, exist_ok=True)
        return read_installed(self.root, self.spec.section)

    async def async_reload(self) -> None:
        """The packs changed (start-up, install): read them and rebuild the view."""
        self.legacy_installed = await self.hass.async_add_executor_job(
            self._prepare_folders
        )
        await self.async_view(refresh=True)

    @callback
    def async_stop(self) -> None:
        """Stop listening and give the shared pack back."""
        if self._unsub_user is not None:
            self._unsub_user()
            self._unsub_user = None
        async_release_pack(self.hass, self.spec.section, self.spec.domain)

    @callback
    def _on_user_changed(self, section: str | None = None) -> None:
        """A writer changed the shared user layer: reload it in the background."""
        if section is not None and section != self.spec.section:
            return
        self.hass.async_create_background_task(
            self._async_reload_user(), f"{self.spec.domain} user catalog reload"
        )

    async def _async_reload_user(self) -> None:
        self.user_revision += 1
        await self.async_view(refresh=True)
        self.notify()

    async def async_set_auto_update(self, value: bool) -> None:
        """Turn automatic installs on or off (kept across restarts).

        One switch for the domain: it applies to every section it reads.
        """
        updaters = get_updaters(self.hass, self.spec.domain)
        for updater in updaters:
            updater.auto_update = value
            updater.shared.set_auto(updater.spec.domain, value)
        await self._store.async_save({"auto_update": value})
        for updater in updaters:
            updater.notify()
        if value:
            for updater in updaters:
                await updater.async_check()

    # -- checks and installs --------------------------------------------------

    async def async_check(self) -> None:
        """Read the current manifest; it is installed when a holder wants it."""
        await self.shared.async_check()

    async def async_install(self) -> None:
        """Install the latest release. Raises HomeAssistantError."""
        domain = self.spec.domain
        latest = self.latest
        if latest is None:
            raise HomeAssistantError(
                translation_domain=domain, translation_key="catalog_unknown"
            )
        if not self.compatible:
            raise HomeAssistantError(
                translation_domain=domain,
                translation_key="catalog_incompatible",
                translation_placeholders={
                    "version": latest.version,
                    "minimum": str(latest.min_integration.get(domain)),
                },
            )
        try:
            await self.shared.async_install()
        except (PackError, OSError) as err:
            raise HomeAssistantError(
                translation_domain=domain,
                translation_key="catalog_install_failed",
                translation_placeholders={"error": str(err)},
            ) from err

    # -- merged view ----------------------------------------------------------

    def _pack_layer(self) -> Layer:
        shared = self._shared_manifest()
        if shared is not None:
            return Layer("pack", self.shared.root, self.shared.url, shared.version)
        own = self.legacy_installed.version if self.legacy_installed else NOT_INSTALLED
        base = f"/{self.spec.domain}_catalog{self.spec.suffix}"
        return Layer("pack", self.root, f"{base}/pack", own)

    def layers(self) -> list[Layer]:
        """The folders the view is read from, least specific first."""
        base = f"/{self.spec.domain}_catalog{self.spec.suffix}"
        layers = []
        builtin = builtin_dir(self.spec)
        if builtin.is_dir():
            layers.append(
                Layer("builtin", builtin, f"{base}/builtin", self.integration_version)
            )
        layers.append(self._pack_layer())
        layers.append(
            Layer("user", self.shared_root, f"{base}/shared", f"u{self.user_revision}")
        )
        layers.append(Layer("user", self.user_root, f"{base}/user", "user"))
        return layers

    @property
    def view(self) -> dict[str, Any]:
        """Merged catalog as last loaded (loaded at start, reloaded on install)."""
        return self._view or {}

    async def async_view(self, refresh: bool = False) -> dict[str, Any]:
        """Merged catalog (built-in < pack < shared user < user), re-read on demand."""
        view = self._view
        if view is None or refresh:
            view = await self.hass.async_add_executor_job(
                build_view, self.layers(), self.spec.section, self.spec.scopes
            )
            self._view = view
        return view


# -- set-up -------------------------------------------------------------------


async def async_setup_catalog(
    hass: HomeAssistant, entry: ConfigEntry, spec: CatalogSpec
) -> CatalogUpdater:
    """Start the updater of a section on its first config entry, register the others.

    A domain reading several sections calls this once per section.
    """
    registry = _registry(hass)
    key = _updater_key(spec.domain, spec.section)
    updater: CatalogUpdater | None = registry.get(key)
    if updater is None:
        stored = await Store(hass, 1, f"{spec.domain}.catalog").async_load() or {}
        auto = bool(stored.get("auto_update", True))
        integration = await async_get_integration(hass, spec.domain)
        shared = await async_acquire_pack(
            hass,
            spec.section,
            spec.domain,
            auto=auto,
            check_hours=spec.check_hours,
            repo=spec.repo,
        )
        updater = CatalogUpdater(
            hass, spec, str(integration.version or "0"), shared, auto
        )
        registry[key] = updater
        await updater.async_start()
        await _async_register_paths(hass, updater)
        _register_websocket(hass, spec.domain)
        if spec.section == "equipment":
            _register_maintenance_command(hass, spec.domain)
    if entry.entry_id not in updater.entry_ids:
        updater.entry_ids.append(entry.entry_id)
    return updater


async def async_unload_catalog(
    hass: HomeAssistant, entry: ConfigEntry, spec: CatalogSpec
) -> None:
    """Forget a config entry; stop the updater with the last one.

    When the entry hosting the catalog entities goes while others stay, the
    next one is reloaded so that it adds them.
    """
    updater = get_updater(hass, spec.domain, spec.section)
    if updater is None or entry.entry_id not in updater.entry_ids:
        return
    was_owner = updater.owner_entry_id == entry.entry_id
    updater.entry_ids.remove(entry.entry_id)
    if not updater.entry_ids:
        updater.async_stop()
        del _registry(hass)[_updater_key(spec.domain, spec.section)]
        # Readers fall back to what they had before the catalog was loaded
        async_dispatcher_send(hass, signal_catalog_changed(spec.domain))
        async_dispatcher_send(hass, signal_catalog_changed(spec.domain, spec.section))
    elif was_owner:
        hass.config_entries.async_schedule_reload(str(updater.owner_entry_id))


async def _async_register_paths(hass: HomeAssistant, updater: CatalogUpdater) -> None:
    """Serve the visuals of the domain's layers (public catalog data).

    The shared pack has its own path (`_async_register_pack_path`).
    """
    key = f"paths_{updater.spec.domain}{updater.spec.suffix}"
    registry = _registry(hass)
    if registry.get(key) or getattr(hass, "http", None) is None:
        return
    registry[key] = True
    base = f"/{updater.spec.domain}_catalog{updater.spec.suffix}"
    paths = [
        (f"{base}/builtin", builtin_dir(updater.spec)),
        (f"{base}/pack", updater.root),
        (f"{base}/shared", updater.shared_root),
        (f"{base}/user", updater.user_root),
    ]
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(url, str(root), cache_headers=False)
            for url, root in paths
            if root.is_dir()
        ]
    )


def _command_updater(
    hass: HomeAssistant, domain: str, connection: ActiveConnection, msg: dict[str, Any]
) -> CatalogUpdater | None:
    """The updater a command asks for (`section`, the first one by default)."""
    updater = get_updater(hass, domain, msg.get("section"))
    if updater is None:
        what = msg.get("section") or "catalog"
        connection.send_error(msg["id"], "not_loaded", f"{domain} {what} is not loaded")
    return updater


def _register_websocket(hass: HomeAssistant, domain: str) -> None:
    """Register the websocket commands of a domain (once per run).

    Every command takes an optional `section`; the first section of the domain
    is the default, so that a card asking for a single section need not name it.
    """
    key = f"websocket_{domain}"
    registry = _registry(hass)
    if registry.get(key):
        return
    registry[key] = True

    def _updater(
        connection: ActiveConnection, msg: dict[str, Any]
    ) -> CatalogUpdater | None:
        return _command_updater(hass, domain, connection, msg)

    @websocket_command(
        {
            vol.Required("type"): f"{domain}/catalog",
            vol.Optional("refresh"): bool,
            vol.Optional("section"): str,
        }
    )
    @async_response
    async def ws_catalog(
        hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
    ) -> None:
        """Merged catalog, with visual URLs."""
        updater = _updater(connection, msg)
        if updater is None:
            return
        connection.send_result(
            msg["id"],
            {
                "section": updater.spec.section,
                "format": MANIFEST_FORMAT,
                "version": updater.installed.version if updater.installed else None,
                "updating": updater.in_progress,
                "data": await updater.async_view(msg.get("refresh", False)),
            },
        )

    @websocket_command(
        {
            vol.Required("type"): f"{domain}/catalog/subscribe",
            vol.Optional("section"): str,
        }
    )
    @callback
    def ws_subscribe(
        hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
    ) -> None:
        """An event `{version, updating}` each time the catalog state changes."""
        updater = _updater(connection, msg)
        if updater is None:
            return
        last: list[Any] = [None]

        @callback
        def _changed() -> None:
            state = {
                "version": updater.installed.version if updater.installed else None,
                "updating": updater.in_progress,
            }
            if state != last[0]:
                last[0] = state
                connection.send_message(event_message(msg["id"], state))

        connection.subscriptions[msg["id"]] = updater.async_add_listener(_changed)
        connection.send_result(msg["id"])
        _changed()

    async_register_command(hass, ws_catalog)
    async_register_command(hass, ws_subscribe)


def _register_maintenance_command(hass: HomeAssistant, domain: str) -> None:
    """Register `<domain>/catalog/maintenance`, for a domain reading equipment."""
    key = f"websocket_maintenance_{domain}"
    registry = _registry(hass)
    if registry.get(key):
        return
    registry[key] = True

    @websocket_command(
        {
            vol.Required("type"): f"{domain}/catalog/maintenance",
            vol.Exclusive("item_id", "ref"): str,
            vol.Exclusive("category_id", "ref"): str,
        }
    )
    @async_response
    async def ws_maintenance(
        hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
    ) -> None:
        """Tasks an equipment would get (category tasks overridden by the item)."""
        updater = _command_updater(
            hass, domain, connection, {"id": msg["id"], "section": "equipment"}
        )
        if updater is None:
            return
        view = await updater.async_view()
        connection.send_result(
            msg["id"],
            {
                "tasks": resolve_maintenance(
                    view, msg.get("item_id"), msg.get("category_id")
                )
            },
        )

    async_register_command(hass, ws_maintenance)


# -- entities -----------------------------------------------------------------


def catalog_entities(
    hass: HomeAssistant, entry: ConfigEntry, domain: str, platform: str
) -> list[Entity]:
    """Entities of the catalog for a platform, only for the hosting entry.

    One update entity per section the entry hosts; one automatic update switch
    for the domain, with the first section.
    """
    hosted = [
        updater
        for updater in get_updaters(hass, domain)
        if updater.owner_entry_id == entry.entry_id
    ]
    if platform == "update":
        return [CatalogUpdateEntity(updater) for updater in hosted]
    if platform == "switch" and hosted and hosted[0] is get_updater(hass, domain):
        return [CatalogAutoUpdateSwitch(hosted[0])]
    return []


class _CatalogEntity(Entity):
    """Common part: the catalog device, follows the updater."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, updater: CatalogUpdater) -> None:
        """Bind to the updater."""
        self._updater = updater
        spec = updater.spec
        # One device for the domain, named after its first section
        first = (get_updater(updater.hass, spec.domain) or updater).spec
        self._device_name = first.device_title or first.title
        self._attr_device_info = DeviceInfo(
            identifiers={(spec.domain, f"catalog_{first.section}")},
            name=self._device_name,
            manufacturer=MANUFACTURER,
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=f"https://github.com/{spec.repo}",
        )
        self._refresh()

    async def async_added_to_hass(self) -> None:
        """Follow checks and installs."""
        self.async_on_remove(self._updater.async_add_listener(self._on_change))

    @callback
    def _on_change(self) -> None:
        self._refresh()
        self.async_write_ha_state()

    def _refresh(self) -> None:
        """Copy the updater state into the entity attributes."""


class CatalogUpdateEntity(_CatalogEntity, UpdateEntity):
    """Installed and latest release of the section; installs on demand."""

    _attr_supported_features = (
        UpdateEntityFeature.INSTALL
        | UpdateEntityFeature.PROGRESS
        | UpdateEntityFeature.RELEASE_NOTES
    )

    def __init__(self, updater: CatalogUpdater) -> None:
        """Bind to the updater."""
        self._attr_unique_id = f"catalog_{updater.spec.section}"
        self._attr_title = updater.spec.title
        super().__init__(updater)
        # Named after its device, unless the device is shared with other sections
        if self._device_name == updater.spec.title:
            self._attr_name = None
        else:
            self._attr_name = updater.spec.title

    def _refresh(self) -> None:
        updater = self._updater
        installed = updater.installed
        latest = updater.latest
        self._attr_installed_version = installed.version if installed else NOT_INSTALLED
        self._attr_latest_version = (
            latest.version
            if latest is not None and updater.update_available
            else self._attr_installed_version
        )
        self._attr_release_url = (
            updater.client.release_url(latest.version) if latest else None
        )
        self._attr_release_summary = (
            f"Needs {updater.spec.domain} {latest.min_integration.get(updater.spec.domain)} or newer."
            if latest is not None and not updater.compatible
            else None
        )
        self._attr_auto_update = updater.auto_update
        self._attr_in_progress = updater.in_progress
        self._attr_update_percentage = updater.progress

    async def async_update(self) -> None:
        """Check for a release now (homeassistant.update_entity, *Check for updates*)."""
        await self._updater.async_check()

    async def async_release_notes(self) -> str | None:
        """Notes of the latest release."""
        latest = self._updater.latest
        return latest.notes if latest and latest.notes else None

    async def async_install(
        self, version: str | None, backup: bool, **kwargs: Any
    ) -> None:
        """Install the latest release."""
        await self._updater.async_install()


class CatalogAutoUpdateSwitch(_CatalogEntity, SwitchEntity):
    """Install new catalog releases as soon as they are published."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "catalog_auto_update"
    _attr_icon = "mdi:cloud-download-outline"

    def __init__(self, updater: CatalogUpdater) -> None:
        """Bind to the updater."""
        self._attr_unique_id = f"catalog_{updater.spec.section}_auto_update"
        super().__init__(updater)

    def _refresh(self) -> None:
        self._attr_is_on = self._updater.auto_update

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn automatic installs on (and install a pending release)."""
        await self._updater.async_set_auto_update(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn automatic installs off."""
        await self._updater.async_set_auto_update(False)

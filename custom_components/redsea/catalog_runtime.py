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

It keeps `<config>/<domain>/catalog/` up to date (check at start-up then
every 12 hours, automatic install unless switched off), merges it with the
built-in snapshot (`catalog_builtin/` next to this file) and the user folder
(`<config>/<domain>/catalog_user/`), serves the visuals at
`/<domain>_catalog/{builtin,pack,user}/...` and answers the cards on the
websocket (`<domain>/catalog`, `<domain>/catalog/subscribe`, and for the
equipment section `<domain>/catalog/maintenance`).

Translation keys expected in the integration: the exceptions
`catalog_unknown`, `catalog_incompatible` (placeholders `version`, `minimum`)
and `catalog_install_failed` (placeholder `error`), and the entity name
`entity.switch.catalog_auto_update`.
"""

from __future__ import annotations

import logging
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
from homeassistant.helpers.dispatcher import async_dispatcher_send
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
    extract_entry,
    is_compatible,
    plan,
    prepare_staging,
    read_installed,
    resolve_maintenance,
    select,
)

_LOGGER = logging.getLogger(__name__)

DATA_KEY = "reeftech_catalog"
BUILTIN_DIR = Path(__file__).parent / "catalog_builtin"
#: Version shown while no pack is installed
NOT_INSTALLED = "0"
MANUFACTURER = "ReefTech"


@dataclass(frozen=True)
class CatalogSpec:
    """What an integration reads from the catalog."""

    domain: str
    section: str  # equipment | supplements
    title: str  # name of the catalog device
    scopes: tuple[str, ...] | None = None  # None keeps every scope
    repo: str = REPO
    check_hours: int = 12


def signal_catalog_changed(domain: str) -> str:
    """Dispatcher signal sent each time the catalog of a domain changes.

    For entities of other config entries (they may be set up before the
    entry hosting the catalog): connect with async_dispatcher_connect.
    """
    return f"{domain}_catalog_changed"


def _registry(hass: HomeAssistant) -> dict[str, Any]:
    return hass.data.setdefault(DATA_KEY, {})


def get_updater(hass: HomeAssistant, domain: str) -> CatalogUpdater | None:
    """The running updater of a domain, if any."""
    return _registry(hass).get(domain)


class CatalogUpdater:
    """State of a domain's catalog: checks, installs and the merged view."""

    def __init__(
        self, hass: HomeAssistant, spec: CatalogSpec, integration_version: str
    ) -> None:
        """Bind to the folders of the domain."""
        self.hass = hass
        self.spec = spec
        self.integration_version = integration_version
        self.root = Path(hass.config.path(spec.domain, "catalog"))
        self.user_root = Path(hass.config.path(spec.domain, "catalog_user"))
        self.client = PackClient(async_get_clientsession(hass), spec.section, spec.repo)
        self.installed: Manifest | None = None
        self.latest: Manifest | None = None
        self.last_error: str | None = None
        self.in_progress = False
        self.progress: int | None = None
        self.auto_update = True
        self.entry_ids: list[str] = []
        self._store: Store[dict[str, Any]] = Store(hass, 1, f"{spec.domain}.catalog")
        self._view: dict[str, Any] | None = None
        self._listeners: list[Callable[[], None]] = []
        self._unsub_timer: CALLBACK_TYPE | None = None

    # -- state ----------------------------------------------------------------

    @property
    def owner_entry_id(self) -> str | None:
        """Config entry hosting the catalog entities."""
        return self.entry_ids[0] if self.entry_ids else None

    @property
    def compatible(self) -> bool:
        """The latest release can be used by this integration."""
        return self.latest is None or is_compatible(
            self.latest, self.spec.domain, self.integration_version
        )

    @property
    def update_available(self) -> bool:
        """A release different from the installed pack (or no pack at all)."""
        if self.latest is None:
            return False
        if self.installed is None:
            return True
        return self.latest.raw != self.installed.raw

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
        for listener in list(self._listeners):
            listener()
        async_dispatcher_send(self.hass, signal_catalog_changed(self.spec.domain))

    # -- life cycle -----------------------------------------------------------

    async def async_start(self) -> None:
        """Read the installed pack and the settings, then check in the background."""
        stored = await self._store.async_load() or {}
        self.auto_update = bool(stored.get("auto_update", True))
        self.installed = await self.hass.async_add_executor_job(self._prepare_folders)
        # Loaded before the platforms, so that entities read it synchronously
        await self.async_view(refresh=True)
        self._notify()
        self._unsub_timer = async_track_time_interval(
            self.hass, self._async_timer, timedelta(hours=self.spec.check_hours)
        )
        # A first check that fails (offline) must not delay nor fail the setup
        self.hass.async_create_background_task(
            self.async_check(), f"{self.spec.domain} catalog check"
        )

    def _prepare_folders(self) -> Manifest | None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.user_root.mkdir(parents=True, exist_ok=True)
        return read_installed(self.root, self.spec.section)

    @callback
    def async_stop(self) -> None:
        """Stop the periodic checks."""
        if self._unsub_timer is not None:
            self._unsub_timer()
            self._unsub_timer = None

    async def _async_timer(self, _now: Any) -> None:
        await self.async_check()

    async def async_set_auto_update(self, value: bool) -> None:
        """Turn automatic installs on or off (kept across restarts)."""
        self.auto_update = value
        await self._store.async_save({"auto_update": value})
        self._notify()
        if value:
            await self.async_check()

    # -- checks ---------------------------------------------------------------

    async def async_check(self) -> None:
        """Read the current manifest; install it when automatic installs are on."""
        try:
            latest = await self.client.latest()
        except PackError as err:
            # Offline or GitHub down: keep the installed catalog, quietly
            self.last_error = str(err)
            _LOGGER.debug("%s catalog check failed: %s", self.spec.domain, err)
            self._notify()
            return
        self.last_error = None
        self.latest = select(latest, self.spec.scopes)
        self._notify()
        if not (self.auto_update and self.update_available) or self.in_progress:
            return
        if not self.compatible:
            _LOGGER.warning(
                "%s catalog %s needs %s %s or newer: not installed",
                self.spec.section,
                latest.version,
                self.spec.domain,
                latest.min_integration.get(self.spec.domain),
            )
            return
        try:
            await self.async_install()
        except HomeAssistantError as err:
            _LOGGER.warning("%s catalog update failed: %s", self.spec.domain, err)

    # -- install --------------------------------------------------------------

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
        if self.in_progress:
            return
        self.in_progress = True
        self.progress = 0
        self._notify()
        try:
            installed = await self.hass.async_add_executor_job(
                read_installed, self.root, self.spec.section
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
            await self.hass.async_add_executor_job(commit, self.root, staging, latest)
            # Set before the final notification, so listeners see the new version
            self.installed = latest
            self._view = await self.hass.async_add_executor_job(
                build_view, self._layers(), self.spec.section, self.spec.scopes
            )
        except (PackError, OSError) as err:
            raise HomeAssistantError(
                translation_domain=domain,
                translation_key="catalog_install_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        finally:
            self.in_progress = False
            self.progress = None
            self._notify()
        _LOGGER.info(
            "%s catalog %s installed (%d entries downloaded, %d kept)",
            self.spec.section,
            latest.version,
            len(fetch),
            len(keep),
        )

    # -- merged view ----------------------------------------------------------

    def _layers(self) -> list[Layer]:
        base = f"/{self.spec.domain}_catalog"
        installed = self.installed.version if self.installed else NOT_INSTALLED
        layers = []
        if BUILTIN_DIR.is_dir():
            layers.append(
                Layer(
                    "builtin", BUILTIN_DIR, f"{base}/builtin", self.integration_version
                )
            )
        layers.append(Layer("pack", self.root, f"{base}/pack", installed))
        layers.append(Layer("user", self.user_root, f"{base}/user", "user"))
        return layers

    @property
    def view(self) -> dict[str, Any]:
        """Merged catalog as last loaded (loaded at start, reloaded on install)."""
        return self._view or {}

    async def async_view(self, refresh: bool = False) -> dict[str, Any]:
        """Merged catalog (built-in < downloaded < user), re-read on demand."""
        view = self._view
        if view is None or refresh:
            view = await self.hass.async_add_executor_job(
                build_view, self._layers(), self.spec.section, self.spec.scopes
            )
            self._view = view
        return view


# -- set-up -------------------------------------------------------------------


async def async_setup_catalog(
    hass: HomeAssistant, entry: ConfigEntry, spec: CatalogSpec
) -> CatalogUpdater:
    """Start the domain's updater on its first config entry, register the others."""
    registry = _registry(hass)
    updater: CatalogUpdater | None = registry.get(spec.domain)
    if updater is None:
        integration = await async_get_integration(hass, spec.domain)
        updater = CatalogUpdater(hass, spec, str(integration.version or "0"))
        registry[spec.domain] = updater
        await updater.async_start()
        await _async_register_paths(hass, updater)
        _register_websocket(hass, spec)
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
    updater: CatalogUpdater | None = _registry(hass).get(spec.domain)
    if updater is None or entry.entry_id not in updater.entry_ids:
        return
    was_owner = updater.owner_entry_id == entry.entry_id
    updater.entry_ids.remove(entry.entry_id)
    if not updater.entry_ids:
        updater.async_stop()
        del _registry(hass)[spec.domain]
        # Readers fall back to what they had before the catalog was loaded
        async_dispatcher_send(hass, signal_catalog_changed(spec.domain))
    elif was_owner:
        hass.config_entries.async_schedule_reload(str(updater.owner_entry_id))


async def _async_register_paths(hass: HomeAssistant, updater: CatalogUpdater) -> None:
    """Serve the visuals of the three layers (public catalog data)."""
    key = f"paths_{updater.spec.domain}"
    registry = _registry(hass)
    if registry.get(key) or getattr(hass, "http", None) is None:
        return
    registry[key] = True
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(layer.url, str(layer.root), cache_headers=False)
            for layer in updater._layers()
        ]
    )


def _register_websocket(hass: HomeAssistant, spec: CatalogSpec) -> None:
    """Register the websocket commands of a domain (once per run)."""
    key = f"websocket_{spec.domain}"
    registry = _registry(hass)
    if registry.get(key):
        return
    registry[key] = True
    domain = spec.domain

    def _updater(
        connection: ActiveConnection, msg: dict[str, Any]
    ) -> CatalogUpdater | None:
        updater = get_updater(hass, domain)
        if updater is None:
            connection.send_error(msg["id"], "not_loaded", f"{domain} is not loaded")
        return updater

    @websocket_command(
        {vol.Required("type"): f"{domain}/catalog", vol.Optional("refresh"): bool}
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
                "section": spec.section,
                "format": MANIFEST_FORMAT,
                "version": updater.installed.version if updater.installed else None,
                "updating": updater.in_progress,
                "data": await updater.async_view(msg.get("refresh", False)),
            },
        )

    @websocket_command({vol.Required("type"): f"{domain}/catalog/subscribe"})
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

    if spec.section != "equipment":
        return

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
        updater = _updater(connection, msg)
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
    """Entities of the catalog for a platform, only for the hosting entry."""
    updater = get_updater(hass, domain)
    if updater is None or updater.owner_entry_id != entry.entry_id:
        return []
    if platform == "update":
        return [CatalogUpdateEntity(updater)]
    if platform == "switch":
        return [CatalogAutoUpdateSwitch(updater)]
    return []


class _CatalogEntity(Entity):
    """Common part: the catalog device, follows the updater."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, updater: CatalogUpdater) -> None:
        """Bind to the updater."""
        self._updater = updater
        spec = updater.spec
        self._attr_device_info = DeviceInfo(
            identifiers={(spec.domain, f"catalog_{spec.section}")},
            name=spec.title,
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

    # Named after its device
    _attr_name = None
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

"""Catalog sections read by the integration, and what follows their updates.

The supplements catalog is the first one (it keeps the plain folders and URLs
the integration has always used); water tests and parameters come with
``by_section``. One config entry hosts the three (see supplements.py), with one
device and one update entity per section.

Parameters and water tests feed the dose regulation, which is pure code: each
time one of them is loaded or updated, ``catalog_tables`` receives the new view.
"""

from __future__ import annotations

from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from . import catalog_tables
from .catalog_runtime import (
    CatalogSpec,
    async_setup_catalog,
    async_unload_catalog,
    get_updater,
    signal_catalog_changed,
)
from .const import DOMAIN
from .supplements import CATALOG as SUPPLEMENTS_CATALOG

WATER_TESTS_CATALOG: Final = CatalogSpec(
    DOMAIN, "water_tests", "ReefBeat water tests catalog", by_section=True
)
PARAMETERS_CATALOG: Final = CatalogSpec(
    DOMAIN, "parameters", "ReefBeat parameters catalog", by_section=True
)
#: In the order they are set up: the first one names the catalog device
CATALOGS: Final[tuple[CatalogSpec, ...]] = (
    SUPPLEMENTS_CATALOG,
    WATER_TESTS_CATALOG,
    PARAMETERS_CATALOG,
)
#: Sections the regulation reads
_TABLE_SECTIONS: Final[tuple[CatalogSpec, ...]] = (
    WATER_TESTS_CATALOG,
    PARAMETERS_CATALOG,
)


@callback
def _install(hass: HomeAssistant, spec: CatalogSpec) -> None:
    """Give the regulation the loaded view of a section."""
    updater = get_updater(hass, DOMAIN, spec.section)
    if updater is not None:
        catalog_tables.install(spec.section, updater.view)


async def async_setup_catalogs(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Start the updater of every section and follow the ones the regulation reads."""
    for spec in CATALOGS:
        await async_setup_catalog(hass, entry, spec)
    for spec in _TABLE_SECTIONS:
        _install(hass, spec)
        entry.async_on_unload(
            async_dispatcher_connect(
                hass,
                signal_catalog_changed(DOMAIN, spec.section),
                lambda spec=spec: _install(hass, spec),  # type: ignore[misc]
            )
        )


async def async_unload_catalogs(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Stop the updaters; the regulation falls back to the built-in snapshots."""
    for spec in CATALOGS:
        await async_unload_catalog(hass, entry, spec)
    catalog_tables.reset()

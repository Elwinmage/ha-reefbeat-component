"""Supplements of the ReefDose, from reeftech-catalog (section supplements).

The list used to live in supplements_list.py. It now comes from the catalog
kept up to date by catalog_runtime.py (downloaded releases, merged with the
built-in snapshot `catalog_builtin/` and the user folder
`<config>/redsea/catalog_user/`), so a new supplement no longer needs a
release of the integration nor of the card.

Entries are returned in the format the doser API expects (the one of the old
list): `device_payload` gives exactly what is sent to the doser.
"""

from __future__ import annotations

from typing import Any, Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback

from .catalog_pack import Layer, build_view
from .catalog_runtime import BUILTIN_DIR, CatalogSpec, get_updater
from .const import DOMAIN

CATALOG: Final = CatalogSpec(DOMAIN, "supplements", "ReefBeat supplements catalog")

# The catalog has a config entry of its own (like Poseidon), created by the
# first ReefDose: its device does not hang on one doser among several.
CONF_CATALOG: Final = "supplements_catalog"
CATALOG_UNIQUE_ID: Final = "catalog_supplements"
SOURCE_CATALOG: Final = "catalog"
CATALOG_PLATFORMS: Final[list[Platform]] = [Platform.SWITCH, Platform.UPDATE]

# Keys sent to the doser, in the order of the old list
_PAYLOAD_KEYS: Final[tuple[str, ...]] = (
    "uid",
    "name",
    "display_name",
    "short_name",
    "brand_name",
    "type",
    "concentration",
    "made_by_redsea",
    "fullname",
    "sizes",
    "bundle",
)
_BUNDLE_PART_KEYS: Final[tuple[str, ...]] = (
    "uid",
    "name",
    "display_name",
    "short_name",
    "brand_name",
    "made_by_redsea",
)

# Built-in snapshot, read once when the integration is imported (Home
# Assistant imports custom integrations in its executor): used until the
# catalog is loaded, and by code running without a ReefDose entry.
_BUILTIN_VIEW: Final[dict[str, Any]] = build_view(
    [Layer("builtin", BUILTIN_DIR, f"/{DOMAIN}_catalog/builtin", "builtin")],
    "supplements",
)


def is_catalog_entry(entry: ConfigEntry) -> bool:
    """Whether a config entry of the integration is the supplements catalog."""
    return bool(entry.data.get(CONF_CATALOG))


@callback
def async_request_catalog_entry(hass: HomeAssistant) -> None:
    """Create the catalog entry if there is none yet (called by the dosers)."""
    entries = hass.config_entries
    if entries.async_entry_for_domain_unique_id(DOMAIN, CATALOG_UNIQUE_ID):
        return
    if entries.flow.async_progress_by_handler(
        DOMAIN, match_context={"source": SOURCE_CATALOG}
    ):
        return
    hass.async_create_task(
        entries.flow.async_init(DOMAIN, context={"source": SOURCE_CATALOG}),
        "redsea supplements catalog entry",
    )


def _catalog_items(hass: HomeAssistant | None) -> dict[str, dict[str, Any]]:
    """Catalog entries by catalog id (loaded catalog, else built-in snapshot)."""
    updater = get_updater(hass, DOMAIN) if hass is not None else None
    items = updater.view.get("items") if updater is not None else None
    return items or _BUILTIN_VIEW.get("items", {})


def _part(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "uid": data.get("uid"),
        "name": data.get("name"),
        "display_name": data.get("display_name"),
        "short_name": data.get("short_name"),
        "brand_name": data.get("brand"),
        "made_by_redsea": bool(data.get("made_by_redsea", False)),
    }


def _legacy(catalog_id: str, items: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """A catalog entry in the format of the old list, plus catalog fields."""
    data = items[catalog_id]
    entry: dict[str, Any] = {
        "uid": data.get("uid", catalog_id),
        "name": data.get("name"),
        "display_name": data.get("display_name"),
        "short_name": data.get("short_name"),
        "brand_name": data.get("brand"),
        "type": "Bundle" if data.get("kind") == "bundle" else None,
        "concentration": None,
        "made_by_redsea": bool(data.get("made_by_redsea", False)),
        "fullname": data.get("fullname"),
    }
    if data.get("sizes"):
        entry["sizes"] = list(data["sizes"])
    if data.get("bundle"):
        entry["bundle"] = {
            str(part["slot"]): {
                "supplement": _part(items.get(part["part"], {})),
                "ratio": part["ratio"],
            }
            for part in sorted(data["bundle"], key=lambda p: p["slot"])
        }
    # Not sent to the doser (see device_payload)
    entry["catalog_id"] = catalog_id
    entry["kind"] = data.get("kind")
    entry["image"] = data.get("image")
    entry["thumb"] = data.get("thumb")
    entry["effects"] = list(data.get("effects") or [])
    entry["verified"] = bool(data.get("verified", False))
    return entry


def supplements(hass: HomeAssistant | None) -> list[dict[str, Any]]:
    """Every supplement, sorted by full name."""
    items = _catalog_items(hass)
    entries = [_legacy(catalog_id, items) for catalog_id in items]
    return sorted(entries, key=lambda e: e.get("fullname") or "")


def supplement_by_uid(hass: HomeAssistant | None, uid: str) -> dict[str, Any] | None:
    """The supplement of a uid, or None."""
    return next((s for s in supplements(hass) if s["uid"] == uid), None)


def device_payload(supplement: dict[str, Any]) -> dict[str, Any]:
    """What is sent to the doser for a supplement: the keys of the old list."""
    return {key: supplement[key] for key in _PAYLOAD_KEYS if key in supplement}


# Kinds of supplements no test result drives: a nutrient reducer (Red Sea
# NO3PO4-X lowers nitrate and phosphate, it raises nothing) or a food
NOT_REGULATED_KINDS: Final[frozenset[str]] = frozenset({"nutrient", "food"})


def supplement_regulated(hass: HomeAssistant | None, uid: str | None) -> bool:
    """Whether a test can drive the dose of a supplement.

    A supplement unknown to the catalog (the user's own) is the user's call.
    """
    if not uid:
        return True
    supplement = supplement_by_uid(hass, uid)
    return supplement is None or supplement.get("kind") not in NOT_REGULATED_KINDS


def supplement_potency(
    hass: HomeAssistant | None, uid: str | None
) -> tuple[str, float] | None:
    """Parameter a supplement raises and by how much 1 mL raises it in 100 L.

    Only verified catalog data (taken from the label) is used.
    """
    if not uid:
        return None
    supplement = supplement_by_uid(hass, uid)
    if supplement is None or not supplement["verified"]:
        return None
    for effect in supplement["effects"]:
        return str(effect["parameter"]), float(effect["per_ml_per_100l"])
    return None

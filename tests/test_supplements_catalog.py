"""The supplements of the ReefDose come from the reeftech-catalog client."""

from __future__ import annotations

import copy

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea import supplements as sup
from custom_components.redsea.catalog_runtime import get_updater
from custom_components.redsea.config_flow import ReefBeatConfigFlow as ConfigFlow
from custom_components.redsea.const import DOMAIN

REEFCARE = "redsea-reefcare"
FOUNDATION_B = "76830db3-a0bd-459a-9974-76a57d026893"


def test_builtin_list_in_the_doser_format() -> None:
    """Without a loaded catalog, the built-in snapshot gives the old list."""
    catalog = sup.supplements(None)
    assert len(catalog) == 95
    assert [s["fullname"] for s in catalog] == sorted(s["fullname"] for s in catalog)
    kh = sup.device_payload(sup.supplement_by_uid(None, FOUNDATION_B) or {})
    assert kh == {
        "uid": FOUNDATION_B,
        "name": "KH/Alkalinity (Foundation B)",
        "display_name": "KH",
        "short_name": "KH",
        "brand_name": "Red Sea",
        "type": None,
        "concentration": None,
        "made_by_redsea": True,
        "fullname": "Red Sea - KH/Alkalinity (Foundation B)",
        "sizes": [5000, 1000, 500, 250],
    }
    bundle = sup.device_payload(sup.supplement_by_uid(None, REEFCARE) or {})
    assert bundle["type"] == "Bundle" and bundle["display_name"] is None
    assert bundle["bundle"]["2"] == {
        "supplement": {
            "uid": "6f6a53db-0985-47f4-92bd-cef092d97d22",
            "name": "Part 2: KH/Alkalinity &PH stabilizer",
            "display_name": "Part 2",
            "short_name": "P2",
            "brand_name": "Red Sea",
            "made_by_redsea": True,
        },
        "ratio": 2,
    }
    # Catalog fields stay out of the doser payload
    full = sup.supplement_by_uid(None, FOUNDATION_B) or {}
    assert full["image"].startswith(f"/{DOMAIN}_catalog/builtin/items/")
    assert full["catalog_id"] == "red-sea-kh-alkalinity-foundation-b"
    assert sup.supplement_by_uid(None, "unknown") is None


def _catalog_entry(hass: HomeAssistant):
    return hass.config_entries.async_entry_for_domain_unique_id(
        DOMAIN, sup.CATALOG_UNIQUE_ID
    )


async def test_doser_creates_the_catalog_entry(
    hass: HomeAssistant, local_dose_config_entry: MockConfigEntry
) -> None:
    """The first doser creates the catalog entry, which hosts the catalog."""
    doser = local_dose_config_entry
    doser.add_to_hass(hass)
    assert await hass.config_entries.async_setup(doser.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)

    catalog = _catalog_entry(hass)
    assert catalog is not None and sup.is_catalog_entry(catalog)
    assert catalog.title == "ReefBeat supplements catalog"
    assert not ConfigFlow.async_supports_options(catalog)
    assert ConfigFlow.async_supports_options(doser)
    updater = get_updater(hass, DOMAIN)
    assert updater is not None and updater.entry_ids == [catalog.entry_id]

    # Its device holds the entities, none on the doser entry
    registry = er.async_get(hass)
    ids = {
        e.unique_id: e.entity_id
        for e in er.async_entries_for_config_entry(registry, catalog.entry_id)
    }
    assert set(ids) == {"catalog_supplements", "catalog_supplements_auto_update"}
    update = hass.states.get(ids["catalog_supplements"])
    switch = hass.states.get(ids["catalog_supplements_auto_update"])
    assert update is not None and update.attributes["installed_version"] == "0"
    assert switch is not None and switch.state == "on"
    doser_ids = {
        e.unique_id for e in er.async_entries_for_config_entry(registry, doser.entry_id)
    }
    assert not doser_ids & set(ids)

    # Already there (or being created): not requested again
    sup.async_request_catalog_entry(hass)
    await hass.async_block_till_done()
    assert len(hass.config_entries.async_entries(DOMAIN)) == 2

    # A catalog release adds a supplement: every head select offers it
    select_id = next(
        e.entity_id
        for e in er.async_entries_for_config_entry(registry, doser.entry_id)
        if e.unique_id.endswith("_supplements_1")
    )
    view = copy.deepcopy(updater.view)
    view["items"]["my-brand-kh"] = {
        "uid": "my-uid",
        "brand": "My Brand",
        "name": "KH",
        "fullname": "My Brand - KH",
        "short_name": "KH",
        "kind": "kh",
        "verified": False,
    }
    updater._view = view
    updater._notify()
    await hass.async_block_till_done()
    select = hass.states.get(select_id)
    assert select is not None
    options = select.attributes["options"]
    assert "My Brand - KH" in options and options[-1] == "other"
    # Same catalog again: nothing written
    updater._notify()

    # Removing the catalog entry stops the catalog; the doser keeps working
    assert await hass.config_entries.async_remove(catalog.entry_id)
    await hass.async_block_till_done()
    assert get_updater(hass, DOMAIN) is None
    select = hass.states.get(select_id)
    assert select is not None and "My Brand - KH" not in select.attributes["options"]


async def test_catalog_requested_once_while_its_flow_runs(
    hass: HomeAssistant, monkeypatch
) -> None:
    """Two dosers starting together create a single catalog entry."""
    # A catalog flow already running: nothing started
    with monkeypatch.context() as patch:
        patch.setattr(
            hass.config_entries.flow,
            "async_progress_by_handler",
            lambda *a, **k: [{}],
        )
        sup.async_request_catalog_entry(hass)
        await hass.async_block_till_done(wait_background_tasks=True)
    assert hass.config_entries.async_entries(DOMAIN) == []

    sup.async_request_catalog_entry(hass)
    sup.async_request_catalog_entry(hass)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    # A flow started by hand while it exists aborts
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": sup.SOURCE_CATALOG}
    )
    assert result.get("type") == "abort"
    assert result.get("reason") == "already_configured"
    entry = _catalog_entry(hass)
    assert entry is not None
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

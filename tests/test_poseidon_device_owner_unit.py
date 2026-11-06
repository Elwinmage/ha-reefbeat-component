"""Owner config entry of a registry device (poseidon/manager.py)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from custom_components.redsea.poseidon.manager import _belongs_to


def test_single_config_entry_id() -> None:
    device = cast(Any, SimpleNamespace(config_entry_id="e1"))
    assert _belongs_to(device, "e1") is True
    assert _belongs_to(device, "e2") is False


def test_older_home_assistant_set_of_entries() -> None:
    device = cast(Any, SimpleNamespace(config_entries={"e1", "e2"}))
    assert _belongs_to(device, "e2") is True
    assert _belongs_to(device, "e3") is False


def test_device_without_entry() -> None:
    assert _belongs_to(cast(Any, SimpleNamespace()), "e1") is False


def test_real_device_entry_does_not_warn(hass: Any, caplog: Any) -> None:
    from homeassistant.helpers import device_registry as dr
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(domain="redsea", data={})
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={("redsea", "hw-1")}
    )
    caplog.clear()
    assert _belongs_to(device, entry.entry_id) is True
    assert _belongs_to(device, "other") is False
    assert "config_entries" not in caplog.text

"""Coverage for `MaintenanceLabelMixin.async_added_to_hass`.

When a maintenance entity is added and the ``redsea_maintenance`` label does
not yet exist, the mixin creates it and applies it to the entity's registry
entry (merging with any user labels).
"""

from __future__ import annotations

from typing import Any, cast

import pytest
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import label_registry as lr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea.const import DOMAIN
from custom_components.redsea.entity import MAINTENANCE_LABEL, MaintenanceLabelMixin


class _Base:
    async def async_added_to_hass(self) -> None:  # provides the super() target
        return None


class _MaintEntity(MaintenanceLabelMixin, _Base):
    def __init__(self, hass: Any, entity_id: str) -> None:
        self.hass = hass
        self.entity_id = entity_id


@pytest.mark.asyncio
async def test_maintenance_label_created_and_applied(hass: Any) -> None:
    entry = MockConfigEntry(domain=DOMAIN, title="d", data={}, unique_id="lbl")
    entry.add_to_hass(hass)
    reg = er.async_get(hass)
    e = reg.async_get_or_create(
        "number", DOMAIN, "SER_clean_probe_interval_1", config_entry=cast(Any, entry)
    )

    # The label does not exist yet -> the mixin must create it.
    lab_reg = lr.async_get(hass)
    assert lab_reg.async_get_label_by_name(MAINTENANCE_LABEL) is None

    ent = _MaintEntity(hass, e.entity_id)
    await ent.async_added_to_hass()

    label = lab_reg.async_get_label_by_name(MAINTENANCE_LABEL)
    assert label is not None
    updated = reg.async_get(e.entity_id)
    assert updated is not None
    assert label.label_id in updated.labels


@pytest.mark.asyncio
async def test_maintenance_label_noop_when_entity_not_registered(hass: Any) -> None:
    # Entity id absent from the registry -> the mixin returns early, no crash.
    ent = _MaintEntity(hass, "number.not_registered")
    await ent.async_added_to_hass()
    lab_reg = lr.async_get(hass)
    assert lab_reg.async_get_label_by_name(MAINTENANCE_LABEL) is None

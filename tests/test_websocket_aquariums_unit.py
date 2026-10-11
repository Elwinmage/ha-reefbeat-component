"""`redsea/aquariums`: cloud aquariums joined with the device registry."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.redsea.const import DOMAIN
from custom_components.redsea.coordinator import ReefBeatCloudCoordinator
from custom_components.redsea.websocket import (
    async_register_websocket,
    cloud_aquariums,
)

AQUARIUMS = "$.sources[?(@.name=='/aquarium')].data"
DEVICES = "$.sources[?(@.name=='/device')].data"


def _cloud(
    aquariums: Any, devices: Any, serial: str = "cloud1", title: str = "me@x"
) -> MagicMock:
    cloud = MagicMock(spec=ReefBeatCloudCoordinator)
    cloud.serial = serial
    cloud.title = title
    cloud.get_data.side_effect = lambda path, *_: {
        AQUARIUMS: aquariums,
        DEVICES: devices,
    }[path]
    return cloud


async def test_aquariums_with_devices(hass: HomeAssistant, hass_ws_client: Any) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    dev_reg = dr.async_get(hass)
    led = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "hw_led")}
    )
    dose = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "hw_dose")}
    )
    shortcut = er.async_get(hass).async_get_or_create(
        "switch", DOMAIN, "cloud1_aq1_shortcut_feeding_1", suggested_object_id="feed"
    )

    hass.data[DOMAIN] = {
        "local": object(),
        "cloud": _cloud(
            [
                {
                    "uid": "aq1",
                    "name": "Reefer",
                    "system_model": "Reefer 425",
                    "system_series": "reefer",
                    "system_type": "mixed-reef",
                    "length": 121.92,
                    "width": "60.96",
                    "height": 40.64,
                    "water_volume": 80,
                    "net_water_volume": 120,
                    "measuring_unit": "gallons",
                },
                {"uid": "aq2", "length": "x", "width": 0, "height": None},
                {"name": "no uid"},
                "junk",
            ],
            [
                {"aquarium_uid": "aq1", "hwid": "hw_led"},
                {"aquarium_uid": "aq1", "hwid": "hw_unknown"},
                {"aquarium_uid": "aq2", "hwid": "hw_dose"},
                "junk",
            ],
        ),
        "broken": _cloud(None, None, "cloud2"),
        "nodevices": _cloud([{"uid": "aq3", "name": "Nano"}], None, "cloud3"),
    }

    async_register_websocket(hass)
    ws = await hass_ws_client(hass)
    await ws.send_json_auto_id({"type": "redsea/aquariums"})
    msg = await ws.receive_json()
    assert msg["success"]
    result = msg["result"]
    assert [a["uid"] for a in result] == ["aq1", "aq2", "aq3"]

    first = result[0]
    assert first == {
        "provider": "redsea",
        "account": "me@x",
        "uid": "aq1",
        "name": "Reefer",
        "system_model": "Reefer 425",
        "system_series": "reefer",
        "system_type": "mixed-reef",
        "dimensions_cm": {"length": 121.92, "width": 60.96, "height": 40.64},
        "water_volume": 80,
        "net_water_volume": 120,
        "measuring_unit": "gallons",
        "device_ids": [led.id],
        "feeding_entities": [shortcut.entity_id],
    }
    assert result[1]["name"] == "aq2"
    assert result[1]["dimensions_cm"] is None
    assert result[1]["device_ids"] == [dose.id]
    assert result[2]["device_ids"] == []


async def test_no_cloud(hass: HomeAssistant) -> None:
    assert cloud_aquariums(hass) == []

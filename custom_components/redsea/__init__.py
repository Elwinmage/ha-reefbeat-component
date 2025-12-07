import logging
import asyncio
import functools
import threading
import time

from homeassistant.core import HomeAssistant, ServiceCall, callback, ServiceResponse, SupportsResponse
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import device_registry
from homeassistant.const import EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STOP

from .const import (
    DOMAIN,
    PLATFORMS,
    CONFIG_FLOW_IP_ADDRESS,
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_CLOUD_USERNAME,
    HW_LED_IDS,
    HW_G1_LED_IDS,
    HW_G2_LED_IDS,
    HW_DOSE_IDS,
    HW_MAT_IDS,
    HW_ATO_IDS,
    HW_RUN_IDS,
    HW_WAVE_IDS,
    VIRTUAL_LED,
    LINKED_LED,
    VIRTUAL_LED_MAX_WAITING_TIME,
    )

from .coordinator import ReefLedCoordinator, ReefLedG2Coordinator,ReefVirtualLedCoordinator,ReefMatCoordinator,ReefDoseCoordinator, ReefATOCoordinator, ReefRunCoordinator, ReefWaveCoordinator, ReefBeatCloudCoordinator

import traceback

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Creation des entités à partir d'une configEntry"""

    _LOGGER.debug(
        "Appel de async_setup_entry entry: entry_id='%s', data='%s'",
        entry.entry_id,
        entry.data,
    )
    # CLOUD
    if CONFIG_FLOW_CLOUD_USERNAME in entry.data:
        try:
            coordinator = ReefBeatCloudCoordinator(hass,entry)
        except:
            return False
        await coordinator._async_setup()
    else:
        ip = entry.data[CONFIG_FLOW_IP_ADDRESS]
        hw = entry.data[CONFIG_FLOW_HW_MODEL]
        if ip.startswith(VIRTUAL_LED):
            coordinator = ReefVirtualLedCoordinator(hass,entry)
        else:
            if hw in HW_G1_LED_IDS:
                coordinator = ReefLedCoordinator(hass,entry)
            elif hw in HW_G2_LED_IDS:
                coordinator = ReefLedG2Coordinator(hass,entry)
            elif hw in HW_DOSE_IDS:
                coordinator = ReefDoseCoordinator(hass,entry)
            elif hw in HW_MAT_IDS:
                coordinator = ReefMatCoordinator(hass,entry)
            elif hw in HW_ATO_IDS:
                coordinator = ReefATOCoordinator(hass,entry)
            elif hw in HW_RUN_IDS:
                coordinator = ReefRunCoordinator(hass,entry)
            elif hw in HW_WAVE_IDS:
                coordinator = ReefWaveCoordinator(hass,entry)
            await coordinator._async_setup()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))
    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN][entry.entry_id].unload()
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

#async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
async def async_setup(hass: HomeAssistant, config) -> bool:
    """Set up my integration."""
    @callback
    async def handle_request(call: ServiceCall) -> ServiceResponse:
        """Handle the service action call."""

        device_id = call.data.get("device_id")

        if device_id not in hass.data[DOMAIN]:
            return {"error":"Device not enabled"}
        device=hass.data[DOMAIN][device_id]
        access_path = call.data.get("access_path")#, DEFAULT_NAME)
        method = call.data.get("method")
        if method=="get":
            r=await device.my_api.http_get(access_path)
        else:
            data = call.data.get("data")
            _LOGGER.debug("Call service send request: %s %s [%s] %s"%(device_id,access_path,method,data))
            r=await device.my_api.http_send(access_path,data,method)
        _LOGGER.debug('REQUEST RESPONSE %s'%r)
        if r:
            try:
                r_text=json.loads(r.text)
            except:
                r_text=r.text
                _LOGGER.debug(r)
            return {"code":r.status_code,"text":r_text}
        else:
            _LOGGER.error("can not access to device "+device._title)
            return {"error": "can not access to device "+device._title}

            
    _LOGGER.debug("request service REGISTERED %s"%config)
    hass.services.async_register(DOMAIN, "request", handle_request,supports_response=SupportsResponse.OPTIONAL)
    return True

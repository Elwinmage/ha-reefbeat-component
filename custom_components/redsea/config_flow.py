"""Config flow for Reefbeat component."""

import voluptuous as vol
import glob
import logging

from typing import Any

from functools import partial
from time import time

from homeassistant import config_entries

from homeassistant.config_entries import ConfigEntry

from homeassistant.core import callback

from homeassistant.data_entry_flow import FlowResult

from .auto_detect import (
    get_reefbeats,
    get_unique_id
)

from .const import (
    PLATFORMS,
    DOMAIN,
    CONFIG_FLOW_IP_ADDRESS,
    CONFIG_FLOW_HW_MODEL,
    VIRTUAL_LED,
    LINKED_LED,
)

_LOGGER = logging.getLogger(__name__)

class ReefBeatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """ReefBeat config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def _unique_id(self, user_input):
        f_kwargs = {}
        f_kwargs["ip"] = user_input[CONFIG_FLOW_IP_ADDRESS].split(' ')[0]
        uuid=await self.hass.async_add_executor_job(partial(get_unique_id,**f_kwargs))
        return uuid

    async def async_step_user(self, user_input=None):
        """Create a new entity from UI."""
        if user_input is not None:
            _LOGGER.error("**/*///*")
            _LOGGER.debug(user_input)
            if user_input[CONFIG_FLOW_IP_ADDRESS] == VIRTUAL_LED:
                title=VIRTUAL_LED+'-'+str(int(time()))
                user_input[CONFIG_FLOW_IP_ADDRESS]=title
                user_input[CONFIG_FLOW_HW_MODEL]=VIRTUAL_LED
                _LOGGER.debug("-- ** UUID ** -- %s"%title)
                await self.async_set_unique_id(title)
            else:
                #Identify device with unique ID
                uuid = await self._unique_id(user_input)
                _LOGGER.info("-- ** UUID ** -- %s"%uuid)
                await self.async_set_unique_id(str(uuid))
                self._abort_if_unique_id_configured()
                title=user_input[CONFIG_FLOW_IP_ADDRESS].split(' ')[2]
                user_input[CONFIG_FLOW_HW_MODEL]=user_input[CONFIG_FLOW_IP_ADDRESS].split(' ')[1]
                user_input[CONFIG_FLOW_IP_ADDRESS]=user_input[CONFIG_FLOW_IP_ADDRESS].split(' ')[0]
                _LOGGER.info("-- ** TITLE ** -- %s"%title)
    
            return self.async_create_entry(
                title=title,
                data=user_input,
            )
        detected_devices = await self.hass.async_add_executor_job(get_reefbeats)
        def device_to_string(d):
            return d['ip']+' '+d['hw_model']+' '+d['friendly_name']
        detected_devices_s =list(map(device_to_string,detected_devices))
        available_devices=detected_devices_s
        _LOGGER.info("Detected devices: %s"%detected_devices)
        if DOMAIN in self.hass.data:
            for device in self.hass.data[DOMAIN]:
                coordinator=self.hass.data[DOMAIN][device]
                if (type(coordinator).__name__=='ReefLedCoordinator' or
                    type(coordinator).__name__=='ReefMatCoordinator' or
                    type(coordinator).__name__=='ReefDoseCoordinator' or
                    type(coordinator).__name__=='ReefATOCoordinator') and coordinator.detected_id in detected_devices_s:
                    _LOGGER.info("%s skipped (already configured)"%coordinator.detected_id)
                    available_devices.remove(coordinator.detected_id)
        _LOGGER.info("Available devices: %s"%detected_devices)
        available_devices += [VIRTUAL_LED]
        _LOGGER.info("Available devices string: %s"%available_devices)
        if len(available_devices) > 1 :
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONFIG_FLOW_IP_ADDRESS
                        ): vol.In(available_devices),
                    }
                     ),
                )

        else:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONFIG_FLOW_IP_ADDRESS, default=VIRTUAL_LED
                        ): str,
                    }
                ),
            )
        
    @staticmethod
    @callback
    def async_get_options_flow(
            config_entry: ConfigEntry,
    ):
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):

    def __init__(self,config_entry):
        self._config_entry=config_entry
        
    async def async_step_init(
            self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            _LOGGER.info(user_input)
            _LOGGER.info(self._config_entry.data)
            data={}
            leds={}
            data[CONFIG_FLOW_IP_ADDRESS]=self._config_entry.data[CONFIG_FLOW_IP_ADDRESS]
            data[CONFIG_FLOW_HW_MODEL]=VIRTUAL_LED
            for led in user_input:
                if user_input[led]:
                    leds[led]=True
            data[LINKED_LED]=leds
            
            _LOGGER.info(user_input)
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=data, options=self.config_entry.options
            )
            return self.async_create_entry(data=data)
        errors = {}
        devices_list=[]
        options_schema=None

        if not self._config_entry.title.startswith(VIRTUAL_LED+'-'):
            errors["base"]="Only virtual"
            options_schema=vol.Schema(
                {
                    vol.Required("not_virtual"): vol.In(devices_list),
                }
            )

        else:
            leds={}
            for dev in self.hass.data[DOMAIN]:
                led = self.hass.data[DOMAIN][dev]
                if type(led).__name__=="ReefLedCoordinator":
                    leds[vol.Required('LED: '+led.serial+' ('+dev+')')]=bool
            options_schema=vol.Schema(leds)
            
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                options_schema, self._config_entry.options
            ),
            errors=errors,
        )

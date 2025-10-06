"""Config flow for Reefbeat component."""

import voluptuous as vol
import glob
import logging
import copy
import ipaddress

from jsonpath_ng import jsonpath
from jsonpath_ng.ext import parse

from typing import Any

from functools import partial
from time import time

from homeassistant import config_entries

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryStore,
    ConfigEntryItems
)

from homeassistant.core import callback

from homeassistant.data_entry_flow import FlowResult

from .auto_detect import (
    get_reefbeats,
    get_unique_id,
    is_reefbeat
)


from .const import (
    PLATFORMS,
    DOMAIN,
    CONFIG_FLOW_ADD_TYPE,
    CONFIG_FLOW_CLOUD_USERNAME,
    CONFIG_FLOW_CLOUD_PASSWORD,
    ADD_TYPES,
    ADD_CLOUD_API,
    ADD_LOCAL_DETECT,
    ADD_MANUAL_MODE,
    CLOUD_SERVER_ADDR,
    CONFIG_FLOW_IP_ADDRESS,
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_SCAN_INTERVAL,
    CONFIG_FLOW_INTENSITY_COMPENSATION,
    CONFIG_FLOW_CONFIG_TYPE,
    LED_INTENSITY_INTERNAL_NAME,
    LEDS_INTENSITY_COMPENSATION,
    HW_LED_IDS,
    HW_DOSE_IDS,
    HW_MAT_IDS,
    HW_ATO_IDS,
    HW_RUN_IDS,
    HW_WAVE_IDS,
    SCAN_INTERVAL,
    VIRTUAL_LED_SCAN_INTERVAL,
    DOSE_SCAN_INTERVAL,
    MAT_SCAN_INTERVAL,
    LED_SCAN_INTERVAL,
    ATO_SCAN_INTERVAL,
    RUN_SCAN_INTERVAL,
    VIRTUAL_LED,
    LINKED_LED,
)

_LOGGER = logging.getLogger(__name__)


def get_scan_interval(hw_model):
    default_scan_interval=SCAN_INTERVAL
    if hw_model in HW_DOSE_IDS:
        default_scan_interval=DOSE_SCAN_INTERVAL
    elif hw_model in HW_MAT_IDS:
        default_scan_interval=MAT_SCAN_INTERVAL
    elif hw_model in HW_ATO_IDS:
        default_scan_interval=ATO_SCAN_INTERVAL
    elif hw_model in HW_LED_IDS:
        default_scan_interval=LED_SCAN_INTERVAL
    elif hw_model in HW_RUN_IDS:
        default_scan_interval=RUN_SCAN_INTERVAL
    return default_scan_interval


class ReefBeatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """ReefBeat config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def _unique_id(self, user_input):
        f_kwargs = {}
        f_kwargs["ip"] = user_input[CONFIG_FLOW_IP_ADDRESS].split(' ')[0]
        uuid=await self.hass.async_add_executor_job(partial(get_unique_id,**f_kwargs))
        return uuid

    def is_network(self, address):
        addr=address.split('/')
        if len(addr) < 2:
            return False
        try:
            ipaddress.ip_address(addr[0])
            ipaddress.ip_address(addr[1])
        except:
            return False
        return True

    async def async_step_user(self, user_input=None):
        """Create a new entity from UI."""
        subnetwork=None
        # FIRST STEP
        if user_input == None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONFIG_FLOW_ADD_TYPE, default=ADD_CLOUD_API): vol.In(ADD_TYPES),
                    }
                ),
            )
        else:
            # SECOND_STEP
            if CONFIG_FLOW_ADD_TYPE in user_input:
                #CLOUD
                if user_input[CONFIG_FLOW_ADD_TYPE]==ADD_CLOUD_API:
                    _LOGGER.info("Adding Reebeat Cloud Account")
                    return self.async_show_form(
                        step_id="user",
                        data_schema=vol.Schema(
                            {
                                vol.Required(CONFIG_FLOW_CLOUD_USERNAME):str,
                                vol.Required(CONFIG_FLOW_CLOUD_PASSWORD):str,
                            }
                        ),
                    )
                #DETECT
                elif user_input[CONFIG_FLOW_ADD_TYPE]==ADD_LOCAL_DETECT:
                    return await self.auto_detect(subnetwork)
                # MANUAL
                elif user_input[CONFIG_FLOW_ADD_TYPE]==ADD_MANUAL_MODE:
                    _LOGGER.debug(user_input)
                    return self.async_show_form(
                        step_id="user",
                        data_schema=vol.Schema(
                            {
                                vol.Required(CONFIG_FLOW_IP_ADDRESS):str
                            }
                        )
                    )
            # Third step create entry
            else:
                _LOGGER.debug(user_input)
                # CLOUD
                if CONFIG_FLOW_CLOUD_USERNAME in user_input:
                    user_input[CONFIG_FLOW_SCAN_INTERVAL]=get_scan_interval(None)
                    user_input[CONFIG_FLOW_CONFIG_TYPE]=False
                    user_input[CONFIG_FLOW_IP_ADDRESS]=CLOUD_SERVER_ADDR
                    user_input[CONFIG_FLOW_HW_MODEL]="Smartphone App"
                    title=user_input[CONFIG_FLOW_CLOUD_USERNAME]
                    await self.async_set_unique_id(title)
                    return self.async_create_entry(
                        title=title,
                        data=user_input,
                    )
                # DETECT and MANUAL
                elif CONFIG_FLOW_IP_ADDRESS in user_input:
                    #Add Virtual LED
                    if user_input[CONFIG_FLOW_IP_ADDRESS] == VIRTUAL_LED:
                        title=VIRTUAL_LED+'-'+str(int(time()))
                        user_input[CONFIG_FLOW_IP_ADDRESS]=title
                        user_input[CONFIG_FLOW_HW_MODEL]=VIRTUAL_LED
                        user_input[CONFIG_FLOW_SCAN_INTERVAL]=VIRTUAL_LED_SCAN_INTERVAL
                        _LOGGER.debug("-- ** UUID ** -- %s"%title)
                        await self.async_set_unique_id(title)
                        return self.async_create_entry(
                            title=title,
                            data=user_input,
                        )
                    if self.is_network(user_input[CONFIG_FLOW_IP_ADDRESS]):
                        subnetwork=user_input[CONFIG_FLOW_IP_ADDRESS]
                        return await self.auto_detect(subnetwork)
                    else:
                        configuration=user_input[CONFIG_FLOW_IP_ADDRESS].split(' ')
                        # manual device
                        if len(configuration) < 2:
                            f_kwargs = {}
                            f_kwargs["ip"] = configuration[0]
                            status,ip,hw_model,friendly_name,uuid=await self.hass.async_add_executor_job(partial(is_reefbeat,**f_kwargs))
                            _LOGGER.info("MANUAL IP DETECTED: %s %s %s %s"%(ip,hw_model,friendly_name,uuid))
                            if status==True:
                                conf=self.device_to_string({"ip":ip,"hw_model":hw_model,"friendly_name":friendly_name})
                                configuration=conf.split(' ')
                            _LOGGER.debug("MANUAL IP info: %s"%(configuration))
                            _LOGGER.debug("MANUAL IP array info: %s"%(configuration))
                            # detected device
                        else:
                            uuid = await self._unique_id(user_input)
                        _LOGGER.info("-- ** UUID ** -- %s"%uuid)
                        await self.async_set_unique_id(str(uuid))
                        self._abort_if_unique_id_configured()
                        #
                        title="-".join(configuration[2:])
                        user_input[CONFIG_FLOW_HW_MODEL]=configuration[1]
                        user_input[CONFIG_FLOW_IP_ADDRESS]=configuration[0]
                        user_input[CONFIG_FLOW_SCAN_INTERVAL]=get_scan_interval(user_input[CONFIG_FLOW_HW_MODEL])
                        user_input[CONFIG_FLOW_CONFIG_TYPE]=False
                        _LOGGER.info("-- ** TITLE ** -- %s"%title)
                        return self.async_create_entry(
                            title=title,
                            data=user_input,
                        )
        
    @staticmethod
    @callback
    def async_get_options_flow(
            config_entry: ConfigEntry,
    ):
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)

    @staticmethod
    def device_to_string(d):
        return d['ip']+' '+d['hw_model']+' '+d['friendly_name']

    # AUTO detect reeefbeat device on specified subnetwork
    async def auto_detect(self,subnetwork):
        f_kwargs = {}
        f_kwargs["subnetwork"] = subnetwork
        detected_devices = await self.hass.async_add_executor_job(partial(get_reefbeats,**f_kwargs))
        available_devices=copy.deepcopy(detected_devices)
        _LOGGER.info("Detected devices: %s"%detected_devices)
        _store = ConfigEntryStore(self.hass)
        data= await _store.async_load()
        for device in detected_devices:
            if any (d['unique_id'] == device['uuid'] for d in data['entries']):
                _LOGGER.info("%s skipped (already configured)"%device['friendly_name'])
                available_devices.remove(device)

        _LOGGER.info("Available devices: %s"%available_devices)
        available_devices_s =list(map(self.device_to_string,available_devices))
        available_devices_s += [VIRTUAL_LED]
        _LOGGER.info("Available devices string: %s"%available_devices_s)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONFIG_FLOW_IP_ADDRESS
                    ): vol.In(available_devices_s),
                }
                 ),
            )

################################################################################
# Entity options
class OptionsFlowHandler(config_entries.OptionsFlow):

    def __init__(self,config_entry):
        self._config_entry=config_entry
        
    async def async_step_init(
            self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            if CONFIG_FLOW_SCAN_INTERVAL in user_input:
                _LOGGER.debug("user input")
                _LOGGER.debug(user_input)
                data={}
                data[CONFIG_FLOW_IP_ADDRESS]=self._config_entry.data[CONFIG_FLOW_IP_ADDRESS]
                data[CONFIG_FLOW_HW_MODEL]=self._config_entry.data[CONFIG_FLOW_HW_MODEL]
                data[CONFIG_FLOW_SCAN_INTERVAL]=user_input[CONFIG_FLOW_SCAN_INTERVAL]
                data[CONFIG_FLOW_CONFIG_TYPE]=user_input[CONFIG_FLOW_CONFIG_TYPE]
                if CONFIG_FLOW_INTENSITY_COMPENSATION in user_input:
                    data[CONFIG_FLOW_INTENSITY_COMPENSATION]=user_input[CONFIG_FLOW_INTENSITY_COMPENSATION]
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=data, options=self.config_entry.options
                )
                return self.async_create_entry(data=data)
            else:
                _LOGGER.info(user_input)
                _LOGGER.info(self._config_entry.data)
                data={}
                leds={}
                data[CONFIG_FLOW_IP_ADDRESS]=self._config_entry.data[CONFIG_FLOW_IP_ADDRESS]
                data[CONFIG_FLOW_HW_MODEL]=VIRTUAL_LED
                data[CONFIG_FLOW_SCAN_INTERVAL]=VIRTUAL_LED_SCAN_INTERVAL
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
            try:
                hw_model=self._config_entry.data[CONFIG_FLOW_HW_MODEL]
                query=parse('$[?(@.name=="'+hw_model+'")]')
                res=query.find(LEDS_INTENSITY_COMPENSATION)
            except:
                hw_model=None
                res=[]
            if len(res) > 0:
                options_schema=vol.Schema(
                    {
                        vol.Required(
                            CONFIG_FLOW_SCAN_INTERVAL, default=get_scan_interval(hw_model)
                        ): int,
                        vol.Required(
                            CONFIG_FLOW_CONFIG_TYPE, default=False
                        ): bool,
                        vol.Required(
                            CONFIG_FLOW_INTENSITY_COMPENSATION, default=False
                        ): bool,
                }
                )
            else:
                options_schema=vol.Schema(
                    {
                        vol.Required(
                            CONFIG_FLOW_SCAN_INTERVAL, default=get_scan_interval(hw_model)
                        ): int,
                        vol.Required(
                            CONFIG_FLOW_CONFIG_TYPE, default=False
                        ): bool,
                        
                }
                )

        else:
            leds={}
            for dev in self.hass.data[DOMAIN]:
                led = self.hass.data[DOMAIN][dev]
                if type(led).__name__=="ReefLedCoordinator" or type(led).__name__=="ReefLedG2Coordinator":
                    leds[vol.Required('LED: '+led.serial+' ('+dev+')')]=bool
            options_schema=vol.Schema(leds)
            
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                options_schema, self._config_entry.options
            ),
            errors=errors,
        )


        

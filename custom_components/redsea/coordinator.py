import logging
import asyncio
import async_timeout

from datetime import  timedelta

from homeassistant.core import HomeAssistant

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)

from typing import Any

from .const import (
    DOMAIN,
    CONFIG_FLOW_IP_ADDRESS,
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_SCAN_INTERVAL,
    SCAN_INTERVAL,
    MODEL_NAME,
    MODEL_ID,
    HW_VERSION,
    SW_VERSION,
    DEVICE_MANUFACTURER,
    VIRTUAL_LED,
    LINKED_LED,
)

from .reefbeat import ReefBeatAPI,ReefLedAPI, ReefMatAPI, ReefDoseAPI, ReefATOAPI

_LOGGER = logging.getLogger(__name__)

class ReefBeatCoordinator(DataUpdateCoordinator[dict[str,Any]]):

    def __init__(
            self,
            hass: HomeAssistant,
            entry,
    ) -> None:
        """Initialize coordinator."""
        if CONFIG_FLOW_SCAN_INTERVAL in entry.data:
            scan_interval=entry.data[CONFIG_FLOW_SCAN_INTERVAL]
        else:
            scan_interval=SCAN_INTERVAL
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=scan_interval))
        self._hass=hass
        self._ip = entry.data[CONFIG_FLOW_IP_ADDRESS]
        self._hw = entry.data[CONFIG_FLOW_HW_MODEL]
        self._title = entry.title
        self.my_api = ReefBeatAPI(self._ip)
        _LOGGER.info("%s scan interval set to %d"%(self._title,scan_interval))
        self._boot=True
        

    async def _async_update_data(self):
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(10):
                return await self.my_api.fetch_data()
        except Exception as e:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            _LOGGER.error("Error communicating with API")
            _LOGGER.error(e)

    async def update(self):
        await self.my_api.fetch_data() 
        
    async def _async_setup(self) -> None:
        """Do initialization logic."""
        _LOGGER.debug("async_setup...")
        if(self._boot==True):
            self._boot=False
            return await self.my_api.get_initial_data()
        return None

    async def async_request_refresh(self):
        #wait fore device to refresh state
        await asyncio.sleep(3)
        return await super().async_request_refresh()
    
    
    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={
                (DOMAIN, self.model_id)
            },
            name=self.title,
            manufacturer=DEVICE_MANUFACTURER,
            model=self.model,
            model_id=self.model_id,
            hw_version=self.hw_version,
            sw_version=self.sw_version,
        )

    def push_values(self):
        self.my_api.push_values()
        
    def get_data(self,name):
        return self.my_api.get_data(name)

    def set_data(self,name,value):
        self.my_api.set_data(name,value)
    
    def data_exist(self,name):
        if name in self.my_api.data:
            return True
        return False

    def press(self,action):
        self.my_api.press(action)
    
    @property
    def title(self):
        return self._title

    @property
    def serial(self):
        return self._title
    
    @property
    def model(self):
        return self.my_api.get_data("$.sources[?(@.name=='/device-info')].data.hw_model")

    @property
    def model_id(self):
        return self.my_api.get_data("$.sources[?(@.name=='/device-info')].data.hwid")

    @property
    def hw_version(self):
        return self.my_api.get_data("$.sources[?(@.name=='/device-info')].data.hw_revision")

    @property
    def sw_version(self):
        return self.my_api.get_data("$.sources[?(@.name=='/firmware')].data.version")

    @property
    def detected_id(self):
        return self._ip+' '+self._hw+' '+self._title


    
class ReefLedCoordinator(ReefBeatCoordinator):

    def __init__(
            self,
            hass: HomeAssistant,
            entry
    ) -> None:
        """Initialize coordinator."""
        super().__init__(hass,entry)
        self.my_api = ReefLedAPI(self._ip)
        
    def force_status_update(self,state=False):
        self.my_api.force_status_update(state)
        
    def daily_prog(self):
        return self.my_api.daily_prog

################################################################################
# VIRTUAL LED
class ReefVirtualLedCoordinator(ReefLedCoordinator):

    def __init__(
            self,
            hass: HomeAssistant,
            entry
    ) -> None:
        """Initialize coordinator."""
        super().__init__(hass, entry)
        # only led linked to this virtual device
        self._linked = []
        _LOGGER.info("Devices linked to %s: "%(self._title))
        if LINKED_LED in entry.data:
            for led in entry.data[LINKED_LED]:
                name=led.split(' ')[1]
                uuid=led.split('(')[1][:-1]
                self._linked+=[self._hass.data[DOMAIN][uuid]]
                _LOGGER.info(" - %s"%(name))

    def force_status_update(self,state=False):
        pass
    
    def get_data(self,name):
        if len(self._linked)>0:
            data=self._linked[0].get_data(name)
            match type(data).__name__:
                case 'bool':
                    return self.get_data_bool(name)
                case 'int':
                    return self.get_data_int(name)
                case 'float':
                    return self.get_data_float(name)
                case _:
                    pass #_LOGGER.warning("Not implemented %s: %s"%(name,data))

    def get_data_bool(self,name):
        for led in self._linked:
            if led.get_data(name):
                return True
        return False

    def get_data_int(self,name):
        res=0
        count=0
        for led in self._linked:
            res+=led.get_data(name)
            count +=1
        return int(res/count)

    def get_data_float(self,name):
        res=0
        count=0
        for led in self._linked:
            _LOGGER.debug("coordinator.get_data_float %s"%name)
            res+=led.get_data(name)
            count +=1
        return res/count

    def set_data(self,name,value):
        for led in self._linked:
            led.set_data(name,value)

    def push_values(self):
        for led in self._linked:
            led.push_values()
        
        
    def data_exist(self,name):
        for led in self._linked:
            if led.data_exist(name):
                _LOGGER.debug("data_exists: %s"%name)
                return True
        _LOGGER.debug("not data_exists: %s"%name)            
        return False

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={
                (DOMAIN, self.title)
            },
            name=self.title,
            manufacturer=DEVICE_MANUFACTURER,
            model=VIRTUAL_LED,
        )

################################################################################
## REEFMAT
class ReefMatCoordinator(ReefBeatCoordinator):

    def __init__(
            self,
            hass: HomeAssistant,
            entry
    ) -> None:
        """Initialize coordinator."""
        super().__init__(hass, entry)
        self.my_api = ReefMatAPI(self._ip)

        
################################################################################
# REEFDOSE
class ReefDoseCoordinator(ReefBeatCoordinator):

    def __init__(
            self,
            hass: HomeAssistant,
            entry,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(hass,entry)
        self.heads_nb=int(entry.data[CONFIG_FLOW_HW_MODEL][-1])
        self.my_api = ReefDoseAPI(self._ip,self.heads_nb)

    def press(self,action,head):
        self.my_api.press(action,head)

    def push_values(self,head):
        self.my_api.push_values(head)
        
    @property
    def hw_version(self):
        return None

        
################################################################################
# REEFATO+
class ReefATOCoordinator(ReefBeatCoordinator):

    def __init__(
            self,
            hass: HomeAssistant,
            entry
    ) -> None:
        """Initialize coordinator."""
        super().__init__(hass,entry)
        self.my_api = ReefATOAPI(self._ip)
        

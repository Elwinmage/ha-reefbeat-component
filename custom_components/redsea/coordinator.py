import logging
import asyncio
import async_timeout

from datetime import  timedelta, datetime

from homeassistant.core import HomeAssistant

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)

from typing import Any

from .const import (
    DOMAIN,
    DEFAULT_TIMEOUT,
    CONFIG_FLOW_IP_ADDRESS,
    CONFIG_FLOW_HW_MODEL,
    CONFIG_FLOW_SCAN_INTERVAL,
    CONFIG_FLOW_INTENSITY_COMPENSATION,
    CONFIG_FLOW_CONFIG_TYPE,
    SCAN_INTERVAL,
    MODEL_NAME,
    MODEL_ID,
    HW_VERSION,
    SW_VERSION,
    DEVICE_MANUFACTURER,
    VIRTUAL_LED,
    LINKED_LED,
    LED_MOON_INTERNAL_NAME,
    LED_WHITE_INTERNAL_NAME,
    LED_BLUE_INTERNAL_NAME,
    LED_KELVIN_INTERNAL_NAME,
    LED_INTENSITY_INTERNAL_NAME,
)

from .reefbeat import ReefBeatAPI,ReefLedAPI, ReefMatAPI, ReefDoseAPI, ReefATOAPI, ReefRunAPI, ReefWaveAPI

_LOGGER = logging.getLogger(__name__)

class ReefBeatCoordinator(DataUpdateCoordinator[dict[str,Any]]):

    def __init__(
            self,
            hass: HomeAssistant,
            entry,
    ) -> None:
        """Initialize coordinator."""
        self._entry = entry
        if CONFIG_FLOW_SCAN_INTERVAL in entry.data:
            scan_interval=entry.data[CONFIG_FLOW_SCAN_INTERVAL]
        else:
            scan_interval=SCAN_INTERVAL
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=scan_interval))
        self._hass=hass
        self._ip = entry.data[CONFIG_FLOW_IP_ADDRESS]
        self._hw = entry.data[CONFIG_FLOW_HW_MODEL]
        self._title = entry.title
        if CONFIG_FLOW_CONFIG_TYPE not in entry.data:
            self._live_config_update= False
        else:
            self._live_config_update = entry.data[CONFIG_FLOW_CONFIG_TYPE]
        self.my_api = ReefBeatAPI(self._ip,self._live_config_update)
        _LOGGER.info("%s scan interval set to %d"%(self._title,scan_interval))
        _LOGGER.info("%s live configuration update %s"%(self._title,self._live_config_update))
        self._boot=True
        

    async def _async_update_data(self):
        try:
            async with async_timeout.timeout(DEFAULT_TIMEOUT*2):
                return await self.my_api.fetch_data()
        except Exception as e:
            _LOGGER.error("Error communicating with API: %s"%self._title)
            _LOGGER.error(e)

    async def update(self):
        await self.my_api.fetch_data() 

    async def fetch_config(self,config_path=None):
        await self.my_api.fetch_config(config_path)
        self.async_update_listeners()
        
    async def _async_setup(self) -> None:
        """Do initialization logic."""
        _LOGGER.debug("async_setup...")
        if(self._boot==True):
            self._boot=False
            return await self.my_api.get_initial_data()
        return None

    async def async_request_refresh(self):
        #wait fore device to refresh state
        await asyncio.sleep(2)
        return await super().async_request_refresh()
    
    async def async_quick_request_refresh(self,source):
        #wait fore device to refresh state
        await asyncio.sleep(2)
        self.my_api.quick_refresh=source
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

    async def push_values(self,source:str='/configuration',method:str='put'):
        await self.my_api.push_values(source,method)
        
    def get_data(self,name, is_None_possible=False):
        return self.my_api.get_data(name,is_None_possible)
    
    def set_data(self,name,value):
        self.my_api.set_data(name,value)
    
    def data_exist(self,name):
        if name in self.my_api.data:
            return True
        return False

    async def press(self,action):
        await self.my_api.press(action)
    
    @property
    def title(self):
        return self._title

    @property
    def serial(self):
        return self._title
    
    @property
    def model(self):
        return self.get_data("$.sources[?(@.name=='/device-info')].data.hw_model")

    @property
    def model_id(self):
        return self.get_data("$.sources[?(@.name=='/device-info')].data.hwid")

    @property
    def hw_version(self):
        hw_vers=self.get_data("$.sources[?(@.name=='/device-info')].data.hw_revision",True)
        if hw_vers==None:
            hw_vers=self.get_data("$.sources[?(@.name=='/firmware')].data.chip_version",True)
        return hw_vers

    @property
    def sw_version(self):
        return self.get_data("$.sources[?(@.name=='/firmware')].data.version")

    @property
    def detected_id(self):
        return self._ip+' '+self._hw+' '+self._title

################################################################################
# LED
################################################################################
class ReefLedCoordinator(ReefBeatCoordinator):

    def __init__(
            self,
            hass: HomeAssistant,
            entry
    ) -> None:
        """Initialize coordinator."""
        super().__init__(hass,entry)
        intensity_compensation=False
        if CONFIG_FLOW_INTENSITY_COMPENSATION in entry.data:
            intensity_compensation=entry.data[CONFIG_FLOW_INTENSITY_COMPENSATION]
        self.my_api = ReefLedAPI(self._ip,self._live_config_update,self._hw,intensity_compensation)
        _LOGGER.info("%s intensity compensation :%s"%(self._title,intensity_compensation))

    def force_status_update(self,state=False):
        self.my_api.force_status_update(state)

    def set_data(self,name,value):
        super().set_data(name,value)
        if name == LED_WHITE_INTERNAL_NAME or name == LED_BLUE_INTERNAL_NAME :
            self.my_api.update_light_wb()
        elif name == LED_KELVIN_INTERNAL_NAME or name == LED_INTENSITY_INTERNAL_NAME:
            if name == LED_KELVIN_INTERNAL_NAME :
                self.my_api.data['local']['manual_trick']['kelvin']=value
            else:
                self.my_api.data['local']['manual_trick']['intensity']=value
            self.my_api.update_light_ki()

    
            
    def daily_prog(self):
        return self.my_api.daily_prog

    async def delete(self,source):
        await self.my_api.delete(source)

    async def post_specific(self,source):
        await self.my_api.post_specific(source)


################################################################################
# LED G2
class ReefLedG2Coordinator(ReefLedCoordinator):

    def __init__(
            self,
            hass: HomeAssistant,
            entry
    ) -> None:
        """Initialize coordinator."""
        super().__init__(hass,entry)

    def set_data(self,name,value):
        self.my_api.set_data(name,value)
        
################################################################################
# VIRTUAL LED
class ReefVirtualLedCoordinator(ReefLedCoordinator):

    def __init__(
            self,
            hass: HomeAssistant,
            entry
    ) -> None:
        """Initialize coordinator."""
        # only led linked to this virtual device
        self._linked = []
        if LINKED_LED in entry.data:
            for led in entry.data[LINKED_LED]:
                name=led.split(' ')[1]
                uuid=led.split('(')[1][:-1]
                self._linked+=[hass.data[DOMAIN][uuid]]
                _LOGGER.info(" - %s"%(name))
        super().__init__(hass, entry)
        if len(self._linked) == 0:
            _LOGGER.error("%s has no led linked, please configure them"%self._title)
        if len(self._linked) == 1:
            _LOGGER.error("%s has only one led linked (%s), please configure one more"%(self._title,self._linked[0]._title))
        _LOGGER.info("Devices linked to %s: "%(self._title))

            
    def force_status_update(self,state=False):
        pass
    
    async def _async_update_data(self):
        pass
        #for led in self._linked:
    #        await led._async_update_data()
    
    def get_data(self,name,is_None_possible=False):
        if len(self._linked)>0:
            data=self._linked[0].get_data(name,is_None_possible)
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
            if not led.get_data(name):
                return False
        return True

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

    async def push_values(self,source,method='post'):
        for led in self._linked:
            await led.push_values(source,method)
        
    def data_exist(self,name):
        for led in self._linked:
            if led.data_exist(name):
                _LOGGER.debug("data_exists: %s"%name)
                return True
        _LOGGER.debug("not data_exists: %s"%name)            
        return False

    async def delete(self,source):
        for led in self._linked:
            await led.delete(source)

    async def post_specific(self,source):
        for led in self._linked:
            await led.post_specific(source)

    async def async_request_refresh(self):
        for led in self._linked:
            await led.async_request_refresh()

    async def async_quick_request_refresh(self,source):
        #wait fore device to refresh state
        #        await asyncio.sleep(2)
        for led in self._linked:
            #led.my_api.quick_refresh=source
            await led.async_quick_request_refresh(source)

            
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
        self.my_api = ReefMatAPI(self._ip,self._live_config_update)

    async def new_roll(self):
        await self.my_api.new_roll()
            
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
        self.my_api = ReefDoseAPI(self._ip,self._live_config_update,self.heads_nb)

    async def press(self,action,head):
        await self.my_api.press(action,head)

    async  def push_values(self,head):
        await self.my_api.push_values(head)
        
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
        self.my_api = ReefATOAPI(self._ip,self._live_config_update)
        
################################################################################
# REEFRUN
# TODO : Implement preview
#  labels: enhancement, rsrun
class ReefRunCoordinator(ReefBeatCoordinator):

    def __init__(
            self,
            hass: HomeAssistant,
            entry
    ) -> None:
        """Initialize coordinator."""
        super().__init__(hass,entry)
        self.my_api = ReefRunAPI(self._ip,self._live_config_update)

    async def set_pump_intensity(self,pump:int,intensity:int):
        _LOGGER.debug("coordinator.ReefRunCoordinator.set_pump_intensity")
        await self.my_api.fetch_config()
        schedule=self.my_api.get_data("$.sources[?(@.name=='/pump/settings')].data.pump_"+str(pump)+".schedule")
        _LOGGER.debug(schedule)
        now= datetime.now()
        now_minutes=now.hour*60+now.minute
        to_update=schedule[0]
        for prog in schedule[1:]:
            if int(prog['st']) < now_minutes:
                to_update=prog
            else:
                break
        to_update['ti']=intensity
        _LOGGER.debug(schedule)
    
    async def push_values(self,source:str=None,method:str=None,pump:int=None):
        await self.my_api.push_values(source,method,pump)

################################################################################
# REEFWAVE
class ReefWaveCoordinator(ReefBeatCoordinator):

    def __init__(
            self,
            hass: HomeAssistant,
            entry
    ) -> None:
        """Initialize coordinator."""
        super().__init__(hass,entry)
        self.my_api = ReefWaveAPI(self._ip,self._live_config_update)
        

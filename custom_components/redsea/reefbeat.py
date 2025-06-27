import logging
import json
import asyncio
import httpx
import datetime

from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    DO_NOT_REFRESH_TIME,
    FAN_INTERNAL_NAME,
    TEMPERATURE_INTERNAL_NAME,
    WHITE_INTERNAL_NAME,
    BLUE_INTERNAL_NAME,
    MOON_INTERNAL_NAME,
    STATUS_INTERNAL_NAME,
    IP_INTERNAL_NAME,
    DAILY_PROG_INTERNAL_NAME,
    CONVERSION_COEF,
    MODEL_NAME,
    MODEL_ID,
    HW_VERSION,
    SW_VERSION,
    MAT_SENSORS_INTERNAL_NAME,
    MAT_BINARY_SENSORS_INTERNAL_NAME,
    DOSE_SENSORS_INTERNAL_NAME,
    DOSE_SENSORS_MISSED_INTERNAL_NAME,
)

_LOGGER = logging.getLogger(__name__)

#API
# /
# /dashboard
# /acclimation
# /device-info
# /firmware
# /moonphase
# /current
# /timer
# /mode : {"mode": "auto|manual|timer"}
# /auto
# /auto/[1-7]
# /preset_name
# /preset_name/[1-7]
# /cloud
# /clouds/[1-7] (intensity: Low,Medium,High)
################################################################################
# Reef beat API
class ReefBeatAPI():
    """ Access to Reefled informations and commands """
    def __init__(self,ip) -> None:
        self._base_url = "http://"+ip
        _LOGGER.debug("API set for %s"%ip)
        self.data={}
        self.last_update_success=None
      
    async def get_initial_data(self):
        """ Get inital datas and device information async """
        _LOGGER.debug('Reefbeat.get_initial_data')
        await self._fetch_infos()
        await self.fetch_data()
        _LOGGER.debug('OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO')
        _LOGGER.debug(self.data)
        _LOGGER.debug('OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO')
        return self.data

    async def fetch_data(self):
        """ Get Led information for light, program, fan, temeprature... """
        # Only if last request where less that 2s """
        if self.last_update_success:
            up = datetime.datetime.now() - self.last_update_success
            last_update  = up.seconds
        else:
            last_update = DO_NOT_REFRESH_TIME +1 
        if last_update > DO_NOT_REFRESH_TIME:
            await self.fetch_device_data()
        else:
            _LOGGER.debug("No refresh, last data retrieved less than 2s")
    
    async def _fetch_infos(self):
        """ Get device information """
        _LOGGER.debug("fecth_info: %s",self._base_url+"/device-info")
        # Device
        async with httpx.AsyncClient(verify=False) as client:
            r = await client.get(self._base_url+"/device-info",timeout=2)
            f = await client.get(self._base_url+"/firmware",timeout=2)
            if r.status_code == 200:
                response=r.json()
                _LOGGER.debug("Get device infos: %s"%response)
                try:
                    self.data[MODEL_NAME]=response[MODEL_NAME]
                    self.data[MODEL_ID]=response[MODEL_ID]
                    if HW_VERSION in response:
                        self.data[HW_VERSION]=response[HW_VERSION]
                    else:
                        self.data[HW_VERSION]=""
                except Exception as e:
                    _LOGGER.error("Getting info %s"%e)
            # Firmware
            if f.status_code == 200:
                response=f.json()
                _LOGGER.debug("Get firmware infos: %s"%response)
                try:
                    self.data[SW_VERSION]=response[SW_VERSION]
                except Exception as e:
                    _LOGGER.error("Getting info %s"%e)

    async def update(self) :       
        """ Update reeefled datas """
        await self.fetch_data()
        return self.data
    
    async def async_first_refresh(self):
        async with httpx.AsyncClient(verify=False) as client:
            r = await client.get(self._base_url+'/',timeout=2)
            if r.status_code == 200:
                response=r.json()
                self.data[IP_INTERNAL_NAME]=response['wifi_ip']
        
    async def async_add_listener(self,callback,context):
        _LOGGER.debug("async_add_listener")
        pass

    async def async_send_new_values(self):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None,self.push_values)
        
################################################################################
#Reef LED
class ReefLedAPI(ReefBeatAPI):
    """ Access to Reefled informations and commands """
    def __init__(self,ip) -> None:
        super().__init__(ip)
        self.data[STATUS_INTERNAL_NAME]=False
        self.data[FAN_INTERNAL_NAME]=0
        self.data[DAILY_PROG_INTERNAL_NAME]=True
        self.programs={}
        
    async def fetch_device_data(self):
        await self._fetch_led_status()
        await self._fetch_program()
        
    async def _fetch_program(self):
        """ Get week program with clouds """
        #get week
        async with httpx.AsyncClient(verify=False) as client:
            r = await client.get(self._base_url+"/preset_name",timeout=2)
            if r.status_code==200:
                response=r.json()
                _LOGGER.debug("Get program data:%s"%response)
 #               try:
                self.data[DAILY_PROG_INTERNAL_NAME] =  True
                old_prog_name=None
                for i in range(1,8):
                    prog_id=response[i-1]['day']
                    prog_name=response[i-1]['name']
                    if i > 1 and prog_name != old_prog_name:
                            self.data[DAILY_PROG_INTERNAL_NAME] = False
                    old_prog_name=prog_name        
                    clouds_data={}
                    if prog_name not in self.programs:
                        r = await client.get(self._base_url+"/auto/"+str(prog_id),timeout=2)
                        if r.status_code==200:
                            prog_data=r.json()
                            self.programs[prog_name]=prog_data
                    else:
                        prog_data=self.programs[prog_name]
                    # Get clouds
                    _LOGGER.info(self._base_url+"/clouds/"+str(prog_id))
                    c = await client.get(self._base_url+"/clouds/"+str(prog_id),timeout=2)
                    if c.status_code==200:
                        clouds_data=c.json()
                    self.data['auto_'+str(prog_id)]={'name':prog_name,'data':prog_data,'clouds':clouds_data}
#                except Exception as e:
#                    _LOGGER.error("Can not get value: %s because %s"%(response,e))
                
    async def _fetch_led_status(self):
        """ Get led information data """
        async with httpx.AsyncClient(verify=False) as client:
            r = await client.get(self._base_url+"/manual",timeout=2)
        if r.status_code == 200:
            response=r.json()
            _LOGGER.debug("Get data: %s"%response)
            try:
                self.data[WHITE_INTERNAL_NAME]=int(response['white']/CONVERSION_COEF)
                self.data[BLUE_INTERNAL_NAME]=int(response['blue']/CONVERSION_COEF)
                self.data[MOON_INTERNAL_NAME]=int(response['moon']/CONVERSION_COEF)
                self.data[FAN_INTERNAL_NAME]=response['fan']
                self.data[TEMPERATURE_INTERNAL_NAME]=response['temperature']
                if ( self.data[WHITE_INTERNAL_NAME]>0 or
                     self.data[BLUE_INTERNAL_NAME]>0 or
                     self.data[MOON_INTERNAL_NAME]>0 ):
                    self.data[STATUS_INTERNAL_NAME]= True
                else:
                    self.data[STATUS_INTERNAL_NAME]= False
                ##
                self.last_update_success=datetime.datetime.now()
                ##
            except Exception as e:
                _LOGGER.error("Getting LED values %s"%e)
    
    def push_values(self):
        payload={"white": self.data[WHITE_INTERNAL_NAME]*CONVERSION_COEF, "blue":self.data[BLUE_INTERNAL_NAME]*CONVERSION_COEF,"moon": self.data[MOON_INTERNAL_NAME]*CONVERSION_COEF}
        r = httpx.post(self._base_url+'/manual', json = payload,verify=False)

        
################################################################################
#ReefMat
class ReefMatAPI(ReefBeatAPI):
    """ Access to Reefled informations and commands """
    def __init__(self,ip) -> None:
        super().__init__(ip)

    # TODO a remonter dans reefbeatapi
    async def fetch_device_data(self):
        async with httpx.AsyncClient(verify=False) as client:
            r = await client.get(self._base_url+"/dashboard",timeout=2)
        if r.status_code == 200:
            response=r.json()
            _LOGGER.debug("Get data: %s"%response)
            try:
                for sensor_name in MAT_SENSORS_INTERNAL_NAME:
                    self.data[sensor_name]=float(response[sensor_name])
                    _LOGGER.debug("%s: %f"%(sensor_name,self.data[sensor_name]))
                for sensor_name in MAT_BINARY_SENSORS_INTERNAL_NAME:
                    self.data[sensor_name]=bool(response[sensor_name])
                    _LOGGER.debug("%s: %s"%(sensor_name,self.data[sensor_name]))
                ##
                self.last_update_success=datetime.datetime.now()
                ##
            except Exception as e:
                _LOGGER.error("Getting MAT values %s"%e)
            
    def push_values(self):
        pass

################################################################################
#ReefDose
class ReefDoseAPI(ReefBeatAPI):
    """ Access to Reefled informations and commands """
    def __init__(self,ip,heads_nb) -> None:
        super().__init__(ip)
        self._heads_nb=heads_nb

        # TODO a remonter dans reefbeatapi
    async def fetch_device_data(self):
        async with httpx.AsyncClient(verify=False) as client:
            r = await client.get(self._base_url+"/dashboard",timeout=2)
        if r.status_code == 200:
            response=r.json()
            _LOGGER.debug("Get data: %s"%response)
            try:
                for head in range (1,self._heads_nb+1):
                    for sensor_name in DOSE_SENSORS_INTERNAL_NAME:
                        fname=str(head)+'_'+sensor_name
                        self.data[fname]=response['heads'][str(head)][sensor_name]
                        _LOGGER.debug("Updating %s: %s"%(fname,self.data[fname]))
                ##
                self.last_update_success=datetime.datetime.now()
                ##
            except Exception as e:
                _LOGGER.error("Getting Dose values %s"%e)

            
    def push_values(self):
        pass
    

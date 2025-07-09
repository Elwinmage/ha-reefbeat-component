import logging
import asyncio
import httpx

import json
from jsonpath_ng import jsonpath
from jsonpath_ng.ext import parse

from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    DEFAULT_TIMEOUT,
    DO_NOT_REFRESH_TIME,
    LED_WHITE_INTERNAL_NAME,
    LED_BLUE_INTERNAL_NAME,
    LED_MOON_INTERNAL_NAME,
    DAILY_PROG_INTERNAL_NAME,
    MODEL_NAME,
    MODEL_ID,
    HW_VERSION,
    SW_VERSION,
    MAT_MIN_ROLL_DIAMETER,
    MAT_MAX_ROLL_DIAMETERS,
    MAT_ROLL_THICKNESS,
    MAT_STARTED_ROLL_DIAMETER_INTERNAL_NAME,
    MAT_AUTO_ADVANCE_INTERNAL_NAME,
    MAT_CUSTOM_ADVANCE_VALUE_INTERNAL_NAME,
    MAT_MODEL_INTERNAL_NAME,
    MAT_POSITION_INTERNAL_NAME,
    ATO_AUTO_FILL_INTERNAL_NAME,
)

_LOGGER = logging.getLogger(__name__)

################################################################################
# Reef beat API
class ReefBeatAPI():
    """ Access to Reefled informations and commands """
    def __init__(self,ip) -> None:
        self._base_url = "http://"+ip
        self.data={"sources": [{"name":"/","get_once":True,"data":""},
                               {"name":"/device-info","get_once":True,"data":""},
                               {"name":"/firmware","get_once":True,"data":""},
                               {"name":"/dashboard","get_once":False,"data":""}]}
        self.last_update_success=None


    async def _call_url(self,client,source):
        r = await client.get(self._base_url+source.value['name'],timeout=DEFAULT_TIMEOUT)
        if r.status_code == 200:
            response=r.json()
            query=parse("$.sources[?(@.name=='"+source.value["name"]+"')]")
            s=query.find(self.data)
            s[0].value['data']=response
        else:
            _LOGGER.error("Can not get data: %s"%source)
            
    async def get_initial_data(self):
        """ Get inital datas and device information async """
        _LOGGER.debug('Reefbeat.get_initial_data')
        query=parse("$.sources[?(@.get_once==true)]")
        sources=query.find(self.data)
        async with httpx.AsyncClient(verify=False) as client:  
            await asyncio.gather(*[self._call_url(client,sources[source]) for source in range(0,len(sources))])
        await self.fetch_data()
        _LOGGER.debug('OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO')
        _LOGGER.debug(self.data)
        _LOGGER.debug('OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO')
        return self.data

    async def fetch_data(self):
        """ Get device data """
        query=parse("$.sources[?(@.get_once==false)]")
        sources=query.find(self.data)
        async with httpx.AsyncClient(verify=False) as client:  
            await asyncio.gather(*[self._call_url(client,sources[source]) for source in range(0,len(sources))])

    def press(self,action):
        payload=''
        _LOGGER.debug("Sending: %s"%action)
        r = httpx.post(self._base_url+'/'+action, json = payload,verify=False,timeout=DEFAULT_TIMEOUT)
        
    def get_data(self,data_name):
        """ get device data named data_name """
        query=parse(data_name)
        res=query.find(self.data)
        if(len(res)==0):
            _LOGGER.error("reefbeat.get_data('%s')"%data_name)
        return res[0].value

    def set_data(self,data_name,value):
        """ set deivce data named data_name to value"""
        query=parse(data_name)
        try:
            res=query.update(self.data,value)
        except:
            _LOGGER.error("reefbeat.set_data('%s')"%data_name)
            
        
################################################################################
#Reef LED
class ReefLedAPI(ReefBeatAPI):
    """ Access to Reefled informations and commands """
    def __init__(self,ip) -> None:
        super().__init__(ip)
        self.data['sources'].insert(len(self.data['sources']),{"name":"/preset_name","get_once": False,"data":""})
        self.data['sources'].insert(len(self.data['sources']),{"name":"/manual","get_once": False,"data":""})
        for day in range(1,8):
            self.data['sources'].insert(len(self.data['sources']),{"name":"/auto/"+str(day),"get_once": False,"data":""})
            self.data['sources'].insert(len(self.data['sources']),{"name":"/clouds/"+str(day),"get_once": False,"data":""})
        self.data['local']={"status":False}

    async def fetch_data(self):
        await super().fetch_data()
        self.force_status_update()
        
    def push_values(self):
        payload={"white": self.get_data(LED_WHITE_INTERNAL_NAME), "blue":self.get_data(LED_BLUE_INTERNAL_NAME),"moon": self.get_data(LED_MOON_INTERNAL_NAME)}
        try:
            r = httpx.post(self._base_url+'/manual', json = payload,verify=False,timeout=DEFAULT_TIMEOUT)
        except:
            _LOGGER.warning("Coul not send command, you must retry")
            asyncio.sleep(1)
            r = httpx.post(self._base_url+'/manual', json = payload,verify=False,timeout=DEFAULT_TIMEOUT)

    def force_status_update(self,state=False):
        if state:
            self.data['local']['status']=True
        else:
            if self.get_data(LED_WHITE_INTERNAL_NAME) > 0 or self.get_data(LED_BLUE_INTERNAL_NAME) > 0 or self.get_data(LED_MOON_INTERNAL_NAME) > 0:
                self.data['local']['status']=True
            else:
                self.data['local']['status']=False

################################################################################
#ReefMat
class ReefMatAPI(ReefBeatAPI):
    """ Access to Reefmat informations and commands """
    def __init__(self,ip) -> None:
        super().__init__(ip)
        self.data['sources'].insert(len(self.data['sources']),{"name":"/configuration","get_once": False,"data":""})
        self.data['local']={"started_roll_diameter":MAT_MIN_ROLL_DIAMETER}
        
    def push_values(self):
        payload={
            'auto_advance': self.get_data(MAT_AUTO_ADVANCE_INTERNAL_NAME),
            'custom_advance_value': self.get_data(MAT_CUSTOM_ADVANCE_VALUE_INTERNAL_NAME),
            'model': self.get_data(MAT_MODEL_INTERNAL_NAME),
            'position': self.get_data(MAT_POSITION_INTERNAL_NAME)}
        r = httpx.put(self._base_url+'/configuration', json = payload,verify=False,timeout=DEFAULT_TIMEOUT)

    def new_roll(self):
        model = self.get_data("$.sources[?(@.name=='/configuration')].data.model")
        diameter = self.get_data(MAT_STARTED_ROLL_DIAMETER_INTERNAL_NAME)
        
        # New roll
        if diameter==MAT_MIN_ROLL_DIAMETER:
            name="New Roll"
            is_partial = False
            diameter=MAT_MAX_ROLL_DIAMETERS[model]
        # Started Roll
        else :
            name ="Started Roll"
            is_partial = True
        #new_length = math.pi/2*(MAT_INNER_DIAMETER+diameter)*((diameter-MAT_INNER_DIAMETER)/(2*MAT_TICKNESS))
        payload={'external_diameter':diameter,'name':name,'thickness':MAT_ROLL_THICKNESS,'is_partial':is_partial}
        _LOGGER.info("New roll: %s"%payload)
        r = httpx.post(self._base_url+'/new-roll', json = payload,verify=False,timeout=DEFAULT_TIMEOUT)
        _LOGGER.debug(r.status_code)
        _LOGGER.debug(r.text)

        
################################################################################
#ReefDose
class ReefDoseAPI(ReefBeatAPI):
    """ Access to ReefDose informations and commands """
    def __init__(self,ip,heads_nb) -> None:
        super().__init__(ip)
        self._heads_nb=heads_nb
        if self._heads_nb == 2:
            self.data['local']={"head":{"1":"","2":""}}
        elif self._heads_nb == 4:
            self.data['local']={"head":{"1":"","2":"","3":"","4":""}}
        else:
            _LOGGER.error("redsea.reefbeat.ReefDoseAPI.__init__() unkown head number: %d"%self._heads_nb)
        for head in range(1,self._heads_nb+1):
            self.data['sources'].insert(len(self.data['sources']),{"name":"/head/"+str(head)+"/settings","get_once": False,"data":""})
            self.data['local']["head"][str(head)]={"manual_dose":0}
            
    def press(self,action,head):
        manual_dose=self.get_data("$.local.head."+str(head)+".manual_dose")
        payload={'manual_dose_scheduled': True,'volume': manual_dose}
        r = httpx.post(self._base_url+'/head/'+str(head)+'/'+action, json = payload,verify=False,timeout=DEFAULT_TIMEOUT)
        
    def push_values(self,head):
        payload=self.get_data("$.sources[?(@.name=='/head/"+str(head)+"/settings')].data")
        try:
            r = httpx.put(self._base_url+'/head/'+str(head)+'/settings', json = payload,verify=False,timeout=DEFAULT_TIMEOUT)
        except Exception as e:
            _LOGGER.error("readsea.reefbeat.ReefDoseAPI.push_value failed")
            _LOGGER.error(e)
    
################################################################################
# ReefATO+
class ReefATOAPI(ReefBeatAPI):
    """ Access to Reefled informations and commands """
    def __init__(self,ip) -> None:
        super().__init__(ip)
        self.data['sources'].insert(len(self.data['sources']),{"name":"/configuration","get_once": False,"data":""})

    def push_values(self):
        payload={'auto_fill': self.get_data(ATO_AUTO_FILL_INTERNAL_NAME)}
        r = httpx.put(self._base_url+'/configuration', json = payload,verify=False,timeout=DEFAULT_TIMEOUT)

################################################################################
# ReefRun
class ReefRunAPI(ReefBeatAPI):
    """ Access to Reefled informations and commands """
    def __init__(self,ip) -> None:
        super().__init__(ip)
        self.data['sources'].insert(len(self.data['sources']),{"name":"/pump/settings","get_once": False,"data":""})

    def push_values(self):
        pass

    

import logging
import asyncio
import httpx
import time
import numpy as np
import json
from jsonpath_ng import jsonpath
from jsonpath_ng.ext import parse

from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    DEFAULT_TIMEOUT,
    DO_NOT_REFRESH_TIME,
    HW_G1_LED_IDS,
    LED_WHITE_INTERNAL_NAME,
    LED_BLUE_INTERNAL_NAME,
    LED_MOON_INTERNAL_NAME,
    LED_MOON_DAY_INTERNAL_NAME,
    LED_MANUAL_DURATION_INTERNAL_NAME,
    LED_KELVIN_INTERNAL_NAME,
    LED_INTENSITY_INTERNAL_NAME,
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
    HTTP_MAX_RETRY,
    HTTP_DELAY_BETWEEN_RETRY,
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
        self.quick_refresh=None


    async def _http_get(self,client,source):
        r = await client.get(self._base_url+source.value['name'],timeout=DEFAULT_TIMEOUT)
        if r.status_code == 200:
            response=r.json()
            query=parse("$.sources[?(@.name=='"+source.value["name"]+"')]")
            s=query.find(self.data)
            s[0].value['data']=response
            return True
        else:
            _LOGGER.error("Can not get data: %s from %s"%(source,self.ip))
            return False

    async def _call_url(self,client,source):
        status_ok=False
        error_count=0
        while status_ok == False and error_count <= HTTP_MAX_RETRY:
            try:
                status_ok=await self._http_get(client,source)
            except Exception as e:
                error_count += 1
                _LOGGER.debug("Can not get data: %s, retry nb %d/%d"%(source.value['name'],error_count,HTTP_MAX_RETRY))
            if not status_ok:
                await asyncio.sleep(HTTP_DELAY_BETWEEN_RETRY)
        if not status_ok:
            _LOGGER.error("Can not get data from %s/%s after %s try"%(self.ip,source.value['name'],HTTP_MAX_RETRY))
            
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
        if self.quick_refresh!= None:
            query=parse("$.sources[?(@.name=='"+self.quick_refresh+"')]")
            sources=query.find(self.data)
            self.quick_refresh=None
        else:
            query=parse("$.sources[?(@.get_once==false)]")
            sources=query.find(self.data)
        async with httpx.AsyncClient(verify=False) as client:  
            await asyncio.gather(*[self._call_url(client,sources[source]) for source in range(0,len(sources))])

    async def press(self,action):
        payload=''
        _LOGGER.debug("Sending: %s"%action)
        await self._http_send(self._base_url+'/'+action,payload)
        
    def get_data(self,data_name):
        """ get device data named data_name """
        query=parse(data_name)
        res=query.find(self.data)
        if(len(res)==0):
            _LOGGER.error("reefbeat.get_data('%s') %s"%(data_name,self._base_url))
            _LOGGER.error("%s"%self.data)
        return res[0].value

    def set_data(self,data_name,value):
        """ set device data named data_name to value"""
        query=parse(data_name)
        try:
            res=query.update(self.data,value)
        except:
            _LOGGER.error("reefbeat.set_data('%s')"%data_name)

    async def _http_send(self,url,payload='',method='post'):
        status_ok=False
        error_count=0
        _LOGGER.debug("%s data: %s to %s"%(method,payload,url))
        while status_ok == False and error_count <= HTTP_MAX_RETRY:
            try:
                if method=='post':
                    r = httpx.post(url, json = payload,verify=False,timeout=DEFAULT_TIMEOUT)
                elif method=='put':
                    r = httpx.put(url, json = payload,verify=False,timeout=DEFAULT_TIMEOUT)
                elif method=='delete':
                    r = httpx.delete(url,verify=False,timeout=DEFAULT_TIMEOUT)
                status_ok=(r.status_code==200)
            except Exception as e:
                error_count += 1
                _LOGGER.debug("Can not post data: %s to %s, retry nb %d/%d"%(payload,url,error_count,HTTP_MAX_RETRY))
            if not status_ok:
                await asyncio.sleep(HTTP_DELAY_BETWEEN_RETRY)
        if not status_ok:
            _LOGGER.error("Can not get data from %s after %s try"%(source.value['name'],HTTP_MAX_RETRY))


    async def push_values(self,source,method='post'):
        payload=self.get_data("$.sources[?(@.name=='"+source+"')].data")
        await self._http_send(self._base_url+source,payload,method)
            
            
            
################################################################################
#Reef LED
################################################################################
LEDS_CONV=[{'name':'RSLED160','kelvin': [9000,12000,15000,20000,23000], 'white_blue':[200,125,100,50,10]},
           {'name':'RSLED90', 'kelvin': [9000,12000,15000,20000,23000], 'white_blue':[200,134,100,50,10]},
           {'name':'RSLED50', 'kelvin': [9000,12000,15000,20000,23000], 'white_blue':[200,100,50,25,5]},
           {'name':'RSLED60','kelvin': [],'white_blue':[]},
           {'name':'RSLED115','kelvin': [],'white_blue':[]},
           {'name':'RSLED170','kelvin': [],'white_blue':[]},
           ]

################################################################################
class ReefLedAPI(ReefBeatAPI):
    """ Access to Reefled informations and commands """
    def __init__(self,ip,hw) -> None:
        super().__init__(ip)
        self.data['sources'].insert(len(self.data['sources']),{"name":"/preset_name","get_once": False,"data":""})
        self.data['sources'].insert(len(self.data['sources']),{"name":"/manual","get_once": False,"data":""})
        self.data['sources'].insert(len(self.data['sources']),{"name":"/acclimation","get_once": False,"data":""})
        self.data['sources'].insert(len(self.data['sources']),{"name":"/moonphase","get_once": False,"data":""})
        for day in range(1,8):
            self.data['sources'].insert(len(self.data['sources']),{"name":"/auto/"+str(day),"get_once": False,"data":""})
            self.data['sources'].insert(len(self.data['sources']),{"name":"/clouds/"+str(day),"get_once": False,"data":""})
        self.data['local']={"status":False,
                            "manual_duration":0,
                            "moonphase":{"moon_day":1},
                            "manual_trick":{"kelvin":None,"intensity":None},
                            "acclimation":{"duration":50,"start_intensity_factor":50,"current_day":1},
                            "leds_conv":LEDS_CONV}
        self._model=hw
        self._g1 = self._model in HW_G1_LED_IDS
        self._kelvin_to_wb=None
        self._wb_to_kelvin=None


    def update_acclimation(self):
        accli=self.get_data("$.sources[?(@.name=='/acclimation')].data")
        variables=['duration','start_intensity_factor']
        for var in variables:
            self.data['local']['acclimation'][var]=accli[var]

    async def get_initial_data(self):
        """ Get inital datas and device information async """
        _LOGGER.debug('Reefbeat.get_initial_data')
        query=parse("$.sources[?(@.get_once==true)]")
        sources=query.find(self.data)
        async with httpx.AsyncClient(verify=False) as client:  
            await asyncio.gather(*[self._call_url(client,sources[source]) for source in range(0,len(sources))])
        #Kelvin conversion
        led_params=self.get_data('$.local.leds_conv[?(@.name=="'+self._model+'")]')
        _LOGGER.debug("LEDS_PARAMS: %s"%led_params)
        if len (led_params['kelvin']) > 0:
            self._kelvin_to_wb=np.poly1d(np.polyfit(np.array(led_params['kelvin']),np.array(led_params['white_blue']), 4))
            self._wb_to_kelvin=np.poly1d(np.polyfit(np.array(led_params['white_blue']),np.array(led_params['kelvin']), 4))
        await self.fetch_data()
        self.update_acclimation()
        _LOGGER.debug('OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO')
        _LOGGER.debug(self.data)
        _LOGGER.debug('OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO')
        return self.data

        
    def _wb(self,value):
        if value >= 100:
            white=100
            blue=200-value
        else:
            blue=100
            white=value
        return white,blue
        
    def kelvin_to_white_and_blue(self,kelvin,intensity=100):
        wb=self._kelvin_to_wb(kelvin)
        white,blue=self._wb(wb)
        white = white * intensity / 100
        blue= blue * intensity / 100
        moon = self.get_data(LED_MOON_INTERNAL_NAME)
        res={'kelvin':int(kelvin),"intensity":int(intensity),"white": int(white),"blue":int(blue),"moon":moon}
        _LOGGER.debug("Kelvin to white and blue: %s (wb=%d)" %(res,wb))
        return res
        
    def white_and_blue_to_kelvin(self,white,blue):
        if white >= blue:
            intensity=white
            wb = 200-blue*100/intensity
        else:
            intensity=blue
            wb= white*100/intensity
        kelvin=self._wb_to_kelvin(wb)
        moon = self.get_data(LED_MOON_INTERNAL_NAME)
        res={'kelvin':int(kelvin),"intensity":int(intensity),"white": int(white),"blue":int(blue),"moon":moon}
        _LOGGER.debug("White and blue to kelvin: %s (wb=%d)" %(res,wb))
        return res

    def update_light_wb(self):
        _LOGGER.debug("**** update_light_wb")
        data = self.get_data('$.sources[?(@.name=="/manual")].data')
        new_data=self.white_and_blue_to_kelvin(data['white'],data['blue'])
        data['kelvin']=new_data['kelvin']
        data['intensity']=new_data['intensity']
        # Must copy this data beacause virtual led get them before availaible in '/manual' "
        self.data['local']['manual_trick']['kelvin']=new_data['kelvin']
        self.data['local']['manual_trick']['intensity']=new_data['intensity']   


    def get_data(self,data_name):
        if self._g1 and data_name==LED_KELVIN_INTERNAL_NAME:
            return  self.data['local']['manual_trick']['kelvin']
        elif self._g1 and data_name==LED_INTENSITY_INTERNAL_NAME:
            return self.data['local']['manual_trick']['intensity']
        else :
            return super().get_data(data_name)
        
    def update_light_ki(self):
        data = self.get_data('$.sources[?(@.name=="/manual")].data')
        new_data=self.kelvin_to_white_and_blue(data['kelvin'],data['intensity'])
        data['white']=new_data['white']
        data['blue']=new_data['blue']
        
    async def fetch_data(self):
        await super().fetch_data()
        # add kelvin and intensity to G1
        if self._g1:
            self.update_light_wb()
        self.update_acclimation()
        self.force_status_update()

    async def delete(self, source):
        await self._http_send(self._base_url+source,method='delete')

    async def post_specific(self, source):
        if source == '/timer' :
            payload=self.get_data('$.sources[?(@.name=="/manual")].data')
            if self.get_data(LED_MANUAL_DURATION_INTERNAL_NAME) > 0:
                payload['duration']=self.get_data(LED_MANUAL_DURATION_INTERNAL_NAME)
                await self._http_send(self._base_url+source,payload,'post')
            else:
                source='/manual'
            _LOGGER.debug("/-- %s %s"%(self._base_url+source,payload))
            await self._http_send(self._base_url+source,payload,'post')
        else:
            payload_name="$.local."+source[1:]
            payload=self.get_data(payload_name)
            await self._http_send(self._base_url+source,payload,'post')

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
        
    # async def push_values(self,source):
    #     #TODO: set put retry on failure
    #     payload={
    #         'auto_advance': self.get_data(MAT_AUTO_ADVANCE_INTERNAL_NAME),
    #         'custom_advance_value': self.get_data(MAT_CUSTOM_ADVANCE_VALUE_INTERNAL_NAME),
    #         'model': self.get_data(MAT_MODEL_INTERNAL_NAME),
    #         'position': self.get_data(MAT_POSITION_INTERNAL_NAME)}
    #     await self._http_send(self._base_url+'/configuration',payload,'put')

    async def new_roll(self):
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
        #r = httpx.post(self._base_url+'/new-roll', json = payload,verify=False,timeout=DEFAULT_TIMEOUT)
        await self._http_send(self._base_url+'/new-roll',payload)

        
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
            
    async def press(self,action,head):
        manual_dose=self.get_data("$.local.head."+str(head)+".manual_dose")
        payload={'manual_dose_scheduled': True,'volume': manual_dose}
        #r = httpx.post(self._base_url+'/head/'+str(head)+'/'+action, json = payload,verify=False,timeout=DEFAULT_TIMEOUT)
        await self._http_send(self._base_url+'/head/'+str(head)+'/'+action,payload)
        
    async def push_values(self,head):
        payload=self.get_data("$.sources[?(@.name=='/head/"+str(head)+"/settings')].data")
        await self._http_send(self._base_url+'/head/'+str(head)+'/settings',payload,'put')
    #     try:
    #         r = httpx.put(self._base_url+'/head/'+str(head)+'/settings', json = payload,verify=False,timeout=DEFAULT_TIMEOUT)
    #     except Exception as e:
    #         _LOGGER.error("readsea.reefbeat.ReefDoseAPI.push_value failed")
    #         _LOGGER.error(e)
    
################################################################################
# ReefATO+
class ReefATOAPI(ReefBeatAPI):
    """ Access to Reefled informations and commands """
    def __init__(self,ip) -> None:
        super().__init__(ip)
        self.data['sources'].insert(len(self.data['sources']),{"name":"/configuration","get_once": False,"data":""})

    async def push_values(self,source='/configuration',method='put'):
        payload={'auto_fill': self.get_data(ATO_AUTO_FILL_INTERNAL_NAME)}
        await self._http_send(self._base_url+'/configuration',payload,method)
        #r = httpx.put(self._base_url+'/configuration', json = payload,verify=False,timeout=DEFAULT_TIMEOUT)

################################################################################
# ReefRun
class ReefRunAPI(ReefBeatAPI):
    """ Access to Reefled informations and commands """
    def __init__(self,ip) -> None:
        super().__init__(ip)
        self.data['sources'].insert(len(self.data['sources']),{"name":"/pump/settings","get_once": False,"data":""})

    async def push_values(self,pump):
        payload=self.get_data("$.sources[?(@.name=='/pump/settings')].data.pump_"+str(pump))
        await self._http_send(self._base_url+'/pump/settings',payload,'put')


    

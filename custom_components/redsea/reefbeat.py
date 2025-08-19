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
    LEDS_CONV,
    LEDS_INTENSITY_COMPENSATION,
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
    def __init__(self,ip,live_config_update) -> None:
        self.ip=ip
        self._base_url = "http://"+ip
        self.data={"sources": [{"name":"/","type": "device-info","data":""},
                               {"name":"/device-info","type": "device-info","data":""},
                               {"name":"/firmware","type": "device-info","data":""},
                               {"name":"/dashboard","type": "data","data":""}]}
        #store object paht according to jsonpath
        self._data_db = {}
        self.last_update_success=None
        self.quick_refresh=None
        self._live_config_update=live_config_update


    async def _http_get(self,client,source):
        _LOGGER.debug("_http_get: %s"%self._base_url+source.value['name'])
        r = await client.get(self._base_url+source.value['name'],timeout=DEFAULT_TIMEOUT)
        if r.status_code == 200:
            response=r.json()
            query=parse("$.sources[?(@.name=='"+source.value["name"]+"')]")
            s=query.find(self.data)
            s[0].value['data']=response
            return True
        else:
            _LOGGER.error("Can not get data: %s from %s"%(source.value['name'],self.ip))
            return False

    async def _call_url(self,client,source):
        status_ok=False
        error_count=0
        while status_ok == False and error_count < HTTP_MAX_RETRY:
            try:
                status_ok=await self._http_get(client,source)
            except Exception as e:
                error_count += 1
                _LOGGER.debug("Can not get data: %s, retry nb %d/%d"%(source.value['name'],error_count,HTTP_MAX_RETRY))
                _LOGGER.debug(e)
            if not status_ok:
                await asyncio.sleep(HTTP_DELAY_BETWEEN_RETRY)
        if not status_ok:
            _LOGGER.error("Can not get data from %s%s after %s try"%(self.ip,source.value['name'],HTTP_MAX_RETRY))
            
    async def get_initial_data(self):
        """ Get inital datas and device information async """
        _LOGGER.debug('Reefbeat.get_initial_data')
        query=parse("$.sources[?(@.type=='device-info')]")
        sources=query.find(self.data)
        async with httpx.AsyncClient(verify=False) as client:  
            await asyncio.gather(*[self._call_url(client,sources[source]) for source in range(0,len(sources))])

        if self._live_config_update == False:
            await self.fetch_config()
        await self.fetch_data()
        _LOGGER.debug('OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO')
        _LOGGER.debug(self.data)
        _LOGGER.debug('OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO')
        return self.data


    async def fetch_config(self,config_path=None):
        _LOGGER.debug("reefbeat.fetch_config")
        if config_path==None:
            query=parse("$.sources[?(@.type=='config')]")
        else:
            query=parse("$.sources[?(@.name=='"+config_path+"')]")
        sources=query.find(self.data)
        async with httpx.AsyncClient(verify=False) as client:  
            await asyncio.gather(*[self._call_url(client,sources[source]) for source in range(0,len(sources))])
        
    async def fetch_data(self):
        """ Get device data """
        if self.quick_refresh!= None:
            query=parse("$.sources[?(@.name=='"+self.quick_refresh+"')]")
            sources=query.find(self.data)
            self.quick_refresh=None
        else:
            if self._live_config_update:
                query=parse("$.sources[?(@.type!='device-info')]")
            else:
                query=parse("$.sources[?(@.type=='data')]")
                
            sources=query.find(self.data)
        async with httpx.AsyncClient(verify=False) as client:  
            await asyncio.gather(*[self._call_url(client,sources[source]) for source in range(0,len(sources))])

    async def press(self,action):
        payload=''
        _LOGGER.debug("Sending: %s"%action)
        await self._http_send(self._base_url+'/'+action,payload)

        
    def get_path(self,obj):
        res=''
        if hasattr(obj,'context') and obj.context!=None:
            res+=self.get_path(obj.context)
        if hasattr(obj,'path') :
            if str(obj.path)=='$':
                pass
            else:
                if str(obj.path)[0]!='[' :
                    res+='["'+str(obj.path)+'"]'
                else:
                    res+=str(obj.path)
        return res
        
    def get_data_link(self,data_name):
        query=parse(data_name)
        res=query.find(self.data)
        if len(res)==0:
               return None
        path=self.get_path(res[0])
        return "data"+path

    #Cache the pointer to data object from jsonpath
    def get_data(self,name,is_None_possible=False):
        if name not in self._data_db:
            r=self.get_data_link(name)
            if r != None:
                self._data_db[name]="self."+r
            else:
                if is_None_possible==False:
                    _LOGGER.error("reefbeat.get_data('%s') %s"%(name,self._base_url))
                    _LOGGER.error("%s"%self.data)
                else:
                    return None
        return eval(self._data_db[name])

    #get data from jsonpath (slow)
    def _get_data(self,data_name,is_None_possible=False):
        """ get device data named data_name """
        query=parse(data_name)
        res=query.find(self.data)
        if len(res)==0:
           if is_None_possible==False:
            _LOGGER.error("reefbeat.get_data('%s') %s"%(data_name,self._base_url))
            _LOGGER.error("%s"%self.data)
           else:
               return None
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
            if status_ok==False:
                await asyncio.sleep(HTTP_DELAY_BETWEEN_RETRY)
        if status_ok==False:
            _LOGGER.error("Can not push data from %s after %s try"%(source.value['name'],HTTP_MAX_RETRY))


    async def push_values(self,source,method='post'):
        payload=self.get_data("$.sources[?(@.name=='"+source+"')].data")
        await self._http_send(self._base_url+source,payload,method)
            
            
            
################################################################################
#Reef LED
################################################################################
class ReefLedAPI(ReefBeatAPI):
    """ Access to Reefled informations and commands """
    def __init__(self,ip,live_config_update,hw,intensity_compensation=False) -> None:
        super().__init__(ip,live_config_update)
        self.data['sources'].insert(len(self.data['sources']),{"name":"/preset_name","type": "config","data":""})
        self.data['sources'].insert(len(self.data['sources']),{"name":"/manual","type": "data","data":""})
        self.data['sources'].insert(len(self.data['sources']),{"name":"/acclimation","type": "config","data":""})
        self.data['sources'].insert(len(self.data['sources']),{"name":"/moonphase","type": "config","data":""})
        self.data['sources'].insert(len(self.data['sources']),{"name":"/mode","type": "config","data":""})
        for day in range(1,8):
            self.data['sources'].insert(len(self.data['sources']),{"name":"/auto/"+str(day),"type": "config","data":""})
            self.data['sources'].insert(len(self.data['sources']),{"name":"/clouds/"+str(day),"type": "config","data":""})
        self.data['local']={"status":False,
                            "manual_duration":0,
                            "constant_intensity": 0,
                            "moonphase":{"moon_day":1},
                            "manual_trick":{"kelvin":None,"intensity":None},
                            "acclimation":{"duration":50,"start_intensity_factor":50,"current_day":1},
                            "leds_conv":LEDS_CONV,
                            "leds_intensity_compensation":LEDS_INTENSITY_COMPENSATION}
        self._model=hw
        self._g1 = self._model in HW_G1_LED_IDS
        _LOGGER.info("G1 protocol: %s"%(self._g1))
        self._kelvin_to_wb=None
        self._wb_to_kelvin=None
        #intensity compensation
        self._must_compensate_intensity=intensity_compensation
        _LOGGER.debug("Intensity compensation: %s"%(self._must_compensate_intensity))
        self._intensity_compensation=None
        #the minial intensity of a let set the maixum intensity for kelvin/intensity set
        self._intensity_compensation_reference=None

    def update_acclimation(self):
        accli=self.get_data("$.sources[?(@.name=='/acclimation')].data")
        variables=['duration','start_intensity_factor']
        for var in variables:
            self.data['local']['acclimation'][var]=accli[var]

    async def get_initial_data(self):
        """ Get inital datas and device information async """
        _LOGGER.debug('Reefbeat.get_initial_data')
        query=parse("$.sources[?(@.type=='device-info')]")
        sources=query.find(self.data)
        async with httpx.AsyncClient(verify=False) as client:  
            await asyncio.gather(*[self._call_url(client,sources[source]) for source in range(0,len(sources))])
        #Kelvin conversion
        led_params=self.get_data('$.local.leds_conv[?(@.name=="'+self._model+'")]')
        _LOGGER.debug("LEDS_PARAMS: %s"%led_params)
        if len (led_params['kelvin']) > 0:
            self._kelvin_to_wb=np.poly1d(np.polyfit(np.array(led_params['kelvin']),np.array(led_params['white_blue']), 4))
            self._wb_to_kelvin=np.poly1d(np.polyfit(np.array(led_params['white_blue']),np.array(led_params['kelvin']), 4))


        # intensity compensation
        if self._must_compensate_intensity:
            led_params=self.get_data('$.local.leds_intensity_compensation[?(@.name=="'+self._model+'")]',True)
            _LOGGER.debug("LEDS_INTENSITY_COMPENSATION: %s"%led_params)
            if led_params != None:
                self._intensity_compensation=np.poly1d(np.polyfit(np.array(led_params['white_blue']),np.array(led_params['intensity']), 5))
                min_blue=self._intensity_compensation(0)
                min_white=self._intensity_compensation(200)
                if min_blue > min_white:
                    self._intensity_compensation_reference = min_white
                else:
                    self._intensity_compensation_reference = min_blue
        if self._live_config_update == False:
            await self.fetch_config()
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
        if self._intensity_compensation != None:
            intensity_compensation_factor=self._intensity_compensation_reference/self._intensity_compensation(wb)
        else:
            intensity_compensation_factor=1
        white = white * intensity / 100 * intensity_compensation_factor
        blue= blue * intensity / 100 *intensity_compensation_factor
        
        moon = self.get_data(LED_MOON_INTERNAL_NAME)
        res={'kelvin':int(kelvin),"intensity":int(intensity),"white": int(white),"blue":int(blue),"moon":moon}
        _LOGGER.debug("Kelvin to white and blue: %s (wb=%d) whit compensation %s" %(res,wb,intensity_compensation_factor))
        return res
        
    def white_and_blue_to_kelvin(self,white,blue):

        if white != 0 or blue != 0:
            if white >= blue:
                intensity=white
                wb = 200-blue*100/intensity
            else:
                intensity=blue
                wb= white*100/intensity
            kelvin=self._wb_to_kelvin(wb)
            moon = self.get_data(LED_MOON_INTERNAL_NAME)

            if self._intensity_compensation != None:
                intensity_compensation_factor=self._intensity_compensation_reference/self._intensity_compensation(wb)
            else:
                intensity_compensation_factor=1

            intensity=intensity/intensity_compensation_factor

            res={'kelvin':int(kelvin),"intensity":int(intensity),"white": int(white),"blue":int(blue),"moon":moon}
        else:
            moon = self.get_data(LED_MOON_INTERNAL_NAME)
            kelvin=self.get_data(LED_KELVIN_INTERNAL_NAME)
            wb=200
            if kelvin == None or kelvin < 8000:
                kelvin=9000
            res={'kelvin':kelvin,"intensity":0,"white": 0,"blue":0,"moon":moon}
        return res

    def update_light_wb(self):
        data = self.get_data('$.sources[?(@.name=="/manual")].data')
        new_data=self.white_and_blue_to_kelvin(data['white'],data['blue'])
        data['kelvin']=new_data['kelvin']
        data['intensity']=new_data['intensity']
        # Must copy this data beacause virtual led get them before available in '/manual' "
        self.data['local']['manual_trick']['kelvin']=new_data['kelvin']
        self.data['local']['manual_trick']['intensity']=new_data['intensity']   


    def get_data(self,data_name,is_None_possible=False):
        if self._g1 and data_name==LED_KELVIN_INTERNAL_NAME:
            return  self.data['local']['manual_trick']['kelvin']
        elif self._g1 and data_name==LED_INTENSITY_INTERNAL_NAME:
            return self.data['local']['manual_trick']['intensity']
        else :
            return super().get_data(data_name,is_None_possible)
        
    def update_light_ki(self):
        f_data = self.get_data('$.sources[?(@.name=="/manual")].data')
        data = {'kelvin':int(self.get_data(LED_KELVIN_INTERNAL_NAME)),'intensity':int(self.get_data(LED_INTENSITY_INTERNAL_NAME))}
        _LOGGER.debug("Update KI: %s"%data)
        new_data=self.kelvin_to_white_and_blue(data['kelvin'],data['intensity'])
        f_data['white']=new_data['white']
        f_data['blue']=new_data['blue']
        
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
    def __init__(self,ip,live_config_update) -> None:
        super().__init__(ip,live_config_update)
        self.data['sources'].insert(len(self.data['sources']),{"name":"/configuration","type": "config","data":""})
        self.data['local']={"started_roll_diameter":MAT_MIN_ROLL_DIAMETER}
        

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
        payload={'external_diameter':diameter,'name':name,'thickness':MAT_ROLL_THICKNESS,'is_partial':is_partial}
        _LOGGER.info("New roll: %s"%payload)
        await self._http_send(self._base_url+'/new-roll',payload)

        
################################################################################
#ReefDose
class ReefDoseAPI(ReefBeatAPI):
    """ Access to ReefDose informations and commands """
    def __init__(self,ip,live_config_update,heads_nb) -> None:
        super().__init__(ip,live_config_update)
        self._heads_nb=heads_nb
        self.data['sources'].insert(len(self.data['sources']),{"name":"/device-settings","type": "config","data":""})

        if self._heads_nb == 2:
            self.data['local']={"head":{"1":"","2":""}}
        elif self._heads_nb == 4:
            self.data['local']={"head":{"1":"","2":"","3":"","4":""}}
        else:
            _LOGGER.error("redsea.reefbeat.ReefDoseAPI.__init__() unkown head number: %d"%self._heads_nb)
        for head in range(1,self._heads_nb+1):
            self.data['sources'].insert(len(self.data['sources']),{"name":"/head/"+str(head)+"/settings","type": "config","data":""})
            self.data['local']["head"][str(head)]={"manual_dose":0}
            
    async def press(self,action,head):
        manual_dose=self.get_data("$.local.head."+str(head)+".manual_dose")
        payload={'manual_dose_scheduled': True,'volume': manual_dose}
        #r = httpx.post(self._base_url+'/head/'+str(head)+'/'+action, json = payload,verify=False,timeout=DEFAULT_TIMEOUT)
        await self._http_send(self._base_url+'/head/'+str(head)+'/'+action,payload)
        
    async def push_values(self,head):
        _LOGGER.debug("type: %s"%type(head).__name__)
        if type(head).__name__ == 'int':
            payload=self.get_data("$.sources[?(@.name=='/head/"+str(head)+"/settings')].data")
            await self._http_send(self._base_url+'/head/'+str(head)+'/settings',payload,'put')
        else:
            payload=self.get_data("$.sources[?(@.name=='"+head+"')].data")
            await self._http_send(self._base_url+head,payload,'put')
            

            
    
################################################################################
# ReefATO+
class ReefATOAPI(ReefBeatAPI):
    """ Access to Reefled informations and commands """
    def __init__(self,ip,live_config_update) -> None:
        super().__init__(ip,live_config_update)
        self.data['sources'].insert(len(self.data['sources']),{"name":"/configuration","type": "config","data":""})

    async def push_values(self,source='/configuration',method='put'):
        payload={'auto_fill': self.get_data(ATO_AUTO_FILL_INTERNAL_NAME)}
        await self._http_send(self._base_url+'/configuration',payload,method)

################################################################################
# ReefRun
class ReefRunAPI(ReefBeatAPI):
    """ Access to Reefled informations and commands """
    def __init__(self,ip,live_config_update) -> None:
        super().__init__(ip,live_config_update)
        self.data['sources'].insert(len(self.data['sources']),{"name":"/pump/settings","type": "config","data":""})


    async def push_values(self,pump=None):
        if pump:
            payload={"pump_"+str(pump): self.get_data("$.sources[?(@.name=='/pump/settings')].data.pump_"+str(pump))}
        else :
            payload={"overskimming": self.get_data("$.sources[?(@.name=='/pump/settings')].data.overskimming")}
        await self._http_send(self._base_url+'/pump/settings',payload,'put')

    

#!/usr/local/bin/python

import socket
import netifaces
import ipaddress
import requests
from lxml import objectify
from multiprocessing import Pool

if __name__ == '__main__':
    from const import HW_DEVICES_IDS
else:
    from .const import HW_DEVICES_IDS
    
def get_local_ips():
    # Get local IP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip=s.getsockname()[0]
    s.close()
    #get subnetwork address and mask
    for netif in netifaces.interfaces():
        try:
            addr=netifaces.ifaddresses(netif)[2][0]
            if addr['addr'] == ip:
                net = ipaddress.ip_network(ip+'/'+addr['netmask'], strict=False)        
                return [str(ip) for ip in ipaddress.IPv4Network(str(net))]
        except:
            pass


def is_reefbeat(ip):
    try:
        r = requests.get('http://'+ip+'/device-info',timeout=2)
        if r.status_code == 200:
            data=r.json()
            hw_model=data["hw_model"]
            name=data["name"]
            if hw_model in HW_DEVICES_IDS:
                return True,ip,hw_model,name
    except:
        pass
    return False,ip,None,None

def get_reefbeats(nb_of_threads=64):
    ips=get_local_ips()
    reefbeats=[]
    with Pool(nb_of_threads) as p:
        res=p.map(is_reefbeat,ips)
        for device in res:
            status,ip,hw_model,friendly_name=device
            if status == True:
                reefbeats+=[{"ip":ip,"hw_model":hw_model,"friendly_name":friendly_name}]
    return reefbeats
                

def get_unique_id(ip):
    try:
        r = requests.get('http://'+ip+'/description.xml',timeout=2)
        if r.status_code == 200:
            tree = objectify.fromstring(r.text)
            udn=str(tree.device.UDN)
            uuid=udn.replace("uuid:","")
            return uuid
    except Exception as e :
        return str(e)
     
if __name__ == '__main__':
    print(HW_DEVICES_IDS)
    res=get_reefbeats()
    print(res)


    

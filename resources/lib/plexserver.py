import xbmcaddon
import xbmc
import xbmcgui
import sys
import os
import xml.etree.ElementTree as etree

__addon__    = xbmcaddon.Addon()
__cachedir__ = __addon__.getAddonInfo('profile')
__cwd__      = xbmc.translatePath(__addon__.getAddonInfo('path')).decode('utf-8')

__resources__ = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib'))
sys.path.append(__resources__)

from settings import addonSettings
from common import *
import requests

DEFAULT_PORT="32400"

class PlexMediaServer:

    def __init__(self, uuid=None, name=None, address=None, port=None, token=None, discovery=None, ):

        self.DEBUG_OFF=0
        self.DEBUG_INFO=1
        self.DEBUG_DEBUG=2
        self.DEBUG_DEBUGPLUS=3

        self.uuid=uuid
        self.server_name=name
        self.address=[address]
        self.port=port
        self.section_list=None
        self.token=token
        self.discovery=discovery
        self.owned=1
        self.master=1
        self.class_type=''
        self.discovered=False
        
    def get_details(self):
                 
        return {'serverName': self.server_name,
                'server'    : self.address[0],
                'port'      : self.port,
                'discovery' : self.discovery,
                'token'     : self.token ,
                'uuid'      : self.uuid,
                'owned'     : self.owned,
                'master'    : self.master,
                'class'     : self.class_type}

    def plex_identification(self):

        return {'X-Plex-Device'            : 'XBMC/KODI' ,
                'X-Plex-Client-Platform'   : 'XBMC/KODI' ,
                'X-Plex-Device-Name'       : 'unknown' ,
                'X-Plex-Language'          : 'en',
                'X-Plex-Model'             : 'unknown' ,
                'X-Plex-Platform'          : 'unknown' ,
                'X-Plex-Client-Identifier' : 'unknown' ,
                'X-Plex-Product'           : 'unknown' ,
                'X-Plex-Platform-Version'  : 'unknown' ,
                'X-Plex-Version'           : 'unknown'  ,
                'X-Plex-Provides'          : "player",
                'X-Plex-Token'             : self.token}
                
    def get_uuid(self):
        return self.uuid
        
    def get_name(self):
        return self.server_name

    def get_address(self):
        return self.address

    def get_port(self):
        return self.port

    def get_token(self):
        return self.token

    def get_discovery(self):
        return self.discovery

    def get_owned(self):
        return self.owned

    def get_class(self):
        return self.class_type

    def get_master(self):
        return self.master
          
    def talk(self,url='/'):
    
        response = requests.get("http://%s:%s%s" % (self.address[0], self.port, url), params=self.plex_identification(), timeout=2)
        
        printDebug("URL was: %s" % response.url,self.DEBUG_DEBUG)
        
        if response.status_code == requests.codes.ok:
            printDebug("===XML===\n%s\n===XML===" % response.text, self.DEBUG_DEBUGPLUS)
            return response.text
            
        return     
    def refresh(self):

        server=etree.fromstring(self.talk())

        self.server_name = server.attrib['friendlyName'].encode('utf-8')
        self.locality='local'
        self.token=None
        self.uuid=server.attrib['machineIdentifier']
        self.owned=1
        self.master=1
        self.class_type=''    
        self.discovered=True
import xbmcaddon
import xbmc
import xbmcgui
import sys
import os
import xml.etree.ElementTree as etree

from settings import addonSettings
from common import *
import requests

printDebug=printDebug("PleXBMC", "plexserver")

DEFAULT_PORT="32400"

class PlexMediaServer:

    def __init__(self, uuid=None, name=None, address=None, port=None, token=None, discovery=None, class_type='primary' ):

        self.DEBUG_OFF=0
        self.DEBUG_INFO=1
        self.DEBUG_DEBUG=2
        self.DEBUG_DEBUGPLUS=3

        self.protocol="http"
        self.uuid=uuid
        self.server_name=name
        self.address=[address]
        self.port=port
        self.section_list=None
        self.token=token
        self.discovery=discovery
        self.owned=1
        self.master=1
        self.class_type=class_type
        self.discovered=False
        self.offline=False
        
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

    def get_url_location(self):
        return '%s://%s:%s' % ( self.protocol, self.address[0], self.port)
        
    def get_location(self):
        return '%s:%s' % ( self.address[0], self.port)
    
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

    def set_owned(self, value):
        self.owned=value

    def set_class(self, value):
        self.class_type=value

    def set_master(self, value):
        self.master=value
        
    def talk(self,url='/',refresh=False):
    
        if not self.offline or refresh:
        
            try:
                response = requests.get("http://%s:%s%s" % (self.address[0], self.port, url), params=self.plex_identification(), timeout=2)
                self.offline=False
            except requests.exceptions.ConnectionError, e:
                printDebug("Server: %s is offline or uncontactable. error: %s" % (self.address[0], e))
                self.offline=True
            else:

                printDebug("URL was: %s" % response.url,self.DEBUG_DEBUG)
                
                if response.status_code == requests.codes.ok:
                    printDebug("===XML===\n%s\n===XML===" % response.text, self.DEBUG_DEBUGPLUS)
                    return response.text
                    
        return '<?xml version="1.0" encoding="UTF-8"?><status>offline</status>'

    def refresh(self):
        data=self.talk(refresh=True)
        
        if data:
            server=etree.fromstring(data)

            self.server_name = server.attrib['friendlyName'].encode('utf-8')
            self.token=None
            self.uuid=server.attrib['machineIdentifier']
            self.owned=1
            self.master=1
            self.class_type=server.get('serverClass','primary')
            self.discovered=True
        else:
            self.discovered=False
            
    def is_offline(self):
        return self.offline
        
    def get_sections(self):
        return self.talk("/library/sections")

    def get_recently_added(self):
        return self.talk("/library/recentlyAdded")

    def get_ondeck(self):
        return self.talk("/library/onDeck")
        
        
    def is_owned(self):
        
        if self.owned == 1 or self.owned == '1':
            return True
        return False

    def is_secondary(self):
        
        if self.class_type == "secondary":
            return True
        return False

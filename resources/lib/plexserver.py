import xbmcaddon
import xbmc
import xbmcgui
import sys
import os
import xml.etree.ElementTree as etree
import urlparse
import urllib

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
        self.section_list=[]
        self.token=token
        self.discovery=discovery
        self.owned=1
        self.master=1
        self.class_type=class_type
        self.discovered=False
        self.offline=False

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
                response = requests.get("http://%s:%s%s" % (self.address[0], self.port, url), params=self.plex_identification(), timeout=3)
                self.offline=False
            except requests.exceptions.ConnectionError, e:
                printDebug("Server: %s is offline or uncontactable. error: %s" % (self.address[0], e))
                self.offline=True
            else:

                printDebug("URL was: %s" % response.url,self.DEBUG_DEBUG)
                
                if response.status_code == requests.codes.ok:
                    printDebug.debug("Encoding: %s" % response.encoding)
                    printDebug("===XML===\n%s\n===XML===" % response.text.encode('utf-8'), self.DEBUG_DEBUGPLUS)
                    return response.text.encode('utf-8')
                    
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
    
        #temp_list=[]
    
        #for section in self.section_list:        
        #    temp_list.append(sections.get_details)
            
        printDebug.debug("Returning sections: %s" % self.section_list)
        return self.section_list
        
    def discover_sections(self):
        
            for section in self.processed_xml("/library/sections"):
            
                self.section_list.append(plex_section(section))

    def get_recently_added(self,section=-1,start=0,size=0):
    
        arguments="?unwatched=1"

        if section < 0:
            return self.processed_xml("/library/recentlyAdded%s" % arguments)    
            
        if size > 0:
            arguments="%s&X-Plex-Container-Start=%s&X-Plex-Container-Size=%s" % (arguments, start, size)
            
        return self.processed_xml("/library/sections/%s/recentlyAdded%s" % (section, arguments))
    
    def get_ondeck(self,section=-1,start=0,size=0):
    
        arguments=""

        if section < 0:
            return self.processed_xml("/library/onDeck%s" % arguments)    
            
        if size > 0:
            arguments="%s?X-Plex-Container-Start=%s&X-Plex-Container-Size=%s" % (arguments, start, size)
            
        return self.processed_xml("/library/sections/%s/onDeck%s" % (section, arguments))

    def get_server_recentlyadded(self):
        return self.get_recentlyadded(section=-1)
  
    def get_server_ondeck(self):
        return self.get_ondeck(section=-1)
  
    def get_channel_recentlyviewed(self):
            
        return self.processed_xml("/channels/recentlyViewed") 
        
    def processed_xml(self,url):
    
        data = self.talk(url)
        return etree.fromstring(data)
   
    def is_owned(self):
        
        if self.owned == 1 or self.owned == '1':
            return True
        return False

    def is_secondary(self):
        
        if self.class_type == "secondary":
            return True
        return False

    def get_formatted_url(self, url, options={}):
    
        options.update(self.plex_identification())
    
        location = "%s%s" % (self.get_url_location(), url)
        
        url_parts = urlparse.urlparse(location)

        query_args = urlparse.parse_qsl(url_parts.query)
        query_args += options.items()

        new_query_args = urllib.urlencode(query_args, True)

        return urlparse.urlunparse((url_parts.scheme, url_parts.netloc, url_parts.path, url_parts.params, new_query_args, url_parts.fragment))

    def get_fanart(self, section, width=1280, height=720):
        '''
            Simply take a URL or path and determine how to format for fanart
            @ input: elementTree element, server name
            @ return formatted URL for photo resizing
        '''
        
        printDebug.debug("Getting fanart for %s" % section.get_title())
        
        if settings.skipimages:
            return ''
            
        if section.get_art().startswith('/'):
            if settings.fullres_fanart:
                return self.get_formatted_url(section.get_art())
            else:
                return self.get_formatted_url('/photo/:/transcode?url=%s&width=%s&height=%s' % (urllib.quote_plus("http://localhost:32400"+section.get_art()), width, height))

        return section.get_art()     
        
class plex_section:

    def __init__(self, data=None):
    
        self.title = None
        self.sectionuuid = None
        self.path = None
        self.key = None
        self.art = None
        self.type = None
        self.location = "local"
    
        if data is not None:
            self.populate(data)
    
    def populate(self,data):
    
        path = data.get('key')
        if not path[0] == "/":
             path = '/library/sections/%s' % path
    
        self.title       = data.get('title', 'Unknown').encode('utf-8')
        self.sectionuuid = data.get('uuid', '')
        self.path        = path.encode('utf-8')
        self.key         = data.get('key')
        self.art         = data.get('art', '').encode('utf-8')
        self.type        = data.get('type', '')

    def get_details(self):
    
        return {'title'       : self.title,
                'sectionuuid' : self.sectionuuid,
                'path'       : self.path,
                'key'        : self.key,
                'location'   : self.local,
                'art'        : self.art,
                'type'       : self.type}
                
    def get_title(self):
        return self.title

    def get_uuid(self):
        return self.sectionuuid

    def get_path(self):
        return self.path

    def get_key(self):
        return self.key

    def get_art(self):
        return self.art

    def get_type(self):
        return self.type

    def is_show(self):
        if self.type == 'show':
            return True
        return False
    
    def is_movie(self):
        if self.type == 'movie':
            return True
        return False

    def is_artist(self):
        if self.type == 'artist':
            return True
        return False

    def is_photo(self):
        if self.type == 'photo':
            return True
        return False
                

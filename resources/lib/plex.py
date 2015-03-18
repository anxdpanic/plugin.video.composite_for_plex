import xbmcaddon
import xbmcgui
import sys
import os
import xml.etree.ElementTree as etree
import base64
import plexgdm
from settings import addonSettings
from common import *
import CacheControl
import requests
from plexserver import PlexMediaServer
import urlparse
import uuid

printDebug=printDebug("PleXBMC", "plex")
DEFAULT_PORT="32400"

class Plex:

    def __init__(self, load=False):
    
        # Provide an interface into Plex 
        self.cache=CacheControl.CacheControl(GLOBAL_SETUP['__cachedir__']+"cache/servers", settings.get_setting('cache'))
        self.myplex_server='https://plex.tv'
        self.myplex_token=None
        self.logged_into_myplex=False
        self.server_list={}
        self.discovered=False
        self.server_list_cache="discovered_plex_servers.cache"
        self.client_id=None
        
        if load:
            self.load()

    def load(self):
        printDebug.info("Loading cached server list")
        data_ok, self.server_list = self.cache.checkCache(self.server_list_cache)
        
        if not data_ok or not len(self.server_list):
            printDebug.info("unsuccessful")
            self.server_list={}
            if not self.discover():
                self.server_list={}
        printDebug.debug("Server list is now: %s" % self.server_list)

    def discover(self):
        self.discover_all_servers()
        
        if self.server_list:
            self.discovered=True
            
        return self.discovered    
         
    def get_server_list(self):
        return self.server_list.values()
            
    def plex_identification(self):
        return {'X-Plex-Device'            : 'PleXBMC' ,
                'X-Plex-Client-Platform'   : 'KODI' ,
                'X-Plex-Device-Name'       : settings.get_setting('devicename') ,
                'X-Plex-Language'          : 'en',
                'X-Plex-Model'             : 'unknown' ,
                'X-Plex-Platform'          : 'PleXBMC' ,
                'X-Plex-Client-Identifier' : self.get_client_identifier() ,
                'X-Plex-Product'           : 'PleXBMC' ,
                'X-Plex-Platform-Version'  : GLOBAL_SETUP['platform'],
                'X-Plex-Version'           : GLOBAL_SETUP['__version__']  ,
                'X-Plex-Provides'          : "player",
                'X-Plex-Token'             : self.myplex_token}

    def get_client_identifier(self):
    
        if self.client_id is None:
            self.client_id = settings.get_setting('client_id')

            if not self.client_id:
                self.client_id = str(uuid.uuid4())
                settings.set_setting('client_id', self.client_id)

        return self.client_id
        
    def ping_server(self, ip="localhost", port=DEFAULT_PORT, url=None):
        response = requests.head("http://%s:%s%s" % (ip, port, url), params=self.plex_identification(), timeout=2)
        
        printDebug.debug("URL was: %s" % response.url)
        
        if response.status_code == requests.codes.ok:
            return True
            
        return False
                
    def talk_direct_to_server(self, ip="localhost", port=DEFAULT_PORT, url=None):
        response = requests.get("http://%s:%s%s" % (ip, port, url), params=self.plex_identification(), timeout=2)
        
        printDebug.debug("URL was: %s" % response.url)
        
        if response.status_code == requests.codes.ok:
            printDebug.debugplus("===XML===\n%s\n===XML===" % response.text)
            return response.text

    def get_processed_myplex_xml(self, url):
        data = self.talk_to_myplex (url)
        return etree.fromstring(data)
            
    def discover_all_servers(self):
        if settings.get_setting('discovery') == "1":
            printDebug.info("local GDM discovery setting enabled.")
            try:
                printDebug.info("Attempting GDM lookup on multicast")
                if settings.get_debug() >= printDebug.DEBUG_INFO:
                    GDM_debug=3
                else:
                    GDM_debug=0

                gdm_client = plexgdm.plexgdm(GDM_debug)
                gdm_client.discover()
                gdm_server_name = gdm_client.getServerList()

                if  gdm_client.discovery_complete and gdm_server_name :
                    printDebug.info("GDM discovery completed")
                    
                    for device in gdm_server_name:
                        server=PlexMediaServer(name=device['serverName'],address=device['server'], port=device['port'], discovery='local')
                        server.refresh()
                        printDebug("Adding server %s %s" % (server.get_name(), server.get_uuid()))
                        self.server_list[server.get_uuid()] = server
                else:
                    printDebug.info("GDM was not able to discover any servers")

            except Exception, e:
                print "PleXBMC -> GDM Issue [%s]" % e

        #Set to Disabled
        else:
            if settings.get_setting('das_host'):

                if not settings.get_setting('das_port'):
                    printDebug.info( "PleXBMC -> No port defined.  Using default of " + DEFAULT_PORT)

                printDebug.info( "PleXBMC -> Settings hostname and port: %s : %s" % ( settings.get_setting('das_host'), settings.get_setting('das_port')))

                local_server=PlexMediaServer(address=settings.get_setting('das_host'), port=settings.get_setting('das_port'), discovery='local')
                local_server.refresh()
                if local_server.discovered:
                    self.server_list[local_server.get_uuid()] = local_server

        if settings.get_setting('myplex_user'):
            printDebug.info( "PleXBMC -> Adding myplex as a server location")

            das_myplex = self.get_myplex_servers()

            if das_myplex:
                printDebug.info("MyPlex discovery completed")
                self.merge_myplex(das_myplex)

        self.cache.writeCache(self.server_list_cache, self.server_list)
        printDebug.info("PleXBMC -> serverList is: %s " % self.server_list)

        return 

    def get_myplex_queue(self):
        return self.get_processed_myplex_xml('/pms/playlists/queue/all')

    def get_myplex_sections(self):
        xml = self.talk_to_myplex('/pms/system/library/sections')
        if xml is False:
            return {}
        return xml
        
    def get_myplex_servers(self):
        tempServers = {}
        xml = self.talk_to_myplex("/pms/servers")

        if xml is False:
            return {}

        server_list = etree.fromstring(xml)

        count = 0
        for server in server_list:
        
            myplex_server=PlexMediaServer( name = server.get('name').encode('utf-8'),
                                           address = server.get('address') ,
                                           port = server.get('port'),
                                           discovery = "myplex" ,
                                           token = server.get('accessToken'),
                                           uuid = server.get('machineIdentifier'))

            if server.get('owned', None) == "0":
                myplex_server.set_owned(0)

            tempServers[myplex_server.get_uuid()]=myplex_server
            printDebug.info("Discovered myplex server %s %s" % (myplex_server.get_name(), myplex_server.get_uuid()))
            
        return tempServers
                                           
    def merge_myplex(self, remote):
        printDebug.info("remote is %s" % remote)
        
        for uuid,server in remote.iteritems():
            
            if uuid in self.server_list.keys():
                printDebug.debug("Merging server %s %s" % (server.get_name(), server.get_uuid()))
            else:
                printDebug.debug("Adding new server %s %s" % (server.get_name(), server.get_uuid()))
                self.server_list[uuid]=server

        return 
        
    def talk_to_myplex(self, path, renew=False, suppress=True):
        printDebug.info("url = %s%s" % (self.myplex_server, path))

        response = requests.get("%s%s" % (self.myplex_server, path), params=dict(self.plex_identification(), **self.get_myplex_token(renew)))
        
        if response.status_code == 401  and not ( renew ):
            return self.talk_to_myplex(path,True)

        if response.status_code >= 400:
            error = "HTTP response error: %s" % ( response.status_code )
            if suppress is False:
                xbmcgui.Dialog().ok("Error",error)
            print error
            return '<?xml version="1.0" encoding="UTF-8"?><message status="offline"></message>'
        else:
            link=response.text.encode('utf-8')
            printDebug.debugplus("====== XML returned =======\n%s====== XML finished ======" % link)

        return link        
    
    def get_myplex_token(self,renew=False):
        user=settings.get_setting('myplex_user')
        if self.myplex_token is None:
            try:
                user, self.myplex_token = settings.get_setting('myplex_token').split('|')
            except:
                self.myplex_token = None
                user=None

        if (self.myplex_token is None) or (renew) or (user != settings.get_setting('myplex_user')):
            self.myplex_token = self.get_new_myplex_token()

        printDebug.info("Using token: %s [Renew: %s]" % ( self.myplex_token, renew) )
        return { 'X-Plex-Token' : self.myplex_token }

    def get_new_myplex_token(self,suppress=True, title="Error"):
        printDebug.info("Getting New token")
        if not settings.get_setting('myplex_user'):
            printDebug.info("No myplex details in config..")
            return None

        base64string = base64.encodestring('%s:%s' % (settings.get_setting('myplex_user'), settings.get_setting('myplex_pass'))).replace('\n', '')
        token = False

        myplex_headers={'Authorization': "Basic %s" % base64string}

        response = requests.post("%s/users/sign_in.xml" % self.myplex_server, headers=dict(self.plex_identification(), **myplex_headers))
        
        if response.status_code == 201:
            try:
                printDebug.debugplus(response.text.encode('utf-8'))
                printDebug.info("Received new plex token")
                token = etree.fromstring(response.text.encode('utf-8')).findtext('authentication-token')
                settings.update_token(token)
            except:
                printDebug.info("No authentication token found")        
        else:
            error = "HTTP response error: %s %s" % (response.status_code, response.reason)
            if suppress is False:
                xbmcgui.Dialog().ok(title, error)
            print error
            return None

        return token

    def get_server_from_ip(self, ip):
        printDebug.debug("IP to lookup: %s" % ip)

        if ':' in ip:
            #We probably have an IP:port being passed
            ip, port = ip.split(':')

        if not is_ip(ip):
            printDebug.info("Not an IP Address")
            return PlexMediaServer(name="dummy",address='127.0.0.1', port=32400, discovery='local')

        for server in self.server_list.values():

            printDebug.debug("checking ip %s against server ip %s" % (ip, server.get_address()))

            if ip == server.get_address():
                printDebug("Translated %s to server %s" % (ip, server.get_name()))
                return server

        printDebug.info("Unable to translate - Returning new plexserver set to %s" % ip )

        return PlexMediaServer(name="Unknown",address=ip, port=port, discovery='local')

    def get_server_from_url(self, url):
        url_parts = urlparse.urlparse(url)    
        return self.get_server_from_ip(url_parts.netloc)        

    def get_server_from_uuid(self, uuid):
        return self.server_list[uuid]
        
    def get_processed_xml(self, url):
        url_parts = urlparse.urlparse(url)
        server = self.get_server_from_ip(url_parts.netloc)
        
        if server:
            return server.processed_xml(url)
        return ''

    def talk_to_server(self, url):  
        url_parts = urlparse.urlparse(url)
        server = self.get_server_from_ip(url_parts.netloc)
        
        if server:
            return server.raw_xml(url)
        return ''
   
    def delete_cache(self):
        return self.cache.deleteCache()
    
import xbmcaddon
import xbmc
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

printDebug=printDebug("PleXBMC", "plex")
DEFAULT_PORT="32400"

class Plex:

    def __init__(self, settings=None, cache=None):
    
        # Provide an interface into Plex 
        if not settings:
            self.settings = addonSettings('plugin.video.plexbmc')
        else:
            self.settings = settings
            
        self.cache=CacheControl.CacheControl(GLOBAL_SETUP['__cachedir__']+"cache/servers", self.settings.debug,self.settings.cache)
        self.myplex_server='https://plex.tv'
        self.myplex_token=None
        self.logged_into_myplex=False
        self.server_list={}
        self.discovered=False
                        
    def discover(self):
        self.discover_all_servers()
        
        if self.server_list:
            self.discovered=True

    def get_server_list(self):
        return self.server_list.values()
            
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
                'X-Plex-Token'             : self.myplex_token}

    def ping_server(self, ip="localhost", port=DEFAULT_PORT, url=None):
    
        response = requests.head("http://%s:%s%s" % (ip, port, url), params=self.plex_identification(), timeout=2)
        
        printDebug.debug("URL was: %s" % response.url)
        
        if response.status_code == requests.codes.ok:
            return True
            
        return False
                
    def talk_to_server(self, ip="localhost", port=DEFAULT_PORT, url=None):
    
        response = requests.get("http://%s:%s%s" % (ip, port, url), params=self.plex_identification(), timeout=2)
        
        printDebug.debug("URL was: %s" % response.url)
        
        if response.status_code == requests.codes.ok:
            printDebug.debugplus("===XML===\n%s\n===XML===" % response.text)
            return response.text
     
    def discover_all_servers(self):
        printDebug.debug("== ENTER ==")

        if self.settings.discovery == "1":
            printDebug.info("local GDM discovery setting enabled.")
            try:
                printDebug.info("Attempting GDM lookup on multicast")
                if self.settings.debug >= printDebug.DEBUG_INFO:
                    GDM_debug=3
                else:
                    GDM_debug=0

                gdm_cache_file="gdm.server.cache"
                gdm_cache_ok = False

                gdm_cache_ok, gdm_server_name = self.cache.checkCache(gdm_cache_file)

                if not gdm_cache_ok:
                    gdm_client = plexgdm.plexgdm(GDM_debug)
                    gdm_client.discover()
                    gdm_server_name = gdm_client.getServerList()

                    self.cache.writeCache(gdm_cache_file, gdm_server_name)

                if  ( gdm_cache_ok or gdm_client.discovery_complete ) and gdm_server_name :
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

            if self.settings.das_host:

                if not self.settings.das_port:
                    printDebug.info( "PleXBMC -> No port defined.  Using default of " + DEFAULT_PORT)
                    self.settings.das_port=DEFAULT_PORT

                printDebug.info( "PleXBMC -> Settings hostname and port: %s : %s" % ( self.settings.das_host, self.settings.das_port))

                local_server=PlexMediaServer(address=self.settings.das_host, port=self.settings.das_port, discovery='local')
                local_server.refresh()
                if local_server.discovered:
                    self.server_list[local_server.get_uuid()] = local_server

        if self.settings.myplex_user:
            printDebug.info( "PleXBMC -> Adding myplex as a server location")

            myplex_cache_file="myplex.server.cache"
            success, das_myplex = self.cache.checkCache(myplex_cache_file)

            if not success:
                das_myplex = self.get_myplex_servers()
                self.cache.writeCache(myplex_cache_file, das_myplex)

            if das_myplex:
                printDebug.info("MyPlex discovery completed")
                self.merge_myplex(das_myplex)

        printDebug.info("PleXBMC -> serverList is: %s " % self.server_list)

        return 

    def get_myplex_queue(self):
        printDebug.debug("== ENTER ==")

        xml = self.getMyPlexURL('/pms/playlists/queue/all')

        if xml is False:
            return {}

        return xml

    def get_myplex_sections(self):
        printDebug.debug("== ENTER ==")

        xml = self.getMyPlexURL('/pms/system/library/sections')

        if xml is False:
            return {}

        return xml
        
    def get_myplex_servers(self):
        '''
            Connect to the myplex service and get a list of all known
            servers.
            @input: nothing
            @return: a list of servers (as Dict)
        '''

        printDebug.debug("== ENTER ==")

        tempServers = {}
        xml = self.getMyPlexURL("/pms/servers")

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
        printDebug.debug("== ENTER ==")

        printDebug.info("remote is %s" % remote)
        
        for uuid,server in remote.iteritems():
            
            if uuid in self.server_list.keys():
                printDebug.debug("Merging server %s %s" % (server.get_name(), server.get_uuid()))
            else:
                printDebug.debug("Adding new server %s %s" % (server.get_name(), server.get_uuid()))
                self.server_list[uuid]=server

        return 
        
    def getMyPlexURL(self, url_path, renew=False, suppress=True):
        '''
            Connect to the my.plexapp.com service and get an XML pages
            A seperate function is required as interfacing into myplex
            is slightly different than getting a standard URL
            @input: url to get, whether we need a new token, whether to display on screen err
            @return: an xml page as string or false
        '''
        printDebug.debug("== ENTER ==")
        printDebug.info("url = "+self.myplex_server+url_path)

        response = requests.get("%s%s" % (self.myplex_server, url_path), params=dict(self.plex_identification(), **self.getMyPlexToken(renew)))
        
        if  response.status_code == 401   and not ( renew ):
            return self.getMyPlexURL(url_path,True)

        if response.status_code >= 400:
            error = "HTTP response error: " + str(data.status) + " " + str(data.reason)
            if suppress is False:
                xbmcgui.Dialog().ok("Error",error)
            print error
            return False
        else:
            link=response.text
            printDebug.debugplus("====== XML returned =======")
            printDebug.debugplus(link)
            printDebug.debugplus("====== XML finished ======")
    # except socket.gaierror :
        # error = 'Unable to lookup host: ' + MYPLEX_SERVER + "\nCheck host name is correct"
        # if suppress is False:
            # xbmcgui.Dialog().ok("Error",error)
        # print error
        # return False
    # except socket.error, msg :
        # error="Unable to connect to " + MYPLEX_SERVER +"\nReason: " + str(msg)
        # if suppress is False:
            # xbmcgui.Dialog().ok("Error",error)
        # print error
        # return False

        return link        
    
    def getMyPlexToken(self,renew=False):
        '''
            Get the myplex token.  If the user ID stored with the token
            does not match the current userid, then get new token.  This stops old token
            being used if plex ID is changed. If token is unavailable, then get a new one
            @input: whether to get new token
            @return: myplex token
        '''
        printDebug.debug("== ENTER ==")

        if self.myplex_token is None:
        
            try:
                user, self.myplex_token = self.settings.myplex_token.split('|')
            except:
                self.myplex_token = None

            if (self.myplex_token is None) or (renew) or (user != self.settings.myplex_user):
                self.myplex_token = self.getNewMyPlexToken()

            printDebug.info("Using token: " + str(self.myplex_token) + "[Renew: " + str(renew) + "]")
        return { 'X-Plex-Token' : self.myplex_token }

    def getNewMyPlexToken(self,suppress=True, title="Error"):
        printDebug.debug("== ENTER ==")

        printDebug.info("Getting New token")
        if not self.settings.myplex_user:
            printDebug.info("No myplex details in config..")
            return None

        base64string = base64.encodestring('%s:%s' % (self.settings.myplex_user, self.settings.myplex_pass)).replace('\n', '')
        token = False

        myplex_headers={'Authorization': "Basic %s" % base64string}

        response = requests.post("%s/users/sign_in.xml" % self.myplex_server, headers=dict(self.plex_identification(), **myplex_headers))
        
        if response.status_code == 201:
            try:
                printDebug.debugplus(response.text)
                printDebug.info("Received new plex token")
                token = etree.fromstring(response.text).findtext('authentication-token')
                self.settings.update_token(token)
            except:
                printDebug.info("No authentication token found")
                
            printDebug.debugplus("====== XML finished ======")
        
        else:
            error = "HTTP response error: %s %s" % (response.status_code, response.reason)
            if suppress is False:
                xbmcgui.Dialog().ok(title, error)
            print error
            return None

        return token

    
        
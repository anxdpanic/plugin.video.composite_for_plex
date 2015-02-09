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
        self.DEBUG_OFF=0
        self.DEBUG_INFO=1
        self.DEBUG_DEBUG=2
        self.DEBUG_DEBUGPLUS=3
        self.myplex_token=None
        self.myplex_server='https://plex.tv'
        self.logged_into_myplex=False
        self.server_list=[]
        self.discovered=False
                        
    def discover(self):
        self.server_list = self.discover_all_servers()
        
        if self.server_list:
            self.discovered=True

    def get_server_list(self):
        return self.server_list
            
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
        
    def talk_to_server(self, ip="localhost", port=DEFAULT_PORT, url=None):
    
        response = requests.get("http://%s:%s%s" % (ip, port, url), params=self.plex_identification(), timeout=2)
        
        printDebug("URL was: %s" % response.url,self.DEBUG_DEBUG)
        
        if response.status_code == requests.codes.ok:
            printDebug("===XML===\n%s\n===XML===" % response.text, self.DEBUG_DEBUGPLUS)
            return response.text
     
    def discover_all_servers(self):
        printDebug("== ENTER ==", level=self.DEBUG_DEBUG)

        das_servers=[]
        das_server_index=0

        if self.settings.discovery == "1":
            printDebug("local GDM discovery setting enabled.")
            try:
                printDebug("Attempting GDM lookup on multicast")
                if self.settings.debug >= self.DEBUG_INFO:
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
                    printDebug("GDM discovery completed")
                    for device in gdm_server_name:

                        server=PlexMediaServer(name=device['serverName'],address=device['server'], port=device['port'], discovery='local')
                        server.refresh()
                        das_servers.append(server)
                else:
                    printDebug("GDM was not able to discover any servers")

            except Exception, e:
                print "PleXBMC -> GDM Issue [%s]" % e

        #Set to Disabled
        else:

            if self.settings.das_host:

                if not self.settings.das_port:
                    printDebug( "PleXBMC -> No port defined.  Using default of " + DEFAULT_PORT)
                    self.settings.das_port=DEFAULT_PORT

                printDebug( "PleXBMC -> Settings hostname and port: %s : %s" % ( self.settings.das_host, self.settings.das_port))

                local_server=PlexMediaServer(address=self.settings.das_host, port=self.settings.das_port, discovery='local')
                local_server.refresh()
                if local_server.discovered:
                    das_servers.append(local_server)

        if self.settings.myplex_user:
            printDebug( "PleXBMC -> Adding myplex as a server location")

            myplex_cache_file="myplex.server.cache"
            success, das_myplex = self.cache.checkCache(myplex_cache_file)

            if not success:
                das_myplex = self.get_myplex_servers()
                self.cache.writeCache(myplex_cache_file, das_myplex)

            if das_myplex:
                printDebug("MyPlex discovery completed")
                for device in das_myplex:

                    das_servers.append(device)

        # # # Remove Cloud Sync servers, since they cause problems
        # # for das_server_index,das_server in das_servers.items():
        # #     # Cloud sync "servers" don't have a version key in the dictionary
        # #     if 'version' not in das_server:
        # #         del das_servers[das_server_index]

        printDebug("PleXBMC -> serverList is: %s " % das_servers)

        return self.deduplicateServers(das_servers)

    def get_local_servers(self, ip_address="localhost", port=32400):
        '''
            Connect to the defined local server (either direct or via bonjour discovery)
            and get a list of all known servers.
            @input: nothing
            @return: a list of servers (as Dict)
        '''
        printDebug("== ENTER ==", level=self.DEBUG_DEBUG)
        
        url_path="/"
        html = self.talk_to_server(ip_address, port, url_path)

        if not html:
             return []

        server=etree.fromstring(html)

        return {'serverName': server.attrib['friendlyName'].encode('utf-8'),
                'server'    : ip_address,
                'port'      : port,
                'discovery' : 'local',
                'token'     : None ,
                'uuid'      : server.attrib['machineIdentifier'],
                'owned'     : '1',
                'master'    : 1,
                'class'     : server.get('machineIdentifier', 'primary')}

    def get_myplex_queue(self):
        printDebug("== ENTER ==", level=self.DEBUG_DEBUG)

        xml = self.getMyPlexURL('/pms/playlists/queue/all')

        if xml is False:
            return {}

        return xml

    def get_myplex_sections(self):
        printDebug("== ENTER ==", level=self.DEBUG_DEBUG)

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

        printDebug("== ENTER ==", level=self.DEBUG_DEBUG)

        tempServers = []
        url_path = "/pms/servers"

        xml = self.getMyPlexURL(url_path)

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

            tempServers.append(myplex_server)

        return tempServers
                                           
    def deduplicateServers( self, server_list ):
        '''
          Return list of all media sections configured
          within PleXBMC
          @input: None
          @Return: unique list of media servers
        '''
        printDebug("== ENTER ==", level=self.DEBUG_DEBUG)

        if len(server_list) <= 1:
            return server_list

        oneCount=0
        for onedevice in server_list:

            twoCount=0
            for twodevice in server_list:

                if oneCount == twoCount:
                    twoCount+=1
                    continue

                if onedevice.get_uuid() == twodevice.get_uuid():
                    if onedevice.get_discovery() == "auto" or onedevice.get_discovery() == "local":
                        server_list.pop(twoCount)
                    else:
                        server_list.pop(oneCount)

                twoCount+=1

            oneCount+=1

        printDebug ("Unique server List: %s" % server_list)

        self.server_list = server_list
        return self.server_list
        
    def getMyPlexURL(self, url_path, renew=False, suppress=True):
        '''
            Connect to the my.plexapp.com service and get an XML pages
            A seperate function is required as interfacing into myplex
            is slightly different than getting a standard URL
            @input: url to get, whether we need a new token, whether to display on screen err
            @return: an xml page as string or false
        '''
        printDebug("== ENTER ==", level=self.DEBUG_DEBUG)
        printDebug("url = "+self.myplex_server+url_path)

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
            printDebug("====== XML returned =======", level=self.DEBUG_DEBUGPLUS)
            printDebug(link, level=self.DEBUG_DEBUGPLUS)
            printDebug("====== XML finished ======", level=self.DEBUG_DEBUGPLUS)
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
        printDebug("== ENTER ==", level=self.DEBUG_DEBUG)

        if self.myplex_token is None:
        
            try:
                user, token = self.settings.myplex_token.split('|')
            except:
                token = None

            if (token is None) or (renew) or (user != self.settings.myplex_user):
                self.myplex_token = self.getNewMyPlexToken()

            printDebug("Using token: " + str(self.myplex_token) + "[Renew: " + str(renew) + "]")
        return { 'X-Plex-Token' : self.myplex_token }

    def getNewMyPlexToken(self,suppress=True, title="Error"):
        printDebug("== ENTER ==", level=self.DEBUG_DEBUG)

        printDebug("Getting New token")
        if not self.settings.myplex_user:
            printDebug("No myplex details in config..")
            return None

        base64string = base64.encodestring('%s:%s' % (self.settings.myplex_user, self.settings.myplex_pass)).replace('\n', '')
        txdata = ""
        token = False

        myplex_headers={'Authorization': "Basic %s" % base64string}

        response = requests.post("%s/users/sign_in.xml" % self.myplex_server, headers=dict(self.plex_identification(), **myplex_headers))
        print response.status_code
        
        if response.status_code == 201:
            try:
                print response.text
                token = etree.fromstring(response.text).findtext('authentication-token')
                settings.update_token(token)
            except:
                printDebug(response.text, level=self.DEBUG_DEBUGPLUS)

            printDebug("====== XML finished ======")
        
        else:
            error = "HTTP response error: %s %s" % (response.status_code, response.reason)
            if suppress is False:
                xbmcgui.Dialog().ok(title, error)
            print error
            return None
        # except socket.gaierror :
            # error = 'Unable to lookup host: MyPlex' + "\nCheck host name is correct"
            # if suppress is False:
                # xbmcgui.Dialog().ok(title, error)
            # print error
            # return ""
        # except socket.error, msg:
            # error="Unable to connect to MyPlex" + "\nReason: " + str(msg)
            # if suppress is False:
                # xbmcgui.Dialog().ok(title, error)
            # print error
            # return ""

        return token


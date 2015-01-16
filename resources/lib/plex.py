import xbmcaddon
import xbmc
import xbmcgui
import sys
import os
import xml.etree.ElementTree as etree
import base64

__addon__    = xbmcaddon.Addon()
__cachedir__ = __addon__.getAddonInfo('profile')
__cwd__      = xbmc.translatePath(__addon__.getAddonInfo('path')).decode('utf-8')

__resources__ = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib'))
sys.path.append(__resources__)

import plexgdm
from settings import addonSettings
from common import *
import CacheControl
import requests

DEFAULT_PORT="32400"

class Plex:

    def __init__(self, settings=None, cache=None):
    
        #Welcome to the Plex Network
        #Will start by looking for some media servers
        if not settings:
            self.settings = addonSettings('plugin.video.plexbmc')
        else:
            self.settings = settings
            
        self.cache=CacheControl.CacheControl(__cachedir__+"cache/servers", self.settings.debug)
        self.DEBUG_OFF=0
        self.DEBUG_INFO=1
        self.DEBUG_DEBUG=2
        self.DEBUG_DEBUGPLUS=3
        self.my_plex_token=None
        self.logged_into_myplex=False
        self.server_list=[]
        self.discovered=False
        
        print self.getMyPlexToken()
        
    def discover(self):
        self.server_list = self.discover_all_servers()
        
        if self.server_list:
            self.discovered=True

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
                'X-Plex-Token'             : self.my_plex_token}
        
    def talk_to_server(self, ip="localhost", port=DEFAULT_PORT, url=None):
    
        response = requests.get("http://%s:%s%s" % (ip, port, url), params=self.plex_identification(), timeout=2)
        
        printDebug("URL was: %s" % response.url,self.DEBUG_DEBUG)
        
        if response.status_code == requests.codes.ok:
            printDebug("===XML===\n%s\n===XML===" % response.text, self.DEBUG_DEBUGPLUS)
            return response.text
     
    def discover_all_servers(self):

        # Take the users settings and add the required master servers
        # to the server list.  These are the devices which will be queried
        # for complete library listings.  There are 3 types:
            # local server - from IP configuration
            # gdm server - from a gdm lookup
            # myplex server - from myplex configuration
        # Alters the global g_serverDict value
        # @input: None
        # @return: None

        printDebug("== ENTER ==", level=self.DEBUG_DEBUG)

        das_servers={}
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

                        das_servers[das_server_index] = device
                        das_server_index = das_server_index + 1
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

                local_server = self.getLocalServers(self.settings.das_host, self.settings.das_port)
                if local_server:
                    das_servers[das_server_index] = local_server
                    das_server_index = das_server_index + 1

        if self.settings.myplex_user:
            printDebug( "PleXBMC -> Adding myplex as a server location")

            myplex_cache_file="myplex.server.cache"
            success, das_myplex = cache.checkCache(myplex_cache_file)

            if not success:
                das_myplex = getMyPlexServers()
                self.cache.writeCache(myplex_cache_file, das_myplex)

            if das_myplex:
                printDebug("MyPlex discovery completed")
                for device in das_myplex:

                    das_servers[das_server_index] = device
                    das_server_index = das_server_index + 1

        # # # Remove Cloud Sync servers, since they cause problems
        # # for das_server_index,das_server in das_servers.items():
        # #     # Cloud sync "servers" don't have a version key in the dictionary
        # #     if 'version' not in das_server:
        # #         del das_servers[das_server_index]

        printDebug("PleXBMC -> serverList is " + str(das_servers))

        return self.deduplicateServers(das_servers)

    def getLocalServers(self, ip_address="localhost", port=32400):
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
                'class'     : ''}

    def getMyPlexServers(self):
        '''
            Connect to the myplex service and get a list of all known
            servers.
            @input: nothing
            @return: a list of servers (as Dict)
        '''

        printDebug("== ENTER ==", level=self.DEBUG_DEBUG)

        tempServers = []
        url_path = "/pms/servers"

        xml = getMyPlexURL(url_path)

        if xml is False:
            return {}

        servers = etree.fromstring(xml)

        count = 0
        for server in servers:
            #data = dict(server.items())

            if server.get('owned', None) == "1":
                owned = '1'
                if count == 0:
                    master = 1
                    count =- 1
                accessToken = getMyPlexToken()
            else:
                owned = '0'
                master = 0
                accessToken = server.get('accessToken')

            tempServers.append({'serverName': server.get('name').encode('utf-8'),
                                'server'    : server.get('address'),
                                'port'      : server.get('port'),
                                'discovery' : 'myplex',
                                'token'     : accessToken,
                                'uuid'      : server.get('machineIdentifier'),
                                'owned'     : owned,
                                'master'    : master,
                                'class'     : ""})

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

        temp_list=server_list.values()
        oneCount=0
        for onedevice in temp_list:

            twoCount=0
            for twodevice in temp_list:

                if oneCount == twoCount:
                    twoCount+=1
                    continue

                if onedevice['uuid'] == twodevice['uuid']:
                    if onedevice['discovery'] == "auto" or onedevice['discovery'] == "local":
                        temp_list.pop(twoCount)
                    else:
                        temp_list.pop(oneCount)

                twoCount+=1

            oneCount+=1


        count=0
        unique_list={}
        for i in temp_list:
            unique_list[count] = i
            count = count + 1

        printDebug ("Unique server List: " + str(unique_list))

        return unique_list
        
    def getMyPlexURL(url_path, renew=False, suppress=True):
        '''
            Connect to the my.plexapp.com service and get an XML pages
            A seperate function is required as interfacing into myplex
            is slightly different than getting a standard URL
            @input: url to get, whether we need a new token, whether to display on screen err
            @return: an xml page as string or false
        '''
        printDebug("== ENTER ==", level=DEBUG_DEBUG)
        printDebug("url = "+MYPLEX_SERVER+url_path)

        try:
            conn = httplib.HTTPSConnection(MYPLEX_SERVER, timeout=10)
            conn.request("GET", url_path+"?X-Plex-Token="+getMyPlexToken(renew))
            data = conn.getresponse()
            if ( int(data.status) == 401 )  and not ( renew ):
                try: conn.close()
                except: pass
                return getMyPlexURL(url_path,True)

            if int(data.status) >= 400:
                error = "HTTP response error: " + str(data.status) + " " + str(data.reason)
                if suppress is False:
                    xbmcgui.Dialog().ok("Error",error)
                print error
                try: conn.close()
                except: pass
                return False
            elif int(data.status) == 301 and type == "HEAD":
                try: conn.close()
                except: pass
                return str(data.status)+"@"+data.getheader('Location')
            else:
                link=data.read()
                printDebug("====== XML returned =======", level=DEBUG_DEBUGPLUS)
                printDebug(link, level=DEBUG_DEBUGPLUS)
                printDebug("====== XML finished ======", level=DEBUG_DEBUGPLUS)
        except socket.gaierror :
            error = 'Unable to lookup host: ' + MYPLEX_SERVER + "\nCheck host name is correct"
            if suppress is False:
                xbmcgui.Dialog().ok("Error",error)
            print error
            return False
        except socket.error, msg :
            error="Unable to connect to " + MYPLEX_SERVER +"\nReason: " + str(msg)
            if suppress is False:
                xbmcgui.Dialog().ok("Error",error)
            print error
            return False
        else:
            try: conn.close()
            except: pass

        if link:
            return link
        else:
            return False        
    
    def getMyPlexToken(self,renew=False):
        '''
            Get the myplex token.  If the user ID stored with the token
            does not match the current userid, then get new token.  This stops old token
            being used if plex ID is changed. If token is unavailable, then get a new one
            @input: whether to get new token
            @return: myplex token
        '''
        printDebug("== ENTER ==", level=self.DEBUG_DEBUG)

        try:
            user, token = self.settings.myplex_token.split('|')
        except:
            token = None

        if (token is None) or (renew) or (user != self.settings.myplex_user):
            token = self.getNewMyPlexToken()

        printDebug("Using token: " + str(token) + "[Renew: " + str(renew) + "]")
        return token

    def getNewMyPlexToken(self,suppress=True, title="Error"):
        '''
            Get a new myplex token from myplex API
            @input: nothing
            @return: myplex token
        '''

        printDebug("== ENTER ==", level=self.DEBUG_DEBUG)

        printDebug("Getting New token")
        if not self.settings.myplex_user:
            printDebug("No myplex details in config..")
            return ""

        base64string = base64.encodestring('%s:%s' % (self.settings.myplex_user, self.settings.myplex_pass)).replace('\n', '')
        txdata = ""
        token = False

        myplex_headers={'Authorization': "Basic %s" % base64string}

        response = requests.post("https://my.plexapp.com/users/sign_in.xml", headers=dict(self.plex_identification(), **myplex_headers))
        print response.status_code
        
        if response.status_code == 201:
            try:
                print response.text
                token = etree.fromstring(response.text).findtext('authentication-token')
                #__settings__.setSetting('myplex_token', myplex_username + "|" + token)
            except:
                printDebug(response.text, level=self.DEBUG_DEBUGPLUS)

            printDebug("====== XML finished ======")
        
        else:
            error = "HTTP response error: %s %s" % (response.status_code, response.reason)
            if suppress is False:
                xbmcgui.Dialog().ok(title, error)
            print error
            return ""
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


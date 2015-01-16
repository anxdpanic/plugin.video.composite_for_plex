'''
    @document   : default.py
    @package    : PleXBMC add-on
    @author     : Hippojay (aka Dave Hawes-Johnson)
    @copyright  : 2011-2012, Hippojay
    @version    : 3.0 (frodo)

    @license    : Gnu General Public License - see LICENSE.TXT
    @description: pleXBMC XBMC add-on

    This file is part of the XBMC PleXBMC Plugin.

    PleXBMC Plugin is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 2 of the License, or
    (at your option) any later version.

    PleXBMC Plugin is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with PleXBMC Plugin.  If not, see <http://www.gnu.org/licenses/>.

'''

import urllib
import urlparse
import re
import xbmcplugin
import xbmcgui
import xbmcaddon
import httplib
import socket
import sys
import os
import time
import base64
import random
import xbmc
import datetime
import xml.etree.ElementTree as etree

print "===== PLEXBMC START ====="

__addon__    = xbmcaddon.Addon()
__plugin__   = __addon__.getAddonInfo('name')
__version__  = __addon__.getAddonInfo('version')
__cachedir__ = __addon__.getAddonInfo('profile')
__settings__ = xbmcaddon.Addon(id='plugin.video.plexbmc')
__cwd__      = xbmc.translatePath(__addon__.getAddonInfo('path')).decode('utf-8')

BASE_RESOURCE_PATH = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib'))
PLUGINPATH = xbmc.translatePath(os.path.join(__cwd__))
sys.path.append(BASE_RESOURCE_PATH)

from settings import addonSettings
import CacheControl
from common import *
import plex
network=plex.Plex()
#network.discover()
#print network.discovered
#Get the setting from the appropriate file.
DEFAULT_PORT="32400"
MYPLEX_SERVER="my.plexapp.com"
_MODE_GETCONTENT=0
_MODE_TVSHOWS=1
_MODE_MOVIES=2
_MODE_ARTISTS=3
_MODE_TVSEASONS=4
_MODE_PLAYLIBRARY=5
_MODE_TVEPISODES=6
_MODE_PLEXPLUGINS=7
_MODE_PROCESSXML=8
_MODE_CHANNELSEARCH=9
_MODE_CHANNELPREFS=10
_MODE_PLAYSHELF=11
_MODE_BASICPLAY=12
_MODE_SHARED_MOVIES=13
_MODE_ALBUMS=14
_MODE_TRACKS=15
_MODE_PHOTOS=16
_MODE_MUSIC=17
_MODE_VIDEOPLUGINPLAY=18
_MODE_PLEXONLINE=19
_MODE_CHANNELINSTALL=20
_MODE_CHANNELVIEW=21
_MODE_DISPLAYSERVERS=22
_MODE_PLAYLIBRARY_TRANSCODE=23
_MODE_MYPLEXQUEUE=24
_MODE_SHARED_SHOWS=25
_MODE_SHARED_MUSIC=26
_MODE_SHARED_PHOTOS=27
_MODE_DELETE_REFRESH=28
_MODE_SHARED_ALL=29
_MODE_PLAYLISTS=30

_SUB_AUDIO_XBMC_CONTROL="0"
_SUB_AUDIO_PLEX_CONTROL="1"
_SUB_AUDIO_NEVER_SHOW="2"

DEBUG_OFF=0
DEBUG_INFO=1
DEBUG_DEBUG=2
DEBUG_DEBUGPLUS=3

DEBUG_MAP={ DEBUG_OFF : "off",
            DEBUG_INFO : "info",
            DEBUG_DEBUG : "debug",
            DEBUG_DEBUGPLUS : "debug+"}

settings=addonSettings('plugin.video.plexbmc')
print settings.__dict__

CACHE=CacheControl.CacheControl(__cachedir__+"cache", settings.debug)

        
print "PleXBMC -> Running Python: %s" % sys.version_info
print "PleXBMC -> Running PleXBMC: %s " % __version__
print "PleXBMC -> CWD is set to: %s" % __cwd__
print "PleXBMC -> Platform: %s" % getPlatform()

wake_servers()

if settings.debug >= DEBUG_INFO:
    print "PleXBMC -> Setting debug: %s" % DEBUG_MAP[settings.debug]
    print "PleXBMC -> FullRes Thumbs are set to: %s" % settings.fullres_thumbnails
    print "PleXBMC -> Settings streaming: %s" % settings.stream
    print "PleXBMC -> Setting filter menus: %s" % settings.secondary
    print "PleXBMC -> Flatten is: %s" % settings.flatten
    if settings.streamControl == _SUB_AUDIO_XBMC_CONTROL:
        print "PleXBMC -> Setting stream Control to : XBMC CONTROL"
    elif settings.streamControl == _SUB_AUDIO_PLEX_CONTROL:
        print "PleXBMC -> Setting stream Control to : PLEX CONTROL"
    elif settings.streamControl == _SUB_AUDIO_NEVER_SHOW:
        print "PleXBMC -> Setting stream Control to : NEVER SHOW"

    print "PleXBMC -> Force DVD playback: %s" % settings.forcedvd
    print "PleXBMC -> SMB IP Override: %s" % settings.nasoverride
    if settings.nasoverride and not settings.nasoverrideip:
        print "PleXBMC -> No NAS IP Specified.  Ignoring setting"
    else:
        print "PleXBMC -> NAS IP: " + settings.nasoverrideip
else:
    print "PleXBMC -> Debug is turned off.  Running silent"

g_thumb = "special://home/addons/plugin.video.plexbmc/resources/thumb.png"

#Set up holding variable for session ID
global g_sessionID
g_sessionID=None
        
#Move to discovery code
def discoverAllServers( ):
    '''
        Take the users settings and add the required master servers
        to the server list.  These are the devices which will be queried
        for complete library listings.  There are 3 types:
            local server - from IP configuration
            bonjour server - from a bonjour lookup
            myplex server - from myplex configuration
        Alters the global g_serverDict value
        @input: None
        @return: None
    '''
    printDebug("== ENTER ==", level=DEBUG_DEBUG)

    das_servers={}
    das_server_index=0

    if settings.discovery == "1":
        printDebug("PleXBMC -> local GDM discovery setting enabled.")
        try:
            import plexgdm
            printDebug("Attempting GDM lookup on multicast")
            if settings.debug >= DEBUG_INFO:
                GDM_debug=3
            else:
                GDM_debug=0

            gdm_cache_file="gdm.server.cache"
            gdm_cache_ok = False

            gdm_cache_ok, gdm_server_name = CACHE.checkCache(gdm_cache_file)

            if not gdm_cache_ok:
                gdm_client = plexgdm.plexgdm(GDM_debug)
                gdm_client.discover()
                gdm_server_name = gdm_client.getServerList()

                CACHE.writeCache(gdm_cache_file, gdm_server_name)

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

        if settings.das_host:

            if not settings.das_port:
                printDebug( "PleXBMC -> No port defined.  Using default of " + DEFAULT_PORT)
                settings.das_port=DEFAULT_PORT

            printDebug( "PleXBMC -> Settings hostname and port: %s : %s" % ( settings.das_host, settings.das_port))

            local_server = getLocalServers(settings.das_host, settings.das_port)
            if local_server:
                das_servers[das_server_index] = local_server
                das_server_index = das_server_index + 1

    if settings.myplex_user:
        printDebug( "PleXBMC -> Adding myplex as a server location")

        myplex_cache_file="myplex.server.cache"
        success, das_myplex = CACHE.checkCache(myplex_cache_file)

        if not success:
            das_myplex = getMyPlexServers()
            CACHE.writeCache(myplex_cache_file, das_myplex)

        if das_myplex:
            printDebug("MyPlex discovery completed")
            for device in das_myplex:

                das_servers[das_server_index] = device
                das_server_index = das_server_index + 1

    # # Remove Cloud Sync servers, since they cause problems
    # for das_server_index,das_server in das_servers.items():
    #     # Cloud sync "servers" don't have a version key in the dictionary
    #     if 'version' not in das_server:
    #         del das_servers[das_server_index]

    printDebug("PleXBMC -> serverList is " + str(das_servers))

    return deduplicateServers(das_servers)

def getLocalServers(ip_address="localhost", port=32400):
    '''
        Connect to the defined local server (either direct or via bonjour discovery)
        and get a list of all known servers.
        @input: nothing
        @return: a list of servers (as Dict)
    '''
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    
    url_path="/"
    html = getURL(ip_address+":"+port+url_path)

    if html is False:
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

def getMyPlexServers( ):
    '''
        Connect to the myplex service and get a list of all known
        servers.
        @input: nothing
        @return: a list of servers (as Dict)
    '''

    printDebug("== ENTER ==", level=DEBUG_DEBUG)

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
                                       
def deduplicateServers( server_list ):
    '''
      Return list of all media sections configured
      within PleXBMC
      @input: None
      @Return: unique list of media servers
    '''
    printDebug("== ENTER ==", level=DEBUG_DEBUG)

    if len(server_list) <= 1:
        return server_list

    temp_list=server_list.values()
    oneCount=0
    for onedevice in temp_list:

        twoCount=0
        for twodevice in temp_list:

            #printDebug( "["+str(oneCount)+":"+str(twoCount)+"] Checking " + onedevice['uuid'] + " and " + twodevice['uuid'])

            if oneCount == twoCount:
                #printDebug( "skip" )
                twoCount+=1
                continue

            if onedevice['uuid'] == twodevice['uuid']:
                #printDebug ( "match" )
                if onedevice['discovery'] == "auto" or onedevice['discovery'] == "local":
                    temp_list.pop(twoCount)
                else:
                    temp_list.pop(oneCount)
            #else:
            #    printDebug( "no match" )

            twoCount+=1

        oneCount+=1


    count=0
    unique_list={}
    for i in temp_list:
        unique_list[count] = i
        count = count + 1

    printDebug ("Unique server List: " + str(unique_list))

    return unique_list

def getServerSections (ip_address, port, name, uuid):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)

    cache_file = "%s.sections.cache" % (uuid)
    success, temp_list = CACHE.checkCache(cache_file)
    
    if not success:
    
        html=getURL('http://%s:%s/library/sections' % ( ip_address, port))

        if html is False:
            return {}

        sections = etree.fromstring(html)
        temp_list = []
        for section in sections:
        
            path = section.get('key')
            if not path[0] == "/":
                path = '/library/sections/%s' % path

            temp_list.append( {'title': section.get('title', 'Unknown').encode('utf-8'),
                    'address'    : ip_address + ":" + port,
                    'serverName' : name,
                    'uuid'       : uuid,
                    'sectionuuid' : section.get('uuid', ''),
                    'path'       : path,
                    'token'      : section.get('accessToken', None),
                    'location'   : "local",
                    'art'        : section.get('art', None),
                    'local'      : '1',
                    'type'       : section.get('type', ''),
                    'owned'      : '1'})
                
            
        CACHE.writeCache(cache_file, temp_list)
        
    return temp_list            

def getMyplexSections ( ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    
    cache_file = "myplex.sections.cache"
    success, temp_list = CACHE.checkCache(cache_file)
    
    if not success:
    
        html=getMyPlexURL('/pms/system/library/sections')

        if html is False:
            return {}

        tree = etree.fromstring(html).getiterator("Directory")
        temp_list=[]
        for sections in tree:

            temp_list.append( {'title'      : sections.get('title','Unknown').encode('utf-8'),
                    'address'    : sections.get('host','Unknown')+":"+sections.get('port'),
                    'serverName' : sections.get('serverName','Unknown').encode('utf-8'),
                    'uuid'       : sections.get('machineIdentifier','Unknown') ,
                    'sectionuuid' : sections.get('uuid','').encode('utf-8'),
                    'path'       : sections.get('path') ,
                    'token'      : sections.get('accessToken',None) ,
                    'location'   : "myplex" ,
                    'art'        : sections.get('art') ,
                    'local'      : sections.get('local') ,
                    'type'       : sections.get('type','Unknown'),
                    'owned'      : sections.get('owned','0') })
                    
        CACHE.writeCache(cache_file, temp_list)
        
    return temp_list            

def getAllSections( server_list = None ):
    '''
        from server_list, get a list of all the available sections
        and deduplicate the sections list
        @input: None
        @return: None (alters the global value g_sectionList)
    '''
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    
    if server_list is None:
        server_list = discoverAllServers()
    
    printDebug("Using servers list: " + str(server_list))

    section_list=[]
    myplex_section_list=[]
    myplex_complete=False
    local_complete=False
    
    for server in server_list.itervalues():

        if server['discovery'] == "local" or server['discovery'] == "auto":
            section_details = getServerSections(server['server'], server['port'], server['serverName'], server['uuid'])
            section_list += section_details
            local_complete=True
            
        elif server['discovery'] == "myplex":
            if not myplex_complete:
                section_details = getMyplexSections()
                myplex_section_list += section_details
                myplex_complete = True

    '''
    logfile = PLUGINPATH + "/_section_list.txt"
    with open(logfile, 'wb') as f:
        f.write(str(section_list))

    logfile = PLUGINPATH + "/_myplex_section_list.txt"
    with open(logfile, 'wb') as f:
        f.write(str(myplex_section_list))
    '''

    #Remove any myplex sections that are locally available
    if myplex_complete and local_complete:
    
        printDebug ("Deduplicating myplex sections list")
    
        for each_server in server_list.values():
        
            printDebug ("Checking server [%s]" % each_server)
            
            if each_server['discovery'] == 'myplex':
                printDebug ("Skipping as a myplex server")
                continue
                    
            myplex_section_list = [x for x in myplex_section_list if not x['uuid'] == each_server['uuid']]
            
    section_list += myplex_section_list

    '''
    logfile = PLUGINPATH + "/_final_section_list.txt"
    with open(logfile, 'wb') as f:
        f.write(str(section_list))
    '''

    return section_list

def getAuthDetails( details, url_format=True, prefix="&" ):
    '''
        Takes the token and creates the required arguments to allow
        authentication.  This is really just a formatting tools
        @input: token as dict, style of output [opt] and prefix style [opt]
        @return: header string or header dict
    '''
    token = details.get('token', None)

    if url_format:
        if token:
            return prefix+"X-Plex-Token="+str(token)
        else:
            return ""
    else:
        if token:
            return {'X-Plex-Token' : token }
        else:
            return {}

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

def getMyPlexToken(renew=False):
    '''
        Get the myplex token.  If the user ID stored with the token
        does not match the current userid, then get new token.  This stops old token
        being used if plex ID is changed. If token is unavailable, then get a new one
        @input: whether to get new token
        @return: myplex token
    '''
    printDebug("== ENTER ==", level=DEBUG_DEBUG)

    try:
        user, token = (__settings__.getSetting('myplex_token')).split('|')
    except:
        token = None

    if (token is None) or (renew) or (user != __settings__.getSetting('myplex_user')):
        token = getNewMyPlexToken()

    printDebug("Using token: " + str(token) + "[Renew: " + str(renew) + "]")
    return token

def getNewMyPlexToken(suppress=True, title="Error"):
    '''
        Get a new myplex token from myplex API
        @input: nothing
        @return: myplex token
    '''

    printDebug("== ENTER ==", level=DEBUG_DEBUG)

    printDebug("Getting New token")
    myplex_username = __settings__.getSetting('myplex_user')
    myplex_password = __settings__.getSetting('myplex_pass')

    if (myplex_username or myplex_password) == "":
        printDebug("No myplex details in config..")
        return ""

    base64string = base64.encodestring('%s:%s' % (myplex_username, myplex_password)).replace('\n', '')
    txdata = ""
    token = False

    myplex_headers={'X-Plex-Platform': "XBMC",
                    'X-Plex-Platform-Version': "12.00/Frodo",
                    'X-Plex-Provides': "player",
                    'X-Plex-Product': "PleXBMC",
                    'X-Plex-Version': __version__,
                    'X-Plex-Device': getPlatform(),
                    'X-Plex-Client-Identifier': "PleXBMC",
                    'Authorization': "Basic %s" % base64string}

    try:
        conn = httplib.HTTPSConnection(MYPLEX_SERVER)
        conn.request("POST", "/users/sign_in.xml", txdata, myplex_headers)
        data = conn.getresponse()

        if int(data.status) == 201:
            link = data.read()
            printDebug("====== XML returned =======")

            try:
                token = etree.fromstring(link).findtext('authentication-token')
                __settings__.setSetting('myplex_token', myplex_username + "|" + token)
            except:
                printDebug(link)

            printDebug("====== XML finished ======")
        else:
            error = "HTTP response error: " + str(data.status) + " " + str(data.reason)
            if suppress is False:
                xbmcgui.Dialog().ok(title, error)
            print error
            return ""
    except socket.gaierror :
        error = 'Unable to lookup host: MyPlex' + "\nCheck host name is correct"
        if suppress is False:
            xbmcgui.Dialog().ok(title, error)
        print error
        return ""
    except socket.error, msg:
        error="Unable to connect to MyPlex" + "\nReason: " + str(msg)
        if suppress is False:
            xbmcgui.Dialog().ok(title, error)
        print error
        return ""

    return token

def getURL(url, suppress=True, type="GET", popup=0):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    try:
        if url[0:4] == "http":
            serversplit=2
            urlsplit=3
        else:
            serversplit=0
            urlsplit=1

        server=url.split('/')[serversplit]
        urlPath="/"+"/".join(url.split('/')[urlsplit:])

        authHeader=getAuthDetails({'token':_PARAM_TOKEN}, url_format=False)

        printDebug("url = "+url)
        printDebug("header = "+str(authHeader))
        conn = httplib.HTTPConnection(server, timeout=10)
        conn.request(type, urlPath, headers=authHeader)
        data = conn.getresponse()
        
        if int(data.status) == 200:
            link=data.read()
            printDebug("====== XML returned =======", level=DEBUG_DEBUGPLUS)
            printDebug(link, level=DEBUG_DEBUGPLUS)
            printDebug("====== XML finished ======", level=DEBUG_DEBUGPLUS)
            try: conn.close()
            except: pass
            return link

        elif ( int(data.status) == 301 ) or ( int(data.status) == 302 ):
            try: conn.close()
            except: pass
            return data.getheader('Location')

        elif int(data.status) == 401:
            error = "Authentication error on server [%s].  Check user/password." % server
            print "PleXBMC -> %s" % error
            if suppress is False:
                if popup == 0:
                    xbmc.executebuiltin("XBMC.Notification(Server authentication error,)")
                else:
                    xbmcgui.Dialog().ok("PleXBMC","Authentication require or incorrect")
                    
        elif int(data.status) == 404:
            error = "Server [%s] XML/web page does not exist." % server
            print "PleXBMC -> %s" % error
            if suppress is False:
                if popup == 0:
                    xbmc.executebuiltin("XBMC.Notification(Server web/XML page error,)")
                else:
                    xbmcgui.Dialog().ok("PleXBMC","Server error, data does not exist")
                    
        elif int(data.status) >= 400:
            error = "HTTP response error: " + str(data.status) + " " + str(data.reason)
            print error
            if suppress is False:
                if popup == 0:
                    xbmc.executebuiltin("XBMC.Notification(URL error: "+ str(data.reason) +",)")
                else:
                    xbmcgui.Dialog().ok("Error",server)
                    
        else:
            link=str(data.read())
            printDebug("====== XML returned =======", level=DEBUG_DEBUGPLUS)
            printDebug(link, level=DEBUG_DEBUGPLUS)
            printDebug("====== XML finished ======", level=DEBUG_DEBUGPLUS)
            try: conn.close()
            except: pass
            return link
            
    except socket.gaierror :
        error = "Unable to locate host [%s]\nCheck host name is correct" % server
        print "PleXBMC %s" % error
        if suppress is False:
            if popup==0:
                xbmc.executebuiltin("XBMC.Notification(\"PleXBMC\": Server name incorrect,)")
            else:
                xbmcgui.Dialog().ok("PleXBMC","Server [%s] not found" % server)
        
    except socket.error, msg :
        error="Server[%s] is offline, or not responding\nReason: %s" % (server, str(msg))
        print "PleXBMC -> %s" % error
        if suppress is False:
            if popup == 0:
                xbmc.executebuiltin("XBMC.Notification(\"PleXBMC\": Server offline or not responding,)")
            else:
                xbmcgui.Dialog().ok("PleXBMC","Server is offline or not responding")

    try: conn.close()
    except: pass
    
    return False

def mediaType( partData, server, dvdplayback=False ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    stream=partData['key']
    file=partData['file']

    if ( file is None ) or ( settings.stream == "1" ):
        printDebug( "Selecting stream")
        return "http://"+server+stream

    #First determine what sort of 'file' file is

    if file[0:2] == "\\\\":
        printDebug("Looks like a UNC")
        type="UNC"
    elif file[0:1] == "/" or file[0:1] == "\\":
        printDebug("looks like a unix file")
        type="nixfile"
    elif file[1:3] == ":\\" or file[1:2] == ":/":
        printDebug("looks like a windows file")
        type="winfile"
    else:
        printDebug("uknown file type")
        printDebug(str(file))
        type="notsure"

    # 0 is auto select.  basically check for local file first, then stream if not found
    if settings.stream == "0":
        #check if the file can be found locally
        if type == "nixfile" or type == "winfile":
            try:
                printDebug("Checking for local file")
                exists = open(file, 'r')
                printDebug("Local file found, will use this")
                exists.close()
                return "file:"+file
            except: pass

        printDebug("No local file")
        if dvdplayback:
            printDebug("Forcing SMB for DVD playback")
            settings.stream="2"
        else:
            return "http://"+server+stream


    # 2 is use SMB
    elif settings.stream == "2" or settings.stream == "3":
        if settings.stream == "2":
            protocol="smb"
        else:
            protocol="afp"

        printDebug( "Selecting smb/unc")
        if type=="UNC":
            filelocation=protocol+":"+file.replace("\\","/")
        else:
            #Might be OSX type, in which case, remove Volumes and replace with server
            server=server.split(':')[0]
            loginstring=""

            if settings.nasoverride:
                if settings.nasoverrideip:
                    server=settings.nasoverrideip
                    printDebug("Overriding server with: " + server)

                if settings.nasuserid:
                    loginstring="%s:%s@" % (settings.nasuserid, settings.naspass)
                    printDebug("Adding AFP/SMB login info for user: %s" % settings.nasuserid)


            if file.find('Volumes') > 0:
                filelocation=protocol+":/"+file.replace("Volumes",loginstring+server)
            else:
                if type == "winfile":
                    filelocation=protocol+"://"+loginstring+server+"/"+file[3:]
                else:
                    #else assume its a file local to server available over smb/samba (now we have linux PMS).  Add server name to file path.
                    filelocation=protocol+"://"+loginstring+server+file

        if settings.nasoverride and settings.nasroot:
            #Re-root the file path
            printDebug("Altering path " + filelocation + " so root is: " +  settings.nasroot)
            if '/'+settings.nasroot+'/' in filelocation:
                components = filelocation.split('/')
                index = components.index(settings.nasroot)
                for i in range(3,index):
                    components.pop(3)
                filelocation='/'.join(components)
    else:
        printDebug( "No option detected, streaming is safest to choose" )
        filelocation="http://"+server+stream

    printDebug("Returning URL: " + filelocation)
    return filelocation

def appendURLArgument(url, arguments):
    '''add a dict of arguments to a URL safely '''
    
    url_parts = urlparse.urlparse(url)

    query_args = urlparse.parse_qsl(url_parts.query)
    query_args += arguments.items()

    new_query_args = urllib.urlencode(query_args, True)

    return urlparse.urlunparse((url_parts.scheme, url_parts.netloc, url_parts.path, url_parts.params, new_query_args, url_parts.fragment))
    
def addGUIItem(url, details, extraData, context=None, folder=True):

        item_title = details.get('title', 'Unknown')

        printDebug("== ENTER ==", level=DEBUG_DEBUG)
        printDebug("Adding Dir for [%s]" % item_title)
        printDebug("Passed details: " + str(details))
        printDebug("Passed extraData: " + str(extraData))

        #Remove, as this is never going to evaluate as true
        #if item_title == '':
        #    return

        if (extraData.get('token',None) is None) and _PARAM_TOKEN:
            extraData['token']=_PARAM_TOKEN

        aToken=getAuthDetails(extraData)
        nToken=getAuthDetails(extraData,url_format=False)
        qToken=getAuthDetails(extraData, prefix='?')

        if extraData.get('mode',None) is None:
            mode="&mode=0"
        else:
            mode="&mode=%s" % extraData['mode']

        #Create the URL to pass to the item
        if ( not folder) and ( extraData['type'] == "image" ):
             u=url+qToken
        elif url.startswith('http') or url.startswith('file'):
            u=sys.argv[0]+"?url="+urllib.quote(url)+mode+aToken
        else:
            u=sys.argv[0]+"?url="+str(url)+mode+aToken
            
        if extraData.get('parameters'):
            for argument, value in extraData.get('parameters').items():
                u = "%s&%s=%s" % (u, argument, urllib.quote(value))

        printDebug("URL to use for listing: " + u)

        thumb = str(extraData.get('thumb', ''))
        if thumb.startswith('http'):
            thumbPath = appendURLArgument(thumb,nToken)
        else:
            thumbPath = thumb

        liz=xbmcgui.ListItem(item_title, thumbnailImage=thumbPath)

        printDebug("Setting thumbnail as " + thumbPath)

        #Set the properties of the item, such as summary, name, season, etc
        liz.setInfo(type=extraData.get('type','Video'), infoLabels=details )

        #Music related tags
        if extraData.get('type','').lower() == "music":
            liz.setProperty('Artist_Genre', details.get('genre',''))
            liz.setProperty('Artist_Description', extraData.get('plot',''))
            liz.setProperty('Album_Description', extraData.get('plot',''))

        if extraData.get('type','').lower() == "video":
            liz.setInfo( type="Video", infoLabels={ "DateAdded": extraData.get('dateadded','')})

        #For all end items    
        if ( not folder):
            liz.setProperty('IsPlayable', 'true')

            if extraData.get('type','video').lower() == "video":
                liz.setProperty('TotalTime', str(extraData.get('duration')))
                liz.setProperty('ResumeTime', str(extraData.get('resume')))

                if not settings.skipmediaflags:
                    printDebug("Setting VrR as : %s" % extraData.get('VideoResolution',''))
                    liz.setProperty('VideoResolution', extraData.get('VideoResolution',''))
                    liz.setProperty('VideoCodec', extraData.get('VideoCodec',''))
                    liz.setProperty('AudioCodec', extraData.get('AudioCodec',''))
                    liz.setProperty('AudioChannels', extraData.get('AudioChannels',''))
                    liz.setProperty('VideoAspect', extraData.get('VideoAspect',''))

                    video_codec={}
                    if extraData.get('xbmc_VideoCodec'): video_codec['codec'] = extraData.get('xbmc_VideoCodec')
                    if extraData.get('xbmc_VideoAspect') : video_codec['aspect'] = float(extraData.get('xbmc_VideoAspect'))
                    if extraData.get('xbmc_height') : video_codec['height'] = int(extraData.get('xbmc_height'))
                    if extraData.get('xbmc_width') : video_codec['width'] = int(extraData.get('xbmc_width'))
                    if extraData.get('duration') : video_codec['duration'] = int(extraData.get('duration'))

                    audio_codec={}
                    if extraData.get('xbmc_AudioCodec') : audio_codec['codec'] = extraData.get('xbmc_AudioCodec')
                    if extraData.get('xbmc_AudioChannels') : audio_codec['channels'] = int(extraData.get('xbmc_AudioChannels'))

                    liz.addStreamInfo('video', video_codec )
                    liz.addStreamInfo('audio', audio_codec )
                
        try:
            #Then set the number of watched and unwatched, which will be displayed per season
            liz.setProperty('TotalEpisodes', str(extraData['TotalEpisodes']))
            liz.setProperty('WatchedEpisodes', str(extraData['WatchedEpisodes']))
            liz.setProperty('UnWatchedEpisodes', str(extraData['UnWatchedEpisodes']))
            
            #Hack to show partial flag for TV shows and seasons
            if extraData.get('partialTV') == 1:            
                liz.setProperty('TotalTime', '100')
                liz.setProperty('ResumeTime', '50')
                
        except: pass

        #Set the fanart image if it has been enabled
        fanart = str(extraData.get('fanart_image', 'None'))

        if fanart != 'None':
            liz.setProperty('fanart_image', appendURLArgument(fanart,nToken))

            printDebug("Setting fan art as " + fanart + " with headers: " + aToken)

        else:
            printDebug("Skipping fanart as None found")

        if extraData.get('banner'):
            bannerImg = str(extraData.get('banner', ''))
            if bannerImg.startswith('http'):
                bannerPath = appendURLArgument(bannerImg,nToken)
            else:
                bannerPath = bannerImg

            liz.setProperty('banner', bannerPath)
            printDebug("Setting banner as " + bannerPath)

        if extraData.get('season_thumb'):
            seasonImg = str(extraData.get('season_thumb', ''))
            if seasonImg.startswith('http'):
                seasonPath = appendURLArgument(seasonImg,nToken)
            else:
                seasonPath = seasonImg

            liz.setProperty('seasonThumb', seasonPath)
            printDebug("Setting season Thumb as " + seasonPath)

        if context is not None:
            printDebug("Building Context Menus")

            if (not folder) and extraData.get('type','video').lower() == "video":
                #Play Transcoded
                playTranscode=u+"&transcode=1"
                plugin_url="XBMC.PlayMedia("+ playTranscode + ")"
                context.insert(0,('Play Transcoded', plugin_url , ))
                printDebug("Setting transcode options to [%s]" % plugin_url)

            liz.addContextMenuItems( context, settings.contextReplace )

        return xbmcplugin.addDirectoryItem(handle=pluginhandle,url=u,listitem=liz,isFolder=folder)

def displaySections( filter=None, shared=False ):
        printDebug("== ENTER ==", level=DEBUG_DEBUG)
        xbmcplugin.setContent(pluginhandle, 'files')

        ds_servers=discoverAllServers()
        numOfServers=len(ds_servers)
        printDebug( "Using list of "+str(numOfServers)+" servers: " +  str(ds_servers))
        
        for section in getAllSections(ds_servers):
        
            if shared and section.get('owned') == '1':
                continue
                
        
            details={'title' : section.get('title', 'Unknown') }

            if len(ds_servers) > 1:
                details['title']=section.get('serverName')+": "+details['title']

            extraData={ 'fanart_image' : getFanart(section, section.get('address')),
                        'type'         : "Video",
                        'thumb'        : g_thumb,
                        'token'        : section.get('token',None) }

            #Determine what we are going to do process after a link is selected by the user, based on the content we find

            path=section['path']

            if section.get('type') == 'show':
                mode=_MODE_TVSHOWS
                if (filter is not None) and (filter != "tvshows"):
                    continue

            elif section.get('type') == 'movie':
                mode=_MODE_MOVIES
                if (filter is not None) and (filter != "movies"):
                    continue

            elif section.get('type') == 'artist':
                mode=_MODE_ARTISTS
                if (filter is not None) and (filter != "music"):
                    continue

            elif section.get('type') == 'photo':
                mode=_MODE_PHOTOS
                if (filter is not None) and (filter != "photos"):
                    continue
            else:
                printDebug("Ignoring section "+details['title']+" of type " + section.get('type') + " as unable to process")
                continue

            if settings.secondary:
                mode=_MODE_GETCONTENT
            else:
                path=path+'/all'

            extraData['mode']=mode
            s_url='http://%s%s' % ( section['address'], path)

            if not settings.skipcontext:
                context=[]
                refreshURL="http://"+section.get('address')+section.get('path')+"/refresh"
                libraryRefresh = "RunScript(plugin.video.plexbmc, update ," + refreshURL + ")"
                context.append(('Refresh library section', libraryRefresh , ))
            else:
                context=None

            #Build that listing..
            addGUIItem(s_url, details,extraData, context)

        if shared:
            xbmcplugin.endOfDirectory(pluginhandle, cacheToDisc=True)
            return
                    
        #For each of the servers we have identified
        allservers=ds_servers
        numOfServers=len(allservers)

            
        if __settings__.getSetting('myplex_user') != '':
            addGUIItem('http://myplexqueue', {'title': 'myplex Queue'}, {'thumb': g_thumb, 'type': 'Video', 'mode': _MODE_MYPLEXQUEUE})

        for server in allservers.itervalues():

            if server['class'] == "secondary":
                continue
        
            #Plex plugin handling
            if (filter is not None) and (filter != "plugins"):
                continue

            if numOfServers > 1:
                prefix=server['serverName']+": "
            else:
                prefix=""

            details={'title' : prefix+"Channels" }
            extraData={'type' : "Video",
                       'thumb' : g_thumb,
                       'token' : server.get('token',None) }

            extraData['mode']=_MODE_CHANNELVIEW
            u="http://"+server['server']+":"+server['port']+"/system/plugins/all" 
            addGUIItem(u,details,extraData)

            #Create plexonline link
            details['title']=prefix+"Plex Online"
            extraData['type'] = "file"
            extraData['thumb'] = g_thumb
            extraData['mode'] = _MODE_PLEXONLINE

            u="http://"+server['server']+":"+server['port']+"/system/plexonline"
            addGUIItem(u,details,extraData)
            
            #create playlist link
            details['title']=prefix+"Playlists"
            extraData['type'] = "file"
            extraData['thumb'] = g_thumb
            extraData['mode'] = _MODE_PLAYLISTS

            u="http://"+server['server']+":"+server['port']+"/playlists"
            addGUIItem(u,details,extraData)
            
            
        if __settings__.getSetting("cache") == "true":
            details = {'title' : "Refresh Data"}
            extraData = {}
            extraData['type']="file"

            extraData['mode']= _MODE_DELETE_REFRESH

            u="http://nothing"
            addGUIItem(u,details,extraData)


        #All XML entries have been parsed and we are ready to allow the user to browse around.  So end the screen listing.
        xbmcplugin.endOfDirectory(pluginhandle, cacheToDisc=False)

def enforceSkinView(mode):

    '''
    Ensure that the views are consistance across plugin usage, depending
    upon view selected by user
    @input: User view selection
    @return: view id for skin
    '''

    printDebug("== ENTER ==", level=DEBUG_DEBUG)

    if __settings__.getSetting('skinoverride') == "false":
        return None

    skinname = __settings__.getSetting('skinname')

    current_skin_name = xbmc.getSkinDir()

    skin_map = { '2' : 'skin.confluence' ,
                 '0' : 'skin.quartz' ,
                 '1' : 'skin.quartz3' ,
                 '3' : 'skin.amber' }
    
    if skin_map[skinname] not in current_skin_name:
        printDebug("Do not have the correct skin [%s] selected in settings [%s] - ignoring" % (current_skin_name, skin_map[skinname]))
        return None
    
    if mode == "movie":
        printDebug("Looking for movie skin settings")
        viewname = __settings__.getSetting('mo_view_%s' % skinname)

    elif mode == "tv":
        printDebug("Looking for tv skin settings")
        viewname = __settings__.getSetting('tv_view_%s' % skinname)

    elif mode == "music":
        printDebug("Looking for music skin settings")
        viewname = __settings__.getSetting('mu_view_%s' % skinname)

    elif mode == "episode":
        printDebug("Looking for music skin settings")
        viewname = __settings__.getSetting('ep_view_%s' % skinname)

    elif mode == "season":
        printDebug("Looking for music skin settings")
        viewname = __settings__.getSetting('se_view_%s' % skinname)

    else:
        viewname = "None"

    printDebug("view name is %s" % viewname)

    if viewname == "None":
        return None

    QuartzV3_views={ 'List' : 50,
                     'Big List' : 51,
                     'MediaInfo' : 52,
                     'MediaInfo 2' : 54,
                     'Big Icons' : 501,
                     'Icons': 53,
                     'Panel' : 502,
                     'Wide' : 55,
                     'Fanart 1' : 57,
                     'Fanart 2' : 59,
                     'Fanart 3' : 500 }

    Quartz_views={ 'List' : 50,
                   'MediaInfo' : 51,
                   'MediaInfo 2' : 52,
                   'Icons': 53,
                   'Wide' : 54,
                   'Big Icons' : 55,
                   'Icons 2' : 56 ,
                   'Panel' : 57,
                   'Fanart' : 58,
                   'Fanart 2' : 59 }

    Confluence_views={ 'List' : 50,
                       'Big List' : 51,
                       'Thumbnail' : 500,
                       'Poster Wrap': 501,
                       'Fanart' : 508,
                       'Media Info' : 504,
                       'Media Info 2' : 503,
                       'Media Info 3' : 515,
                       'Wide Icons' : 505 }
    
    Amber_views = {  'List' : 50,
                       'Big List' : 52,
                       'Panel': 51,
                       'Low List' : 54,
                       'Icons' : 53,
                       'Big Panel' : 55,
                       'Fanart' : 59 }

    skin_list={"0" : Quartz_views ,
               "1" : QuartzV3_views,
               "2" : Confluence_views,
               "3" : Amber_views }

    printDebug("Using skin view: %s" % skin_list[skinname][viewname])

    try:
        return skin_list[skinname][viewname]
    except:
        print "PleXBMC -> skin name or view name error"
        return None

def Movies( url, tree=None ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    xbmcplugin.setContent(pluginhandle, 'movies')
    
    xbmcplugin.addSortMethod(pluginhandle, 37 ) #maintain original plex sorted
    xbmcplugin.addSortMethod(pluginhandle, 25 ) #video title ignore THE
    xbmcplugin.addSortMethod(pluginhandle, 19 )  #date added
    xbmcplugin.addSortMethod(pluginhandle, 3 )  #date
    xbmcplugin.addSortMethod(pluginhandle, 18 ) #rating
    xbmcplugin.addSortMethod(pluginhandle, 17 ) #year
    xbmcplugin.addSortMethod(pluginhandle, 29 ) #runtime
    xbmcplugin.addSortMethod(pluginhandle, 28 ) #by MPAA
    
    #get the server name from the URL, which was passed via the on screen listing..
    tree=getXML(url,tree)
    if tree is None:
        return

    server=getServerFromURL(url)

    setWindowHeading(tree)
    randomNumber=str(random.randint(1000000000,9999999999))
    #Find all the video tags, as they contain the data we need to link to a file.
    MovieTags=tree.findall('Video')
    fullList=[]
    for movie in MovieTags:

        movieTag(url, server, tree, movie, randomNumber)

    printDebug ("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('movie')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle)

def buildContextMenu( url, itemData ):
    context=[]
    server=getServerFromURL(url)
    refreshURL=url.replace("/all", "/refresh")
    plugin_url="RunScript(plugin.video.plexbmc, "
    ID=itemData.get('ratingKey','0')

    #Mark media unwatched
    unwatchURL="http://"+server+"/:/unscrobble?key="+ID+"&identifier=com.plexapp.plugins.library"+getAuthDetails(itemData)
    unwatched=plugin_url+"watch, " + unwatchURL + ")"
    context.append(('Mark as Unwatched', unwatched , ))

    #Mark media watched
    watchURL="http://"+server+"/:/scrobble?key="+ID+"&identifier=com.plexapp.plugins.library"+getAuthDetails(itemData)
    watched=plugin_url+"watch, " + watchURL + ")"
    context.append(('Mark as Watched', watched , ))

    #Initiate Library refresh
    libraryRefresh = plugin_url+"update, " + refreshURL.split('?')[0]+getAuthDetails(itemData,prefix="?") + ")"
    context.append(('Rescan library section', libraryRefresh , ))

    #Delete media from Library
    deleteURL="http://"+server+"/library/metadata/"+ID+getAuthDetails(itemData,prefix="?")
    removed=plugin_url+"delete, " + deleteURL + ")"
    context.append(('Delete media', removed , ))

    #Display plugin setting menu
    #settingDisplay=plugin_url+"setting)"
    #context.append(('PleXBMC settings', settingDisplay , ))

    #Reload media section
    listingRefresh=plugin_url+"refresh)"
    context.append(('Reload Section', listingRefresh , ))

    #alter audio
    alterAudioURL="http://"+server+"/library/metadata/"+ID+getAuthDetails(itemData,prefix="?")
    alterAudio=plugin_url+"audio, " + alterAudioURL + ")"
    context.append(('Select Audio', alterAudio , ))

    #alter subs
    alterSubsURL="http://"+server+"/library/metadata/"+ID+getAuthDetails(itemData,prefix="?")
    alterSubs=plugin_url+"subs, " + alterSubsURL + ")"
    context.append(('Select Subtitle', alterSubs , ))

    printDebug("Using context menus " + str(context))

    return context

def TVShows( url, tree=None ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    xbmcplugin.setContent(pluginhandle, 'tvshows')
    xbmcplugin.addSortMethod(pluginhandle, 25 ) #video title ignore THE
    xbmcplugin.addSortMethod(pluginhandle, 3 )  #date
    xbmcplugin.addSortMethod(pluginhandle, 18 ) #rating
    xbmcplugin.addSortMethod(pluginhandle, 17 ) #year
    xbmcplugin.addSortMethod(pluginhandle, 28 ) #by MPAA

    #Get the URL and server name.  Get the XML and parse
    tree=getXML(url,tree)
    if tree is None:
        return

    server=getServerFromURL(url)

    setWindowHeading(tree)
    #For each directory tag we find
    ShowTags=tree.findall('Directory')
    for show in ShowTags:

        tempgenre=[]

        for child in show:
            if child.tag == "Genre":
                        tempgenre.append(child.get('tag',''))

        watched = int(show.get('viewedLeafCount',0))

        #Create the basic data structures to pass up
        details={'title'      : show.get('title','Unknown').encode('utf-8') ,
                 'sorttitle'  : show.get('titleSort', show.get('title','Unknown')).encode('utf-8') ,
                 'tvshowname' : show.get('title','Unknown').encode('utf-8') ,
                 'studio'     : show.get('studio','').encode('utf-8') ,
                 'plot'       : show.get('summary','').encode('utf-8') ,
                 'season'     : 0 ,
                 'episode'    : int(show.get('leafCount',0)) ,
                 'mpaa'       : show.get('contentRating','') ,
                 'aired'      : show.get('originallyAvailableAt','') ,
                 'genre'      : " / ".join(tempgenre) }

        extraData={'type'              : 'video' ,
                   'UnWatchedEpisodes' : int(details['episode']) - watched,
                   'WatchedEpisodes'   : watched,
                   'TotalEpisodes'     : details['episode'],
                   'thumb'             : getThumb(show, server) ,
                   'fanart_image'      : getFanart(show, server) ,
                   'token'             : _PARAM_TOKEN ,
                   'key'               : show.get('key','') ,
                   'ratingKey'         : str(show.get('ratingKey',0)) }

        #banner art
        if show.get('banner',None) is not None:
            extraData['banner'] = 'http://'+server+show.get('banner')
        else:
            extraData['banner'] = g_thumb

        #Set up overlays for watched and unwatched episodes
        if extraData['WatchedEpisodes'] == 0:
            details['playcount'] = 0
        elif extraData['UnWatchedEpisodes'] == 0:
            details['playcount'] = 1
        else:
            extraData['partialTV'] = 1

        #Create URL based on whether we are going to flatten the season view
        if settings.flatten == "2":
            printDebug("Flattening all shows")
            extraData['mode']=_MODE_TVEPISODES
            u='http://%s%s'  % ( server, extraData['key'].replace("children","allLeaves"))
        else:
            extraData['mode']=_MODE_TVSEASONS
            u='http://%s%s'  % ( server, extraData['key'])

        if not settings.skipcontext:
            context=buildContextMenu(url, extraData)
        else:
            context=None

        addGUIItem(u,details,extraData, context)

    printDebug ("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('tv')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle, cacheToDisc=True)

def TVSeasons( url ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    xbmcplugin.setContent(pluginhandle, 'seasons')

    #Get URL, XML and parse
    server=getServerFromURL(url)
    tree=getXML(url)
    if tree is None:
        return

    willFlatten=False
    if settings.flatten == "1":
        #check for a single season
        if int(tree.get('size',0)) == 1:
            printDebug("Flattening single season show")
            willFlatten=True

    sectionart=getFanart(tree, server)
    banner=tree.get('banner')
    setWindowHeading(tree)
    #For all the directory tags
    SeasonTags=tree.findall('Directory')
    for season in SeasonTags:

        if willFlatten:
            url='http://'+server+season.get('key')
            TVEpisodes(url)
            return

        watched=int(season.get('viewedLeafCount',0))

        #Create the basic data structures to pass up
        details={'title'      : season.get('title','Unknown').encode('utf-8') ,
                 'tvshowname' : season.get('title','Unknown').encode('utf-8') ,
                 'sorttitle'  : season.get('titleSort', season.get('title','Unknown')).encode('utf-8') ,
                 'studio'     : season.get('studio','').encode('utf-8') ,
                 'plot'       : season.get('summary','').encode('utf-8') ,
                 'season'     : 0 ,
                 'episode'    : int(season.get('leafCount',0)) ,
                 'mpaa'       : season.get('contentRating','') ,
                 'aired'      : season.get('originallyAvailableAt','') }

        if season.get('sorttitle'): details['sorttitle'] = season.get('sorttitle')

        extraData={'type'              : 'video' ,
                   'WatchedEpisodes'   : watched ,
                   'UnWatchedEpisodes' : details['episode'] - watched ,
                   'thumb'             : getThumb(season, server) ,
                   'fanart_image'      : getFanart(season, server) ,
                   'token'             : _PARAM_TOKEN ,
                   'key'               : season.get('key','') ,
                   'ratingKey'         : str(season.get('ratingKey',0)) ,
                   'mode'              : _MODE_TVEPISODES }

        if banner:
            extraData['banner']="http://"+server+banner
                   
        if extraData['fanart_image'] == "":
            extraData['fanart_image']=sectionart

        #Set up overlays for watched and unwatched episodes
        if extraData['WatchedEpisodes'] == 0:
            details['playcount'] = 0
        elif extraData['UnWatchedEpisodes'] == 0:
            details['playcount'] = 1
        else:
            extraData['partialTV'] = 1

        url='http://%s%s' % ( server , extraData['key'] )

        if not settings.skipcontext:
            context=buildContextMenu(url, season)
        else:
            context=None

        #Build the screen directory listing
        addGUIItem(url,details,extraData, context)

    printDebug ("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('season')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=True)

def TVEpisodes( url, tree=None ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    xbmcplugin.setContent(pluginhandle, 'episodes')
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_EPISODE )  #episode
    xbmcplugin.addSortMethod(pluginhandle, 3 )  #date
    xbmcplugin.addSortMethod(pluginhandle, 25 ) #video title ignore THE
    xbmcplugin.addSortMethod(pluginhandle, 19 )  #date added
    xbmcplugin.addSortMethod(pluginhandle, 18 ) #rating
    xbmcplugin.addSortMethod(pluginhandle, 17 ) #year
    xbmcplugin.addSortMethod(pluginhandle, 29 ) #runtime
    xbmcplugin.addSortMethod(pluginhandle, 28 ) #by MPAA

    tree=getXML(url,tree)
    if tree is None:
        return

    setWindowHeading(tree)

    #get banner thumb
    banner = tree.get('banner')

    #get season thumb for SEASON NODE
    season_thumb = tree.get('thumb', '')

    ShowTags=tree.findall('Video')
    server=getServerFromURL(url)

    if not settings.skipimages:
        sectionart=getFanart(tree, server)

    randomNumber=str(random.randint(1000000000,9999999999))

    for episode in ShowTags:

        printDebug("---New Item---")
        tempgenre=[]
        tempcast=[]
        tempdir=[]
        tempwriter=[]

        for child in episode:
            if child.tag == "Media":
                mediaarguments = dict(child.items())
            elif child.tag == "Genre" and not settings.skipmetadata:
                tempgenre.append(child.get('tag'))
            elif child.tag == "Writer"  and not settings.skipmetadata:
                tempwriter.append(child.get('tag'))
            elif child.tag == "Director"  and not settings.skipmetadata:
                tempdir.append(child.get('tag'))
            elif child.tag == "Role"  and not settings.skipmetadata:
                tempcast.append(child.get('tag'))

        printDebug("Media attributes are " + str(mediaarguments))

        #Gather some data
        view_offset=episode.get('viewOffset',0)
        duration=int(mediaarguments.get('duration',episode.get('duration',0)))/1000

        #Required listItem entries for XBMC
        details={'plot'        : episode.get('summary','').encode('utf-8') ,
                 'title'       : episode.get('title','Unknown').encode('utf-8') ,
                 'sorttitle'   : episode.get('titleSort', episode.get('title','Unknown')).encode('utf-8')  ,
                 'rating'      : float(episode.get('rating',0)) ,
                 'studio'      : episode.get('studio',tree.get('studio','')).encode('utf-8') ,
                 'mpaa'        : episode.get('contentRating', tree.get('grandparentContentRating','')) ,
                 'year'        : int(episode.get('year',0)) ,
                 'tagline'     : episode.get('tagline','').encode('utf-8') ,
                 'episode'     : int(episode.get('index',0)) ,
                 'aired'       : episode.get('originallyAvailableAt','') ,
                 'tvshowtitle' : episode.get('grandparentTitle',tree.get('grandparentTitle','')).encode('utf-8') ,
                 'season'      : int(episode.get('parentIndex',tree.get('parentIndex',0))) }

        if episode.get('sorttitle'):
            details['sorttitle'] = episode.get('sorttitle').encode('utf-8')

        if tree.get('mixedParents','0') == '1':
            details['title'] = "%s - %sx%s %s" % ( details['tvshowtitle'], details['season'], str(details['episode']).zfill(2), details['title'] )
        #else:
        #    details['title'] = str(details['episode']).zfill(2) + ". " + details['title']


        #Extra data required to manage other properties
        extraData={'type'         : "Video" ,
                   'thumb'        : getThumb(episode, server) ,
                   'fanart_image' : getFanart(episode, server) ,
                   'token'        : _PARAM_TOKEN ,
                   'key'          : episode.get('key',''),
                   'ratingKey'    : str(episode.get('ratingKey',0)),
                   'duration'     : duration,
                   'resume'       : int(int(view_offset)/1000) }

        if extraData['fanart_image'] == "" and not settings.skipimages:
            extraData['fanart_image'] = sectionart

        if season_thumb:
            extraData['season_thumb'] = "http://" + server + season_thumb

        #get ALL SEASONS thumb
        if not season_thumb and episode.get('parentThumb', ""):
            extraData['season_thumb'] = "http://" + server + episode.get('parentThumb', "")

        if banner:
            extraData['banner'] = "http://" + server + banner
            
        #Determine what tupe of watched flag [overlay] to use
        if int(episode.get('viewCount',0)) > 0:
            details['playcount'] = 1
        else: 
            details['playcount'] = 0

        #Extended Metadata
        if not settings.skipmetadata:
            details['cast']     = tempcast
            details['director'] = " / ".join(tempdir)
            details['writer']   = " / ".join(tempwriter)
            details['genre']    = " / ".join(tempgenre)

        #Add extra media flag data
        if not settings.skipmediaflags:
            extraData.update(getMediaData(mediaarguments))

        #Build any specific context menu entries
        if not settings.skipcontext:
            context=buildContextMenu(url, extraData)
        else:
            context=None

        extraData['mode']=_MODE_PLAYLIBRARY
        # http:// <server> <path> &mode=<mode> &t=<rnd>
        separator = "?"
        if "?" in extraData['key']:
            separator = "&"
        u="http://%s%s%st=%s" % (server, extraData['key'], separator, randomNumber)

        addGUIItem(u,details,extraData, context, folder=False)

    printDebug ("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('episode')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=True)

def getAudioSubtitlesMedia( server, tree, full=False ):
    '''
        Cycle through the Parts sections to find all "selected" audio and subtitle streams
        If a stream is marked as selected=1 then we will record it in the dict
        Any that are not, are ignored as we do not need to set them
        We also record the media locations for playback decision later on
    '''
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    printDebug("Gather media stream info" )

    parts=[]
    partsCount=0
    subtitle={}
    subCount=0
    audio={}
    audioCount=0
    media={}
    subOffset=-1
    audioOffset=-1
    selectedSubOffset=-1
    selectedAudioOffset=-1
    full_data={}
    contents="type"
    media_type="unknown"
    extra={}
    
    timings = tree.find('Video')
    if timings is not None:
        media_type="video"
    else:
        timings = tree.find('Track')
        if timings:
            media_type="music"
        else:
            timings = tree.find('Photo')
            if timings:
                media_type="picture"
            else:
                printDebug("No Video data found")
                return {}

    media['viewOffset']=timings.get('viewOffset',0)    
    media['duration']=timings.get('duration',12*60*60)

    if full:
        if media_type == "video":
            full_data={ 'plot'      : timings.get('summary','').encode('utf-8') ,
                        'title'     : timings.get('title','Unknown').encode('utf-8') ,
                        'sorttitle' : timings.get('titleSort', timings.get('title','Unknown')).encode('utf-8') ,
                        'rating'    : float(timings.get('rating',0)) ,
                        'studio'    : timings.get('studio','').encode('utf-8'),
                        'mpaa'      : timings.get('contentRating', '').encode('utf-8'),
                        'year'      : int(timings.get('year',0)) ,
                        'tagline'   : timings.get('tagline','') ,
                        'thumbnailImage': getThumb(timings,server) }
                        
            if timings.get('type') == "episode":
                full_data['episode']     = int(timings.get('index',0)) 
                full_data['aired']       = timings.get('originallyAvailableAt','') 
                full_data['tvshowtitle'] = timings.get('grandparentTitle',tree.get('grandparentTitle','')).encode('utf-8') 
                full_data['season']      = int(timings.get('parentIndex',tree.get('parentIndex',0))) 

        elif media_type == "music":
                        
            full_data={'TrackNumber' : int(timings.get('index',0)) ,
                       'title'       : str(timings.get('index',0)).zfill(2)+". "+timings.get('title','Unknown').encode('utf-8') ,
                       'rating'      : float(timings.get('rating',0)) ,
                       'album'       : timings.get('parentTitle', tree.get('parentTitle','')).encode('utf-8') ,
                       'artist'      : timings.get('grandparentTitle', tree.get('grandparentTitle','')).encode('utf-8') ,
                       'duration'    : int(timings.get('duration',0))/1000 ,
                       'thumbnailImage': getThumb(timings,server) }

            extra['album']=timings.get('parentKey')
            extra['index']=timings.get('index')                       
                       
    details = timings.findall('Media')
        
    media_details_list=[]
    for media_details in details:
                
        resolution=""        
        try:       
            if media_details.get('videoResolution') == "sd":
                resolution="SD"
            elif int(media_details.get('videoResolution',0)) >= 1080:
                resolution="HD 1080"
            elif int(media_details.get('videoResolution',0)) >= 720:
                resolution="HD 720"
            elif int(media_details.get('videoResolution',0)) < 720:
                resolution="SD"
        except:
            pass
        
        media_details_temp = { 'bitrate'          : round(float(media_details.get('bitrate',0))/1000,1) ,
                               'videoResolution'  : resolution ,
                               'container'        : media_details.get('container','unknown') }
                                                  
        options = media_details.findall('Part')
        
        #Get the media locations (file and web) for later on
        for stuff in options:

            try:
                bits=stuff.get('key'), stuff.get('file')
                parts.append(bits)
                media_details_list.append(media_details_temp)
                partsCount += 1
            except: pass

    #if we are deciding internally or forcing an external subs file, then collect the data
    if media_type == "video" and settings.streamControl == _SUB_AUDIO_PLEX_CONTROL:

        contents="all"
        tags=tree.getiterator('Stream')

        for bits in tags:
            stream=dict(bits.items())
            
            #Audio Streams
            if stream['streamType'] == '2':
                audioCount += 1
                audioOffset += 1
                if stream.get('selected') == "1":
                    printDebug("Found preferred audio id: " + str(stream['id']) )
                    audio=stream
                    selectedAudioOffset=audioOffset
            
            #Subtitle Streams
            elif stream['streamType'] == '3':
            
                if subOffset == -1:
                    subOffset = int(stream.get('index',-1))
                elif stream.get('index',-1) > 0 and stream.get('index',-1) < subOffset:
                    subOffset = int(stream.get('index',-1))
                    
                if stream.get('selected') == "1":
                    printDebug( "Found preferred subtitles id : " + str(stream['id']))
                    subCount += 1
                    subtitle=stream
                    if stream.get('key'):
                        subtitle['key'] = 'http://'+server+stream['key']
                    else:
                        selectedSubOffset=int( stream.get('index') ) - subOffset
                    
    else:
            printDebug( "Stream selection is set OFF")

    streamData={'contents'   : contents ,                #What type of data we are holding
                'audio'      : audio ,                   #Audio data held in a dict
                'audioCount' : audioCount ,              #Number of audio streams
                'subtitle'   : subtitle ,                #Subtitle data (embedded) held as a dict
                'subCount'   : subCount ,                #Number of subtitle streams
                'parts'      : parts ,                   #The differet media locations
                'partsCount' : partsCount ,              #Number of media locations
                'media'      : media ,                   #Resume/duration data for media
                'details'    : media_details_list ,      #Bitrate, resolution and container for each part
                'subOffset'  : selectedSubOffset ,       #Stream index for selected subs
                'audioOffset': selectedAudioOffset ,     #STream index for select audio
                'full_data'  : full_data ,               #Full metadata extract if requested
                'type'       : media_type ,              #Type of metadata
                'extra'      : extra }                   #Extra data
            
    printDebug ( str(streamData) )
    return streamData

def playPlaylist ( server, data ):    
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    printDebug("Creating new playlist")
    playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
    playlist.clear()
    
    tree = getXML(server+data['extra'].get('album')+"/children")
    
    if tree is None:
        return
        
    TrackTags=tree.findall('Track')
    for track in TrackTags:

        printDebug("Adding playlist item")
    
        url, item = trackTag(server, tree, track, listing = False)
        
        liz=xbmcgui.ListItem(item.get('title','Unknown'), iconImage=data['full_data'].get('thumbnailImage','') , thumbnailImage=data['full_data'].get('thumbnailImage',''))

        liz.setInfo( type='music', infoLabels=item )        
        playlist.add(url, liz)
    
    index = int(data['extra'].get('index',0)) - 1
    printDebug("Playlist complete.  Starting playback from track %s [playlist index %s] " % (data['extra'].get('index',0), index ))
    xbmc.Player().playselected( index )   
    
    return
    
def playLibraryMedia( vids, override=0, force=None, full_data=False, shelf=False ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)

    if override == 1:
        override = True
        full_data = True
    else:
        override = False
    
    getTranscodeSettings(override)

    server=getServerFromURL(vids)

    id=vids.split('?')[0].split('&')[0].split('/')[-1]

    tree=getXML(vids)
    if tree is None:
        return
            
    if force:
        full_data = True
        
    streams=getAudioSubtitlesMedia(server,tree, full_data)  
    
    if force and streams['type'] == "music":
        playPlaylist(server, streams)
        return
    
    url=selectMedia(streams, server)

    if url is None:
        return

    protocol=url.split(':',1)[0]

    if protocol == "file":
        printDebug( "We are playing a local file")
        playurl=url.split(':',1)[1]
    elif protocol == "http":
        printDebug( "We are playing a stream")
        if g_transcode == "true":
            printDebug( "We will be transcoding the stream")
            playurl=transcode(id,url)+getAuthDetails({'token':_PARAM_TOKEN})

        else:
            playurl=url+getAuthDetails({'token':_PARAM_TOKEN},prefix="?")
    else:
        playurl=url

    resume=int(int(streams['media']['viewOffset'])/1000)
    duration=int(int(streams['media']['duration'])/1000)

    if not resume == 0 and shelf:
        printDebug("Shelf playback: display resume dialog")
        displayTime = str(datetime.timedelta(seconds=resume))
        display_list = [ "Resume from " + displayTime , "Start from beginning"]
        resumeScreen = xbmcgui.Dialog()
        result = resumeScreen.select('Resume',display_list)
        if result == -1:
            return False
            
        if result == 1:
           resume=0

    printDebug("Resume has been set to " + str(resume))

    item = xbmcgui.ListItem(path=playurl)

    if streams['full_data']:
        item.setInfo( type=streams['type'], infoLabels=streams['full_data'] )
        item.setThumbnailImage(streams['full_data'].get('thumbnailImage',''))
        item.setIconImage(streams['full_data'].get('thumbnailImage',''))
    
    if force:
        
        if int(force) > 0:
            resume=int(int(force)/1000)
        else:
            resume=force
        
    if force or shelf:    
        if resume:
            printDebug ("Playback from resume point")
            item.setProperty('ResumeTime', str(resume) )
            item.setProperty('TotalTime', str(duration) )

            
    if streams['type'] == "picture":
        import json
        request=json.dumps({ "id"      : 1,
                             "jsonrpc" : "2.0",
                             "method"  : "Player.Open",
                             "params"  : { "item"  :  {"file": playurl } } } )
        html=xbmc.executeJSONRPC(request)
        return
    else:
        start = xbmcplugin.setResolvedUrl(pluginhandle, True, item)

    # record the playing file and server in the home window
    # so that plexbmc helper can find out what is playing
    WINDOW = xbmcgui.Window( 10000 )
    WINDOW.setProperty('plexbmc.nowplaying.server', server)
    WINDOW.setProperty('plexbmc.nowplaying.id', id)

    #Set a loop to wait for positive confirmation of playback
    count = 0
    while not xbmc.Player().isPlaying():
        printDebug( "Not playing yet...sleep for 2")
        count = count + 2
        if count >= 20:
            return
        else:
            time.sleep(2)

    if not (g_transcode == "true" ):
        setAudioSubtitles(streams)

    if streams['type'] == "video":
        monitorPlayback(id,server)

    return

def setAudioSubtitles( stream ):
    '''
        Take the collected audio/sub stream data and apply to the media
        If we do not have any subs then we switch them off
    '''

    printDebug("== ENTER ==", level=DEBUG_DEBUG)

    #If we have decided not to collect any sub data then do not set subs
    if stream['contents'] == "type":
        printDebug ("No audio or subtitle streams to process.")

        #If we have decided to force off all subs, then turn them off now and return
        if settings.streamControl == _SUB_AUDIO_NEVER_SHOW :
            xbmc.Player().showSubtitles(False)
            printDebug ("All subs disabled")

        return True

    #Set the AUDIO component
    if settings.streamControl == _SUB_AUDIO_PLEX_CONTROL:
        printDebug("Attempting to set Audio Stream")

        audio = stream['audio']
        
        if stream['audioCount'] == 1:
            printDebug ("Only one audio stream present - will leave as default")

        elif audio:
            printDebug ("Attempting to use selected language setting: %s" % audio.get('language',audio.get('languageCode','Unknown')).encode('utf8'))
            printDebug ("Found preferred language at index " + str(stream['audioOffset']))
            try:
                xbmc.Player().setAudioStream(stream['audioOffset'])
                printDebug ("Audio set")
            except:
                printDebug ("Error setting audio, will use embedded default stream")

    #Set the SUBTITLE component
    if settings.streamControl == _SUB_AUDIO_PLEX_CONTROL:
        printDebug("Attempting to set preferred subtitle Stream")
        subtitle=stream['subtitle']
        if subtitle:
            printDebug ("Found preferred subtitle stream" )
            try:
                xbmc.Player().showSubtitles(False)
                if subtitle.get('key'):
                    xbmc.Player().setSubtitles(subtitle['key']+getAuthDetails({'token':_PARAM_TOKEN},prefix="?"))                
                else:
                    printDebug ("Enabling embedded subtitles at index %s" % stream['subOffset'])
                    xbmc.Player().setSubtitleStream(int(stream['subOffset']))

                xbmc.Player().showSubtitles(True)      
                return True
            except:
                printDebug ("Error setting subtitle")

        else:
            printDebug ("No preferred subtitles to set")
            xbmc.Player().showSubtitles(False)

    return False

def selectMedia( data, server ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    #if we have two or more files for the same movie, then present a screen
    result=0
    dvdplayback=False

    count=data['partsCount']
    options=data['parts']
    details=data['details']
    
    if count > 1:

        dialogOptions=[]
        dvdIndex=[]
        indexCount=0
        for items in options:

            if items[1]:
                name=items[1].split('/')[-1]
                #name="%s %s %sMbps" % (items[1].split('/')[-1], details[indexCount]['videoResolution'], details[indexCount]['bitrate'])
            else:
                name="%s %s %sMbps" % (items[0].split('.')[-1], details[indexCount]['videoResolution'], details[indexCount]['bitrate'])
                
            if settings.forcedvd:
                if '.ifo' in name.lower():
                    printDebug( "Found IFO DVD file in " + name )
                    name="DVD Image"
                    dvdIndex.append(indexCount)

            dialogOptions.append(name)
            indexCount+=1

        printDebug("Create selection dialog box - we have a decision to make!")
        startTime = xbmcgui.Dialog()
        result = startTime.select('Select media to play',dialogOptions)
        if result == -1:
            return None

        if result in dvdIndex:
            printDebug( "DVD Media selected")
            dvdplayback=True

    else:
        if settings.forcedvd:
            if '.ifo' in options[result]:
                dvdplayback=True

    newurl=mediaType({'key': options[result][0] , 'file' : options[result][1]},server,dvdplayback)

    printDebug("We have selected media at " + newurl)
    return newurl

def remove_html_tags( data ):
    p = re.compile(r'<.*?>')
    return p.sub('', data)

def monitorPlayback( id, server ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)

    if __settings__.getSetting('monitoroff') == "true":
        return
    
    if len(server.split(':')) == 1:
        server=server

    monitorCount=0
    progress = 0
    complete = 0
    playedTime = 0
    #Whilst the file is playing back
    while xbmc.Player().isPlaying():
        #Get the current playback time

        currentTime = int(xbmc.Player().getTime())
        totalTime = int(xbmc.Player().getTotalTime())
        try:
            progress = int(( float(currentTime) / float(totalTime) ) * 100)
        except:
            progress = 0

        if currentTime < 30:
            printDebug("Less that 30 seconds, will not set resume")

        #If we are less than 95% completem, store resume time
        elif progress < 95:
            printDebug( "Movies played time: %s secs of %s @ %s%%" % ( currentTime, totalTime, progress) )
            getURL("http://"+server+"/:/progress?key="+id+"&identifier=com.plexapp.plugins.library&time="+str(currentTime*1000)+"&state=playing",suppress=True)
            complete=0
            playedTime = currentTime

        #Otherwise, mark as watched
        else:
            if complete == 0:
                printDebug( "Movie marked as watched. Over 95% complete")
                getURL("http://"+server+"/:/scrobble?key="+id+"&identifier=com.plexapp.plugins.library",suppress=True)
                complete=1
                # playedTime = 0 in order to avoid a bug of tract plex plugin (check on completed tv episode when time==duration)
                playedTime = 0

        xbmc.sleep(5000)

    #If we get this far, playback has stopped
    printDebug("Playback Stopped")

    # The follwing progress:stopped update is necessary only for plugin trakt to 'cancel watching' on trakt.tv server, otherwise it will keep status 'watching' for about 15min
    getURL("http://"+server+"/:/progress?key="+id+"&identifier=com.plexapp.plugins.library&time="+str(playedTime*1000)+"&state=stopped",suppress=True)

    if g_sessionID is not None:
        printDebug("Stopping PMS transcode job with session " + g_sessionID)
        stopURL='http://'+server+'/video/:/transcode/segmented/stop?session='+g_sessionID
        html=getURL(stopURL)

    return

def PLAY( url ):
        printDebug("== ENTER ==", level=DEBUG_DEBUG)

        if url[0:4] == "file":
            printDebug( "We are playing a local file")
            #Split out the path from the URL
            playurl=url.split(':',1)[1]
        elif url[0:4] == "http":
            printDebug( "We are playing a stream")
            if '?' in url:
                playurl=url+getAuthDetails({'token':_PARAM_TOKEN})
            else:
                playurl=url+getAuthDetails({'token':_PARAM_TOKEN},prefix="?")
        else:
            playurl=url

        item = xbmcgui.ListItem(path=playurl)
        return xbmcplugin.setResolvedUrl(pluginhandle, True, item)

def videoPluginPlay(vids, prefix=None, indirect=None ):
    '''
        Plays Plugin Videos, which do not require library feedback
        but require further processing
        @input: url of video, plugin identifier
        @return: nothing. End of Script
    '''
    printDebug("== ENTER ==", level=DEBUG_DEBUG)

    server=getServerFromURL(vids)
    if "node.plexapp.com" in server:
        server=getMasterServer()['address']

    #If we find the url lookup service, then we probably have a standard plugin, but possibly with resolution choices
    if '/services/url/lookup' in vids:
        printDebug("URL Lookup service")
        html=getURL(vids, suppress=False)
        if not html:
            return
        tree=etree.fromstring(html)

        mediaCount=0
        mediaDetails=[]
        for media in tree.getiterator('Media'):
            mediaCount+=1
            tempDict={'videoResolution' : media.get('videoResolution',"Unknown")}

            for child in media:
                tempDict['key']=child.get('key','')

            tempDict['identifier']=tree.get('identifier','')
            mediaDetails.append(tempDict)

        printDebug( str(mediaDetails) )

        #If we have options, create a dialog menu
        result=0
        if mediaCount > 1:
            printDebug ("Select from plugin video sources")
            dialogOptions=[x['videoResolution'] for x in mediaDetails ]
            videoResolution = xbmcgui.Dialog()

            result = videoResolution.select('Select resolution..',dialogOptions)

            if result == -1:
                return

        videoPluginPlay(getLinkURL('',mediaDetails[result],server))
        return

    #Check if there is a further level of XML required
    if indirect or '&indirect=1' in vids:
        printDebug("Indirect link")
        html=getURL(vids, suppress=False)
        if not html:
            return
        tree=etree.fromstring(html)

        for bits in tree.getiterator('Part'):
            videoPluginPlay(getLinkURL(vids,bits,server))
            break

        return

    #if we have a plex URL, then this is a transcoding URL
    if 'plex://' in vids:
        printDebug("found webkit video, pass to transcoder")
        getTranscodeSettings(True)
        if not (prefix):
            prefix="system"
        vids=transcode(0, vids, prefix)
        
        #Workaround for XBMC HLS request limit of 1024 byts
        if len(vids) > 1000:
            printDebug("XBMC HSL limit detected, will pre-fetch m3u8 playlist")
            
            playlist = getURL(vids)
            
            if not playlist or not "#EXTM3U" in playlist:
            
                printDebug("Unable to get valid m3u8 playlist from transcoder")
                return
            
            server=getServerFromURL(vids)
            session=playlist.split()[-1]
            vids="http://"+server+"/video/:/transcode/segmented/"+session+"?t=1"
            
    printDebug("URL to Play: " + vids)
    printDebug("Prefix is: " + str(prefix))

    #If this is an Apple movie trailer, add User Agent to allow access
    if 'trailers.apple.com' in vids:
        url=vids+"|User-Agent=QuickTime/7.6.5 (qtver=7.6.5;os=Windows NT 5.1Service Pack 3)"
    elif server in vids:
        url=vids+getAuthDetails({'token': _PARAM_TOKEN})
    else:
        url=vids

    printDebug("Final URL is : " + url)

    item = xbmcgui.ListItem(path=url)
    start = xbmcplugin.setResolvedUrl(pluginhandle, True, item)

    if 'transcode' in url:
        try:
            pluginTranscodeMonitor(g_sessionID,server)
        except:
            printDebug("Unable to start transcode monitor")
    else:
        printDebug("Not starting monitor")

    return

def pluginTranscodeMonitor( sessionID, server ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)

    #Logic may appear backward, but this does allow for a failed start to be detected
    #First while loop waiting for start

    if __settings__.getSetting('monitoroff') == "true":
        return
   
    count=0
    while not xbmc.Player().isPlaying():
        printDebug( "Not playing yet...sleep for 2")
        count = count + 2
        if count >= 40:
            #Waited 20 seconds and still no movie playing - assume it isn't going to..
            return
        else:
            time.sleep(2)

    while xbmc.Player().isPlaying():
        printDebug("Waiting for playback to finish")
        time.sleep(4)

    printDebug("Playback Stopped")
    printDebug("Stopping PMS transcode job with session: " + sessionID)
    stopURL='http://'+server+'/video/:/transcode/segmented/stop?session='+sessionID

    html=getURL(stopURL)

    return

def get_params( paramstring ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    printDebug("Parameter string: " + paramstring)
    param={}
    if len(paramstring)>=2:
            params=paramstring

            if params[0] == "?":
                cleanedparams=params[1:]
            else:
                cleanedparams=params

            if (params[len(params)-1]=='/'):
                    params=params[0:len(params)-2]

            pairsofparams=cleanedparams.split('&')
            for i in range(len(pairsofparams)):
                    splitparams={}
                    splitparams=pairsofparams[i].split('=')
                    if (len(splitparams))==2:
                            param[splitparams[0]]=splitparams[1]
                    elif (len(splitparams))==3:
                            param[splitparams[0]]=splitparams[1]+"="+splitparams[2]
    print "PleXBMC -> Detected parameters: " + str(param)
    return param

def channelSearch (url, prompt):
    '''
        When we encounter a search request, branch off to this function to generate the keyboard
        and accept the terms.  This URL is then fed back into the correct function for
        onward processing.
    '''
    printDebug("== ENTER ==", level=DEBUG_DEBUG)

    if prompt:
        prompt=urllib.unquote(prompt)
    else:
        prompt="Enter Search Term..."

    kb = xbmc.Keyboard('', 'heading')
    kb.setHeading(prompt)
    kb.doModal()
    if (kb.isConfirmed()):
        text = kb.getText()
        printDebug("Search term input: "+ text)
        url=url+'&query='+urllib.quote(text)
        PlexPlugins( url )
    return

def getContent( url ):
    '''
        This function takes teh URL, gets the XML and determines what the content is
        This XML is then redirected to the best processing function.
        If a search term is detected, then show keyboard and run search query
        @input: URL of XML page
        @return: nothing, redirects to another function
    '''
    printDebug("== ENTER ==", level=DEBUG_DEBUG)

    server=getServerFromURL(url)
    lastbit=url.split('/')[-1]
    printDebug("URL suffix: " + str(lastbit))

    #Catch search requests, as we need to process input before getting results.
    if lastbit.startswith('search'):
        printDebug("This is a search URL.  Bringing up keyboard")
        kb = xbmc.Keyboard('', 'heading')
        kb.setHeading('Enter search term')
        kb.doModal()
        if (kb.isConfirmed()):
            text = kb.getText()
            printDebug("Search term input: "+ text)
            url=url+'&query='+urllib.quote(text)
        else:
            return

    html=getURL(url, suppress=False, popup=1 )

    if html is False:
        return

    tree=etree.fromstring(html)

    setWindowHeading(tree)

    if lastbit == "folder" or lastbit == "playlists":
        processXML(url,tree)
        return

    view_group=tree.get('viewGroup',None)

    if view_group == "movie":
        printDebug( "This is movie XML, passing to Movies")
        Movies(url, tree)
    elif view_group == "show":
        printDebug( "This is tv show XML")
        TVShows(url,tree)
    elif view_group == "episode":
        printDebug("This is TV episode XML")
        TVEpisodes(url,tree)
    elif view_group == 'artist':
        printDebug( "This is music XML")
        artist(url, tree)
    elif view_group== 'album' or view_group == 'albums':
        albums(url,tree)
    elif view_group == 'track':
        printDebug("This is track XML")
        tracks(url, tree) #sorthing is handled here
    elif view_group =="photo":
        printDebug("This is a photo XML")
        photo(url,tree)
    else:
        processDirectory(url,tree)

    return

def processDirectory( url, tree=None ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    printDebug("Processing secondary menus")
    xbmcplugin.setContent(pluginhandle, "")

    server = getServerFromURL(url)
    setWindowHeading(tree)
    for directory in tree:
        details={'title' : directory.get('title','Unknown').encode('utf-8') }
        extraData={'thumb'        : getThumb(tree, server) ,
                   'fanart_image' : getFanart(tree, server) }

        #if extraData['thumb'] == '':
        #    extraData['thumb']=extraData['fanart_image']

        extraData['mode'] = _MODE_GETCONTENT
        u='%s' % (getLinkURL(url, directory, server))

        addGUIItem(u, details, extraData)

    xbmcplugin.endOfDirectory(pluginhandle, cacheToDisc=True)

def getMasterServer(all=False):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)

    possibleServers=[]
    current_master=__settings__.getSetting('masterServer')
    for serverData in discoverAllServers().values():
        printDebug( str(serverData) )
        if serverData['master'] == 1:
            possibleServers.append({'address' : serverData['server']+":"+serverData['port'] ,
                                    'discovery' : serverData['discovery'],
                                    'name'      : serverData['serverName'],
                                    'token'     : serverData.get('token') })
    printDebug( "Possible master servers are " + str(possibleServers) )

    if all:
        return possibleServers

    if len(possibleServers) > 1:
        preferred="local"
        for serverData in possibleServers:
            if serverData['name'] == current_master:
                printDebug("Returning current master")
                return serverData
            if preferred == "any":
                printDebug("Returning 'any'")
                return serverData
            else:
                if serverData['discovery'] == preferred:
                    printDebug("Returning local")
                    return serverData
    elif len(possibleServers) == 0:
        return 
    
    return possibleServers[0]

def transcode( id, url, identifier=None ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)

    server=getServerFromURL(url)

    #Check for myplex user, which we need to alter to a master server
    if 'plexapp.com' in url:
        server=getMasterServer()

    printDebug("Using preferred transcoding server: " + server)
    printDebug ("incoming URL is: %s" % url)

    transcode_request="/video/:/transcode/segmented/start.m3u8"
    transcode_settings={ '3g' : 0 ,
                         'offset' : 0 ,
                         'quality' : g_quality ,
                         'session' : g_sessionID ,
                         'identifier' : identifier ,
                         'httpCookie' : "" ,
                         'userAgent' : "" ,
                         'ratingKey' : id ,
                         'subtitleSize' : __settings__.getSetting('subSize').split('.')[0] ,
                         'audioBoost' : __settings__.getSetting('audioSize').split('.')[0] ,
                         'key' : "" }

    if identifier:
        transcode_target=url.split('url=')[1]
        transcode_settings['webkit']=1
    else:
        transcode_settings['identifier']="com.plexapp.plugins.library"
        transcode_settings['key']=urllib.quote_plus("http://%s/library/metadata/%s" % (server, id))
        transcode_target=urllib.quote_plus("http://127.0.0.1:32400"+"/"+"/".join(url.split('/')[3:]))
        printDebug ("filestream URL is: %s" % transcode_target )

    transcode_request="%s?url=%s" % (transcode_request, transcode_target)

    for argument, value in transcode_settings.items():
                transcode_request="%s&%s=%s" % ( transcode_request, argument, value )

    printDebug("new transcode request is: %s" % transcode_request )

    now=str(int(round(time.time(),0)))

    msg = transcode_request+"@"+now
    printDebug("Message to hash is " + msg)

    #These are the DEV API keys - may need to change them on release
    publicKey="KQMIY6GATPC63AIMC4R2"
    privateKey = base64.decodestring("k3U6GLkZOoNIoSgjDshPErvqMIFdE0xMTx8kgsrhnC0=")

    import hmac
    import hashlib
    hash=hmac.new(privateKey,msg,digestmod=hashlib.sha256)

    printDebug("HMAC after hash is " + hash.hexdigest())

    #Encode the binary hash in base64 for transmission
    token=base64.b64encode(hash.digest())

    #Send as part of URL to avoid the case sensitive header issue.
    fullURL="http://"+server+transcode_request+"&X-Plex-Access-Key="+publicKey+"&X-Plex-Access-Time="+str(now)+"&X-Plex-Access-Code="+urllib.quote_plus(token)+"&"+capability

    printDebug("Transcoded media location URL " + fullURL)

    return fullURL

def artist( url, tree=None ):
    '''
        Process artist XML and display data
        @input: url of XML page, or existing tree of XML page
        @return: nothing
    '''
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    xbmcplugin.setContent(pluginhandle, 'artists')
    xbmcplugin.addSortMethod(pluginhandle, 12 ) #artist title ignore THE
    xbmcplugin.addSortMethod(pluginhandle, 34 ) #last played
    xbmcplugin.addSortMethod(pluginhandle, 17 ) #year
 
    #Get the URL and server name.  Get the XML and parse
    tree=getXML(url,tree)
    if tree is None:
        return

    server=getServerFromURL(url)
    setWindowHeading(tree)
    ArtistTag=tree.findall('Directory')
    for artist in ArtistTag:

        details={'artist'  : artist.get('title','').encode('utf-8') }

        details['title']=details['artist']

        extraData={'type'         : "Music" ,
                   'thumb'        : getThumb(artist, server) ,
                   'fanart_image' : getFanart(artist, server) ,
                   'ratingKey'    : artist.get('title','') ,
                   'key'          : artist.get('key','') ,
                   'mode'         : _MODE_ALBUMS ,
                   'plot'         : artist.get('summary','') }

        url='http://%s%s' % (server, extraData['key'] )

        addGUIItem(url,details,extraData)

    printDebug ("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('music')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=True)

def albums( url, tree=None ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    xbmcplugin.setContent(pluginhandle, 'albums')
    xbmcplugin.addSortMethod(pluginhandle, 24 ) #album title ignore THE
    xbmcplugin.addSortMethod(pluginhandle, 12 )  #artist ignore THE
    xbmcplugin.addSortMethod(pluginhandle, 34 ) #last played
    xbmcplugin.addSortMethod(pluginhandle, 17 ) #year
    
    #Get the URL and server name.  Get the XML and parse
    tree=getXML(url,tree)
    if tree is None:
        return

    server=getServerFromURL(url)
    sectionart=getFanart(tree, server)
    setWindowHeading(tree)
    AlbumTags=tree.findall('Directory')
    for album in AlbumTags:

        details={'album'   : album.get('title','').encode('utf-8') ,
                 'year'    : int(album.get('year',0)) ,
                 'artist'  : tree.get('parentTitle', album.get('parentTitle','')).encode('utf-8') }

        details['title']=details['album']

        extraData={'type'         : "Music" ,
                   'thumb'        : getThumb(album, server) ,
                   'fanart_image' : getFanart(album, server) ,
                   'key'          : album.get('key',''),
                   'mode'         : _MODE_TRACKS ,
                   'plot'         : album.get('summary','')}

        if extraData['fanart_image'] == "":
            extraData['fanart_image']=sectionart

        url='http://%s%s' % (server, extraData['key'] )

        addGUIItem(url,details,extraData)

    printDebug ("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('music')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=True)

def tracks( url,tree=None ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    xbmcplugin.setContent(pluginhandle, 'songs')
    xbmcplugin.addSortMethod(pluginhandle, 10 ) #title title ignore THE
    xbmcplugin.addSortMethod(pluginhandle, 8 ) #duration
    xbmcplugin.addSortMethod(pluginhandle, 27 ) #song rating
    xbmcplugin.addSortMethod(pluginhandle, 7 ) #track number

    tree=getXML(url,tree)
    if tree is None:
        return

    playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
    playlist.clear()
     
    server=getServerFromURL(url)
    sectionart=getFanart(tree, server)
    sectionthumb=getThumb(tree, server)
    setWindowHeading(tree)
    TrackTags=tree.findall('Track')
    for track in TrackTags:
        if track.get('thumb'):
            sectionthumb=getThumb(track, server)

        trackTag(server, tree, track, sectionart, sectionthumb)

    printDebug ("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('music')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=True)

def getXML (url, tree=None):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)

    if tree is None:

        html=getURL(url)

        if html is False:
            print "PleXBMC -> Server [%s] offline, not responding or no data was received" % getServerFromURL(url)
            return None

        tree=etree.fromstring(html)

    if tree.get('message'):
        xbmcgui.Dialog().ok(tree.get('header','Message'),tree.get('message',''))
        return None

    #setWindowHeading(tree)

    return tree

def PlexPlugins(url, tree=None):
    '''
        Main function to parse plugin XML from PMS
        Will create dir or item links depending on what the
        main tag is.
        @input: plugin page URL
        @return: nothing, creates XBMC GUI listing
    '''
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    xbmcplugin.setContent(pluginhandle, 'addons')

    tree = getXML(url, tree)
    if tree is None:
        return

    myplex_url=False
    server=getServerFromURL(url)
    if (tree.get('identifier') != "com.plexapp.plugins.myplex") and ( "node.plexapp.com" in url ) :
        myplex_url=True
        printDebug("This is a myplex URL, attempting to locate master server")
        server=getMasterServer()['address']

    for plugin in tree:

        details={'title'   : plugin.get('title','Unknown').encode('utf-8') }

        if details['title'] == "Unknown":
            details['title']=plugin.get('name',"Unknown").encode('utf-8')
            
        if plugin.get('summary'):
            details['plot']=plugin.get('summary')

        extraData={'thumb'        : getThumb(plugin, server) ,
                   'fanart_image' : getFanart(plugin, server) ,
                   'identifier'   : tree.get('identifier','') ,
                   'type'         : "Video" ,
                   'key'          : plugin.get('key','') }

        if myplex_url:
            extraData['key']=extraData['key'].replace('node.plexapp.com:32400',server)
              
        if extraData['fanart_image'] == "":
            extraData['fanart_image']=getFanart(tree, server)

        p_url=getLinkURL(url, extraData, server)

        if plugin.tag == "Directory" or plugin.tag == "Podcast":

            if plugin.get('search') == '1':
                extraData['mode']=_MODE_CHANNELSEARCH
                extraData['parameters']={'prompt' : plugin.get('prompt',"Enter Search Term").encode('utf-8') }
            else:
                extraData['mode']=_MODE_PLEXPLUGINS

            addGUIItem(p_url, details, extraData)

        elif plugin.tag == "Video":
            extraData['mode']=_MODE_VIDEOPLUGINPLAY
            
            for child in plugin:
                if child.tag == "Media":
                    extraData['parameters'] = {'indirect' : child.get('indirect','0')}            
            
            addGUIItem(p_url, details, extraData, folder=False)

        elif plugin.tag == "Setting":

            if plugin.get('option') == 'hidden':
                value="********"
            elif plugin.get('type') == "text":
                value=plugin.get('value')
            elif plugin.get('type') == "enum":
                value=plugin.get('values').split('|')[int(plugin.get('value',0))]
            else:
                value=plugin.get('value')

            details['title']= "%s - [%s]" % (plugin.get('label','Unknown').encode('utf-8'), value)
            extraData['mode']=_MODE_CHANNELPREFS
            extraData['parameters']={'id' : plugin.get('id') }
            addGUIItem(url, details, extraData)


    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=True)

def channelSettings ( url, settingID ):
    '''
        Take the setting XML and parse it to create an updated
        string with the new settings.  For the selected value, create
        a user input screen (text or list) to update the setting.
        @ input: url
        @ return: nothing
    '''
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    printDebug("Setting preference for ID: %s" % settingID )

    if not settingID:
        printDebug("ID not set")
        return

    tree=getXML(url)
    if tree is None:
        return

    setWindowHeading(tree)
    setString=None
    for plugin in tree:

        if plugin.get('id') == settingID:
            printDebug("Found correct id entry for: %s" % settingID)
            id=settingID

            label=plugin.get('label',"Enter value").encode('utf-8')
            option=plugin.get('option').encode('utf-8')
            value=plugin.get('value').encode('utf-8')

            if plugin.get('type') == "text":
                printDebug("Setting up a text entry screen")
                kb = xbmc.Keyboard(value, 'heading')
                kb.setHeading(label)

                if option == "hidden":
                    kb.setHiddenInput(True)
                else:
                    kb.setHiddenInput(False)

                kb.doModal()
                if (kb.isConfirmed()):
                    value = kb.getText()
                    printDebug("Value input: "+ value)
                else:
                    printDebug("User cancelled dialog")
                    return False

            elif plugin.get('type') == "enum":
                printDebug("Setting up an enum entry screen")

                values=plugin.get('values').split('|')

                settingScreen = xbmcgui.Dialog()
                value = settingScreen.select(label,values)
                if value == -1:
                    printDebug("User cancelled dialog")
                    return False
            else:
                printDebug('Unknown option type: %s' % plugin.get('id') )

        else:
            value=plugin.get('value')
            id=plugin.get('id')

        if setString is None:
            setString='%s/set?%s=%s' % (url, id, value)
        else:
            setString='%s&%s=%s' % (setString, id, value)

    printDebug ("Settings URL: %s" % setString )
    getURL (setString)
    xbmc.executebuiltin("Container.Refresh")

    return False

def processXML( url, tree=None ):
    '''
        Main function to parse plugin XML from PMS
        Will create dir or item links depending on what the
        main tag is.
        @input: plugin page URL
        @return: nothing, creates XBMC GUI listing
    '''
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    xbmcplugin.setContent(pluginhandle, 'movies')
    server=getServerFromURL(url)
    tree=getXML(url,tree)
    if tree is None:
        return
    setWindowHeading(tree)
    for plugin in tree:

        details={'title'   : plugin.get('title','Unknown').encode('utf-8') }

        if details['title'] == "Unknown":
            details['title']=plugin.get('name',"Unknown").encode('utf-8')

        extraData={'thumb'        : getThumb(plugin, server) ,
                   'fanart_image' : getFanart(plugin, server) ,
                   'identifier'   : tree.get('identifier','') ,
                   'type'         : "Video" }

        if extraData['fanart_image'] == "":
            extraData['fanart_image']=getFanart(tree, server)

        p_url=getLinkURL(url, plugin, server)

        if plugin.tag == "Directory" or plugin.tag == "Podcast":
            extraData['mode']=_MODE_PROCESSXML
            addGUIItem(p_url, details, extraData)

        elif plugin.tag == "Track":
            trackTag(server, tree, plugin)

        elif plugin.tag == "Playlist":
            playlistTag(url, server, tree, plugin)
            
        elif tree.get('viewGroup') == "movie":
            Movies(url, tree)
            return

        elif tree.get('viewGroup') == "episode":
            TVEpisodes(url, tree)
            return

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=True)

def movieTag(url, server, tree, movie, randomNumber):

    printDebug("---New Item---")
    tempgenre=[]
    tempcast=[]
    tempdir=[]
    tempwriter=[]

    #Lets grab all the info we can quickly through either a dictionary, or assignment to a list
    #We'll process it later
    for child in movie:
        if child.tag == "Media":
            mediaarguments = dict(child.items())
        elif child.tag == "Genre" and not settings.skipmetadata:
            tempgenre.append(child.get('tag'))
        elif child.tag == "Writer"  and not settings.skipmetadata:
            tempwriter.append(child.get('tag'))
        elif child.tag == "Director"  and not settings.skipmetadata:
            tempdir.append(child.get('tag'))
        elif child.tag == "Role"  and not settings.skipmetadata:
            tempcast.append(child.get('tag'))

    printDebug("Media attributes are " + str(mediaarguments))

    #Gather some data
    view_offset=movie.get('viewOffset',0)
    duration=int(mediaarguments.get('duration',movie.get('duration',0)))/1000
    if movie.get('originallyAvailableAt') is not None:
        release_date = time.strftime('%d.%m.%Y',(time.strptime(movie.get('originallyAvailableAt'), '%Y-%m-%d')))
    else:
        release_date = ""

    #Required listItem entries for XBMC
    details={'plot'      : movie.get('summary','').encode('utf-8') ,
             'title'     : movie.get('title','Unknown').encode('utf-8') ,
             'sorttitle' : movie.get('titleSort', movie.get('title','Unknown')).encode('utf-8') ,
             'rating'    : float(movie.get('rating',0)) ,
             'studio'    : movie.get('studio','').encode('utf-8'),
             'mpaa'      : movie.get('contentRating', '').encode('utf-8'),
             'year'      : int(movie.get('year',0)),
             'date'      : release_date,
             'tagline'   : movie.get('tagline','')}

    #Extra data required to manage other properties
    extraData={'type'         : "Video" ,
               'thumb'        : getThumb(movie, server) ,
               'fanart_image' : getFanart(movie, server) ,
               'token'        : _PARAM_TOKEN ,
               'key'          : movie.get('key',''),
               'ratingKey'    : str(movie.get('ratingKey',0)),
               'duration'     : duration,
               'dateadded'    : str(datetime.datetime.fromtimestamp(int(movie.get('addedAt',0)))),
               'resume'       : int (int(view_offset)/1000) }

    #Determine what type of watched flag [overlay] to use
    if int(movie.get('viewCount',0)) > 0:
        details['playcount'] = 1
    elif int(movie.get('viewCount',0)) == 0:
        details['playcount'] = 0

    #Extended Metadata
    if not settings.skipmetadata:
        details['cast']     = tempcast
        details['director'] = " / ".join(tempdir)
        details['writer']   = " / ".join(tempwriter)
        details['genre']    = " / ".join(tempgenre)

    #Add extra media flag data
    if not settings.skipmediaflags:
        extraData.update(getMediaData(mediaarguments))

    #Build any specific context menu entries
    if not settings.skipcontext:
        context=buildContextMenu(url, extraData)
    else:
        context=None
    # http:// <server> <path> &mode=<mode> &t=<rnd>
    extraData['mode']=_MODE_PLAYLIBRARY
    separator = "?"
    if "?" in extraData['key']:
        separator = "&"
    u="http://%s%s%st=%s" % (server, extraData['key'], separator, randomNumber)

    addGUIItem(u,details,extraData,context,folder=False)
    return
    
def getMediaData ( tag_dict ):
    '''
        Extra the media details from the XML
        @input: dict of <media /> tag attributes
        @output: dict of required values
    '''
    printDebug("== ENTER ==", level=DEBUG_DEBUG)

    return     {'VideoResolution'    : tag_dict.get('videoResolution','') ,
                'VideoCodec'         : tag_dict.get('videoCodec','') ,
                'AudioCodec'         : tag_dict.get('audioCodec','') ,
                'AudioChannels'      : tag_dict.get('audioChannels','') ,
                'VideoAspect'        : tag_dict.get('aspectRatio','') ,
                'xbmc_height'        : tag_dict.get('height') ,
                'xbmc_width'         : tag_dict.get('width') ,
                'xbmc_VideoCodec'    : tag_dict.get('videoCodec') ,
                'xbmc_AudioCodec'    : tag_dict.get('audioCodec') ,
                'xbmc_AudioChannels' : tag_dict.get('audioChannels') ,
                'xbmc_VideoAspect'   : tag_dict.get('aspectRatio') }

def trackTag( server, tree, track, sectionart="", sectionthumb="", listing=True ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    xbmcplugin.setContent(pluginhandle, 'songs')

    for child in track:
        for babies in child:
            if babies.tag == "Part":
                partDetails=(dict(babies.items()))

    printDebug( "Part is " + str(partDetails))

    details={'TrackNumber' : int(track.get('index',0)) ,
             'title'       : str(track.get('index',0)).zfill(2)+". "+track.get('title','Unknown').encode('utf-8') ,
             'rating'      : float(track.get('rating',0)) ,
             'album'       : track.get('parentTitle', tree.get('parentTitle','')).encode('utf-8') ,
             'artist'      : track.get('grandparentTitle', tree.get('grandparentTitle','')).encode('utf-8') ,
             'duration'    : int(track.get('duration',0))/1000 
             }

    extraData={'type'         : "Music" ,
               #'fanart_image' : getFanart(track, server) ,
               #'thumb'        : getThumb(track, server) ,
               'fanart_image' : sectionart ,
               'thumb'      : sectionthumb ,
               'ratingKey'    : track.get('key','') }


    #If we are streaming, then get the virtual location
    url=mediaType(partDetails,server)

    extraData['mode']=_MODE_BASICPLAY
    u="%s" % (url)

    if listing:
        addGUIItem(u,details,extraData,folder=False)
    else:
        return ( url, details )

def playlistTag(url, server, tree, track, sectionart="", sectionthumb="", listing=True ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)

    details={'title'       : track.get('title','Unknown').encode('utf-8') ,
             'duration'    : int(track.get('duration',0))/1000 
             }

    extraData={'type'         : track.get('playlistType', ''),
               'thumb'      : getThumb({'thumb' : track.get('composite', '')},server)} 

    if extraData['type'] == "video":
        extraData['mode'] = _MODE_MOVIES
    elif extraData['type'] == "audio":
        extraData['mode'] = _MODE_TRACKS
    else:
        extraData['mode']=_MODE_GETCONTENT
    
    u=getLinkURL(url, track, server)

    if listing:
        addGUIItem(u,details,extraData,folder=True)
    else:
        return ( url, details )

def photo( url,tree=None ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    server=url.split('/')[2]

    xbmcplugin.setContent(pluginhandle, 'photo')

    tree=getXML(url,tree)
    if tree is None:
        return

    sectionArt=getFanart(tree,server)
    setWindowHeading(tree)
    for picture in tree:

        details={'title' : picture.get('title',picture.get('name','Unknown')).encode('utf-8') }

        if not details['title']:
            details['title'] = "Unknown"
        
        extraData={'thumb'        : getThumb(picture, server) ,
                   'fanart_image' : getFanart(picture, server) ,
                   'type'         : "image" }

        if extraData['fanart_image'] == "":
            extraData['fanart_image']=sectionArt

        u=getLinkURL(url, picture, server)

        if picture.tag == "Directory":
            extraData['mode']=_MODE_PHOTOS
            addGUIItem(u,details,extraData)

        elif picture.tag == "Photo":

            if tree.get('viewGroup','') == "photo":
                for photo in picture:
                    if photo.tag == "Media":
                        for images in photo:
                            if images.tag == "Part":
                                extraData['key']="http://"+server+images.get('key','')
                                details['size']=int(images.get('size',0))
                                u=extraData['key']

            addGUIItem(u,details,extraData,folder=False)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=True)

def music( url, tree=None ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    xbmcplugin.setContent(pluginhandle, 'artists')

    server=getServerFromURL(url)

    tree=getXML(url,tree)
    if tree is None:
        return

    setWindowHeading(tree)
    for grapes in tree:

        if grapes.get('key',None) is None:
            continue

        details={'genre'       : grapes.get('genre','').encode('utf-8') ,
                 'artist'      : grapes.get('artist','').encode('utf-8') ,
                 'year'        : int(grapes.get('year',0)) ,
                 'album'       : grapes.get('album','').encode('utf-8') ,
                 'tracknumber' : int(grapes.get('index',0)) ,
                 'title'       : "Unknown" }


        extraData={'type'        : "Music" ,
                   'thumb'       : getThumb(grapes, server) ,
                   'fanart_image': getFanart(grapes, server) }

        if extraData['fanart_image'] == "":
            extraData['fanart_image']=getFanart(tree, server)

        u=getLinkURL(url, grapes, server)

        if grapes.tag == "Track":
            printDebug("Track Tag")
            xbmcplugin.setContent(pluginhandle, 'songs')

            details['title']=grapes.get('track',grapes.get('title','Unknown')).encode('utf-8')
            details['duration']=int(int(grapes.get('totalTime',0))/1000)

            extraData['mode']=_MODE_BASICPLAY
            addGUIItem(u,details,extraData,folder=False)

        else:

            if grapes.tag == "Artist":
                printDebug("Artist Tag")
                xbmcplugin.setContent(pluginhandle, 'artists')
                details['title']=grapes.get('artist','Unknown').encode('utf-8')

            elif grapes.tag == "Album":
                printDebug("Album Tag")
                xbmcplugin.setContent(pluginhandle, 'albums')
                details['title']=grapes.get('album','Unknown').encode('utf-8')

            elif grapes.tag == "Genre":
                details['title']=grapes.get('genre','Unknown').encode('utf-8')

            else:
                printDebug("Generic Tag: " + grapes.tag)
                details['title']=grapes.get('title','Unknown').encode('utf-8')

            extraData['mode']=_MODE_MUSIC
            addGUIItem(u,details,extraData)

    printDebug ("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('music')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=True)

def getThumb(data, server, width=720, height=720):
    '''
        Simply take a URL or path and determine how to format for images
        @ input: elementTree element, server name
        @ return formatted URL
    '''

    if settings.skipimages:
        return ''

    thumbnail=data.get('thumb','').split('?t')[0].encode('utf-8')

    if thumbnail == '':
        return g_thumb

    elif thumbnail[0:4] == "http" :
        return thumbnail

    elif thumbnail[0] == '/':
        if settings.fullres_thumbnails:
            return 'http://'+server+thumbnail
        else:
            return photoTranscode(server, 'http://localhost:32400'+thumbnail, width, height)

    else:
        return g_thumb

def getShelfThumb(data, server, seasonThumb=0, width=400, height=400):
    '''
        Simply take a URL or path and determine how to format for images
        @ input: elementTree element, server name
        @ return formatted URL
    '''

    if seasonThumb == 1:
        thumbnail=data.get('grandparentThumb','').split('?t')[0].encode('utf-8')    
    
    else:
        thumbnail=data.get('thumb','').split('?t')[0].encode('utf-8')

    if thumbnail == '':
        return g_thumb

    elif thumbnail[0:4] == "http" :
        return thumbnail

    elif thumbnail[0] == '/':
        if settings.fullres_thumbnails:
            return 'http://'+server+thumbnail
        else:
            return photoTranscode(server, 'http://localhost:32400' + thumbnail, width, height)


    else:
        return g_thumb

def getFanart(data, server, width=1280, height=720):
    '''
        Simply take a URL or path and determine how to format for fanart
        @ input: elementTree element, server name
        @ return formatted URL for photo resizing
    '''
    if settings.skipimages:
        return ''
        
    fanart=data.get('art','').encode('utf-8')

    if fanart == '':
        return ''

    elif fanart[0:4] == "http" :
        return fanart

    elif fanart[0] == '/':
        if settings.fullres_fanart:
            return 'http://%s%s' % (server, fanart)
        else:
            return photoTranscode(server, 'http://localhost:32400' + fanart, width, height)

    else:
        return ''

def getServerFromURL( url ):
    '''
    Simply split the URL up and get the server portion, sans port
    @ input: url, woth or without protocol
    @ return: the URL server
    '''
    if url[0:4] == "http" or url[0:4] == "plex":
        return url.split('/')[2]
    else:
        return url.split('/')[0]

def getLinkURL(url, pathData, server, season_shelf=False):
    '''
        Investigate the passed URL and determine what is required to
        turn it into a usable URL
        @ input: url, XML data and PM server address
        @ return: Usable http URL
    '''
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    if not season_shelf:
        path = pathData.get('key', '')
    else:
        path = pathData.get('parentKey', '') + "/children"
        
    printDebug("Path is " + path, level=DEBUG_DEBUG)

    if path == '':
        printDebug("Empty Path")
        return

    #If key starts with http, then return it
    if path[0:4] == "http":
        printDebug("Detected http link", level=DEBUG_DEBUG)
        return path

    #If key starts with a / then prefix with server address
    elif path[0] == '/':
        printDebug("Detected base path link", level=DEBUG_DEBUG)
        return 'http://%s%s' % (server, path)

    #If key starts with plex:// then it requires transcoding
    elif path[0:5] == "plex:":
        printDebug("Detected plex link", level=DEBUG_DEBUG)
        components = path.split('&')
        for i in components:
            if 'prefix=' in i:
                del components[components.index(i)]
                break
        if pathData.get('identifier',None):
            components.append('identifier='+pathData['identifier'])

        path='&'.join(components)
        return 'plex://'+server+'/'+'/'.join(path.split('/')[3:])
        
    elif path[0:5] == "rtmp:" or path[0:6] == "rtmpe:" :
        printDebug("Detected RTMP link", level=DEBUG_DEBUG)
        return path

    #Any thing else is assumed to be a relative path and is built on existing url
    else:
        printDebug("Detected relative link", level=DEBUG_DEBUG)
        return "%s/%s" % (url, path)

    return url

def plexOnline( url ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    xbmcplugin.setContent(pluginhandle, 'addons')

    server=getServerFromURL(url)

    tree=getXML(url)
    if tree is None:
        return

    for plugin in tree:

        details={'title' : plugin.get('title',plugin.get('name','Unknown')).encode('utf-8') }
        extraData={'type'      : "Video" ,
                   'installed' : int(plugin.get('installed',2)) ,
                   'key'       : plugin.get('key','') ,
                   'thumb'     : getThumb(plugin,server)}

        extraData['mode']=_MODE_CHANNELINSTALL

        if extraData['installed'] == 1:
            details['title']=details['title']+" (installed)"

        elif extraData['installed'] == 2:
            extraData['mode']=_MODE_PLEXONLINE

        u=getLinkURL(url, plugin, server)

        extraData['parameters']={'name' : details['title'] }
        
        addGUIItem(u, details, extraData)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=True)

def install( url, name ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    tree=getXML(url)
    if tree is None:
        return

    operations={}
    i=0
    for plums in tree.findall('Directory'):
        operations[i]=plums.get('title')

        #If we find an install option, switch to a yes/no dialog box
        if operations[i].lower() == "install":
            printDebug("Not installed.  Print dialog")
            ret = xbmcgui.Dialog().yesno("Plex Online","About to install " + name)

            if ret:
                printDebug("Installing....")
                installed = getURL(url+"/install")
                tree = etree.fromstring(installed)

                msg=tree.get('message','(blank)')
                printDebug(msg)
                xbmcgui.Dialog().ok("Plex Online",msg)
            return

        i+=1

    #Else continue to a selection dialog box
    ret = xbmcgui.Dialog().select("This plugin is already installed..",operations.values())

    if ret == -1:
        printDebug("No option selected, cancelling")
        return

    printDebug("Option " + str(ret) + " selected.  Operation is " + operations[ret])
    u=url+"/"+operations[ret].lower()

    action = getURL(u)
    tree = etree.fromstring(action)

    msg=tree.get('message')
    printDebug(msg)
    xbmcgui.Dialog().ok("Plex Online",msg)
    xbmc.executebuiltin("Container.Refresh")


    return

def channelView( url ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    tree=getXML(url)
    if tree is None:
        return
    server=getServerFromURL(url)
    setWindowHeading(tree)
    for channels in tree.getiterator('Directory'):

        if channels.get('local','') == "0":
            continue

        arguments=dict(channels.items())

        extraData={'fanart_image' : getFanart(channels, server) ,
                   'thumb'        : getThumb(channels, server) }

        details={'title' : channels.get('title','Unknown') }

        suffix=channels.get('path').split('/')[1]

        if channels.get('unique','')=='0':
            details['title']=details['title']+" ("+suffix+")"

        #Alter data sent into getlinkurl, as channels use path rather than key
        p_url=getLinkURL(url, {'key': channels.get('path',None), 'identifier' : channels.get('path',None)} , server)

        if suffix == "photos":
            extraData['mode']=_MODE_PHOTOS
        elif suffix == "video":
            extraData['mode']=_MODE_PLEXPLUGINS
        elif suffix == "music":
            extraData['mode']=_MODE_MUSIC
        else:
            extraData['mode']=_MODE_GETCONTENT

        addGUIItem(p_url,details,extraData)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=True)

def photoTranscode( server, url, width=1280, height=720 ):
        return 'http://%s/photo/:/transcode?url=%s&width=%s&height=%s' % (server, urllib.quote_plus(url), width, height)

def skin( server_list=None, type=None ):
    #Gather some data and set the window properties
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    #Get the global host variable set in settings
    WINDOW = xbmcgui.Window( 10000 )

    sectionCount=0
    serverCount=0
    sharedCount=0
    shared_flag={}
    hide_shared = __settings__.getSetting('hide_shared')

    if server_list is None:
        server_list = discoverAllServers()

    #For each of the servers we have identified
    for section in getAllSections(server_list):

        extraData={ 'fanart_image' : getFanart(section, section['address']) ,
                    'thumb'        : getFanart(section, section['address'], False) }

        #Determine what we are going to do process after a link is selected by the user, based on the content we find

        path=section['path']

        if section['type'] == 'show':
            if hide_shared == "true" and section.get('owned') == '0':
                shared_flag['show']=True
                continue
            window="VideoLibrary"
            mode=_MODE_TVSHOWS
        if  section['type'] == 'movie':
            if hide_shared == "true" and section.get('owned') == '0':
                shared_flag['movie']=True
                continue
            window="VideoLibrary"
            mode=_MODE_MOVIES
        if  section['type'] == 'artist':
            if hide_shared == "true" and section.get('owned') == '0':
                shared_flag['artist']=True
                continue
            window="MusicFiles"
            mode=_MODE_ARTISTS
        if  section['type'] == 'photo':
            if hide_shared == "true" and section.get('owned') == '0':
                shared_flag['photo']=True
                continue
            window="Pictures"
            mode=_MODE_PHOTOS

        aToken=getAuthDetails(section)
        qToken=getAuthDetails(section, prefix='?')

        if settings.secondary:
            mode=_MODE_GETCONTENT
        else:
            path=path+'/all'

        s_url='http://%s%s&mode=%s%s' % ( section['address'], path, mode, aToken)

        #Build that listing..
        WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , section['title'])
        WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , section['serverName'])
        WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow("+window+",plugin://plugin.video.plexbmc/?url="+s_url+",return)")
        WINDOW.setProperty("plexbmc.%d.art"      % (sectionCount) , extraData['fanart_image']+qToken)
        WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , section['type'])
        WINDOW.setProperty("plexbmc.%d.icon"     % (sectionCount) , extraData['thumb']+qToken)
        WINDOW.setProperty("plexbmc.%d.thumb"    % (sectionCount) , extraData['thumb']+qToken)
        WINDOW.setProperty("plexbmc.%d.partialpath" % (sectionCount) , "ActivateWindow("+window+",plugin://plugin.video.plexbmc/?url=http://"+section['address']+section['path'])
        WINDOW.setProperty("plexbmc.%d.search" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=http://%s%s%s&mode=%s%s,return)" % (window, section['address'], section['path'], "/search?type=1", mode, aToken) )
        WINDOW.setProperty("plexbmc.%d.recent" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=http://%s%s%s&mode=%s%s,return)" % (window, section['address'], section['path'], "/recentlyAdded", mode, aToken) )
        WINDOW.setProperty("plexbmc.%d.all" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=http://%s%s%s&mode=%s%s,return)" % (window, section['address'], section['path'], "/all", mode, aToken) )
        WINDOW.setProperty("plexbmc.%d.viewed" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=http://%s%s%s&mode=%s%s,return)" % (window, section['address'], section['path'], "/recentlyViewed", mode, aToken) )
        WINDOW.setProperty("plexbmc.%d.ondeck" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=http://%s%s%s&mode=%s%s,return)" % (window, section['address'], section['path'], "/onDeck", mode, aToken) )
        WINDOW.setProperty("plexbmc.%d.released" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=http://%s%s%s&mode=%s%s,return)" % (window, section['address'], section['path'], "/newest", mode, aToken) )
        WINDOW.setProperty("plexbmc.%d.shared"     % (sectionCount) , "false")

        if section['type'] == "artist":
            WINDOW.setProperty("plexbmc.%d.album" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=http://%s%s%s&mode=%s%s,return)" % (window, section['address'], section['path'], "/albums", mode, aToken) )
            WINDOW.setProperty("plexbmc.%d.search" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=http://%s%s%s&mode=%s%s,return)" % (window, section['address'], section['path'], "/search?type=10", mode, aToken) )
        elif section['type'] == "photo":
            WINDOW.setProperty("plexbmc.%d.year" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=http://%s%s%s&mode=%s%s,return)" % (window, section['address'], section['path'], "/year", mode, aToken) )
        elif section['type'] == "show":
            WINDOW.setProperty("plexbmc.%d.search" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=http://%s%s%s&mode=%s%s,return)" % (window, section['address'], section['path'], "/search?type=4", mode, aToken) )
        elif section['type'] == "movie":
            WINDOW.setProperty("plexbmc.%d.search" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=http://%s%s%s&mode=%s%s,return)" % (window, section['address'], section['path'], "/search?type=1", mode, aToken) )
        
        printDebug("Building window properties index [" + str(sectionCount) + "] which is [" + section['title'] + "]")
        printDebug("PATH in use is: ActivateWindow("+window+",plugin://plugin.video.plexbmc/?url="+s_url+",return)")
        sectionCount += 1

   
    if type == "nocat":
        WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared...")
        WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
        WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=/&mode="+str(_MODE_SHARED_ALL)+",return)")
        WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "movie")
        WINDOW.setProperty("plexbmc.%d.shared"     % (sectionCount) , "true")
        sectionCount += 1
    
    else:
   
        if shared_flag.get('movie'):
            WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared...")
            WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=/&mode="+str(_MODE_SHARED_MOVIES)+",return)")
            WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "movie")
            WINDOW.setProperty("plexbmc.%d.shared"     % (sectionCount) , "true")
            sectionCount += 1

        if shared_flag.get('show'):
            WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared...")
            WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=/&mode="+str(_MODE_SHARED_SHOWS)+",return)")
            WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "show")
            WINDOW.setProperty("plexbmc.%d.shared"     % (sectionCount) , "true")
            sectionCount += 1
            
        if shared_flag.get('artist'):
            WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared...")
            WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(MusicFiles,plugin://plugin.video.plexbmc/?url=/&mode="+str(_MODE_SHARED_MUSIC)+",return)")
            WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "artist")
            WINDOW.setProperty("plexbmc.%d.shared"     % (sectionCount) , "true")
            sectionCount += 1
            
        if shared_flag.get('photo'):
            WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared...")
            WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(Pictures,plugin://plugin.video.plexbmc/?url=/&mode="+str(_MODE_SHARED_PHOTOS)+",return)")
            WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "photo")
            WINDOW.setProperty("plexbmc.%d.shared"     % (sectionCount) , "true")
            sectionCount += 1
        
        
    #For each of the servers we have identified
    numOfServers=len(server_list)

    for server in server_list.values():
    
        if server['class'] == "secondary":
            continue
    
        aToken=getAuthDetails(server)
        qToken=getAuthDetails(server, prefix='?')
        
        if settings.channelview:
            WINDOW.setProperty("plexbmc.channel", "1")
            WINDOW.setProperty("plexbmc.%d.server.channel" % (serverCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=http://"+server['server']+":"+server['port']+"/system/plugins/all&mode=21"+aToken+",return)")
        else:
            WINDOW.clearProperty("plexbmc.channel")
            WINDOW.setProperty("plexbmc.%d.server.video" % (serverCount) , "http://"+server['server']+":"+server['port']+"/video&mode=7"+aToken)
            WINDOW.setProperty("plexbmc.%d.server.music" % (serverCount) , "http://"+server['server']+":"+server['port']+"/music&mode=17"+aToken)
            WINDOW.setProperty("plexbmc.%d.server.photo" % (serverCount) , "http://"+server['server']+":"+server['port']+"/photos&mode=16"+aToken)

        WINDOW.setProperty("plexbmc.%d.server.online" % (serverCount) , "http://"+server['server']+":"+server['port']+"/system/plexonline&mode=19"+aToken)

        WINDOW.setProperty("plexbmc.%d.server" % (serverCount) , server['serverName'])
        printDebug ("Name mapping is :" + server['serverName'])

        serverCount+=1

    #Clear out old data
    try:
        printDebug("Clearing properties from [" + str(sectionCount) + "] to [" + WINDOW.getProperty("plexbmc.sectionCount") + "]")

        for i in range(sectionCount, int(WINDOW.getProperty("plexbmc.sectionCount"))+1):
            WINDOW.clearProperty("plexbmc.%d.uuid"    % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.title"    % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.subtitle" % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.url"      % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.path"     % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.window"   % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.art"      % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.type"     % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.icon"     % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.thumb"    % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.recent"    % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.all"    % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.search"    % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.viewed"    % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.ondeck" % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.released" % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.shared"     % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.album"     % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.year"     % ( i ) )

    except:
        pass

    printDebug("Total number of skin sections is [" + str(sectionCount) + "]")
    printDebug("Total number of servers is ["+str(numOfServers)+"]")
    WINDOW.setProperty("plexbmc.sectionCount", str(sectionCount))
    WINDOW.setProperty("plexbmc.numServers", str(numOfServers))
    if __settings__.getSetting('myplex_user') != '':
        WINDOW.setProperty("plexbmc.queue" , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=http://myplexqueue&mode=24,return)")
        WINDOW.setProperty("plexbmc.myplex",  "1" )
    else:
        WINDOW.clearProperty("plexbmc.myplex")

    return

def amberskin():
    #Gather some data and set the window properties
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    #Get the global host variable set in settings
    WINDOW = xbmcgui.Window( 10000 )

    sectionCount=0
    serverCount=0
    sharedCount=0
    shared_flag={}
    hide_shared = __settings__.getSetting('hide_shared')

    server_list = discoverAllServers()
    printDebug("Using list of " + str(len(server_list)) + " servers: " + str(server_list))

    #For each of the servers we have identified
    sections = getAllSections(server_list)
    printDebug("Total sections: " + str(len(sections)))

    for section in sections:

        printDebug("=Enter amberskin section=")
        printDebug(str(section))
        printDebug("=/section=")

        extraData = {'fanart_image': getFanart(section, section['address']), 'thumb': g_thumb}

        #Determine what we are going to do process after a link is selected by the user, based on the content we find
        path = section['path']

        if section['type'] == 'show':
            if hide_shared == "true" and section.get('owned') == '0':
                shared_flag['show']=True
                sharedCount += 1
                continue
            window="VideoLibrary"
            mode=_MODE_TVSHOWS
        elif  section['type'] == 'movie':
            if hide_shared == "true" and section.get('owned') == '0':
                shared_flag['movie']=True
                sharedCount += 1
                continue
            window="VideoLibrary"
            mode=_MODE_MOVIES
        elif  section['type'] == 'artist':
            if hide_shared == "true" and section.get('owned') == '0':
                shared_flag['artist']=True
                sharedCount += 1
                continue
            window="MusicFiles"
            mode=_MODE_ARTISTS
        elif  section['type'] == 'photo':
            if hide_shared == "true" and section.get('owned') == '0':
                shared_flag['photo']=True
                sharedCount += 1
                continue
            window="Pictures"
        else:
            if hide_shared == "true" and section.get('owned') == '0':
                shared_flag['movie']=True
                sharedCount += 1
                continue
            window="Videos"
            mode=_MODE_PHOTOS

        aToken=getAuthDetails(section)
        qToken=getAuthDetails(section, prefix='?')

        printDebug("===TOKENS ARE===")
        printDebug(aToken)
        printDebug("===/TOKENS ===")

        if settings.secondary:
            mode=_MODE_GETCONTENT
        else:
            path=path+'/all'

        s_url='http://%s%s&mode=%s%s' % ( section['address'], path, mode, aToken)

        #Build that listing..
        WINDOW.setProperty("plexbmc.%d.uuid" % (sectionCount) , section['sectionuuid'])
        WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , section['title'])
        WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , section['serverName'])
        WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow("+window+",plugin://plugin.video.plexbmc/?url="+s_url+",return)")
        WINDOW.setProperty("plexbmc.%d.art"      % (sectionCount) , extraData['fanart_image']+qToken)
        WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , section['type'])
        WINDOW.setProperty("plexbmc.%d.icon"     % (sectionCount) , extraData['thumb']+qToken)
        WINDOW.setProperty("plexbmc.%d.thumb"    % (sectionCount) , extraData['thumb']+qToken)
        WINDOW.setProperty("plexbmc.%d.partialpath" % (sectionCount) , "ActivateWindow("+window+",plugin://plugin.video.plexbmc/?url=http://"+section['address']+section['path'])
        WINDOW.setProperty("plexbmc.%d.search" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=http://%s%s%s&mode=%s%s,return)" % (window, section['address'], section['path'], "/search?type=1", mode, aToken) )
        WINDOW.setProperty("plexbmc.%d.recent" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=http://%s%s%s&mode=%s%s,return)" % (window, section['address'], section['path'], "/recentlyAdded", mode, aToken) )
        WINDOW.setProperty("plexbmc.%d.all" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=http://%s%s%s&mode=%s%s,return)" % (window, section['address'], section['path'], "/all", mode, aToken) )
        WINDOW.setProperty("plexbmc.%d.viewed" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=http://%s%s%s&mode=%s%s,return)" % (window, section['address'], section['path'], "/recentlyViewed", mode, aToken) )
        WINDOW.setProperty("plexbmc.%d.ondeck" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=http://%s%s%s&mode=%s%s,return)" % (window, section['address'], section['path'], "/onDeck", mode, aToken) )
        WINDOW.setProperty("plexbmc.%d.released" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=http://%s%s%s&mode=%s%s,return)" % (window, section['address'], section['path'], "/newest", mode, aToken) )
        WINDOW.setProperty("plexbmc.%d.shared"     % (sectionCount) , "false")

        if section['type'] == "artist":
            WINDOW.setProperty("plexbmc.%d.album" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=http://%s%s%s&mode=%s%s,return)" % (window, section['address'], section['path'], "/albums", mode, aToken) )
            WINDOW.setProperty("plexbmc.%d.search" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=http://%s%s%s&mode=%s%s,return)" % (window, section['address'], section['path'], "/search?type=10", mode, aToken) )
        elif section['type'] == "photo":
            WINDOW.setProperty("plexbmc.%d.year" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=http://%s%s%s&mode=%s%s,return)" % (window, section['address'], section['path'], "/year", mode, aToken) )
        elif section['type'] == "show":
            WINDOW.setProperty("plexbmc.%d.search" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=http://%s%s%s&mode=%s%s,return)" % (window, section['address'], section['path'], "/search?type=4", mode, aToken) )
        elif section['type'] == "movie":
            WINDOW.setProperty("plexbmc.%d.search" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=http://%s%s%s&mode=%s%s,return)" % (window, section['address'], section['path'], "/search?type=1", mode, aToken) )

        printDebug("Building window properties index [" + str(sectionCount) + "] which is [" + section['title'] + "]")
        printDebug("PATH in use is: ActivateWindow("+window+",plugin://plugin.video.plexbmc/?url="+s_url+",return)")
        sectionCount += 1


    if __settings__.getSetting('myplex_user') != '' and hide_shared == 'true' and sharedCount != 0:
        WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared Content")
        WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
        WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=/&mode="+str(_MODE_SHARED_ALL)+",return)")
        WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "shared")
        WINDOW.setProperty("plexbmc.%d.shared"     % (sectionCount) , "true")
        sectionCount += 1

    elif sharedCount != 0:

        if shared_flag.get('movie'):
            WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared...")
            WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=/&mode="+str(_MODE_SHARED_MOVIES)+",return)")
            WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "shared")
            WINDOW.setProperty("plexbmc.%d.shared"     % (sectionCount) , "true")
            sectionCount += 1

        if shared_flag.get('show'):
            WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared...")
            WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=/&mode="+str(_MODE_SHARED_SHOWS)+",return)")
            WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "shared")
            WINDOW.setProperty("plexbmc.%d.shared"     % (sectionCount) , "true")
            sectionCount += 1

        if shared_flag.get('artist'):
            WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared...")
            WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(MusicFiles,plugin://plugin.video.plexbmc/?url=/&mode="+str(_MODE_SHARED_MUSIC)+",return)")
            WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "shared")
            WINDOW.setProperty("plexbmc.%d.shared"     % (sectionCount) , "true")
            sectionCount += 1

        if shared_flag.get('photo'):
            WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared...")
            WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(Pictures,plugin://plugin.video.plexbmc/?url=/&mode="+str(_MODE_SHARED_PHOTOS)+",return)")
            WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "shared")
            WINDOW.setProperty("plexbmc.%d.shared"     % (sectionCount) , "true")
            sectionCount += 1

    else:
        pass

    #For each of the servers we have identified
    numOfServers=len(server_list)
    shelfChannel (server_list)

    for server in server_list.values():

        if server['class'] == "secondary":
            continue

        aToken=getAuthDetails(server)
        #qToken=getAuthDetails(server, prefix='?')

        if settings.channelview:
            WINDOW.setProperty("plexbmc.channel", "1")
            WINDOW.setProperty("plexbmc.%d.server.channel" % (serverCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=http://"+server['server']+":"+server['port']+"/system/plugins/all&mode=21"+aToken+",return)")
        else:
            WINDOW.clearProperty("plexbmc.channel")
            WINDOW.setProperty("plexbmc.%d.server.video" % (serverCount) , "http://"+server['server']+":"+server['port']+"/video&mode=7"+aToken)
            WINDOW.setProperty("plexbmc.%d.server.music" % (serverCount) , "http://"+server['server']+":"+server['port']+"/music&mode=17"+aToken)
            WINDOW.setProperty("plexbmc.%d.server.photo" % (serverCount) , "http://"+server['server']+":"+server['port']+"/photos&mode=16"+aToken)

        WINDOW.setProperty("plexbmc.%d.server.online" % (serverCount) , "http://"+server['server']+":"+server['port']+"/system/plexonline&mode=19"+aToken)

        WINDOW.setProperty("plexbmc.%d.server" % (serverCount) , server['serverName'])
        printDebug ("Name mapping is :" + server['serverName'])

        serverCount+=1

    #Clear out old data
    try:
        printDebug("Clearing properties from [" + str(sectionCount) + "] to [" + WINDOW.getProperty("plexbmc.sectionCount") + "]")

        for i in range(sectionCount, int(WINDOW.getProperty("plexbmc.sectionCount"))+1):
            WINDOW.clearProperty("plexbmc.%d.uuid"    % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.title"    % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.subtitle" % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.url"      % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.path"     % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.window"   % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.art"      % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.type"     % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.icon"     % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.thumb"    % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.recent"    % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.all"    % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.search"    % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.viewed"    % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.ondeck" % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.released" % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.shared"     % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.album"     % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.year"     % ( i ) )

    except:
        pass

    printDebug("Total number of skin sections is [" + str(sectionCount) + "]")
    printDebug("Total number of servers is ["+str(numOfServers)+"]")
    WINDOW.setProperty("plexbmc.sectionCount", str(sectionCount))
    WINDOW.setProperty("plexbmc.numServers", str(numOfServers))

    if __settings__.getSetting('myplex_user') != '':
        WINDOW.setProperty("plexbmc.queue" , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=http://myplexqueue&mode=24,return)")
        WINDOW.setProperty("plexbmc.myplex",  "1" )

        #Now let's populate queue shelf items since we have MyPlex login
        if __settings__.getSetting('homeshelf') != '3':
            printDebug("== ENTER ==", level=DEBUG_DEBUG)
            aToken = getMyPlexToken()
            myplex_server = getMyPlexURL('/pms/playlists/queue/all')
            root = etree.fromstring(myplex_server)
            server_address = getMasterServer()['address']
            queue_count = 1

            for media in root:
                printDebug("Found a queue item entry: [%s]" % (media.get('title', '').encode('UTF-8') , ))
                m_url = "plugin://plugin.video.plexbmc?url=%s&mode=%s&indirect=%s&t=%s" % (getLinkURL('http://'+server_address, media, server_address), 18, 1, aToken)
                m_thumb = getShelfThumb(media, server_address, seasonThumb=0)+aToken

                try:
                    movie_runtime = str(int(float(media.get('duration'))/1000/60))
                except:
                    movie_runtime = ""

                WINDOW.setProperty("Plexbmc.Queue.%s.Path" % queue_count, m_url)
                WINDOW.setProperty("Plexbmc.Queue.%s.Title" % queue_count, media.get('title', 'Unknown').encode('UTF-8'))
                WINDOW.setProperty("Plexbmc.Queue.%s.Year" % queue_count, media.get('originallyAvailableAt', '').encode('UTF-8'))
                WINDOW.setProperty("Plexbmc.Queue.%s.Duration" % queue_count, movie_runtime)
                WINDOW.setProperty("Plexbmc.Queue.%s.Thumb" % queue_count, m_thumb)

                queue_count += 1

                printDebug("Building Queue item: %s" % media.get('title', 'Unknown').encode('UTF-8'))
                printDebug("Building Queue item url: %s" % m_url)
                printDebug("Building Queue item thumb: %s" % m_thumb)

            clearQueueShelf(queue_count)

    else:
        WINDOW.clearProperty("plexbmc.myplex")

    fullShelf (server_list)

def fullShelf(server_list={}):
    #Gather some data and set the window properties
    printDebug("== ENTER ==", level=DEBUG_DEBUG)

    if __settings__.getSetting('homeshelf') == '3' or ((__settings__.getSetting('movieShelf') == "false" and __settings__.getSetting('tvShelf') == "false" and __settings__.getSetting('musicShelf') == "false")):
        printDebug("Disabling all shelf items")
        clearShelf()
        clearOnDeckShelf()
        return

    #Get the global host variable set in settings
    WINDOW = xbmcgui.Window( 10000 )

    recentMovieCount=1
    recentSeasonCount=1
    recentMusicCount=1
    recentPhotoCount=1
    ondeckMovieCount=1
    ondeckSeasonCount=1
    recent_list={}
    ondeck_list={}
    full_count=0

    #if server_list == {}:
    #    server_list=discoverAllServers()

    if server_list == {}:
        xbmc.executebuiltin("XBMC.Notification(Unable to see any media servers,)")
        clearShelf(0, 0, 0, 0)
        return

    randomNumber = str(random.randint(1000000000,9999999999))

    '''
    logfile = PLUGINPATH+"/_server_list.txt"
    logfileh = open(logfile, "w")
    logfileh.write(str(server_list))
    logfileh.close()
    '''

    for server_details in server_list.values():

        if not server_details['owned'] == '1':
            continue

        global _PARAM_TOKEN
        _PARAM_TOKEN = server_details.get('token', '')
        aToken=getAuthDetails({'token': _PARAM_TOKEN})
        qToken='?' + aToken

        sections = getAllSections(server_list)
        #ra_log_count = 1

        if __settings__.getSetting('homeshelf') == '0' or __settings__.getSetting('homeshelf') == '2':

            '''
            logfile = PLUGINPATH+"/_shelf_sections_.txt"
            logfileh = open(logfile, "w")
            logfileh.write(str(sections))
            logfileh.close()
            '''
            
            for section in sections:
                
                _PARAM_TOKEN = section.get('token', '')
                fullpath = section.get('address') + section.get("path")
                tree = getXML('http://' + fullpath + "/recentlyAdded")
                _PARAM_TOKEN = server_details.get('token', '')

                '''
                eetee = etree.ElementTree()
                eetee._setroot(tree)
                logfile = PLUGINPATH+"/RecentlyAdded"+ str(ra_file_count) + ".xml"
                logfileh = open(logfile, "w")
                eetee.write(logfileh)
                logfileh.close()
                ra_log_count += 1
                '''

                if tree is None:
                    printDebug("PLEXBMC -> RecentlyAdded items not found on: " + fullpath)
                    continue

                libraryuuid = tree.attrib["librarySectionUUID"]
                ep_helper = {}  # helper season counter
                ra_item_count = 1
                for eachitem in tree:
                    if ra_item_count > 15:
                        break

                    if eachitem.get("type", "") == "episode":
                        key = int(eachitem.get("parentRatingKey"))  # season identifier

                        if key in ep_helper or ((__settings__.getSetting('hide_watched_recent_items') == 'true' and int(eachitem.get("viewCount", 0)) > 0)):
                            pass

                        else:
                            recent_list[full_count] = (eachitem, server_details['server'] + ":" + server_details['port'], aToken, qToken, libraryuuid)
                            ep_helper[key] = key  # use seasons as dict key so we can check
                            full_count += 1
                            ra_item_count += 1

                    else:
                        recent_list[full_count] = (eachitem, server_details['server']+":"+server_details['port'], aToken, qToken, libraryuuid)
                        full_count += 1
                        ra_item_count += 1

            full_count = 0

            '''
            logfile = PLUGINPATH+"/Recent_list.log"
            logfileh = open(logfile, "w")
            for item in recent_list:
                logfileh.write("%s\n" % item)
            logfileh.close()
            '''

            #deck_log_count = 1

        if __settings__.getSetting('homeshelf') == '1' or __settings__.getSetting('homeshelf') == '2':

            for section in sections:
                
                _PARAM_TOKEN = section.get('token', '')
                fullpath = section.get("address") + section.get("path")
                tree = getXML('http://' + fullpath + "/onDeck")
                _PARAM_TOKEN = server_details.get('token', '')
                
                '''
                eetee = etree.ElementTree()
                eetee._setroot(tree)
                logfile = PLUGINPATH+"/OnDeck"+ str(deck_file_count) + ".xml"
                logfileh = open(logfile, "w")
                eetee.write(logfileh)
                logfileh.close()
                deck_log_count += 1
                '''

                if tree is None:
                    #xbmc.executebuiltin("XBMC.Notification(Unable to contact server: "+server_details['serverName']+",)")
                    #clearShelf()
                    #return
                    print ("PLEXBMC -> OnDeck items not found on: " + fullpath, False)
                    continue

                deck_item_count = 1
                libraryuuid = tree.attrib["librarySectionUUID"]
                for eachitem in tree:
                    if deck_item_count > 15: break
                    deck_item_count +=1

                    #libraryuuid = tree.attrib["librarySectionUUID"]
                    ondeck_list[full_count] = (eachitem, server_details['server']+":"+server_details['port'], aToken, qToken, libraryuuid)
                    full_count += 1

    #For each of the servers we have identified
    for index in recent_list:

        media = recent_list[index][0]
        server_address = recent_list[index][1]
        aToken = recent_list[index][2]
        qToken = recent_list[index][3]
        libuuid = recent_list[index][4]

        if media.get('type',None) == "movie":

            if __settings__.getSetting('movieShelf') == "false":
                WINDOW.clearProperty("Plexbmc.LatestMovie.1.Path" )
                continue

            title_name=media.get('title','Unknown').encode('UTF-8')
            printDebug("Found a recent movie entry: [%s]" % title_name)

            if __settings__.getSetting('hide_watched_recent_items') == 'false' or media.get("viewCount", 0) == 0:

                title_url="plugin://plugin.video.plexbmc?url=%s&mode=%s&t=%s%s" % ( getLinkURL('http://'+server_address,media,server_address), _MODE_PLAYSHELF, randomNumber, aToken)
                title_thumb = getShelfThumb(media,server_address,seasonThumb=0)+aToken

                if media.get('duration') > 0:
                    #movie_runtime = media.get('duration', '0')
                    movie_runtime = str(int(float(media.get('duration'))/1000/60))
                else:
                    movie_runtime = ""

                if media.get('rating') > 0:
                    movie_rating = str(round(float(media.get('rating')), 1))
                else:
                    movie_rating = ''

                WINDOW.setProperty("Plexbmc.LatestMovie.%s.Path" % recentMovieCount, title_url)
                WINDOW.setProperty("Plexbmc.LatestMovie.%s.Title" % recentMovieCount, title_name)
                WINDOW.setProperty("Plexbmc.LatestMovie.%s.Year" % recentMovieCount, media.get('year', '').encode('UTF-8'))
                WINDOW.setProperty("Plexbmc.LatestMovie.%s.Rating" % recentMovieCount, movie_rating)
                WINDOW.setProperty("Plexbmc.LatestMovie.%s.Duration" % recentMovieCount, movie_runtime)
                WINDOW.setProperty("Plexbmc.LatestMovie.%s.Thumb" % recentMovieCount, title_thumb)
                WINDOW.setProperty("Plexbmc.LatestMovie.%s.uuid" % recentMovieCount, libuuid.encode('UTF-8'))
                WINDOW.setProperty("Plexbmc.LatestMovie.%s.Plot" % recentMovieCount, media.get('summary', '').encode('UTF-8'))

                m_genre = []

                for child in media:
                    if child.tag == "Genre":
                        m_genre.append(child.get('tag'))
                    else:
                        continue

                WINDOW.setProperty("Plexbmc.LatestMovie.%s.Genre" % recentMovieCount, ", ".join(m_genre).encode('UTF-8'))

                recentMovieCount += 1

            else:
                continue

        elif media.get('type',None) == "season":

            title_name=media.get('parentTitle','Unknown').encode('UTF-8')
            printDebug("Found a recent season entry [%s]" % title_name)

            if __settings__.getSetting('tvShelf') == "false":
                WINDOW.clearProperty("Plexbmc.LatestEpisode.1.Path" )
                continue

            title_url="ActivateWindow(VideoLibrary, plugin://plugin.video.plexbmc?url=%s&mode=%s%s, return)" % ( getLinkURL('http://'+server_address,media,server_address), _MODE_TVEPISODES, aToken)
            title_thumb=getShelfThumb(media,server_address,seasonThumb=0)+aToken

            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.Path" % recentSeasonCount, title_url )
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeTitle" % recentSeasonCount, '')
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeSeason" % recentSeasonCount, media.get('title','').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.ShowTitle" % recentSeasonCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.Thumb" % recentSeasonCount, title_thumb)
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.uuid" % recentSeasonCount, media.get('librarySectionUUID','').encode('UTF-8'))

            recentSeasonCount += 1

        elif media.get('type') == "album":

            if __settings__.getSetting('musicShelf') == "false":
                WINDOW.clearProperty("Plexbmc.LatestAlbum.1.Path" )
                continue

            title_name=media.get('parentTitle','Unknown').encode('UTF-8')
            title_url="ActivateWindow(MusicFiles, plugin://plugin.video.plexbmc?url=%s&mode=%s%s, return)" % ( getLinkURL('http://'+server_address,media,server_address), _MODE_TRACKS, aToken)
            title_thumb=getShelfThumb(media,server_address,seasonThumb=0)+aToken

            printDebug("Found a recent album entry: [%s]", title_name)
            
            WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Path" % recentMusicCount, title_url )
            WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Title" % recentMusicCount, media.get('title','Unknown').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Artist" % recentMusicCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Thumb" % recentMusicCount, title_thumb)

            recentMusicCount += 1

        elif media.get('type') == "photo":


            title_name=media.get('title','Unknown').encode('UTF-8')
            title_url="ActivateWindow(Pictures, plugin://plugin.video.plexbmc/?url=http://%s%s&mode=%s%s,return" % ( server_address, "/recentlyAdded", _MODE_PHOTOS, aToken)
            title_thumb = getShelfThumb(media, server_address, seasonThumb=0) + aToken

            printDebug("Found a recent photo entry: [%s]" % title_name)

            WINDOW.setProperty("Plexbmc.LatestPhoto.%s.Path" % recentPhotoCount, title_url)
            WINDOW.setProperty("Plexbmc.LatestPhoto.%s.Title" % recentPhotoCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestPhoto.%s.Thumb" % recentPhotoCount, title_thumb)

            recentPhotoCount += 1

        elif media.get('type',None) == "episode":

            title_name=media.get('title','Unknown').encode('UTF-8')
            printDebug("Found an Recent episode entry [%s]" % title_name)

            if __settings__.getSetting('tvShelf') == "false":
                WINDOW.clearProperty("Plexbmc.LatestEpisode.1.Path" )
                continue

            title_url="ActivateWindow(Videos, plugin://plugin.video.plexbmc?url=%s&mode=%s%s, return)" % ( getLinkURL('http://'+server_address, media, server_address, season_shelf=True), _MODE_TVEPISODES, aToken)
            title_thumb = getShelfThumb(media, server_address, seasonThumb=1) + aToken

            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.Path" % recentSeasonCount, title_url)
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeTitle" % recentSeasonCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeNumber" % recentSeasonCount, media.get('index','').encode('utf-8'))
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeSeason" % recentSeasonCount, media.get('parentIndex','').encode('UTF-8')+'.'+media.get('index','Unknown').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeSeasonNumber" % recentSeasonCount, media.get('parentIndex','').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.ShowTitle" % recentSeasonCount, media.get('grandparentTitle','').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.Thumb" % recentSeasonCount, title_thumb)
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.uuid" % recentSeasonCount, libuuid.encode('utf-8'))

            recentSeasonCount += 1

        printDebug(" Building Recent window title: %s\n    Building Recent window url: %s\n    Building Recent window thumb: %s" % (title_name, title_url, title_thumb), level=DEBUG_DEBUG)
        
    clearShelf(recentMovieCount, recentSeasonCount, recentMusicCount, recentPhotoCount)

    #For each of the servers we have identified
    for index in sorted(ondeck_list):

        media = ondeck_list[index][0]
        server_address = ondeck_list[index][1]
        aToken = ondeck_list[index][2]
        qToken = ondeck_list[index][3]
        libuuid = ondeck_list[index][4]

        if media.get('type',None) == "movie":

            title_name=media.get('title','Unknown').encode('UTF-8')
            printDebug("Found a OnDeck movie entry: [%s]" % title_name)

            if __settings__.getSetting('movieShelf') == "false":
                WINDOW.clearProperty("Plexbmc.OnDeckMovie.1.Path" )
                continue

            title_url = "plugin://plugin.video.plexbmc?url=%s&mode=%s&t=%s%s" % ( getLinkURL('http://'+server_address,media,server_address), _MODE_PLAYSHELF, randomNumber, aToken)
            title_thumb = getShelfThumb(media,server_address,seasonThumb=0)+aToken

            if media.get('duration') > 0:
                #movie_runtime = media.get('duration', '0')
                movie_runtime = str(int(float(media.get('duration'))/1000/60))
            else:
                movie_runtime = ""

            if media.get('rating') > 0:
                title_rating = str(round(float(media.get('rating')), 1))
            else:
                title_rating = ''

            WINDOW.setProperty("Plexbmc.OnDeckMovie.%s.Path" % ondeckMovieCount, title_url)
            WINDOW.setProperty("Plexbmc.OnDeckMovie.%s.Title" % ondeckMovieCount, title_name)
            WINDOW.setProperty("Plexbmc.OnDeckMovie.%s.Year" % ondeckMovieCount, media.get('year','').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.OnDeckMovie.%s.Rating" % ondeckMovieCount, title_rating)
            WINDOW.setProperty("Plexbmc.OnDeckMovie.%s.Duration" % ondeckMovieCount, movie_runtime)
            WINDOW.setProperty("Plexbmc.OnDeckMovie.%s.Thumb" % ondeckMovieCount, title_thumb)
            WINDOW.setProperty("Plexbmc.OnDeckMovie.%s.uuid" % ondeckMovieCount, libuuid.encode('UTF-8'))

            ondeckMovieCount += 1

        elif media.get('type',None) == "season":

            title_name=media.get('parentTitle','Unknown').encode('UTF-8')
            printDebug("Found a OnDeck season entry [%s]" % title_name)

            if __settings__.getSetting('tvShelf') == "false":
                WINDOW.clearProperty("Plexbmc.OnDeckEpisode.1.Path" )
                continue

            title_url="ActivateWindow(VideoLibrary, plugin://plugin.video.plexbmc?url=%s&mode=%s%s, return)" % ( getLinkURL('http://'+server_address,media,server_address), _MODE_TVEPISODES, aToken)
            title_thumb=getShelfThumb(media,server_address,seasonThumb=0)+aToken

            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.Path" % ondeckSeasonCount, title_url )
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.EpisodeTitle" % ondeckSeasonCount, '')
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.EpisodeSeason" % ondeckSeasonCount, media.get('title','').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.ShowTitle" % ondeckSeasonCount, title_name)
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.Thumb" % ondeckSeasonCount, title_thumb)

            ondeckSeasonCount += 1

        elif media.get('type',None) == "episode":

            title_name=media.get('title','Unknown').encode('UTF-8')
            printDebug("Found an onDeck episode entry [%s]" % title_name)

            if __settings__.getSetting('tvShelf') == "false":
                WINDOW.clearProperty("Plexbmc.OnDeckEpisode.1.Path" )
                continue

            title_url="PlayMedia(plugin://plugin.video.plexbmc?url=%s&mode=%s&t=%s%s)" % (getLinkURL('http://'+server_address, media, server_address), _MODE_PLAYSHELF, randomNumber, aToken)
            #s_thumb="http://"+server_address+media.get('grandparentThumb','')
            title_thumb=getShelfThumb(media, server_address, seasonThumb=1)

            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.Path" % ondeckSeasonCount, title_url)
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.EpisodeTitle" % ondeckSeasonCount, title_name)
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.EpisodeNumber" % ondeckSeasonCount, media.get('index','').encode('utf-8'))
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.EpisodeSeason" % ondeckSeasonCount, media.get('grandparentTitle','Unknown').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.EpisodeSeasonNumber" % ondeckSeasonCount, media.get('parentIndex','').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.ShowTitle" % ondeckSeasonCount, title_name)
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.Thumb" % ondeckSeasonCount, title_thumb+aToken)
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.uuid" % ondeckSeasonCount, libuuid.encode('UTF-8'))

            ondeckSeasonCount += 1

        printDebug(" Building onDeck window title: %s\n    Building onDeck window url: %s\n    Building onDeck window thumb: %s" % (title_name, title_url, title_thumb), level=DEBUG_DEBUG)

    clearOnDeckShelf(ondeckMovieCount, ondeckSeasonCount)

    if __settings__.getSetting('channelShelf') == "true" or __settings__.getSetting('homeshelf') != '3':
        shelfChannel(server_list)

    else:
        printDebug("Disabling channel shelf items")
        clearChannelShelf()

def displayContent( acceptable_level, content_level ):

    '''
        Takes a content Rating and decides whether it is an allowable
        level, as defined by the content filter
        @input: content rating
        @output: boolean
    '''

    printDebug ("Checking rating flag [%s] against [%s]" % (content_level, acceptable_level))

    if acceptable_level == "Adults":
        printDebug ("OK to display")
        return True

    content_map = { 'Kids' : 0 ,
                    'Teens' : 1 ,
                    'Adults' : 2 }

    rating_map= { 'G' : 0 ,       # MPAA Kids
                  'PG' : 0 ,      # MPAA Kids
                  'PG-13' : 1 ,   # MPAA Teens
                  'R' : 2 ,       # MPAA Adults
                  'NC-17' : 2 ,   # MPAA Adults
                  'NR' : 2 ,      # MPAA Adults
                  'Unrated' : 2 , # MPAA Adults

                  'U' : 0 ,       # BBFC Kids
                  'PG' : 0 ,      # BBFC Kids
                  '12' : 1 ,      # BBFC Teens
                  '12A' : 1 ,     # BBFC Teens
                  '15' : 1 ,      # BBFC Teens
                  '18' : 2 ,      # BBFC Adults
                  'R18' : 2 ,     # BBFC Adults

                  'E' : 0 ,       #ACB Kids (hopefully)
                  'G' : 0 ,       #ACB Kids
                  'PG' : 0 ,      #ACB Kids
                  'M' : 1 ,       #ACB Teens
                  'MA15+' : 2 ,   #ADC Adults
                  'R18+' : 2 ,    #ACB Adults
                  'X18+' : 2 ,    #ACB Adults

                  'TV-Y'  : 0 ,   # US TV - Kids
                  'TV-Y7' : 0 ,   # US TV - Kids
                  'TV -G' : 0 ,   # Us TV - kids
                  'TV-PG' : 1 ,   # US TV - Teens
                  'TV-14' : 1 ,   # US TV - Teens
                  'TV-MA' : 2 ,   # US TV - Adults

                  'G' :  0 ,      # CAN - kids
                  'PG' : 0 ,      # CAN - kids
                  '14A' : 1 ,     # CAN - teens
                  '18A' : 2 ,     # CAN - Adults
                  'R' : 2 ,       # CAN - Adults
                  'A' : 2 }       # CAN - Adults

    if content_level is None or content_level == "None":
        printDebug("Setting [None] rating as %s" % ( __settings__.getSetting('contentNone') , ))
        if content_map[__settings__.getSetting('contentNone')] <= content_map[acceptable_level]:
            printDebug ("OK to display")
            return True
    else:
        try:
            if rating_map[content_level] <= content_map[acceptable_level]:
                printDebug ("OK to display")
                return True
        except:
            print "Unknown rating flag [%s] whilst lookuing for [%s] - will filter for now, but needs to be added" % (content_level, acceptable_level)

    printDebug ("NOT OK to display")
    return False

def shelf( server_list=None ):
    #Gather some data and set the window properties
    printDebug("== ENTER ==", level=DEBUG_DEBUG)

    if (__settings__.getSetting('movieShelf') == "false" and __settings__.getSetting('tvShelf') == "false" and\
                    __settings__.getSetting('musicShelf') == "false") or __settings__.getSetting('homeshelf') == '3':
        printDebug("Disabling all shelf items")
        clearShelf()
        return

    #Get the global host variable set in settings
    WINDOW = xbmcgui.Window( 10000 )

    movieCount=1
    seasonCount=1
    musicCount=1
    added_list={}    
    direction=True
    full_count=0
    
    if server_list is None:
        server_list=discoverAllServers()

    if server_list == {}:
        xbmc.executebuiltin("XBMC.Notification(Unable to see any media servers,)")
        clearShelf(0,0,0)
        return
        
    if __settings__.getSetting('homeshelf') == '0' or __settings__.getSetting('homeshelf') == '2':
        endpoint="/library/recentlyAdded"
    else:
        direction=False
        endpoint="/library/onDeck"

        
    randomNumber=str(random.randint(1000000000,9999999999))
        
    for server_details in server_list.values():

        if server_details['class'] == "secondary":
            continue
    
        if not server_details['owned'] == '1':
            continue
    
        global _PARAM_TOKEN
        _PARAM_TOKEN = server_details.get('token','')
        aToken=getAuthDetails({'token': _PARAM_TOKEN} )
        qToken=getAuthDetails({'token': _PARAM_TOKEN}, prefix='?')
        
        tree=getXML('http://'+server_details['server']+":"+server_details['port']+endpoint)
        if tree is None:
            xbmc.executebuiltin("XBMC.Notification(Unable to contact server: "+server_details['serverName']+",)")
            clearShelf()
            return

        for eachitem in tree:

            if direction:
                added_list[int(eachitem.get('addedAt',0))] = (eachitem, server_details['server']+":"+server_details['port'], aToken, qToken )
            else:
                added_list[full_count] = (eachitem, server_details['server']+":"+server_details['port'], aToken, qToken )
                full_count += 1

    library_filter = __settings__.getSetting('libraryfilter')
    acceptable_level = __settings__.getSetting('contentFilter')

    #For each of the servers we have identified
    for index in sorted(added_list, reverse=direction):

        media=added_list[index][0]
        server_address=added_list[index][1]
        aToken=added_list[index][2]
        qToken=added_list[index][3]

        if media.get('type',None) == "movie":

            title_name=media.get('title','Unknown').encode('UTF-8')

            printDebug("Found a recent movie entry: [%s]" % title_name )

            if __settings__.getSetting('movieShelf') == "false":
                WINDOW.clearProperty("Plexbmc.LatestMovie.1.Path" )
                continue

            if not displayContent( acceptable_level , media.get('contentRating') ):
                continue

            if media.get('librarySectionID') == library_filter:
                printDebug("SKIPPING: Library Filter match: %s = %s " % (library_filter, media.get('librarySectionID')))
                continue

            title_url="plugin://plugin.video.plexbmc?url=%s&mode=%s&t=%s%s" % ( getLinkURL('http://'+server_address,media,server_address), _MODE_PLAYSHELF, randomNumber, aToken)
            title_thumb=getThumb(media,server_address)

            WINDOW.setProperty("Plexbmc.LatestMovie.%s.Path" % movieCount, title_url)
            WINDOW.setProperty("Plexbmc.LatestMovie.%s.Title" % movieCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestMovie.%s.Thumb" % movieCount, title_thumb+qToken)

            movieCount += 1

        elif media.get('type',None) == "season":

            printDebug("Found a recent season entry [%s]" % ( media.get('parentTitle','Unknown').encode('UTF-8') , ))

            if __settings__.getSetting('tvShelf') == "false":
                WINDOW.clearProperty("Plexbmc.LatestEpisode.1.Path" )
                continue

            title_name=media.get('parentTitle','Unknown').encode('UTF-8')
            title_url="ActivateWindow(VideoLibrary, plugin://plugin.video.plexbmc?url=%s&mode=%s%s, return)" % ( getLinkURL('http://'+server_address,media,server_address), _MODE_TVEPISODES, aToken)
            title_thumb=getThumb(media,server_address)

            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.Path" % seasonCount, title_url )
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeTitle" % seasonCount, '')
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeSeason" % seasonCount, media.get('title','').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.ShowTitle" % seasonCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.Thumb" % seasonCount, title_thumb+qToken)
            seasonCount += 1

        elif media.get('type') == "album":

            if __settings__.getSetting('musicShelf') == "false":
                WINDOW.clearProperty("Plexbmc.LatestAlbum.1.Path" )
                continue
            
            printDebug("Found a recent album entry")

            title_name=media.get('parentTitle','Unknown').encode('UTF-8')
            title_url="ActivateWindow(MusicFiles, plugin://plugin.video.plexbmc?url=%s&mode=%s%s, return)" % ( getLinkURL('http://'+server_address,media,server_address), _MODE_TRACKS, aToken)
            title_thumb=getThumb(media,server_address)

            WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Path" % musicCount, title_url )
            WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Title" % musicCount, media.get('title','Unknown').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Artist" % musicCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Thumb" % musicCount, title_thumb+qToken)
            musicCount += 1

        elif media.get('type',None) == "episode":

            title_name=media.get('title','Unknown').encode('UTF-8')
            printDebug("Found an onDeck episode entry [%s]" % title_name)

            if __settings__.getSetting('tvShelf') == "false":
                WINDOW.clearProperty("Plexbmc.LatestEpisode.1.Path" )
                continue

            title_url="PlayMedia(plugin://plugin.video.plexbmc?url=%s&mode=%s%s)" % ( getLinkURL('http://'+server_address,media,server_address), _MODE_PLAYSHELF, aToken)
            title_thumb="http://"+server_address+media.get('grandparentThumb','')

            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.Path" % seasonCount, title_url )
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeTitle" % seasonCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeSeason" % seasonCount, media.get('grandparentTitle','Unknown').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.ShowTitle" % seasonCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.Thumb" % seasonCount, title_thumb+qToken)
            seasonCount += 1

        printDebug(" Building Recent window title: %s\n        Building Recent window url: %s\n        Building Recent window thumb: %s" % (title_name, title_url, title_thumb), level=DEBUG_DEBUG)
     
    clearShelf( movieCount, seasonCount, musicCount)

def clearShelf (movieCount=0, seasonCount=0, musicCount=0, photoCount=0):
    #Clear out old data
    WINDOW = xbmcgui.Window( 10000 )
    printDebug("Clearing unused properties")

    try:
        for i in range(movieCount, 50+1):
            WINDOW.clearProperty("Plexbmc.LatestMovie.%s.Path"   % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestMovie.%s.Title"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestMovie.%s.Year"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestMovie.%s.Rating"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestMovie.%s.Duration"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestMovie.%s.Thumb"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestMovie.%s.uuid"  % ( i ) )
        printDebug("Done clearing movies")
    except: pass

    try:
        for i in range(seasonCount, 50+1):
            WINDOW.clearProperty("Plexbmc.LatestEpisode.%s.Path"           % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestEpisode.%s.EpisodeTitle"   % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestEpisode.%s.EpisodeSeason"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestEpisode.%s.ShowTitle"      % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestEpisode.%s.Thumb"          % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestEpisode.%s.uuid"  % ( i ) )
        printDebug("Done clearing tv")
    except: pass

    try:
        for i in range(musicCount, 25+1):
            WINDOW.clearProperty("Plexbmc.LatestAlbum.%s.Path"   % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestAlbum.%s.Title"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestAlbum.%s.Artist" % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestAlbum.%s.Thumb"  % ( i ) )
        printDebug("Done clearing music")
    except: pass

    try:
        for i in range(photoCount, 25+1):
            WINDOW.clearProperty("Plexbmc.LatestPhoto.%s.Path"   % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestPhoto.%s.Title"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestPhoto.%s.Thumb"  % ( i ) )
        printDebug("Done clearing photos")
    except: pass

    return

def clearOnDeckShelf (movieCount=0, seasonCount=0):
    #Clear out old data
    WINDOW = xbmcgui.Window( 10000 )
    printDebug("Clearing unused On Deck properties")

    try:
        for i in range(movieCount, 60+1):
            WINDOW.clearProperty("Plexbmc.OnDeckMovie.%s.Path"   % ( i ) )
            WINDOW.clearProperty("Plexbmc.OnDeckMovie.%s.Title"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.OnDeckMovie.%s.Thumb"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.OnDeckMovie.%s.Rating"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.OnDeckMovie.%s.Duration"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.OnDeckMovie.%s.Year"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.OnDeckMovie.%s.uuid"  % ( i ) )
        printDebug("Done clearing On Deck movies")
    except: pass

    try:
        for i in range(seasonCount, 60+1):
            WINDOW.clearProperty("Plexbmc.OnDeckEpisode.%s.Path"           % ( i ) )
            WINDOW.clearProperty("Plexbmc.OnDeckEpisode.%s.EpisodeTitle"   % ( i ) )
            WINDOW.clearProperty("Plexbmc.OnDeckEpisode.%s.EpisodeSeason"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.OnDeckEpisode.%s.ShowTitle"      % ( i ) )
            WINDOW.clearProperty("Plexbmc.OnDeckEpisode.%s.Thumb"          % ( i ) )
            WINDOW.clearProperty("Plexbmc.OnDeckEpisode.%s.uuid"  % ( i ) )
        printDebug("Done clearing On Deck tv")
    except: pass


    return

def shelfChannel(server_list = None):
    #Gather some data and set the window properties
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    
    if __settings__.getSetting('channelShelf') == "false" or __settings__.getSetting('homeshelf') == '3':
        printDebug("Disabling channel shelf")
        clearChannelShelf()
        return
        
    #Get the global host variable set in settings
    WINDOW = xbmcgui.Window( 10000 )

    channelCount=1
    
    if server_list is None:
        server_list=discoverAllServers()
    
    if server_list == {}:
        xbmc.executebuiltin("XBMC.Notification(Unable to see any media servers,)")
        clearChannelShelf()
        return
    
    for server_details in server_list.values():

        if server_details['class'] == "secondary":
            continue
    
        if not server_details['owned'] == '1':
            continue
        
        global _PARAM_TOKEN
        _PARAM_TOKEN = server_details.get('token','')
        aToken=getAuthDetails({'token': _PARAM_TOKEN} )
        qToken=getAuthDetails({'token': _PARAM_TOKEN}, prefix='?')

        if __settings__.getSetting('channelShelf') == "false" or __settings__.getSetting('homeshelf') == '3':
            WINDOW.clearProperty("Plexbmc.LatestChannel.1.Path" )
            return

        tree=getXML('http://'+server_details['server']+":"+server_details['port']+'/channels/recentlyViewed')
        if tree is None:
            xbmc.executebuiltin("XBMC.Notification(Unable to contact server: "+server_details['serverName']+",)")
            clearChannelShelf(0)
            return

        #For each of the servers we have identified
        for media in tree:

            printDebug("Found a recent channel entry")
            suffix=media.get('key').split('/')[1]

            if suffix == "photos":
                mode=_MODE_PHOTOS
                channel_window = "Pictures"

            elif suffix == "video":
                mode=_MODE_PLEXPLUGINS
                channel_window="VideoLibrary"

            elif suffix == "music":
                mode=_MODE_MUSIC
                channel_window="MusicFiles"

            else:
                mode=_MODE_GETCONTENT
                channel_window="VideoLibrary"

            c_url="ActivateWindow(%s, plugin://plugin.video.plexbmc?url=%s&mode=%s%s)" % ( channel_window, getLinkURL('http://'+server_details['server']+":"+server_details['port'],media,server_details['server']+":"+server_details['port']), mode , aToken)
            pms_thumb = str(media.get('thumb', ''))

            if pms_thumb.startswith('/'):
                c_thumb = 'http://' + server_details['server'] + ":" + server_details['port'] + pms_thumb

            else:
                c_thumb = pms_thumb

            WINDOW.setProperty("Plexbmc.LatestChannel.%s.Path" % channelCount, c_url)
            WINDOW.setProperty("Plexbmc.LatestChannel.%s.Title" % channelCount, media.get('title', 'Unknown'))
            WINDOW.setProperty("Plexbmc.LatestChannel.%s.Thumb" % channelCount, c_thumb+aToken)

            channelCount += 1

            printDebug("Building Recent window title: %s\n      Building Recent window url: %s\n      Building Recent window thumb: %s" % (media.get('title', 'Unknown'),c_url,c_thumb), level=DEBUG_DEBUG)

    clearChannelShelf(channelCount)        
    return
    
def clearChannelShelf (channelCount=0):
            
    WINDOW = xbmcgui.Window( 10000 )
        
    try:
        for i in range(channelCount, 30+1):
            WINDOW.clearProperty("Plexbmc.LatestChannel.%s.Path"   % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestChannel.%s.Title"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestChannel.%s.Thumb"  % ( i ) )
        printDebug("Done clearing channels")
    except: pass

    return

def clearQueueShelf (queueCount=0):

    WINDOW = xbmcgui.Window( 10000 )

    try:
        for i in range(queueCount, 15+1):
            WINDOW.clearProperty("Plexbmc.Queue.%s.Path"   % ( i ) )
            WINDOW.clearProperty("Plexbmc.Queue.%s.Title"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.Queue.%s.Thumb"  % ( i ) )
        printDebug("Done clearing Queue shelf")
    except: pass

    return

def myPlexQueue():
    printDebug("== ENTER ==", level=DEBUG_DEBUG)

    if __settings__.getSetting('myplex_user') == '':
        xbmc.executebuiltin("XBMC.Notification(myplex not configured,)")
        return

    html=getMyPlexURL('/pms/playlists/queue/all')
    tree=etree.fromstring(html)

    PlexPlugins('http://my.plexapp.com/playlists/queue/all', tree)
    return

def libraryRefresh( url ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    html=getURL(url)
    printDebug ("Library refresh requested")
    xbmc.executebuiltin("XBMC.Notification(\"PleXBMC\",Library Refresh started,100)")
    return

def watched( url ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)

    if url.find("unscrobble") > 0:
        printDebug ("Marking as unwatched with: " + url)
    else:
        printDebug ("Marking as watched with: " + url)

    html=getURL(url)
    xbmc.executebuiltin("Container.Refresh")

    return

def displayServers( url ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    type=url.split('/')[2]
    printDebug("Displaying entries for " + type)
    Servers = discoverAllServers()
    Servers_list=len(Servers)

    #For each of the servers we have identified
    for mediaserver in Servers.values():

        if mediaserver['class'] == "secondary":
            continue
    
        details={'title' : mediaserver.get('serverName','Unknown') }

        if mediaserver.get('token',None):
            extraData={'token' : mediaserver.get('token') }
        else:
            extraData={}

        if type == "video":
            extraData['mode']=_MODE_PLEXPLUGINS
            s_url='http://%s:%s/video' % ( mediaserver.get('server',''), mediaserver.get('port') )
            if Servers_list == 1:
                PlexPlugins(s_url+getAuthDetails(extraData,prefix="?"))
                return

        elif type == "online":
            extraData['mode']=_MODE_PLEXONLINE
            s_url='http://%s:%s/system/plexonline' % ( mediaserver.get('server', ''),mediaserver.get('port') )
            if Servers_list == 1:
                plexOnline(s_url+getAuthDetails(extraData,prefix="?"))
                return

        elif type == "music":
            extraData['mode']=_MODE_MUSIC
            s_url='http://%s:%s/music' % ( mediaserver.get('server', ''),mediaserver.get('port') )
            if Servers_list == 1:
                music(s_url+getAuthDetails(extraData,prefix="?"))
                return

        elif type == "photo":
            extraData['mode']=_MODE_PHOTOS
            s_url='http://%s:%s/photos' % ( mediaserver.get('server', ''),mediaserver.get('port') )
            if Servers_list == 1:
                photo(s_url+getAuthDetails(extraData,prefix="?"))
                return

        addGUIItem(s_url, details, extraData )

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=True)

def getTranscodeSettings( override=False ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)

    global g_transcode
    g_transcode = __settings__.getSetting('transcode')

    if override is True:
            printDebug( "Transcode override.  Will play media with addon transcoding settings")
            g_transcode="true"

    if g_transcode == "true":
        #If transcode is set, ignore the stream setting for file and smb:
        settings.stream = "1"
        printDebug( "We are set to Transcode, overriding stream selection")
        global g_transcodefmt
        g_transcodefmt="m3u8"

        global g_quality
        g_quality = str(int(__settings__.getSetting('quality'))+3)
        printDebug( "Transcode format is " + g_transcodefmt)
        printDebug( "Transcode quality is " + g_quality)

        baseCapability="http-live-streaming,http-mp4-streaming,http-streaming-video,http-streaming-video-1080p,http-mp4-video,http-mp4-video-1080p;videoDecoders=h264{profile:high&resolution:1080&level:51};"

        g_audioOutput=__settings__.getSetting("audiotype")
        if g_audioOutput == "0":
            audio="mp3,aac{bitrate:160000}"
        elif g_audioOutput == "1":
            audio="ac3{channels:6}"
        elif g_audioOutput == "2":
            audio="dts{channels:6}"

        global capability
        capability="X-Plex-Client-Capabilities="+urllib.quote_plus("protocols="+baseCapability+"audioDecoders="+audio)
        printDebug("Plex Client Capability = " + capability)

        import uuid
        global g_sessionID
        g_sessionID=str(uuid.uuid4())

def deleteMedia( url ):
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    printDebug ("deleteing media at: " + url)

    return_value = xbmcgui.Dialog().yesno("Confirm file delete?","Delete this item? This action will delete media and associated data files.")

    if return_value:
        printDebug("Deleting....")
        installed = getURL(url,type="DELETE")
        xbmc.executebuiltin("Container.Refresh")

    return True

def getAuthTokenFromURL( url ):
    if "X-Plex-Token=" in url:
        return url.split('X-Plex-Token=')[1]
    else:
        return ""
        
def alterSubs ( url ):
    '''
        Display a list of available Subtitle streams and allow a user to select one.
        The currently selected stream will be annotated with a *
    '''
    printDebug("== ENTER ==", level=DEBUG_DEBUG)
    html=getURL(url)

    tree=etree.fromstring(html)

    sub_list=['']
    display_list=["None"]
    fl_select=False
    for parts in tree.getiterator('Part'):

        part_id=parts.get('id')

        for streams in parts:

            if streams.get('streamType','') == "3":

                stream_id=streams.get('id')
                lang=streams.get('languageCode',"Unknown").encode('utf-8')
                printDebug("Detected Subtitle stream [%s] [%s]" % ( stream_id, lang ) )

                if streams.get('format',streams.get('codec')) == "idx":
                    printDebug("Stream: %s - Ignoring idx file for now" % stream_id)
                    continue
                else:
                    sub_list.append(stream_id)

                    if streams.get('selected',None) == '1':
                        fl_select=True
                        language=streams.get('language','Unknown')+"*"
                    else:
                        language=streams.get('language','Unknown')

                    display_list.append(language)
        break

    if not fl_select:
        display_list[0]=display_list[0]+"*"

    subScreen = xbmcgui.Dialog()
    result = subScreen.select('Select subtitle',display_list)
    if result == -1:
        return False

    authtoken=getAuthTokenFromURL(url)
    sub_select_URL="http://%s/library/parts/%s?subtitleStreamID=%s" % ( getServerFromURL(url), part_id, sub_list[result] ) +getAuthDetails({'token':authtoken})

    printDebug("User has selected stream %s" % sub_list[result])
    printDebug("Setting via URL: %s" % sub_select_URL )
    outcome=getURL(sub_select_URL, type="PUT")

    printDebug( sub_select_URL )

    return True

def alterAudio ( url ):
    '''
        Display a list of available audio streams and allow a user to select one.
        The currently selected stream will be annotated with a *
    '''
    printDebug("== ENTER ==", level=DEBUG_DEBUG)

    html=getURL(url)
    tree=etree.fromstring(html)

    audio_list=[]
    display_list=[]
    for parts in tree.getiterator('Part'):

        part_id=parts.get('id')

        for streams in parts:

            if streams.get('streamType','') == "2":

                stream_id=streams.get('id')
                audio_list.append(stream_id)
                lang=streams.get('languageCode', "Unknown")

                printDebug("Detected Audio stream [%s] [%s] " % ( stream_id, lang))

                if streams.get('channels','Unknown') == '6':
                    channels="5.1"
                elif streams.get('channels','Unknown') == '7':
                    channels="6.1"
                elif streams.get('channels','Unknown') == '2':
                    channels="Stereo"
                else:
                    channels=streams.get('channels','Unknown')

                if streams.get('codec','Unknown') == "ac3":
                    codec="AC3"
                elif streams.get('codec','Unknown') == "dca":
                    codec="DTS"
                else:
                    codec=streams.get('codec','Unknown')

                language="%s (%s %s)" % ( streams.get('language','Unknown').encode('utf-8') , codec, channels )

                if streams.get('selected') == '1':
                    language=language+"*"

                display_list.append(language)
        break

    audioScreen = xbmcgui.Dialog()
    result = audioScreen.select('Select audio',display_list)
    if result == -1:
        return False

    authtoken=getAuthTokenFromURL(url)        
    audio_select_URL="http://%s/library/parts/%s?audioStreamID=%s" % ( getServerFromURL(url), part_id, audio_list[result] ) +getAuthDetails({'token':authtoken})
    printDebug("User has selected stream %s" % audio_list[result])
    printDebug("Setting via URL: %s" % audio_select_URL )

    outcome=getURL(audio_select_URL, type="PUT")

    return True

def setWindowHeading(tree) :
    WINDOW = xbmcgui.Window( xbmcgui.getCurrentWindowId() )
    try:
        WINDOW.setProperty("heading", tree.get('title1'))
    except:
        WINDOW.clearProperty("heading")
    try:
        WINDOW.setProperty("heading2", tree.get('title2'))
    except:
        WINDOW.clearProperty("heading2")

def setMasterServer () :
    printDebug("== ENTER ==", level=DEBUG_DEBUG)

    servers=getMasterServer(True)
    printDebug(str(servers))
    
    current_master=__settings__.getSetting('masterServer')
    
    displayList=[]
    for address in servers:
        found_server = address['name']
        if found_server == current_master:
            found_server = found_server+"*"
        displayList.append(found_server)
    
    audioScreen = xbmcgui.Dialog()
    result = audioScreen.select('Select master server',displayList)
    if result == -1:
        return False

    printDebug("Setting master server to: %s" % (servers[result]['name'],))
    __settings__.setSetting('masterServer',servers[result]['name'])
    return
  
##So this is where we really start the plugin.
printDebug( "PleXBMC -> Script argument is " + str(sys.argv))

try:
    params=get_params(sys.argv[2])
except:
    params={}

#Now try and assign some data to them
param_url=params.get('url',None)

if param_url and ( param_url.startswith('http') or param_url.startswith('file') ):
        param_url = urllib.unquote(param_url)

param_name=urllib.unquote_plus(params.get('name',""))
mode=int(params.get('mode',-1))
param_transcodeOverride=int(params.get('transcode',0))
param_identifier=params.get('identifier',None)
param_indirect=params.get('indirect',None)
_PARAM_TOKEN=params.get('X-Plex-Token',None)
force=params.get('force')

#Populate Skin variables
if str(sys.argv[1]) == "skin":
    try:
        type=sys.argv[2]
    except:
        type=None
    skin(type=type)

elif str(sys.argv[1]) == "amberskin":
    amberskin()
 
#Populate recently/on deck shelf items 
elif str(sys.argv[1]) == "shelf":
    shelf()

#Populate channel recently viewed items    
elif str(sys.argv[1]) == "channelShelf":
    shelfChannel()
    
#Send a library update to Plex    
elif sys.argv[1] == "update":
    url=sys.argv[2]
    libraryRefresh(url)
    
#Mark an item as watched/unwatched in plex    
elif sys.argv[1] == "watch":
    url=sys.argv[2]
    watched(url)
    
#Open the add-on settings page, then refresh plugin
elif sys.argv[1] == "setting":
    __settings__.openSettings()
    WINDOW = xbmcgui.getCurrentWindowId()
    if WINDOW == 10000:
        printDebug("Currently in home - refreshing to allow new settings to be taken")
        xbmc.executebuiltin("XBMC.ActivateWindow(Home)")
              
#nt currently used              
elif sys.argv[1] == "refreshplexbmc":
    server_list = discoverAllServers()
    skin(server_list)
    shelf(server_list)
    shelfChannel(server_list)

#delete media from PMS    
elif sys.argv[1] == "delete":
    url=sys.argv[2]
    deleteMedia(url)

#Refresh the current XBMC listing    
elif sys.argv[1] == "refresh":
    xbmc.executebuiltin("Container.Refresh")
    
#Display subtitle selection screen    
elif sys.argv[1] == "subs":
    url=sys.argv[2]
    alterSubs(url)
    
#Display audio streanm selection screen    
elif sys.argv[1] == "audio":
    url=sys.argv[2]
    alterAudio(url)
    
#Allow a mastre server to be selected (for myplex queue)    
elif sys.argv[1] == "master":
    setMasterServer()

#Delete cache and refresh it    
elif str(sys.argv[1]) == "cacherefresh":
    CACHE.deleteCache()
    xbmc.executebuiltin("ReloadSkin()")

#else move to the main code    
else:

    pluginhandle = int(sys.argv[1])

    WINDOW = xbmcgui.Window( xbmcgui.getCurrentWindowId() )
    WINDOW.clearProperty("heading")
    WINDOW.clearProperty("heading2")

    if settings.debug >= DEBUG_INFO:
        print "PleXBMC -> Mode: "+str(mode)
        print "PleXBMC -> URL: "+str(param_url)
        print "PleXBMC -> Name: "+str(param_name)
        print "PleXBMC -> identifier: " + str(param_identifier)
        print "PleXBMC -> token: " + str(_PARAM_TOKEN)

    #Run a function based on the mode variable that was passed in the URL
    if ( mode == None ) or ( param_url == None ) or ( len(param_url)<1 ):
        displaySections()

    elif mode == _MODE_GETCONTENT:
        getContent(param_url)

    elif mode == _MODE_TVSHOWS:
        TVShows(param_url)

    elif mode == _MODE_MOVIES:
        Movies(param_url)

    elif mode == _MODE_ARTISTS:
        artist(param_url)

    elif mode == _MODE_TVSEASONS:
        TVSeasons(param_url)

    elif mode == _MODE_PLAYLIBRARY:
        playLibraryMedia(param_url,force=force, override=param_transcodeOverride)

    elif mode == _MODE_PLAYSHELF:
        playLibraryMedia(param_url,full_data=True, shelf=True)

    elif mode == _MODE_TVEPISODES:
        TVEpisodes(param_url)

    elif mode == _MODE_PLEXPLUGINS:
        PlexPlugins(param_url)

    elif mode == _MODE_PROCESSXML:
        processXML(param_url)

    elif mode == _MODE_BASICPLAY:
        PLAY(param_url)

    elif mode == _MODE_ALBUMS:
        albums(param_url)

    elif mode == _MODE_TRACKS:
        tracks(param_url)

    elif mode == _MODE_PHOTOS:
        photo(param_url)

    elif mode == _MODE_MUSIC:
        music(param_url)

    elif mode == _MODE_VIDEOPLUGINPLAY:
        videoPluginPlay(param_url,param_identifier,param_indirect)

    elif mode == _MODE_PLEXONLINE:
        plexOnline(param_url)

    elif mode == _MODE_CHANNELINSTALL:
        install(param_url,param_name)

    elif mode == _MODE_CHANNELVIEW:
        channelView(param_url)

    elif mode == _MODE_DISPLAYSERVERS:
        displayServers(param_url)

    elif mode == _MODE_PLAYLIBRARY_TRANSCODE:
        playLibraryMedia(param_url,override=True)

    elif mode == _MODE_MYPLEXQUEUE:
        myPlexQueue()

    elif mode == _MODE_CHANNELSEARCH:
        channelSearch( param_url, params.get('prompt') )

    elif mode == _MODE_CHANNELPREFS:
        channelSettings ( param_url, params.get('id') )

    elif mode == _MODE_SHARED_MOVIES:
        displaySections(filter="movies", shared=True)

    elif mode == _MODE_SHARED_SHOWS:
        displaySections(filter="tvshows", shared=True)
        
    elif mode == _MODE_SHARED_PHOTOS:
        displaySections(filter="photos", shared=True)
        
    elif mode == _MODE_SHARED_MUSIC:
        displaySections(filter="music", shared=True)

    elif mode == _MODE_SHARED_ALL:
        displaySections(shared=True)
        
    elif mode == _MODE_DELETE_REFRESH:
        CACHE.deleteCache()
        xbmc.executebuiltin("Container.Refresh")

    elif mode == _MODE_PLAYLISTS:
        processXML(param_url)
        

        
print "===== PLEXBMC STOP ====="

#clear done and exit.
sys.modules.clear()

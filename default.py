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
import urllib2
import re
import xbmcplugin
import xbmcgui
import xbmcaddon
import httplib
import socket
import sys
import os
import datetime
import time
import inspect
import base64
import hashlib
import random

__settings__ = xbmcaddon.Addon(id='plugin.video.plexbmc')
__cwd__ = __settings__.getAddonInfo('path')
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
PLUGINPATH=xbmc.translatePath( os.path.join( __cwd__) )
sys.path.append(BASE_RESOURCE_PATH)
PLEXBMC_VERSION="3.1.0"

print "===== PLEXBMC START ====="

print "PleXBMC -> running Python: " + str(sys.version_info)
print "PleXBMC -> running PleXBMC: " + str(PLEXBMC_VERSION)

try:
  from lxml import etree
  print("PleXBMC -> Running with lxml.etree")
except ImportError:
  try:
    # Python 2.5
    import xml.etree.cElementTree as etree
    print("PleXBMC -> Running with cElementTree on Python 2.5+")
  except ImportError:
    try:
      # Python 2.5
      import xml.etree.ElementTree as etree
      print("PleXBMC -> Running with ElementTree on Python 2.5+")
    except ImportError:
      try:
        # normal cElementTree install
        import cElementTree as etree
        print("PleXBMC -> Running with built-in cElementTree")
      except ImportError:
        try:
          # normal ElementTree install
          import elementtree.ElementTree as etree
          print("PleXBMC -> Running with built-in ElementTree")
        except ImportError:
            try:
                import ElementTree as etree
                print("PleXBMC -> Running addon ElementTree version")
            except ImportError:
                print("PleXBMC -> Failed to import ElementTree from any known place")

#try:
#    import StorageServer
#except:
#    import storageserverdummy as StorageServer
#
#cache = StorageServer.StorageServer("plugins.video.plexbmc", 1)
    
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
_MODE_BASICPLAY=12
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

_OVERLAY_XBMC_UNWATCHED=6  #Blank
_OVERLAY_XBMC_WATCHED=7    #Tick
_OVERLAY_PLEX_UNWATCHED=4  #Dot
_OVERLAY_PLEX_WATCHED=0    #Blank
_OVERLAY_PLEX_PARTIAL=5    #half - Reusing XBMC overlaytrained

_SUB_AUDIO_XBMC_CONTROL="0"
_SUB_AUDIO_PLEX_CONTROL="1"
_SUB_AUDIO_EXTERNAL="2"
_SUB_AUDIO_NEVER_SHOW="3"

#Check debug first...
g_debug = __settings__.getSetting('debug')

def printDebug( msg, functionname=True ):
    if g_debug == "true":
        if functionname is False:
            print str(msg)
        else:
            print "PleXBMC -> " + inspect.stack()[1][3] + ": " + str(msg)

def getPlatform( ):

    if xbmc.getCondVisibility('system.platform.osx'):
        return "OSX"
    elif xbmc.getCondVisibility('system.platform.atv2'):
        return "ATV2"
    elif xbmc.getCondVisibility('system.platform.ios'):
        return "iOS"
    elif xbmc.getCondVisibility('system.platform.windows'):
        return "Windows"
    elif xbmc.getCondVisibility('system.platform.linux'):
        return "Linux/RPi"
    elif xbmc.getCondVisibility('system.platform.android'): 
        return "Linux/Android"

    return "Unknown"

PLEXBMC_PLATFORM=getPlatform()
print "PleXBMC -> Platform: " + str(PLEXBMC_PLATFORM)

#Next Check the WOL status - lets give the servers as much time as possible to come up
g_wolon = __settings__.getSetting('wolon')
if g_wolon == "true":
    from WOL import wake_on_lan
    printDebug("PleXBMC -> Wake On LAN: " + g_wolon, False)
    for i in range(1,12):
        wakeserver = __settings__.getSetting('wol'+str(i))
        if not wakeserver == "":
            try:
                printDebug ("PleXBMC -> Waking server " + str(i) + " with MAC: " + wakeserver, False)
                wake_on_lan(wakeserver)
            except ValueError:
                printDebug("PleXBMC -> Incorrect MAC address format for server " + str(i), False)
            except:
                printDebug("PleXBMC -> Unknown wake on lan error", False)

g_serverDict=[]
g_sections=[]

g_stream = __settings__.getSetting('streaming')
g_secondary = __settings__.getSetting('secondary')
g_streamControl = __settings__.getSetting('streamControl')
g_channelview = __settings__.getSetting('channelview')
g_flatten = __settings__.getSetting('flatten')
printDebug("PleXBMC -> Flatten is: "+ g_flatten, False)
g_forcedvd = __settings__.getSetting('forcedvd')

if g_debug == "true":
    print "PleXBMC -> Settings streaming: " + g_stream
    print "PleXBMC -> Setting filter menus: " + g_secondary
    print "PleXBMC -> Setting debug to " + g_debug
    if g_streamControl == _SUB_AUDIO_XBMC_CONTROL:
        print "PleXBMC -> Setting stream Control to : XBMC CONTROL (%s)" % g_streamControl
    elif g_streamControl == _SUB_AUDIO_PLEX_CONTROL:
        print "PleXBMC -> Setting stream Control to : PLEX CONTROL (%s)" % g_streamControl
    elif g_streamControl == _SUB_AUDIO_EXTERNAL:
        print "PleXBMC -> Setting stream Control to : EXTERNAL (%s)" % g_streamControl
    elif g_streamControl == _SUB_AUDIO_NEVER_SHOW:
        print "PleXBMC -> Setting stream Control to : NEVER SHOW (%s)" % g_streamControl

    print "PleXBMC -> Force DVD playback: " + g_forcedvd
else:
    print "PleXBMC -> Debug is turned off.  Running silent"

#NAS Override
g_nasoverride = __settings__.getSetting('nasoverride')
printDebug("PleXBMC -> SMB IP Override: " + g_nasoverride, False)
if g_nasoverride == "true":
    g_nasoverrideip = __settings__.getSetting('nasoverrideip')
    if g_nasoverrideip == "":
        printDebug("PleXBMC -> No NAS IP Specified.  Ignoring setting")
    else:
        printDebug("PleXBMC -> NAS IP: " + g_nasoverrideip, False)

    g_nasroot = __settings__.getSetting('nasroot')

#Get look and feel
if __settings__.getSetting("contextreplace") == "true":
    g_contextReplace=True
else:
    g_contextReplace=False

g_skipcontext = __settings__.getSetting("skipcontextmenus")
g_skipmetadata= __settings__.getSetting("skipmetadata")
g_skipmediaflags= __settings__.getSetting("skipflags")
g_skipimages= __settings__.getSetting("skipimages")

g_loc = "special://home/addons/plugin.video.plexbmc"

#Create the standard header structure and load with a User Agent to ensure we get back a response.
g_txheaders = {
              'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US;rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 ( .NET CLR 3.5.30729)',
              }

#Set up holding variable for session ID
global g_sessionID
g_sessionID=None
        
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
    printDebug("== ENTER: discoverAllServers ==", False)
    
    das_servers={}
    das_server_index=0
    
    g_discovery = __settings__.getSetting('discovery')

    #Set to Bonjour
    if g_discovery == "1":
        printDebug("PleXBMC -> local Bonjour discovery has been deprecated.", False)
    
    elif g_discovery == "2":
        printDebug("PleXBMC -> local GDM discovery setting enabled.", False)
        try:
            import plexgdm
            printDebug("Attempting GDM lookup on multicast")
            if g_debug == "true":
                GDM_debug=3
            else:
                GDM_debug=0

            gdm_client = plexgdm.plexgdm(GDM_debug)

            gdm_client.discover()
            gdm_server_name = gdm_client.getServerList()
                        
            if gdm_client.discovery_complete and gdm_server_name:
                printDebug("GDM discovery completed")
                for device in gdm_server_name:
                
                    das_servers[das_server_index] = device
                    das_server_index = das_server_index + 1
            else:
                printDebug("GDM was not able to discover any servers")

        except:
            print "PleXBMC -> GDM Issue."

    #Set to Disabled
    else:
        das_host = __settings__.getSetting('ipaddress')
        das_port =__settings__.getSetting('port')

        if not das_host or das_host == "<none>":
            das_host=None
        elif not das_port:
            printDebug( "PleXBMC -> No port defined.  Using default of " + DEFAULT_PORT, False)
            das_port=DEFAULT_PORT
       
        printDebug( "PleXBMC -> Settings hostname and port: %s : %s" % ( das_host, das_port), False)

        if das_host is not None:
            das_servers[das_server_index] = getLocalServers(das_host, das_port)
            das_server_index = das_server_index + 1
                                 
    if __settings__.getSetting('myplex_user') != "":
        printDebug( "PleXBMC -> Adding myplex as a server location", False)

        das_myplex = getMyPlexServers()
        if das_myplex:
            printDebug("MyPlex discovery completed")
            for device in das_myplex:
            
                das_servers[das_server_index] = device
                das_server_index = das_server_index + 1


    printDebug("PleXBMC -> serverList is " + str(das_servers), False)

    return deduplicateServers(das_servers)

def getLocalServers( ip_address, port ):
    '''
        Connect to the defined local server (either direct or via bonjour discovery)
        and get a list of all known servers.
        @input: nothing
        @return: a list of servers (as Dict)
    '''
    printDebug("== ENTER: getLocalServers ==", False)
    
    url_path="/"
    html = getURL(ip_address+":"+port+url_path)

    if html is False:
         return []

    server=etree.fromstring(html)

    return {'serverName': server.get('friendlyName','Unknown').encode('utf-8') ,
                        'server'    : ip_address,
                        'port'      : port ,
                        'discovery' : 'local' ,
                        'token'     : None ,
                        'uuid'      : server.get('machineIdentifier') ,
                        'owned'     : '1' ,
                        'master'    : 1 }

def getMyPlexServers( ):
    '''
        Connect to the myplex service and get a list of all known
        servers.
        @input: nothing
        @return: a list of servers (as Dict)
    '''

    printDebug("== ENTER: getMyPlexServers ==", False)

    tempServers=[]
    url_path="/pms/servers"

    html = getMyPlexURL(url_path)

    if html is False:
        return {}

    server=etree.fromstring(html).findall('Server')
    count=0
    for servers in server:
        data=dict(servers.items())

        if data.get('owned',None) == "1":
            if count == 0:
                master=1
                count=-1
            accessToken=getMyPlexToken()
        else:
            master='0'
            accessToken=data.get('accessToken',None)

        tempServers.append({'serverName': data['name'].encode('utf-8') ,
                            'server'    : data['address'] ,
                            'port'      : data['port'] ,
                            'discovery' : 'myplex' ,
                            'token'     : accessToken ,
                            'uuid'      : data['machineIdentifier'] ,
                            'owned'     : data.get('owned',0) ,
                            'master'    : master })

    return tempServers
                                       
def deduplicateServers( server_list ):
    '''
      Return list of all media sections configured
      within PleXBMC
      @input: None
      @Return: unique list of media servers
    '''
    printDebug("== ENTER: deduplicateServers ==", False)

    '''If we have more than one server source, then
       we need to ensure uniqueness amonst the
       seperate servers.

       If we have only one server source, then the assumption
       is that Plex will deal with this for us.
    '''

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
                if onedevice['discovery'] == "auto":
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

def getServerSections ( ip_address, port, name, uuid):
    printDebug("== ENTER: getServerSections ==", False)

    html=getURL('http://%s:%s/library/sections' % ( ip_address, port))

    if html is False:
        return {}

    tree = etree.fromstring(html).getiterator("Directory")
    temp_list=[]
    for sections in tree:

        temp_list.append( {'title'      : sections.get('title','Unknown').encode('utf-8'),
                'address'    : ip_address+":"+port ,
                'serverName' : name ,
                'uuid'       : uuid ,
                'path'       : '/library/sections/'+sections.get('key') ,
                'token'      : sections.get('accessToken',None) ,
                'location'   : "local" ,
                'art'        : sections.get('art') ,
                'local'      : '1' ,
                'type'       : sections.get('type','Unknown') })
                
    return temp_list            

def getMyplexSections ( ):
    printDebug("== ENTER: getMyplexSections ==", False)

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
                'path'       : sections.get('path') ,
                'token'      : sections.get('accessToken',None) ,
                'location'   : "myplex" ,
                'art'        : sections.get('art') ,
                'local'      : sections.get('local') ,
                'type'       : sections.get('type','Unknown') })
    
    return temp_list            

def getAllSections( server_list = None ):
    '''
        from server_list, get a list of all the available sections
        and deduplicate the sections list
        @input: None
        @return: None (alters the global value g_sectionList)
    '''
    printDebug("== ENTER: getAllSections ==", False)
    
    if not server_list:
        server_list = discoveryAllServers()
    
    printDebug("Using servers list: " + str(server_list))

    section_list=[]
    myplex_section_list=[]
    myplex_complete=False
    local_complete=False
    
    for server in server_list.itervalues():

        if server['discovery'] == "local" or server['discovery'] == "auto":
            section_details =  getServerSections( server['server'], server['port'] , server['serverName'], server['uuid']) 
            section_list += section_details
            local_complete=True
            
        elif server['discovery'] == "myplex":
            if not myplex_complete:
                section_details = getMyplexSections()
                myplex_section_list += section_details
                myplex_complete = True

    '''Remove any myplex sections that are locally available'''
    if myplex_complete and local_complete:
    
        printDebug ("Deduplicating myplex sections list")
    
        for each_server in server_list.values():
        
            printDebug ("Checking server [%s]" % each_server)
            
            if each_server['discovery'] == 'myplex':
                printDebug ("Skipping as a myplex server")
                continue
                    
            myplex_section_list = [x for x in myplex_section_list if not x['uuid'] == each_server['uuid']]
            
    section_list += myplex_section_list

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

def getMyPlexURL( url_path, renew=False, suppress=True ):
    '''
        Connect to the my.plexapp.com service and get an XML pages
        A seperate function is required as interfacing into myplex
        is slightly different than getting a standard URL
        @input: url to get, whether we need a new token, whether to display on screen err
        @return: an xml page as string or false
    '''
    printDebug("== ENTER: getMyPlexURL ==", False)
    printDebug("url = "+MYPLEX_SERVER+url_path)

    try:
        conn = httplib.HTTPSConnection(MYPLEX_SERVER)#, timeout=5)
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
            printDebug("====== XML returned =======")
            printDebug(link, False)
            printDebug("====== XML finished ======")
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

        return link

def getMyPlexToken( renew=False ):
    '''
        Get the myplex token.  If the user ID stored with the token
        does not match the current userid, then get new token.  This stops old token
        being used if plex ID is changed. If token is unavailable, then get a new one
        @input: whether to get new token
        @return: myplex token
    '''
    printDebug("== ENTER: getMyPlexToken ==", False)

    try:
        user,token=(__settings__.getSetting('myplex_token')).split('|')
    except:
        token=""

    if ( token == "" ) or (renew) or (user != __settings__.getSetting('myplex_user')):
        token = getNewMyPlexToken()

    printDebug("Using token: " + str(token) + "[Renew: " + str(renew) + "]")
    return token

def getNewMyPlexToken( suppress=True , title="Error" ):
    '''
        Get a new myplex token from myplex API
        @input: nothing
        @return: myplex token
    '''

    printDebug("== ENTER: getNewMyPlexToken ==", False)

    printDebug("Getting New token")
    myplex_username = __settings__.getSetting('myplex_user')
    myplex_password = __settings__.getSetting('myplex_pass')

    if ( myplex_username or myplex_password ) == "":
        printDebug("No myplex details in config..")
        return ""

    base64string = base64.encodestring('%s:%s' % (myplex_username, myplex_password)).replace('\n', '')
    txdata=""
    token=False

    myplex_headers={'X-Plex-Platform': "XBMC",
                    'X-Plex-Platform-Version': "12.00/Frodo",
                    'X-Plex-Provides': "player",
                    'X-Plex-Product': "PleXBMC",
                    'X-Plex-Version': PLEXBMC_VERSION,
                    'X-Plex-Device': PLEXBMC_PLATFORM,
                    'X-Plex-Client-Identifier': "PleXBMC",
                    'Authorization': "Basic %s" % base64string }

    try:
        conn = httplib.HTTPSConnection(MYPLEX_SERVER)
        conn.request("POST", "/users/sign_in.xml", txdata, myplex_headers)
        data = conn.getresponse()

        if int(data.status) == 201:
            link=data.read()
            printDebug("====== XML returned =======")

            try:
                token=etree.fromstring(link).findtext('authentication-token')
                __settings__.setSetting('myplex_token',myplex_username+"|"+token)
            except:
                printDebug(link)

            printDebug("====== XML finished ======")
        else:
            error = "HTTP response error: " + str(data.status) + " " + str(data.reason)
            if suppress is False:
                xbmcgui.Dialog().ok(title,error)
            print error
            return ""
    except socket.gaierror :
        error = 'Unable to lookup host: ' + server + "\nCheck host name is correct"
        if suppress is False:
            xbmcgui.Dialog().ok(title,error)
        print error
        return ""
    except socket.error, msg :
        error="Unable to connect to " + server +"\nReason: " + str(msg)
        if suppress is False:
            xbmcgui.Dialog().ok(title,error)
        print error
        return ""

    return token

def getURL( url, suppress=True, type="GET", popup=0 ):
    printDebug("== ENTER: getURL ==", False)
    try:
        if url[0:4] == "http":
            serversplit=2
            urlsplit=3
        else:
            serversplit=0
            urlsplit=1

        server=url.split('/')[serversplit]
        urlPath="/"+"/".join(url.split('/')[urlsplit:])

        authHeader=getAuthDetails({'token':_PARAM_TOKEN}, False)

        printDebug("url = "+url)
        printDebug("header = "+str(authHeader))
        conn = httplib.HTTPConnection(server)#,timeout=5)
        conn.request(type, urlPath, headers=authHeader)
        data = conn.getresponse()
        if int(data.status) == 200:
            link=data.read()
            printDebug("====== XML returned =======")
            printDebug(link, False)
            printDebug("====== XML finished ======")

        elif ( int(data.status) == 301 ) or ( int(data.status) == 302 ):
            try: conn.close()
            except: pass
            return data.getheader('Location')

        elif int(data.status) >= 400:
            error = "HTTP response error: " + str(data.status) + " " + str(data.reason)
            print error
            if suppress is False:
                if popup == 0:
                    xbmc.executebuiltin("XBMC.Notification(URL error: "+ str(data.reason) +",)")
                else:
                    xbmcgui.Dialog().ok("Error",server)
            print error
            try: conn.close()
            except: pass
            return False
        else:
            link=data.read()
            printDebug("====== XML returned =======")
            printDebug(link, False)
            printDebug("====== XML finished ======")
    except socket.gaierror :
        error = 'Unable to lookup host: ' + server + "\nCheck host name is correct"
        print error
        if suppress is False:
            if popup==0:
                xbmc.executebuiltin("XBMC.Notification(\"PleXBMC\": URL error: Unable to find server,)")
            else:
                xbmcgui.Dialog().ok("","Unable to contact host")
        print error
        return False
    except socket.error, msg :
        error="Unable to connect to " + server +"\nReason: " + str(msg)
        print error
        if suppress is False:
            if popup == 0:
                xbmc.executebuiltin("XBMC.Notification(\"PleXBMC\": URL error: Unable to connect to server,)")
            else:
                xbmcgui.Dialog().ok("","Unable to connect to host")
        print error
        return False
    else:
        try: conn.close()
        except: pass

        return link

def mediaType( partData, server, dvdplayback=False ):
    printDebug("== ENTER: mediaType ==", False)
    stream=partData['key']
    file=partData['file']

    global g_stream

    if ( file is None ) or ( g_stream == "1" ):
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
    if g_stream == "0":
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
            g_stream="2"
        else:
            return "http://"+server+stream


    # 2 is use SMB
    elif g_stream == "2" or g_stream == "3":
        if g_stream == "2":
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

            if g_nasoverride == "true":
                if not g_nasoverrideip == "":
                    server=g_nasoverrideip
                    printDebug("Overriding server with: " + server)

                nasuser=__settings__.getSetting('nasuserid')
                if not nasuser == "":
                    loginstring=__settings__.getSetting('nasuserid')+":"+__settings__.getSetting('naspass')+"@"
                    printDebug("Adding AFP/SMB login info for user " + nasuser)


            if file.find('Volumes') > 0:
                filelocation=protocol+":/"+file.replace("Volumes",loginstring+server)
            else:
                if type == "winfile":
                    filelocation=protocol+"://"+loginstring+server+"/"+file[3:]
                else:
                    #else assume its a file local to server available over smb/samba (now we have linux PMS).  Add server name to file path.
                    filelocation=protocol+"://"+loginstring+server+file

        if g_nasoverride == "true" and g_nasroot != "":
            #Re-root the file path
            printDebug("Altering path " + filelocation + " so root is: " +  g_nasroot)
            if '/'+g_nasroot+'/' in filelocation:
                components = filelocation.split('/')
                index = components.index(g_nasroot)
                for i in range(3,index):
                    components.pop(3)
                filelocation='/'.join(components)
    else:
        printDebug( "No option detected, streaming is safest to choose" )
        filelocation="http://"+server+stream

    printDebug("Returning URL: " + filelocation)
    return filelocation

def addGUIItem( url, details, extraData, context=None, folder=True ):
        printDebug("== ENTER: addGUIItem ==", False)
        printDebug("Adding Dir for [%s]" % details.get('title','Unknown'))
        printDebug("Passed details: " + str(details))
        printDebug("Passed extraData: " + str(extraData))

        if details.get('title','') == '':
            return

        if (extraData.get('token',None) is None) and _PARAM_TOKEN:
            extraData['token']=_PARAM_TOKEN

        aToken=getAuthDetails(extraData)
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
                u="%s&%s=%s" % ( u, argument, urllib.quote(value) )

        printDebug("URL to use for listing: " + u)

        #Create the ListItem that will be displayed
        thumb=str(extraData.get('thumb',''))
        if thumb.startswith('http'):
            if '?' in thumb:
                thumbPath=thumb+aToken
            else:
                thumbPath=thumb+qToken
        else:
            thumbPath=thumb

        liz=xbmcgui.ListItem(details.get('title','Unknown'), iconImage=thumbPath, thumbnailImage=thumbPath)

        printDebug("Setting thumbnail as " + thumbPath)

        #Set the properties of the item, such as summary, name, season, etc
        liz.setInfo( type=extraData.get('type','Video'), infoLabels=details )

        #Music related tags
        if extraData.get('type','').lower() == "music":
            liz.setProperty('Artist_Genre', details.get('genre',''))
            liz.setProperty('Artist_Description', extraData.get('plot',''))
            liz.setProperty('Album_Description', extraData.get('plot',''))

        #For all end items    
        if ( not folder):
            liz.setProperty('IsPlayable', 'true')

            if extraData.get('type','video').lower() == "video":
                liz.setProperty('TotalTime', str(extraData.get('duration')))
                liz.setProperty('ResumeTime', str(extraData.get('resume')))
            
                if g_skipmediaflags == "false":
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
                    if extraData.get('xbmc_width') : video_codec['width'] = int(extraData.get('xbmc_height'))
                    if extraData.get('duration') : video_codec['duration'] = int(extraData.get('duration'))

                    audio_codec={}
                    if extraData.get('xbmc_AudioCodec') : audio_codec['codec'] = extraData.get('xbmc_AudioCodec')
                    if extraData.get('xbmc_AudioChannels') : audio_codec['channels'] = int(extraData.get('xbmc_AudioChannels'))

                    liz.addStreamInfo('video', video_codec )
                    liz.addStreamInfo('audio', audio_codec )
                
        try:
            #Then set the number of watched and unwatched, which will be displayed per season
            liz.setProperty('WatchedEpisodes', str(extraData['WatchedEpisodes']))
            liz.setProperty('UnWatchedEpisodes', str(extraData['UnWatchedEpisodes']))
            
            #Hack to show partial flag for TV shows and seasons
            if extraData.get('partialTV') == 1:            
                liz.setProperty('TotalTime', '100')
                liz.setProperty('ResumeTime', '50')
                
        except: pass

        #Set the fanart image if it has been enabled
        fanart=str(extraData.get('fanart_image',''))
        if '?' in fanart:
            liz.setProperty('fanart_image', fanart+aToken)
        else:
            liz.setProperty('fanart_image', fanart+qToken)

        printDebug( "Setting fan art as " + fanart +" with headers: "+ aToken)

        if context is not None:
            printDebug("Building Context Menus")
            liz.addContextMenuItems( context, g_contextReplace )

        return xbmcplugin.addDirectoryItem(handle=pluginhandle,url=u,listitem=liz,isFolder=folder)

def displaySections( filter=None ):
        printDebug("== ENTER: displaySections() ==", False)
        xbmcplugin.setContent(pluginhandle, 'movies')

        ds_servers=discoverAllServers()
        numOfServers=len(ds_servers)
        printDebug( "Using list of "+str(numOfServers)+" servers: " +  str(ds_servers))
        
        for section in getAllSections(ds_servers):

            details={'title' : section.get('title', 'Unknown').encode('utf-8') }

            if len(ds_servers) > 1:
                details['title']=section.get('serverName')+": "+details['title']

            extraData={ 'fanart_image' : getFanart(section, section.get('address')) ,
                        'type'         : "Video" ,
                        'thumb'        : getFanart(section, section.get('address'), False) ,
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

            if g_secondary == "true":
                mode=_MODE_GETCONTENT
            else:
                path=path+'/all'

            extraData['mode']=mode
            s_url='http://%s%s' % ( section['address'], path)

            if g_skipcontext == "false":
                context=[]
                refreshURL="http://"+section.get('address')+section.get('path')+"/refresh"
                libraryRefresh = "XBMC.RunScript("+g_loc+"/default.py, update ," + refreshURL + ")"
                context.append(('Refresh library section', libraryRefresh , ))
            else:
                context=None

            #Build that listing..
            addGUIItem(s_url, details,extraData, context)

        #For each of the servers we have identified
        allservers=ds_servers
        numOfServers=len(allservers)

        if __settings__.getSetting('myplex_user') != '':
            addGUIItem('http://myplexqueue', {'title':'myplex Queue'},{'type':'Video' , 'mode' : _MODE_MYPLEXQUEUE})

        for server in allservers.itervalues():

            #Plex plugin handling
            if (filter is not None) and (filter != "plugins"):
                continue

            if numOfServers > 1:
                prefix=server['serverName']+": "
            else:
                prefix=""

            details={'title' : prefix+"Channels" }
            extraData={'type' : "Video",
                       'token' : server.get('token',None) }

            extraData['mode']=_MODE_CHANNELVIEW
            u="http://"+server['server']+":"+server['port']+"/system/plugins/all" 
            addGUIItem(u,details,extraData)

            #Create plexonline link
            details['title']=prefix+"Plex Online"
            extraData['type']="file"

            extraData['mode']=_MODE_PLEXONLINE

            u="http://"+server['server']+":"+server['port']+"/system/plexonline"
            addGUIItem(u,details,extraData)

        #All XML entries have been parsed and we are ready to allow the user to browse around.  So end the screen listing.
        xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

def enforceSkinView(mode):
    '''
        Ensure that the views are consistance across plugin usage, depending
        upon view selected by user
        @input: User view selection
        @return: view id for skin
    '''
    printDebug("== ENTER: enforceSkinView ==", False)

    if __settings__.getSetting('skinoverride') == "false":
        return None

    skinname = __settings__.getSetting('skinname')

    current_skin_name = xbmc.getSkinDir()

    skin_map = { '2' : 'skin.confluence' ,
                 '0' : 'skin.quartz' ,
                 '1' : 'skin.quartz3' }
    
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
                       'Wide Icons' : 505 }

    skin_list={"0" : Quartz_views ,
               "1" : QuartzV3_views,
               "2" : Confluence_views}

    printDebug("Using skin view: %s" % skin_list[skinname][viewname])

    try:
        return skin_list[skinname][viewname]
    except:
        print "PleXBMC -> skin name or view name error"
        return None

def Movies( url, tree=None ):
    printDebug("== ENTER: Movies() ==", False)
    xbmcplugin.setContent(pluginhandle, 'movies')

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
    plugin_url="XBMC.RunScript("+g_loc+"/default.py, "
    ID=itemData.get('ratingKey','0')

    #Initiate Library refresh
    libraryRefresh = plugin_url+"update, " + refreshURL.split('?')[0]+getAuthDetails(itemData,prefix="?") + ")"
    context.append(('Rescan library section', libraryRefresh , ))

    #Mark media unwatched
    unwatchURL="http://"+server+"/:/unscrobble?key="+ID+"&identifier=com.plexapp.plugins.library"+getAuthDetails(itemData)
    unwatched=plugin_url+"watch, " + unwatchURL + ")"
    context.append(('Mark as Unwatched', unwatched , ))

    #Mark media watched
    watchURL="http://"+server+"/:/scrobble?key="+ID+"&identifier=com.plexapp.plugins.library"+getAuthDetails(itemData)
    watched=plugin_url+"watch, " + watchURL + ")"
    context.append(('Mark as Watched', watched , ))

    #Delete media from Library
    deleteURL="http://"+server+"/library/metadata/"+ID+getAuthDetails(itemData,prefix="?")
    removed=plugin_url+"delete, " + deleteURL + ")"
    context.append(('Delete media', removed , ))

    #Display plugin setting menu
    settingDisplay=plugin_url+"setting)"
    context.append(('PleXBMC settings', settingDisplay , ))

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
    printDebug("== ENTER: TVShows() ==", False)
    xbmcplugin.setContent(pluginhandle, 'tvshows')

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
            tempgenre.append(child.get('tag',''))

        watched=int(show.get('viewedLeafCount',0))

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
                   'WatchedEpisodes'   : watched ,
                   'UnWatchedEpisodes' : details['episode'] - watched ,
                   'thumb'             : getThumb(show, server) ,
                   'fanart_image'      : getFanart(show, server) ,
                   'token'             : _PARAM_TOKEN ,
                   'key'               : show.get('key','') ,
                   'ratingKey'         : str(show.get('ratingKey',0)) }

        #banner art
        if show.get('banner',None) is not None:
            extraData['banner']='http://'+server+show.get('banner').split('?')[0]+"/banner.jpg"

        #Set up overlays for watched and unwatched episodes
        if extraData['WatchedEpisodes'] == 0:
            details['playcount'] = 0
        elif extraData['UnWatchedEpisodes'] == 0:
            details['playcount'] = 1
        else:
            extraData['partialTV'] = 1

        #Create URL based on whether we are going to flatten the season view
        if g_flatten == "2":
            printDebug("Flattening all shows")
            extraData['mode']=_MODE_TVEPISODES
            u='http://%s%s'  % ( server, extraData['key'].replace("children","allLeaves"))
        else:
            extraData['mode']=_MODE_TVSEASONS
            u='http://%s%s'  % ( server, extraData['key'])

        if g_skipcontext == "false":
            context=buildContextMenu(url, extraData)
        else:
            context=None

        addGUIItem(u,details,extraData, context)

    printDebug ("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('tv')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

def TVSeasons( url ):
    printDebug("== ENTER: season() ==", False)
    xbmcplugin.setContent(pluginhandle, 'seasons')

    #Get URL, XML and parse
    server=getServerFromURL(url)
    tree=getXML(url)
    if tree is None:
        return

    willFlatten=False
    if g_flatten == "1":
        #check for a single season
        if int(tree.get('size',0)) == 1:
            printDebug("Flattening single season show")
            willFlatten=True

    sectionart=getFanart(tree, server)
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

        if g_skipcontext == "false":
            context=buildContextMenu(url, season)
        else:
            context=None

        #Build the screen directory listing
        addGUIItem(url,details,extraData, context)

    printDebug ("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('season')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

def TVEpisodes( url, tree=None ):
    printDebug("== ENTER: TVEpisodes() ==", False)
    xbmcplugin.setContent(pluginhandle, 'episodes')

    tree=getXML(url,tree)
    if tree is None:
        return

    setWindowHeading(tree)
    ShowTags=tree.findall('Video')
    server=getServerFromURL(url)

    if g_skipimages == "false":
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
            elif child.tag == "Genre" and g_skipmetadata == "false":
                tempgenre.append(child.get('tag'))
            elif child.tag == "Writer"  and g_skipmetadata == "false":
                tempwriter.append(child.get('tag'))
            elif child.tag == "Director"  and g_skipmetadata == "false":
                tempdir.append(child.get('tag'))
            elif child.tag == "Role"  and g_skipmetadata == "false":
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

        if episode.get('sorttitle'): details['sorttitle'] = episode.get('sorttitle').encode('utf-8')

        if tree.get('mixedParents','0') == '1':
            details['title'] = "%s - %sx%s %s" % ( details['tvshowtitle'], details['season'], str(details['episode']).zfill(2), details['title'] )
        else:
            details['title'] = str(details['episode']).zfill(2) + ". " + details['title']


        #Extra data required to manage other properties
        extraData={'type'         : "Video" ,
                   'thumb'        : getThumb(episode, server) ,
                   'fanart_image' : getFanart(episode, server) ,
                   'token'        : _PARAM_TOKEN ,
                   'key'          : episode.get('key',''),
                   'ratingKey'    : str(episode.get('ratingKey',0)),
                   'duration'     : duration,
                   'resume'       : int(int(view_offset)/1000) }

        if extraData['fanart_image'] == "" and g_skipimages == "false":
            extraData['fanart_image']=sectionart

        #Determine what tupe of watched flag [overlay] to use
        if int(episode.get('viewCount',0)) > 0:
            details['playcount'] = 1
        else: 
            details['playcount'] = 0

        #Extended Metadata
        if g_skipmetadata == "false":
            details['cast']     = tempcast
            details['director'] = " / ".join(tempdir)
            details['writer']   = " / ".join(tempwriter)
            details['genre']    = " / ".join(tempgenre)

        #Add extra media flag data
        if g_skipmediaflags == "false":
            extraData.update(getMediaData(mediaarguments))

        #Build any specific context menu entries
        if g_skipcontext == "false":
            context=buildContextMenu(url, extraData)
        else:
            context=None

        extraData['mode']=_MODE_PLAYLIBRARY
        # http:// <server> <path> &mode=<mode> &t=<rnd>
        u="http://%s%s?t=%s" % (server, extraData['key'], randomNumber)

        addGUIItem(u,details,extraData, context, folder=False)

    printDebug ("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('episode')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

def getAudioSubtitlesMedia( server, id ):
    '''
        Cycle through the Parts sections to find all "selected" audio and subtitle streams
        If a stream is marked as selected=1 then we will record it in the dict
        Any that are not, are ignored as we do not need to set them
        We also record the media locations for playback decision later on
    '''
    printDebug("== ENTER: getAudioSubtitlesMedia ==", False)
    printDebug("Gather media stream info" )

    #get metadata for audio and subtitle
    suburl="http://"+server+"/library/metadata/"+id

    html=getURL(suburl)
    tree=etree.fromstring(html)

    parts=[]
    partsCount=0
    subtitle={}
    subCount=0
    audio={}
    audioCount=0
    external={}
    media={}
    subOffset=-1
    audioOffset=-1
    selectedSubOffset=-1
    selectedAudioOffset=-1

    timings = tree.find('Video')

    media['viewOffset']=timings.get('viewOffset',0)
    media['duration']=timings.get('duration',12*60*60)

    options = tree.getiterator('Part')

    contents="type"

    #Get the media locations (file and web) for later on
    for stuff in options:
        try:
            bits=stuff.get('key'), stuff.get('file')
            parts.append(bits)
            partsCount += 1
        except: pass

    #if we are deciding internally or forcing an external subs file, then collect the data
    if g_streamControl == _SUB_AUDIO_PLEX_CONTROL or g_streamControl == _SUB_AUDIO_EXTERNAL:

        contents="all"
        tags=tree.getiterator('Stream')

        for bits in tags:
            stream=dict(bits.items())
            if stream['streamType'] == '2':
                audioCount += 1
                audioOffset += 1
                try:
                    if stream['selected'] == "1":
                        printDebug("Found preferred audio id: " + str(stream['id']) )
                        audio=stream
                        selectedAudioOffset=audioOffset
                except: pass

            elif stream['streamType'] == '3':
                subOffset += 1
                try:
                    if stream['key']:
                        printDebug( "Found external subtitles id : " + str(stream['id']))
                        external=stream
                        external['key']='http://'+server+external['key']
                except:
                    #Otherwise it's probably embedded
                    try:
                        if stream['selected'] == "1":
                            printDebug( "Found preferred subtitles id : " + str(stream['id']))
                            subCount += 1
                            subtitle=stream
                            selectedSubOffset=subOffset
                    except: pass

    else:
            printDebug( "Stream selection is set OFF")

    streamData={'contents'   : contents ,                #What type of data we are holding
                'audio'      : audio ,                   #Audio data held in a dict
                'audioCount' : audioCount ,              #Number of audio streams
                'subtitle'   : subtitle ,                #Subtitle data (embedded) held as a dict
                'subCount'   : subCount ,                #Number of subtitle streams
                'external'   : external ,                #Subtitle data (external files) as a dict
                'parts'      : parts ,                   #The differet media locations
                'partsCount' : partsCount ,              #Number of media locations
                'media'      : media ,                   #Resume/duration data for media
                'subOffset'  : selectedSubOffset ,       #Stream index for selected subs
                'audioOffset': selectedAudioOffset }     #STream index for select audio

    printDebug ( str(streamData) )
    return streamData

def playLibraryMedia( vids, override=False, force=None ):
    printDebug("== ENTER: playLibraryMedia ==", False)

    getTranscodeSettings(override)

    server=getServerFromURL(vids)

    id=vids.split('?')[0].split('&')[0].split('/')[-1]

    streams=getAudioSubtitlesMedia(server,id)
    url=selectMedia(streams['partsCount'],streams['parts'], server)

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

    printDebug("Resume has been set to " + str(resume))

    item = xbmcgui.ListItem(path=playurl)

    if force:
        if int(force) > 0:
            resume=int(int(force)/1000)
        else:
            resume=force
        
        if resume:
            printDebug ("Playback from resume point")
            item.setProperty('ResumeTime', str(resume) )
            item.setProperty('TotalTime', str(duration) )

    if override:
        start=xbmc.Player().play(listitem=item)
    else:
        start = xbmcplugin.setResolvedUrl(pluginhandle, True, item)

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

    monitorPlayback(id,server)

    return

def setAudioSubtitles( stream ):
    '''
        Take the collected audio/sub stream data and apply to the media
        If we do not have any subs then we switch them off
    '''

    printDebug("== ENTER: setAudioSubtitles ==", False)

    #If we have decided not to collect any sub data then do not set subs
    if stream['contents'] == "type":
        printDebug ("No streams to process.")

        #If we have decided to force off all subs, then turn them off now and return
        if g_streamControl == _SUB_AUDIO_NEVER_SHOW :
            xbmc.Player().showSubtitles(False)
            printDebug ("All subs disabled")

        return True

    #Set the AUDIO component
    if ( g_streamControl == _SUB_AUDIO_PLEX_CONTROL ) or ( g_streamControl == _SUB_AUDIO_EXTERNAL ):
        printDebug("Attempting to set Audio Stream")

        if stream['audioCount'] == 1:
            printDebug ("Only one audio stream present - will leave as default")

        elif stream['audioCount'] > 1:
            audio=stream['audio']
            language=audio.get('language',audio.get('languageCode','Unknown')).encode('utf8')
            printDebug ("Attempting to use selected language setting: %s" % language)
            try:
                if audio['selected'] == "1":
                    printDebug ("Found preferred language at index " + str(stream['audioOffset']))
                    xbmc.Player().setAudioStream(stream['audioOffset'])
                    printDebug ("Audio set")
            except:
                    printDebug ("Error setting audio, will use embedded default stream")

    #Set the SUBTITLE component
    if g_streamControl == _SUB_AUDIO_PLEX_CONTROL:
        subtitle=stream['subtitle']
        printDebug("Attempting to set subtitle Stream", True)
        try:
            if stream['subCount'] > 0 and subtitle['languageCode']:
                printDebug ("Found embedded subtitle for local language" )
                printDebug ("Enabling embedded subtitles at index %s" % stream['subOffset'])
                xbmc.Player().showSubtitles(False)
                xbmc.Player().setSubtitleStream(stream['subOffset'])
                xbmc.Player().showSubtitles(True)
                return True
            else:
                printDebug ("No embedded subtitles to set")
        except:
            printDebug("Unable to set subtitles")

    #Set external subtitles if they exist and if embedded have not been set
    if ( g_streamControl == _SUB_AUDIO_PLEX_CONTROL ) or ( g_streamControl == _SUB_AUDIO_EXTERNAL ):
        external=stream['external']
        printDebug("Attempting to set external subtitle stream")

        try:
            if external:
                try:
                    printDebug ("External of type ["+external['codec']+"]")
                    if external['codec'] == "idx" or external['codec'] =="sub":
                        printDebug ("Skipping IDX/SUB pair - not supported yet")
                    else:
                        xbmc.Player().setSubtitles(external['key']+getAuthDetails({'token':_PARAM_TOKEN},prefix="?"))
                        return True
                except: pass
            else:
                printDebug ("No external subtitles available. Will turn off subs")
        except:
            printDebug ("No External subs to set")

    xbmc.Player().showSubtitles(False)
    return False

def selectMedia( count, options, server ):
    printDebug("== ENTER: selectMedia ==", False)
    #if we have two or more files for the same movie, then present a screen
    result=0
    dvdplayback=False

    if count > 1:

        dialogOptions=[]
        dvdIndex=[]
        indexCount=0
        for items in options:

            name=items[1].split('/')[-1]

            if g_forcedvd == "true":
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
        if g_forcedvd == "true":
            if '.ifo' in options[result]:
                dvdplayback=True

    newurl=mediaType({'key': options[result][0] , 'file' : options[result][1]},server,dvdplayback)

    printDebug("We have selected media at " + newurl)
    return newurl

def remove_html_tags( data ):
    p = re.compile(r'<.*?>')
    return p.sub('', data)

def monitorPlayback( id, server ):
    printDebug("== ENTER: monitorPlayback ==", False)

    if len(server.split(':')) == 1:
        server=server

    monitorCount=0
    progress = 0
    complete = 0
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
            getURL("http://"+server+"/:/progress?key="+id+"&identifier=com.plexapp.plugins.library&time="+str(currentTime*1000),suppress=True)
            complete=0

        #Otherwise, mark as watched
        else:
            if complete == 0:
                printDebug( "Movie marked as watched. Over 95% complete")
                getURL("http://"+server+"/:/scrobble?key="+id+"&identifier=com.plexapp.plugins.library",suppress=True)
                complete=1

        time.sleep(5)

    #If we get this far, playback has stopped
    printDebug("Playback Stopped")

    if g_sessionID is not None:
        printDebug("Stopping PMS transcode job with session " + g_sessionID)
        stopURL='http://'+server+'/video/:/transcode/segmented/stop?session='+g_sessionID
        html=getURL(stopURL)

    return

def PLAY( url ):
        printDebug("== ENTER: PLAY ==", False)

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

def videoPluginPlay( vids, prefix=None ):
    '''
        Plays Plugin Videos, which do not require library feedback
        but require further processing
        @input: url of video, plugin identifier
        @return: nothing. End of Script
    '''
    printDebug("== ENTER: videopluginplay with URL + " + vids + " ==", False)

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
    if '&indirect=1' in vids:
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
        session=vids

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
    printDebug("== ENTER: pluginTranscodeMonitor ==", False)

    #Logic may appear backward, but this does allow for a failed start to be detected
    #First while loop waiting for start

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
    printDebug("== ENTER: get_params ==", False)
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
    printDebug("== ENTER: channelsearch ==", False)

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
    printDebug("== ENTER: getContent ==", False)

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

    WINDOW = xbmcgui.Window( xbmcgui.getCurrentWindowId() )
    WINDOW.setProperty("heading", tree.get('title2',tree.get('title1','')))


    if lastbit == "folder":
        processXML(url,tree)
        return

    view_group=tree.get('viewGroup',None)

    if view_group == "movie":
        printDebug( "This is movie XML, passing to Movies")
        if not (lastbit.startswith('recently') or lastbit.startswith('newest')):
            xbmcplugin.addSortMethod(pluginhandle,xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
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
    elif view_group == "track":
        printDebug("This is track XML")
        tracks(url, tree)
    elif view_group =="photo":
        printDebug("This is a photo XML")
        photo(url,tree)
    else:
        processDirectory(url,tree)

    return

def processDirectory( url, tree=None ):
    printDebug("== ENTER: processDirectory ==", False)
    printDebug("Processing secondary menus")
    xbmcplugin.setContent(pluginhandle, 'movies')

    server=getServerFromURL(url)
    setWindowHeading(tree)
    for directory in tree:
        details={'title' : directory.get('title','Unknown').encode('utf-8') }
        extraData={'thumb'        : getThumb(directory, server) ,
                   'fanart_image' : getFanart(tree, server, False) }

        if extraData['thumb'] == '':
            extraData['thumb']=extraData['fanart_image']

        extraData['mode']=_MODE_GETCONTENT
        u='%s' % ( getLinkURL(url,directory,server))

        addGUIItem(u,details,extraData)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

def getMasterServer(all=False):
    printDebug("== ENTER: getmasterserver ==", False)

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
    printDebug("== ENTER: transcode ==", False)

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
    printDebug("== ENTER: artist ==", False)
    xbmcplugin.setContent(pluginhandle, 'artists')

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

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

def albums( url, tree=None ):
    printDebug("== ENTER: albums ==", False)
    xbmcplugin.setContent(pluginhandle, 'albums')

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

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

def tracks( url,tree=None ):
    printDebug("== ENTER: tracks ==", False)
    xbmcplugin.setContent(pluginhandle, 'songs')

    tree=getXML(url,tree)
    if tree is None:
        return

    server=getServerFromURL(url)
    sectionart=getFanart(tree,server)
    setWindowHeading(tree)
    TrackTags=tree.findall('Track')
    for track in TrackTags:

        trackTag(server, tree, track)

    printDebug ("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('music')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

def getXML (url, tree=None):
    printDebug("== ENTER: getXML ==", False)

    if tree is None:

        html=getURL(url)

        if html is False:
            return None

        tree=etree.fromstring(html)

    if tree.get('message'):
        xbmcgui.Dialog().ok(tree.get('header','Message'),tree.get('message',''))
        return None

    setWindowHeading(tree)

    return tree

def PlexPlugins( url, tree=None ):
    '''
        Main function to parse plugin XML from PMS
        Will create dir or item links depending on what the
        main tag is.
        @input: plugin page URL
        @return: nothing, creates XBMC GUI listing
    '''
    printDebug("== ENTER: PlexPlugins ==", False)
    xbmcplugin.setContent(pluginhandle, 'movies')

    tree=getXML(url,tree)
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


    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

def channelSettings ( url, settingID ):
    '''
        Take the setting XML and parse it to create an updated
        string with the new settings.  For the selected value, create
        a user input screen (text or list) to update the setting.
        @ input: url
        @ return: nothing
    '''
    printDebug("== ENTER: channelSettings ==", False)
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
    printDebug("== ENTER: processXML ==", False)
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

        elif tree.get('viewGroup') == "movie":
            Movies(url, tree)
            return

        elif tree.get('viewGroup') == "episode":
            TVEpisodes(url, tree)
            return

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

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
        elif child.tag == "Genre" and g_skipmetadata == "false":
            tempgenre.append(child.get('tag'))
        elif child.tag == "Writer"  and g_skipmetadata == "false":
            tempwriter.append(child.get('tag'))
        elif child.tag == "Director"  and g_skipmetadata == "false":
            tempdir.append(child.get('tag'))
        elif child.tag == "Role"  and g_skipmetadata == "false":
            tempcast.append(child.get('tag'))

    printDebug("Media attributes are " + str(mediaarguments))

    #Gather some data
    view_offset=movie.get('viewOffset',0)
    duration=int(mediaarguments.get('duration',movie.get('duration',0)))/1000

    #Required listItem entries for XBMC
    details={'plot'      : movie.get('summary','').encode('utf-8') ,
             'title'     : movie.get('title','Unknown').encode('utf-8') ,
             'sorttitle'  : movie.get('titleSort', movie.get('title','Unknown')).encode('utf-8') ,
             'rating'    : float(movie.get('rating',0)) ,
             'studio'    : movie.get('studio','').encode('utf-8') ,
             'mpaa'      : "Rated " + movie.get('contentRating', 'unknown') ,
             'year'      : int(movie.get('year',0)) ,
             'tagline'   : movie.get('tagline','') } 

    #Extra data required to manage other properties
    extraData={'type'         : "Video" ,
               'thumb'        : getThumb(movie, server) ,
               'fanart_image' : getFanart(movie, server) ,
               'token'        : _PARAM_TOKEN ,
               'key'          : movie.get('key',''),
               'ratingKey'    : str(movie.get('ratingKey',0)),
               'duration'     : duration,
               'resume'       : int (int(view_offset)/1000) }

    #Determine what tupe of watched flag [overlay] to use
    if int(movie.get('viewCount',0)) > 0:
        details['playcount'] = 1
    elif int(movie.get('viewCount',0)) == 0:
        details['playcount'] = 0

    #Extended Metadata
    if g_skipmetadata == "false":
        details['cast']     = tempcast
        details['director'] = " / ".join(tempdir)
        details['writer']   = " / ".join(tempwriter)
        details['genre']    = " / ".join(tempgenre)

    #Add extra media flag data
    if g_skipmediaflags == "false":
        extraData.update(getMediaData(mediaarguments))

    #Build any specific context menu entries
    if g_skipcontext == "false":
        context=buildContextMenu(url, extraData)
    else:
        context=None
    # http:// <server> <path> &mode=<mode> &t=<rnd>
    extraData['mode']=_MODE_PLAYLIBRARY
    u="http://%s%s?t=%s" % (server, extraData['key'], randomNumber)

    addGUIItem(u,details,extraData,context,folder=False)
    return

def getMediaData ( tag_dict ):
    '''
        Extra the media details from the XML
        @input: dict of <media /> tag attributes
        @output: dict of required values
    '''
    printDebug("== ENTER: getMediaData ==", False)

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

def trackTag( server, tree, track ):
    printDebug("== ENTER: trackTAG ==", False)
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
             'duration'    : int(track.get('duration',0))/1000 }

    extraData={'type'         : "Music" ,
               'fanart_image' : getFanart(track, server) ,
               'thumb'        : getThumb(track, server) ,
               'ratingKey'    : track.get('key','') }

    if '/resources/plex.png' in extraData['thumb']:
        printDebug("thumb is default")
        extraData['thumb']=getThumb(tree, server)

    if extraData['fanart_image'] == "":
        extraData['fanart_image']=getFanart(tree, server)

    #If we are streaming, then get the virtual location
    url=mediaType(partDetails,server)

    extraData['mode']=_MODE_BASICPLAY
    u="%s" % (url)

    addGUIItem(u,details,extraData,folder=False)

def photo( url,tree=None ):
    printDebug("== ENTER: photos ==", False)
    server=url.split('/')[2]

    xbmcplugin.setContent(pluginhandle, 'photo')

    tree=getXML(url,tree)
    if tree is None:
        return

    sectionArt=getFanart(tree,server)
    setWindowHeading(tree)
    for picture in tree:

        details={'title' : picture.get('title',picture.get('name','Unknown')).encode('utf-8') }

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

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

def music( url, tree=None ):
    printDebug("== ENTER: music ==", False)
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

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

def getThumb( data, server, transcode=False, width=None, height=None ):
    '''
        Simply take a URL or path and determine how to format for images
        @ input: elementTree element, server name
        @ return formatted URL
    '''
    
    if g_skipimages == "true":
        return ''
        
    thumbnail=data.get('thumb','').split('?t')[0].encode('utf-8')


    if thumbnail == '':
        return g_loc+'/resources/plex.png'

    elif thumbnail[0:4] == "http" :
        return thumbnail

    elif thumbnail[0] == '/':
        if transcode:
            return photoTranscode(server,'http://localhost:32400'+thumbnail,width,height)
        else:
            return 'http://'+server+thumbnail

    else:
        return g_loc+'/resources/plex.png'

def getFanart( data, server, transcode=True ):
    '''
        Simply take a URL or path and determine how to format for fanart
        @ input: elementTree element, server name
        @ return formatted URL for photo resizing
    '''
    if g_skipimages == "true":
        return ''

    fanart=data.get('art','').encode('utf-8')

    if fanart == '':
        return ''

    elif fanart[0:4] == "http" :
        return fanart

    elif fanart[0] == '/':
        if transcode:
            return photoTranscode(server,'http://localhost:32400'+fanart,1280,720)
        else:
            return 'http://%s%s' % (server, fanart)

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

def getLinkURL( url, pathData, server ):
    '''
        Investigate the passed URL and determine what is required to
        turn it into a usable URL
        @ input: url, XML data and PM server address
        @ return: Usable http URL
    '''
    printDebug("== ENTER: getLinkURL ==")
    path=pathData.get('key','')
    printDebug("Path is " + path)

    if path == '':
        printDebug("Empty Path")
        return

    #If key starts with http, then return it
    if path[0:4] == "http":
        printDebug("Detected http link")
        return path

    #If key starts with a / then prefix with server address
    elif path[0] == '/':
        printDebug("Detected base path link")
        return 'http://%s%s' % ( server, path )

    #If key starts with plex:// then it requires transcoding
    elif path[0:5] == "plex:":
        printDebug("Detected plex link")
        components=path.split('&')
        for i in components:
            if 'prefix=' in i:
                del components[components.index(i)]
                break
        if pathData.get('identifier',None):
            components.append('identifier='+pathData['identifier'])

        path='&'.join(components)
        return 'plex://'+server+'/'+'/'.join(path.split('/')[3:])
    elif path[0:5] == "rtmp:":
        printDebug("Detected plex link")
        return path

    #Any thing else is assumed to be a relative path and is built on existing url
    else:
        printDebug("Detected relative link")
        return "%s/%s" % ( url, path )

    return url

def plexOnline( url ):
    printDebug("== ENTER: plexOnline ==")
    xbmcplugin.setContent(pluginhandle, 'files')

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

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

def install( url, name ):
    printDebug("== ENTER: install ==", False)
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
    printDebug("== ENTER: channelView ==", False)
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

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

def photoTranscode( server, url, width=1280, height=720 ):
        return 'http://%s/photo/:/transcode?url=%s&width=%s&height=%s' % (server, urllib.quote_plus(url), width, height)

def skin( ):
    #Gather some data and set the window properties
    printDebug("== ENTER: skin() ==", False)
    #Get the global host variable set in settings
    WINDOW = xbmcgui.Window( 10000 )

    sectionCount=0
    serverCount=0

    server_list = discoverAllServers()
    
    #For each of the servers we have identified
    for section in getAllSections(server_list):

        extraData={ 'fanart_image' : getFanart(section, section['address']) ,
                    'thumb'        : getFanart(section, section['address'], False) }

        #Determine what we are going to do process after a link is selected by the user, based on the content we find

        path=section['path']

        if section['type'] == 'show':
            window="VideoLibrary"
            mode=_MODE_TVSHOWS
        if  section['type'] == 'movie':
            window="VideoLibrary"
            mode=_MODE_MOVIES
        if  section['type'] == 'artist':
            window="MusicFiles"
            mode=_MODE_ARTISTS
        if  section['type'] == 'photo':
            window="Pictures"
            mode=_MODE_PHOTOS

        aToken=getAuthDetails(section)
        qToken=getAuthDetails(section, prefix='?')

        if g_secondary == "true":
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

        printDebug("Building window properties index [" + str(sectionCount) + "] which is [" + section['title'] + "]")
        printDebug("PATH in use is: ActivateWindow("+window+",plugin://plugin.video.plexbmc/?url="+s_url+",return)")
        sectionCount += 1

    #For each of the servers we have identified
    numOfServers=len(server_list)

    for server in server_list.values():
    
        aToken=getAuthDetails(server)
        qToken=getAuthDetails(server, prefix='?')
        
        if g_channelview == "true":
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
            WINDOW.clearProperty("plexbmc.%d.title"    % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.subtitle" % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.url"      % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.path"     % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.window"   % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.art"      % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.type"     % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.icon"     % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.thumb"    % ( i ) )
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

def shelf( ):
    #Gather some data and set the window properties
    printDebug("== ENTER: shelf() ==", False)
    #Get the global host variable set in settings
    WINDOW = xbmcgui.Window( 10000 )

    movieCount=1
    seasonCount=1
    musicCount=1
    server_list=discoverAllServers()

    if not server_list:
        xbmc.executebuiltin("XBMC.Notification(Unable to see any media servers,)")
        clearShelf(0,0,0)
        return

    for server_details in server_list.values():

        if not server_details['owned'] == '1':
            continue
    
        _PARAM_TOKEN = server_details.get('token','')
        
        tree=getXML('http://'+server_details['server']+":"+server_details['port']+'/library/recentlyAdded')
        if tree is None:
            xbmc.executebuiltin("XBMC.Notification(Unable to contact server: "+server_details['serverName']+",)")
            clearShelf()
            return

        aToken=getAuthDetails({'token': _PARAM_TOKEN} )
        qToken=getAuthDetails({'token': _PARAM_TOKEN}, prefix='?')

        library_filter = __settings__.getSetting('libraryfilter')
        acceptable_level = __settings__.getSetting('contentFilter')

        #For each of the servers we have identified
        for media in tree:

            if media.get('type',None) == "movie":

                printDebug("Found a recent movie entry: [%s]" % ( media.get('title','Unknown').encode('UTF-8') , ))

                if __settings__.getSetting('movieShelf') == "false":
                    WINDOW.clearProperty("Plexbmc.LatestMovie.1.Path" )
                    continue

                if not displayContent( acceptable_level , media.get('contentRating') ):
                    continue

                if media.get('librarySectionID') == library_filter:
                    printDebug("SKIPPING: Library Filter match: %s = %s " % (library_filter, media.get('librarySectionID')))
                    continue

                m_url="plugin://plugin.video.plexbmc?url=%s&mode=%s%s" % ( getLinkURL('http://'+server_details['server']+":"+server_details['port'],media,server_details['server']+":"+server_details['port']), _MODE_PLAYLIBRARY, aToken)
                m_thumb=getThumb(media,server_details['server']+":"+server_details['port'])

                WINDOW.setProperty("Plexbmc.LatestMovie.%s.Path" % movieCount, m_url)
                WINDOW.setProperty("Plexbmc.LatestMovie.%s.Title" % movieCount, media.get('title','Unknown').encode('UTF-8'))
                WINDOW.setProperty("Plexbmc.LatestMovie.%s.Thumb" % movieCount, m_thumb+qToken)

                movieCount += 1

                printDebug("Building Recent window title: %s" % media.get('title','Unknown').encode('UTF-8'))
                printDebug("Building Recent window url: %s" % m_url)
                printDebug("Building Recent window thumb: %s" % m_thumb)

            elif media.get('type',None) == "season":

                printDebug("Found a recent season entry [%s]" % ( media.get('parentTitle','Unknown').encode('UTF-8') , ))

                if __settings__.getSetting('tvShelf') == "false":
                    WINDOW.clearProperty("Plexbmc.LatestEpisode.1.Path" )
                    continue

                s_url="ActivateWindow(VideoLibrary, plugin://plugin.video.plexbmc?url=%s&mode=%s%s, return)" % ( getLinkURL('http://'+server_details['server']+":"+server_details['port'],media,server_details['server']+":"+server_details['port']), _MODE_TVEPISODES, aToken)
                s_thumb=getThumb(media,server_details['server']+":"+server_details['port'])

                WINDOW.setProperty("Plexbmc.LatestEpisode.%s.Path" % seasonCount, s_url )
                WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeTitle" % seasonCount, '')
                WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeSeason" % seasonCount, media.get('title','').encode('UTF-8'))
                WINDOW.setProperty("Plexbmc.LatestEpisode.%s.ShowTitle" % seasonCount, media.get('parentTitle','Unknown').encode('UTF-8'))
                WINDOW.setProperty("Plexbmc.LatestEpisode.%s.Thumb" % seasonCount, s_thumb+qToken)
                seasonCount += 1

                printDebug("Building Recent window title: %s" % media.get('parentTitle','Unknown').encode('UTF-8'))
                printDebug("Building Recent window url: %s" % s_url)
                printDebug("Building Recent window thumb: %s" % s_thumb)

            elif media.get('type') == "album":

                if __settings__.getSetting('musicShelf') == "false":
                    WINDOW.clearProperty("Plexbmc.LatestAlbum.1.Path" )
                    continue
                printDebug("Found a recent album entry")

                s_url="ActivateWindow(MusicFiles, plugin://plugin.video.plexbmc?url=%s&mode=%s%s, return)" % ( getLinkURL('http://'+server_details['server']+":"+server_details['port'],media,server_details['server']+":"+server_details['port']), _MODE_TRACKS, aToken)
                s_thumb=getThumb(media,server_details['server']+":"+server_details['port'])

                WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Path" % musicCount, s_url )
                WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Title" % musicCount, media.get('title','Unknown').encode('UTF-8'))
                WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Artist" % musicCount, media.get('parentTitle','Unknown').encode('UTF-8'))
                WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Thumb" % musicCount, s_thumb+qToken)
                musicCount += 1

                printDebug("Building Recent window title: %s" % media.get('parentTitle','Unknown').encode('UTF-8'))
                printDebug("Building Recent window url: %s" % s_url)
                printDebug("Building Recent window thumb: %s" % s_thumb)
            
    clearShelf( movieCount, seasonCount, musicCount)

def clearShelf (movieCount=0, seasonCount=0, musicCount=0):
    #Clear out old data
    WINDOW = xbmcgui.Window( 10000 )
    printDebug("Clearing unused properties")

    try:
        for i in range(movieCount, 10+1):
            WINDOW.clearProperty("Plexbmc.LatestMovie.%s.Path"   % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestMovie.%s.Title"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestMovie.%s.Thumb"  % ( i ) )
        printDebug("Done clearing movies")
    except: pass

    try:
        for i in range(seasonCount, 10+1):
            WINDOW.clearProperty("Plexbmc.LatestEpisode.%s.Path"           % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestEpisode.%s.EpisodeTitle"   % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestEpisode.%s.EpisodeSeason"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestEpisode.%s.ShowTitle"      % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestEpisode.%s.Thumb"          % ( i ) )
        printDebug("Done clearing tv")
    except: pass

    try:
        for i in range(musicCount, 10+1):
            WINDOW.clearProperty("Plexbmc.LatestAlbum.%s.Path"   % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestAlbum.%s.Title"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestAlbum.%s.Artist" % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestAlbum.%s.Thumb"  % ( i ) )
        printDebug("Done clearing music")
    except: pass


    return

def shelfChannel( ):
    #Gather some data and set the window properties
    printDebug("== ENTER: shelfChannels() ==", False)
    #Get the global host variable set in settings
    WINDOW = xbmcgui.Window( 10000 )

    channelCount=1
    server_list=discoverAllServers()
    
    if server_list is None:
        xbmc.executebuiltin("XBMC.Notification(Unable to any media servers,)")
        clearChannelShelf()
        return
    
    for server_details in server_list.values():

        if not server_details['owned'] == '1':
            continue
        
        global _PARAM_TOKEN
        _PARAM_TOKEN = server_details.get('token','')

        if __settings__.getSetting('channelShelf') == "false":
            WINDOW.clearProperty("Plexbmc.LatestChannel.1.Path" )
            return

        tree=getXML('http://'+server_details['server']+":"+server_details['port']+'/channels/recentlyViewed')
        if tree is None:
            xbmc.executebuiltin("XBMC.Notification(Unable to contact server: "+server_details['serverName']+",)")
            clearChannelShelf(0)
            return

        aToken=getAuthDetails({'token': _PARAM_TOKEN} )
        qToken=getAuthDetails({'token': _PARAM_TOKEN}, prefix='?')

        #For each of the servers we have identified
        for media in tree:

            if media.get('type') == "channel":

                printDebug("Found a recent channel entry")

                suffix=media.get('key').split('/')[1]

                if suffix == "photos":
                    mode=_MODE_PHOTOS
                    channel_window="Pictures"
                elif suffix == "video":
                    mode=_MODE_PLEXPLUGINS
                    channel_window="VideoLibrary"
                elif suffix == "music":
                    mode=_MODE_MUSIC
                    channel_window="MusicFiles"
                else:
                    mode=_MODE_GETCONTENT
                    channel_window="VideoLibrary"


                p_url="ActivateWindow(%s, plugin://plugin.video.plexbmc?url=%s&mode=%s%s, return)" % ( channel_window, getLinkURL('http://'+server_details['server']+":"+server_details['port'],media,server_details['server']+":"+server_details['port']), mode , aToken)
                p_thumb=getThumb(media,server_details['server']+":"+server_details['port'])

                WINDOW.setProperty("Plexbmc.LatestChannel.%s.Path" % channelCount, p_url)
                WINDOW.setProperty("Plexbmc.LatestChannel.%s.Title" % channelCount, media.get('title','Unknown'))
                WINDOW.setProperty("Plexbmc.LatestChannel.%s.Thumb" % channelCount, p_thumb+qToken)

                channelCount += 1

                printDebug("Building Recent window title: %s" % media.get('title','Unknown'))
                printDebug("Building Recent window url: %s" % p_url)
                printDebug("Building Recent window thumb: %s" % p_thumb)

    clearChannelShelf(channelCount)        
    return
    
def clearChannelShelf (channelCount=0):
            
    WINDOW = xbmcgui.Window( 10000 )
        
    try:
        for i in range(channelCount, 10+1):
            WINDOW.clearProperty("Plexbmc.LatestChannel.%s.Path"   % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestChannel.%s.Title"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestChannel.%s.Thumb"  % ( i ) )
        printDebug("Done clearing channels")
    except: pass

    return

def myPlexQueue():
    printDebug("== ENTER: myplexqueue ==", False)

    if __settings__.getSetting('myplex_user') == '':
        xbmc.executebuiltin("XBMC.Notification(myplex not configured,)")
        return

    html=getMyPlexURL('/pms/playlists/queue/all')
    tree=etree.fromstring(html)

    PlexPlugins('http://my.plexapp.com/playlists/queue/all', tree)
    return

def libraryRefresh( url ):
    printDebug("== ENTER: libraryRefresh ==", False)
    html=getURL(url)
    printDebug ("Library refresh requested")
    xbmc.executebuiltin("XBMC.Notification(\"PleXBMC\",Library Refresh started,100)")
    return

def watched( url ):
    printDebug("== ENTER: watched ==", False)

    if url.find("unscrobble") > 0:
        printDebug ("Marking as unwatched with: " + url)
    else:
        printDebug ("Marking as watched with: " + url)

    html=getURL(url)
    xbmc.executebuiltin("Container.Refresh")

    return

def displayServers( url ):
    printDebug("== ENTER: displayServers ==", False)
    type=url.split('/')[2]
    printDebug("Displaying entries for " + type)
    Servers = discoverAllServers()
    Servers_list=len(Servers)

    #For each of the servers we have identified
    for mediaserver in Servers.values():

        details={'title' : mediaserver.get('serverName','Unknown') }

        if mediaserver.get('token',None):
            extraData={'token' : mediaserver.get('token') }
        else:
            extraData={}

        if type == "video":
            extraData['mode']=_MODE_PLEXPLUGINS
            s_url='http://%s:%s/video' % ( mediaserver.get('server',''), mediaserver.get('port') )
            if Servers_list == 1:
                PlexPlugins(s_url)
                return

        elif type == "online":
            extraData['mode']=_MODE_PLEXONLINE
            s_url='http://%s:%s/system/plexonline' % ( mediaserver.get('server', ''),mediaserver.get('port') )
            if Servers_list == 1:
                plexOnline(s_url)
                return

        elif type == "music":
            extraData['mode']=_MODE_MUSIC
            s_url='http://%s:%s/music' % ( mediaserver.get('server', ''),mediaserver.get('port') )
            if Servers_list == 1:
                music(s_url)
                return

        elif type == "photo":
            extraData['mode']=_MODE_PHOTOS
            s_url='http://%s:%s/photos' % ( mediaserver.get('server', ''),mediaserver.get('port') )
            if Servers_list == 1:
                photo(s_url)
                return

        addGUIItem(s_url, details, extraData )

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=False)

def getTranscodeSettings( override=False ):
    printDebug("== ENTER: gettranscodesettings ==", False)

    global g_transcode
    g_transcode = __settings__.getSetting('transcode')

    if override is True:
            printDebug( "Transcode override.  Will play media with addon transcoding settings")
            g_transcode="true"

    if g_transcode == "true":
        #If transcode is set, ignore the stream setting for file and smb:
        global g_stream
        g_stream = "1"
        printDebug( "We are set to Transcode, overriding stream selection")
        global g_transcodefmt
        g_transcodefmt="m3u8"

        global g_quality
        g_quality = str(int(__settings__.getSetting('quality'))+3)
        printDebug( "Transcode format is " + g_transcodefmt)
        printDebug( "Transcode quality is " + g_quality)

        baseCapability="http-live-streaming,http-mp4-streaming,http-streaming-video,http-mp4-video"

        g_audioOutput=__settings__.getSetting("audiotype")
        if g_audioOutput == "0":
            audio="mp3,aac{bitrate:160000}"
        elif g_audioOutput == "1":
            audio="ac3{channels:6}"
        elif g_audioOutput == "2":
            audio="dts{channels:6}"

        global capability
        capability="X-Plex-Client-Capabilities="+urllib.quote_plus("protocols="+baseCapability+";videoDecoders=h264{profile:high&resolution:1080&level:51};audioDecoders="+audio)
        printDebug("Plex Client Capability = " + capability)

        import uuid
        global g_sessionID
        g_sessionID=str(uuid.uuid4())

def deleteMedia( url ):
    printDebug("== ENTER: deleteMedia ==", False)
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
    printDebug("== ENTER: alterSubs ==", False)
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
    printDebug("== ENTER: alterAudio ==", False)

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
    WINDOW.setProperty("heading", tree.get('title2',tree.get('title1','')))

def setMasterServer () :
    printDebug("== ENTER: setmasterserver ==", False)

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
printDebug( "PleXBMC -> Script argument is " + str(sys.argv[1]), False)

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
_PARAM_TOKEN=params.get('X-Plex-Token',None)
force=params.get('force')

if str(sys.argv[1]) == "skin":
    skin()
elif str(sys.argv[1]) == "shelf":
    if __settings__.getSetting('movieShelf') == "false" and __settings__.getSetting('tvShelf') == "false" and __settings__.getSetting('musicShelf') == "false":
        printDebug("Disabling all shelf items")
    else:
        shelf()
elif str(sys.argv[1]) == "channelShelf":
    if __settings__.getSetting('channelShelf') == "false":
        printDebug("Disabling channel shelf")
    else:
        shelfChannel()
elif sys.argv[1] == "update":
    url=sys.argv[2]
    libraryRefresh(url)
elif sys.argv[1] == "watch":
    url=sys.argv[2]
    watched(url)
elif sys.argv[1] == "setting":
    __settings__.openSettings()
    WINDOW = xbmcgui.getCurrentWindowId()
    if WINDOW == 10000:
        printDebug("Currently in home - refreshing to allow new settings to be taken")
        xbmc.executebuiltin("XBMC.ActivateWindow(Home)")
elif sys.argv[1] == "delete":
    url=sys.argv[2]
    deleteMedia(url)
elif sys.argv[1] == "refresh":
    xbmc.executebuiltin("Container.Refresh")
elif sys.argv[1] == "subs":
    url=sys.argv[2]
    alterSubs(url)
elif sys.argv[1] == "audio":
    url=sys.argv[2]
    alterAudio(url)
elif sys.argv[1] == "master":
    setMasterServer()
else:

    pluginhandle = int(sys.argv[1])

    WINDOW = xbmcgui.Window( xbmcgui.getCurrentWindowId() )
    WINDOW.clearProperty("heading")

    if g_debug == "true":
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
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE )
        Movies(param_url)

    elif mode == _MODE_ARTISTS:
        artist(param_url)

    elif mode == _MODE_TVSEASONS:
        TVSeasons(param_url)

    elif mode == _MODE_PLAYLIBRARY:
        playLibraryMedia(param_url,force=force)

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
        videoPluginPlay(param_url,param_identifier)

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

print "===== PLEXBMC STOP ====="

#clear done and exit.
sys.modules.clear()

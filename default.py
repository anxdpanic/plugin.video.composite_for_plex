'''
    @document   : default.py
    @package    : PleXBMC add-on
    @author     : Hippojay (aka Dave Hawes-Johnson)
    @copyright  : 2011-2012, Hippojay
    @version    : 2.0b3

    @license    : Gnu General Public License - see LICENSE.TXT
    @description: myPlex XBMC add-on

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
import cProfile

__settings__ = xbmcaddon.Addon(id='plugin.video.plexbmc')
__cwd__ = __settings__.getAddonInfo('path')
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
PLUGINPATH=xbmc.translatePath( os.path.join( __cwd__) )
sys.path.append(BASE_RESOURCE_PATH)
PLEXBMC_VERSION="2.0b rev 1"

try:
    from bonjourFind import *
except:
    print "BonjourFind Import Error"
    
print "===== PLEXBMC START ====="

print "PleXBMC -> running on " + str(sys.version_info)
print "PleXBMC -> running on " + str(PLEXBMC_VERSION)

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

#Check debug first...
g_debug = __settings__.getSetting('debug')

def printDebug( msg, functionname=True ):
    if g_debug == "true":
        if functionname is False:
            print str(msg)
        else:
            print "PleXBMC -> " + inspect.stack()[1][3] + ": " + str(msg)

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
                    
global g_stream 
g_stream = __settings__.getSetting('streaming')
g_secondary = __settings__.getSetting('secondary')
g_streamControl = __settings__.getSetting('streamControl')
g_channelview = __settings__.getSetting('channelview')
g_flatten = __settings__.getSetting('flatten')
printDebug("PleXBMC -> Flatten is: "+ g_flatten, False)
#g_playtheme = __settings__.getSetting('playtvtheme')
g_forcedvd = __settings__.getSetting('forcedvd')
g_skintype= __settings__.getSetting('skinwatch')    
g_skinwatched="xbmc"
g_skin = xbmc.getSkinDir()

if g_skintype == "true":
    if g_skin.find('.plexbmc'):
        g_skinwatched="plexbmc"
        
if g_debug == "true":
    print "PleXBMC -> Settings streaming: " + g_stream
    print "PleXBMC -> Setting filter menus: " + g_secondary
    print "PleXBMC -> Setting debug to " + g_debug
    print "PleXBMC -> Setting stream Control to : " + g_streamControl
    print "PleXBMC -> Running skin: " + g_skin
    print "PleXBMC -> Running watch view skin: " + g_skinwatched
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
    

def discoverAllServers( ): # CHECKED
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
    g_bonjour = __settings__.getSetting('bonjour')

    #Set to Bonjour
    if g_bonjour == "1":
        printDebug("PleXBMC -> local Bonjour discovery setting enabled.", False)
        try:
            printDebug("Attempting bonjour lookup on _plexmediasvr._tcp")
            bonjourServer = bonjourFind("_plexmediasvr._tcp")
                                                
            if bonjourServer.complete:
                printDebug("Bonjour discovery completed")
                #Add the first found server to the list - we will find rest from here
                
                bj_server_name = bonjourServer.bonjourName[0].encode('utf-8')
                
                g_serverDict.append({'name'      : bj_server_name.split('.')[0] ,
                                     'address'   : bonjourServer.bonjourIP[0]+":"+bonjourServer.bonjourPort[0] ,
                                     'discovery' : 'bonjour' , 
                                     'token'     : None ,
                                     'uuid'      : None })
                                     
                                     
            else:
                printDebug("BonjourFind was not able to discovery any servers")

        except:
            print "PleXBMC -> Bonjour Issue.  Possibly not installed on system"
            xbmcgui.Dialog().ok("Bonjour Error","Is Bonojur installed on this system?")

    #Set to Disabled       
    else:
        g_host = __settings__.getSetting('ipaddress')
        g_port =__settings__.getSetting('port')
        
        if not g_host or g_host == "<none>":
            g_host=None
        elif not g_port:
            printDebug( "PleXBMC -> No port defined.  Using default of " + DEFAULT_PORT, False)
            g_host=g_host+":"+DEFAULT_PORT
        else:
            g_host=g_host+":"+g_port
            printDebug( "PleXBMC -> Settings hostname and port: " + g_host, False)
    
        if g_host is not None:
            g_serverDict.append({'serverName': 'unknown' ,
                                 'address'   : g_host ,
                                 'discovery' : 'local' , 
                                 'token'     : None ,
                                 'uuid'      : None ,
                                 'role'      : 'master' })    
        
    if __settings__.getSetting('myplex_user') != "":
        printDebug( "PleXBMC -> Adding myplex as a server location", False)
        g_serverDict.append({'serverName': 'MYPLEX' ,
                             'address'   : "my.plex.app" ,
                             'discovery' : 'myplex' , 
                             'token'     : None ,
                             'uuid'      : None ,
                             'role'      : 'master' })
    
    
    printDebug("PleXBMC -> serverList is " + str(g_serverDict), False)

def resolveAllServers( ): # CHECKED
    '''
      Return list of all media sections configured
      within PleXBMC
      @input: None
      @Return: unique list of media sections
    '''
    printDebug("== ENTER: resolveAllServers ==", False)
    localServers=[]
      
    for servers in g_serverDict:
    
        if ( servers['discovery'] == 'local' ) or ( servers['discovery'] == 'bonjour' ):
            localServers+=getLocalServers()
        elif servers['discovery'] == 'myplex':
            localServers+=getMyPlexServers()
    
    printDebug ("Resolved server List: " + str(localServers))
    
    '''If we have more than one server source, then
       we need to ensure uniqueness amonst the
       seperate servers.
       
       If we have only one server source, then the assumption
       is that Plex will deal with this for us.
    '''
    
    if len(g_serverDict) > 1:
        oneCount=0
        for onedevice in localServers:
        
            twoCount=0
            for twodevice in localServers:

                printDebug( "["+str(oneCount)+":"+str(twoCount)+"] Checking " + onedevice['uuid'] + " and " + twodevice['uuid'])

                if oneCount == twoCount:
                    printDebug( "skip" )
                    twoCount+=1
                    continue
                    
                if onedevice['uuid'] == twodevice['uuid']:
                    printDebug ( "match" )
                    if onedevice['discovery'] == "local":
                        localServers.pop(twoCount)
                    else:
                        localServers.pop(oneCount)
                else:
                    printDebug( "no match" )
                
                twoCount+=1
             
            oneCount+=1
    
    printDebug ("Unique server List: " + str(localServers))
    return localServers     
            
def getAllSections( ): # CHECKED
    '''
        from g_serverDict, get a list of all the available sections
        and deduplicate the sections list
        @input: None
        @return: None (alters the global value g_sectionList)
    '''
    printDebug("== ENTER: getAllSections ==", False)
    printDebug("Using servers list: " + str(g_serverDict))

    for server in g_serverDict:
                                                                        
        if server['discovery'] == "local" or server['discovery'] == "bonjour":                                                
            html=getURL('http://'+server['address']+'/system/library/sections')
        elif server['discovery'] == "myplex":
            html=getMyPlexURL('/pms/system/library/sections')
            
        if html is False:
            continue
                
        tree = etree.fromstring(html).getiterator("Directory")
        
        for sections in tree:
                                
            g_sections.append({'title':sections.get('title','Unknown').encode('utf-8'), 
                               'address': sections.get('host','Unknown')+":"+sections.get('port'),
                               'serverName' : sections.get('serverName','Unknown').encode('utf-8'),
                               'uuid' : sections.get('machineIdentifier','Unknown') ,
                               'path' : sections.get('path') ,
                               'token' : sections.get('accessToken',None) ,
                               'location' : server['discovery'] ,
                               'art' : sections.get('art') ,
                               'local' : sections.get('local') ,
                               'type' : sections.get('type','Unknown') })
    
    '''If we have more than one server source, then
       we need to ensure uniqueness amonst the
       seperate sections.
       
       If we have only one server source, then the assumption
       is that Plex will deal with this for us
    '''
    if len(g_serverDict) > 1:    
        oneCount=0
        for onedevice in g_sections:
        
            twoCount=0
            for twodevice in g_sections:

                printDebug( "["+str(oneCount)+":"+str(twoCount)+"] Checking " + str(onedevice['title']) + " and " + str(twodevice['title']))
                printDebug( "and "+ onedevice['uuid'] + " is equal " + twodevice['uuid'])

                if oneCount == twoCount:
                    printDebug( "skip" )
                    twoCount+=1
                    continue
                    
                if ( str(onedevice['title']) == str(twodevice['title']) ) and ( onedevice['uuid'] == twodevice['uuid'] ):
                    printDebug( "match")
                    if onedevice['local'] == "1":
                        printDebug ( "popping 2 " + str(g_sections.pop(twoCount)))
                    else:
                        printDebug ( "popping 1 " + str(g_sections.pop(oneCount)))
                else:
                    printDebug( "no match")
                
                twoCount+=1
             
            oneCount+=1
             
def getAuthDetails( details, url_format=True, prefix="&" ): # CHECKED
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
            
def getMyPlexServers( ): # CHECKED
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
        return
        
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
                            'address'   : data['address']+":"+data['port'] ,
                            'discovery' : 'myplex' , 
                            'token'     : accessToken ,
                            'uuid'      : data['machineIdentifier'] ,
                            'owned'     : data.get('owned',0) ,  
                            'master'    : master })
                            
    return tempServers                         
    
def getLocalServers( ): # CHECKED
    '''
        Connect to the defined local server (either direct or via bonjour discovery)
        and get a list of all known servers.
        @input: nothing
        @return: a list of servers (as Dict)
    '''

    printDebug("== ENTER: getLocalServers ==", False)

    tempServers=[]
    url_path="/servers"
    html=False
    
    for local in g_serverDict:
    
        if local.get('discovery') == "local" or local.get('discovery') == "bonjour":
            html = getURL(local['address']+url_path)
            break
        
    if html is False:
         return tempServers
             
    server=etree.fromstring(html).findall('Server')
    count=0
    for servers in server:
        data=dict(servers.items())
        
        if count == 0:
            master=1
        else:
            master=0
        
        tempServers.append({'serverName': data['name'].encode('utf-8') ,
                            'address'   : data['address']+":"+data['port'] ,
                            'discovery' : 'local' , 
                            'token'     : data.get('accessToken',None) ,
                            'uuid'      : data['machineIdentifier'] ,
                            'owned'     : '1' ,
                            'master'    : master })

        count+=1                   
    return tempServers                         
                             
def getMyPlexURL( url_path, renew=False, suppress=True ): # CHECKED
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
        conn = httplib.HTTPSConnection(MYPLEX_SERVER) 
        conn.request("GET", url_path+"?X-Plex-Token="+getMyPlexToken(renew)) 
        data = conn.getresponse() 
        if ( int(data.status) == 401 )  and not ( renew ):
            return getMyPlexURL(url_path,True)
            
        if int(data.status) >= 400:
            error = "HTTP response error: " + str(data.status) + " " + str(data.reason)
            if suppress is False:
                xbmcgui.Dialog().ok("Error",error)
            print error
            return False
        elif int(data.status) == 301 and type == "HEAD":
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
        return link

def getMyPlexToken( renew=False ): # CHECKED
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
 
def getNewMyPlexToken( ): # CHECKED
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
        return False
    
    base64string = base64.encodestring('%s:%s' % (myplex_username, myplex_password)).replace('\n', '')
    txdata=""
    token=False
    
    myplex_headers={'X-Plex-Platform': "XBMC",
                    'X-Plex-Platform-Version': "11.00",
                    'X-Plex-Provides': "player",
                    'X-Plex-Product': "PleXBMC",
                    'X-Plex-Version': "2.0b",
                    'X-Plex-Device': "Not Known",
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
            return False
    except socket.gaierror :
        error = 'Unable to lookup host: ' + server + "\nCheck host name is correct"
        if suppress is False:
            xbmcgui.Dialog().ok(title,error)
        print error
        return False
    except socket.error, msg : 
        error="Unable to connect to " + server +"\nReason: " + str(msg)
        if suppress is False:
            xbmcgui.Dialog().ok(title,error)
        print error
        return False
    
    return token

def getURL( url, suppress=True, type="GET", popup=0 ): # CHECKED
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
        conn = httplib.HTTPConnection(server) 
        conn.request(type, urlPath, headers=authHeader) 
        data = conn.getresponse() 
        if int(data.status) == 200:
            link=data.read()
            printDebug("====== XML returned =======")
            printDebug(link, False)
            printDebug("====== XML finished ======")

        elif ( int(data.status) == 301 ) or ( int(data.status) == 302 ): 
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
        return link
      
def mediaType( partData, server, dvdplayback=False ): # CHECKED
    printDebug("== ENTER: mediaType ==", False)    
    stream=partData['key']
    file=partData['file']
    
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
        global g_stream
        if dvdplayback:
            printDebug("Forcing SMB for DVD playback")
            g_stream="2"
        else:
            g_stream="1"
        
    # 1 is stream no matter what
    if g_stream == "1":
        printDebug( "Selecting stream")
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
        
def addGUIItem( url, details, extraData, context=None, folder=True ): # CHECKED
        printDebug("== ENTER: addDir ==", False)
        printDebug("Adding Dir for [%s]" % details.get('title','Unknown'))
        printDebug("Passed details: " + str(details))
        printDebug("Passed extraData: " + str(extraData))
        
        if details.get('title','') == '':
            return
              
        if (extraData.get('token',None) is None) and _PARAM_TOKEN:
            extraData['token']=_PARAM_TOKEN

        aToken=getAuthDetails(extraData)
        qToken=getAuthDetails(extraData, prefix='?')
        
        #Create the URL to pass to the item
        if ( not folder) and ( extraData['type'] =="Picture" ):
             u=url+qToken
        else:
            u=sys.argv[0]+"?url="+str(url)+aToken

        printDebug("URL to use for listing: " + u)
                
        #Create the ListItem that will be displayed
        thumb=str(extraData.get('thumb',''))
        if '?' in thumb:
            liz=xbmcgui.ListItem(details.get('title','Unknown'), iconImage=thumb+aToken, thumbnailImage=thumb+aToken)
        else:
            liz=xbmcgui.ListItem(details.get('title','Unknown'), iconImage=thumb+qToken, thumbnailImage=thumb+qToken)
        printDebug("Setting thumbnail as " + thumb + qToken)
                
        #Set the properties of the item, such as summary, name, season, etc
        liz.setInfo( type=extraData.get('type','Video'), infoLabels=details ) 
        
        #Music related tags
        if extraData.get('type','').lower() == "music":
            liz.setProperty('Artist_Genre', details.get('genre',''))
            liz.setProperty('Artist_Description', details.get('plot',''))
            liz.setProperty('Album_Description', details.get('plot',''))
        
        if ( not folder):
            if g_skipmediaflags == "false":
                liz.setProperty('VideoResolution', extraData.get('VideoResolution',''))
                liz.setProperty('VideoCodec', extraData.get('VideoCodec',''))
                liz.setProperty('AudioCodec', extraData.get('AudioCodec',''))
                liz.setProperty('AudioChannels', extraData.get('AudioChannels',''))
                liz.setProperty('VideoAspect', extraData.get('VideoAspect',''))
                
                #liz.addStreamInfo('video', {'codec': extraData.get('VideoCodec','') ,
                #                            'aspect' : float(extraData.get('VideoAspect','')) ,
                #                            'height' : int(extraData.get('VideoResolution','')) } )
                #                            
                #liz.addStreamInfo('audio', {'codec': extraData.get('AudioCodec','') ,
                #                            'channels' : int(extraData.get('AudioChannels','')) } )

                                            
            liz.setProperty('IsPlayable', 'true')

            try:
                #Then set the number of watched and unwatched, which will be displayed per season
                liz.setProperty('WatchedEpisodes', str(extraData['WatchedEpisodes']))
                liz.setProperty('UnWatchedEpisodes', str(extraData['UnWatchedEpisodes']))
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
        
def displaySections( filter=None ): # CHECKED
        printDebug("== ENTER: displaySections() ==", False)
        xbmcplugin.setContent(pluginhandle, 'movies')

        numOfServers=len(g_serverDict)
        printDebug( "Using list of "+str(numOfServers)+" servers: " +  str(g_serverDict))
        getAllSections()
        
        for section in g_sections:
                
            details={'title' : section.get('title', 'Unknown') }
            
            if len(g_serverDict) > 1:
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
                
            s_url='http://%s%s&mode=%s' % ( section['address'], path, mode )
           
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
        allservers=resolveAllServers()
        numOfServers=len(allservers)
        
        if __settings__.getSetting('myplex_user') != '':
            addGUIItem('http://myplexqueue&mode='+str(_MODE_MYPLEXQUEUE), {'title':'myplex Queue'},{'type':'Video'})
        
        for server in allservers:
                                                                                              
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
                
            u="http://"+server['address']+"/system/plugins/all&mode="+str(_MODE_CHANNELVIEW)
            addGUIItem(u,details,extraData)
                    
            #Create plexonline link
            details['title']=prefix+"Plex Online"
            extraData['type']="file"
            
            u="http://"+server['address']+"/system/plexonline&mode="+str(_MODE_PLEXONLINE)
            addGUIItem(u,details,extraData)
          
        #All XML entries have been parsed and we are ready to allow the user to browse around.  So end the screen listing.
        xbmcplugin.endOfDirectory(pluginhandle)  

def Movies( url, tree=None ): # CHECKED
    printDebug("== ENTER: Movies() ==", False)
    xbmcplugin.setContent(pluginhandle, 'movies')
            
    #get the server name from the URL, which was passed via the on screen listing..
    if tree is None:
        #Get some XML and parse it
        html=getURL(url)
        
        if html is False:
            return
            
        tree = etree.fromstring(html)

    server=getServerFromURL(url)
                    
    randomNumber=str(random.randint(1000000000,9999999999))   
    #Find all the video tags, as they contain the data we need to link to a file.
    MovieTags=tree.findall('Video')
    fullList=[]
    for movie in MovieTags:
        
        movieTag(url, server, tree, movie, randomNumber)
        
    xbmcplugin.endOfDirectory(pluginhandle)
 
def buildContextMenu( url, itemData ): # CHECKED
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
    deleteURL="http://"+server+"/library/metadata/"+ID+getAuthDetails(itemData)
    removed=plugin_url+"delete, " + deleteURL + ")"
    context.append(('Delete media', removed , ))

    #Display plugin setting menu
    settingDisplay=plugin_url+"setting)"
    context.append(('PleXBMC settings', settingDisplay , ))

    #Reload media section
    listingRefresh=plugin_url+"refresh)"
    context.append(('Reload Section', listingRefresh , ))

    printDebug("Using context menus " + str(context))
    
    return context
    
def TVShows( url, tree=None ): # CHECKED
    printDebug("== ENTER: TVShows() ==", False)
    xbmcplugin.setContent(pluginhandle, 'tvshows')
            
    #Get the URL and server name.  Get the XML and parse
    if tree is None:
        html=getURL(url)
    
        if html is False:
            return

        tree=etree.fromstring(html)

    server=getServerFromURL(url)

    #For each directory tag we find
    ShowTags=tree.findall('Directory') 
    for show in ShowTags:

        tempgenre=[]
        
        for child in show:
            tempgenre.append(child.get('tag',''))
            
        watched=int(show.get('viewedLeafCount',0))
        
        #Create the basic data structures to pass up
        details={'title'      : show.get('title','Unknown').encode('utf-8') ,
                 'tvshowname' : show.get('title','Unknown').encode('utf-8') ,
                 'studio'     : show.get('studio','') ,
                 'plot'       : show.get('summary','') ,
                 'overlay'    : _OVERLAY_XBMC_UNWATCHED ,
                 'playcount'  : 0 , 
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
            if g_skinwatched == "plexbmc":
                details['overlay']=_OVERLAY_PLEX_UNWATCHED   
        elif extraData['UnWatchedEpisodes'] == 0: 
            if g_skinwatched == "xbmc":
                details['overlay']=_OVERLAY_XBMC_WATCHED   
            elif g_skinwatched == "plexbmc":
                details['overlay']=_OVERLAY_PLEX_WATCHED   
        else:
            if g_skinwatched == "plexbmc":
                details['overlay'] = _OVERLAY_PLEX_PARTIAL
        
        #Create URL based on whether we are going to flatten the season view
        if g_flatten == "2":
            printDebug("Flattening all shows")
            u='http://%s%s&mode=%s'  % ( server, extraData['key'].replace("children","allLeaves"), str(_MODE_TVEPISODES))
        else:
            u='http://%s%s&mode=%s'  % ( server, extraData['key'], str(_MODE_TVSEASONS))
            
        if g_skipcontext == "false":
            context=buildContextMenu(url, extraData)
        else:
            context=None
            
        addGUIItem(u,details,extraData, context) 
        
    #End the listing    
    xbmcplugin.endOfDirectory(pluginhandle)
 
def TVSeasons( url ): # CHECKED
    printDebug("== ENTER: season() ==", False)
    xbmcplugin.setContent(pluginhandle, 'seasons')

    #Get URL, XML and parse
    server=getServerFromURL(url)
    html=getURL(url)
    
    if html is False:
        return
   
    tree=etree.fromstring(html)
    
    willFlatten=False
    if g_flatten == "1":
        #check for a single season
        if int(tree.get('size',0)) == 1:
            printDebug("Flattening single season show")
            willFlatten=True
    
    sectionart=getFanart(tree, server)
          
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
                 'studio'     : season.get('studio','') ,
                 'plot'       : season.get('summary','') ,
                 'overlay'    : _OVERLAY_XBMC_UNWATCHED ,
                 'playcount'  : 0 , 
                 'season'     : 0 ,
                 'episode'    : int(season.get('leafCount',0)) ,
                 'mpaa'       : season.get('contentRating','') ,
                 'aired'      : season.get('originallyAvailableAt','') }
                 
        extraData={'type'              : 'video' ,
                   'WatchedEpisodes'   : watched ,
                   'UnWatchedEpisodes' : details['episode'] - watched ,
                   'thumb'             : getThumb(season, server) ,
                   'fanart_image'      : getFanart(season, server) ,
                   'token'             : _PARAM_TOKEN ,
                   'key'               : season.get('key','') ,
                   'ratingKey'         : str(season.get('ratingKey',0)) }
                     
        if extraData['fanart_image'] == "":
            extraData['fanart_image']=sectionart

        #Set up overlays for watched and unwatched episodes
        if extraData['WatchedEpisodes'] == 0:
            if g_skinwatched == "plexbmc":
                details['overlay']=_OVERLAY_PLEX_UNWATCHED   
        elif extraData['UnWatchedEpisodes'] == 0: 
            if g_skinwatched == "xbmc":
                details['overlay']=_OVERLAY_XBMC_WATCHED   
            elif g_skinwatched == "plexbmc":
                details['overlay']=_OVERLAY_PLEX_WATCHED   
        else:
            if g_skinwatched == "plexbmc":
                details['overlay'] = _OVERLAY_PLEX_PARTIAL
            
        url='http://%s%s&mode=%s' % ( server , extraData['key'], str(_MODE_TVEPISODES) )

        if g_skipcontext == "false":
            context=buildContextMenu(url, season)
        else:
            context=None
            
        #Build the screen directory listing
        addGUIItem(url,details,extraData, context) 
        
    #All done, so end the listing
    xbmcplugin.endOfDirectory(pluginhandle)
 
def TVEpisodes( url, tree=None ): # CHECKED
    printDebug("== ENTER: TVEpisodes() ==", False)
    xbmcplugin.setContent(pluginhandle, 'episodes')
                
    if tree is None:
        #Get URL, XML and Parse
        html=getURL(url)
        
        if html is False:
            return
        
        tree=etree.fromstring(html)
    
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
        details={'plot'        : episode.get('summary','') ,
                 'title'       : episode.get('title','Unknown').encode('utf-8') ,
                 'playcount'   : int(episode.get('viewCount',0)) ,
                 'rating'      : float(episode.get('rating',0)) ,
                 'studio'      : episode.get('studio',tree.get('studio','')) ,
                 'mpaa'        : episode.get('contentRating', tree.get('grandparentContentRating','')) ,
                 'year'        : int(episode.get('year',0)) ,
                 'tagline'     : episode.get('tagline','') ,
                 'duration'    : str(datetime.timedelta(seconds=duration)) ,
                 'overlay'     : _OVERLAY_XBMC_UNWATCHED ,
                 'episode'     : int(episode.get('index',0)) ,
                 'aired'       : episode.get('originallyAvailableAt','') ,
                 'tvshowtitle' : episode.get('grandparentTitle',tree.get('grandparentTitle','')) ,
                 'season'      : episode.get('parentIndex',tree.get('parentIndex',0)) }

        details['title'] = str(details['episode']).zfill(2) + ". " + details['title']
                 
        if tree.get('mixedParents',0) == 1:
            details['title'] = details['tvshowtitle'] + ": " + details['title']
        
        #Extra data required to manage other properties
        extraData={'type'         : "Video" ,
                   'thumb'        : getThumb(episode, server) ,
                   'fanart_image' : getFanart(episode, server) ,
                   'token'        : _PARAM_TOKEN ,
                   'key'          : episode.get('key',''),
                   'ratingKey'    : str(episode.get('ratingKey',0)) }

        if extraData['fanart_image'] == "":
            extraData['fanart_image']=sectionart
                          
        #Determine what tupe of watched flag [overlay] to use
        if details['playcount'] > 0:
            if g_skinwatched == "xbmc":
                details['overlay']=_OVERLAY_XBMC_WATCHED
            elif g_skinwatched == "plexbmc":
                details['overlay']=_OVERLAY_PLEX_WATCHED
        else: #if details['playcount'] == 0: 
            if g_skinwatched == "plexbmc":
                details['overlay']=_OVERLAY_PLEX_UNWATCHED
        
        if g_skinwatched == "plexbmc" and int(view_offset) > 0:
            details['overlay'] = _OVERLAY_PLEX_PARTIAL
        
        #Extended Metadata
        if g_skipmetadata == "false":
            details['cast']     = tempcast
            details['director'] = " / ".join(tempdir)
            details['writer']   = " / ".join(tempwriter)
            details['genre']    = " / ".join(tempgenre)
             
        #Add extra media flag data
        if g_skipmediaflags == "false":
            extraData['VideoResolution'] = mediaarguments.get('videoResolution','')
            extraData['VideoCodec']      = mediaarguments.get('videoCodec','')
            extraData['AudioCodec']      = mediaarguments.get('audioCodec','')
            extraData['AudioChannels']   = mediaarguments.get('audioChannels','')
            extraData['VideoAspect']     = mediaarguments.get('aspectRatio','')

        #Build any specific context menu entries
        if g_skipcontext == "false":
            context=buildContextMenu(url, extraData)    
        else:
            context=None
        
        # http:// <server> <path> &mode=<mode> &id=<media_id> &t=<rnd>
        u="http://%s%s&mode=%s&id=%s&t=%s" % (server, extraData['key'], _MODE_PLAYLIBRARY, extraData['ratingKey'], randomNumber)

        addGUIItem(u,details,extraData, context, folder=False)        
    
    xbmcplugin.endOfDirectory(pluginhandle)

def getAudioSubtitlesMedia( server, id ): # CHECKED
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
    media['duration']=timings.get('duration',0)
    
    options = tree.getiterator('Part')    
    
    contents="type"
    
    #Get the Parts info for media type and source selection 
    for stuff in options:
        try:
            bits=stuff.get('key'), stuff.get('file')
            parts.append(bits)
            partsCount += 1
        except: pass
        
    if g_streamControl == "1" or g_streamControl == "2":

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
              
    
    streamData={'contents'   : contents ,
                'audio'      : audio , 
                'audioCount' : audioCount , 
                'subtitle'   : subtitle , 
                'subCount'   : subCount ,
                'external'   : external , 
                'parts'      : parts , 
                'partsCount' : partsCount , 
                'media'      : media , 
                'subOffset'  : selectedSubOffset , 
                'audioOffset': selectedAudioOffset }
    
    printDebug ( str(streamData) )
    return streamData
   
def playLibraryMedia( id, vids, override=False ): # CHECKED
    printDebug("== ENTER: playLibraryMedia ==", False)
    
    getTranscodeSettings(override)
  
    server=getServerFromURL(vids)
    
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

    try:
        resume=int(int(streams['media']['viewOffset'])/1000)
    except:
        resume=0
    
    printDebug("Resume has been set to " + str(resume))
    
    item = xbmcgui.ListItem(path=playurl)
    result=1

    if resume > 0:       
        displayTime = str(datetime.timedelta(seconds=int(resume)))
        dialogOptions = [ "Resume from " + displayTime , "Start from beginning"]
        printDebug( "We have part way through video.  Display resume dialog")
        startTime = xbmcgui.Dialog()
        result = startTime.select('Resuming playback..',dialogOptions)

        if result == -1:
            return
    
    printDebug("handle is " + str(pluginhandle))
    #item.setProperty('ResumeTime', '300' )
    #item.setProperty('TotalTime', '1200' )

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
               
    #If we get this far, then XBMC must be playing
    
    #If the user chose to resume...
    if result == 0:
        #Need to skip forward (seconds)
        printDebug("Seeking to " + str(resume))
        xbmc.Player().pause()
        xbmc.Player().seekTime((resume)) 
        time.sleep(1)
        seek=xbmc.Player().getTime()

        while not ((seek - 10) < resume < (seek + 10)):
            printDebug( "Do not appear to have seeked correctly. Try again")
            xbmc.Player().seekTime((resume)) 
            time.sleep(1)
            seek=xbmc.Player().getTime()
        
        xbmc.Player().pause()

    if not (g_transcode == "true" ): 
        setAudioSubtitles(streams)
 
    monitorPlayback(id,server)
    
    return

def setAudioSubtitles( stream ): # CHECKED
    printDebug("== ENTER: setAudioSubtitles ==", False)
        
    if stream['contents'] == "type":
        printDebug ("No streams to process.")
        
        if g_streamControl == "3":
            xbmc.Player().showSubtitles(False)    
            printDebug ("All subs disabled")

        return True

    if g_streamControl == "1" or  g_streamControl == "2":
        audio=stream['audio']
        printDebug("Attempting to set Audio Stream")
        #Audio Stream first        
        if stream['audioCount'] == 1:
            printDebug ("Only one audio stream present - will leave as default")
        elif stream['audioCount'] > 1:
            printDebug ("Multiple audio stream. Attempting to set to local language")
            try:
                if audio['selected'] == "1":
                    printDebug ("Found preferred language at index " + str(stream['audioOffset']))
                    xbmc.Player().setAudioStream(stream['audioOffset'])
                    printDebug ("Audio set")
            except: pass
      
    #Try and set embedded subtitles
    if g_streamControl == "1":
        subtitle=stream['subtitle']
        printDebug("Attempting to set subtitle Stream", True)
        try:
            if stream['subCount'] > 0 and subtitle['languageCode']:
                printDebug ("Found embedded subtitle for local language" )
                printDebug ("Enabling embedded subtitles")
                xbmc.Player().showSubtitles(False)
                xbmc.Player().setSubtitleStream(stream['subOffset'])
                return True
            else:
                printDebug ("No embedded subtitles to set")
        except:
            printDebug("Unable to set subtitles")
  
    if g_streamControl == "1" or g_streamControl == "2":
        external=stream['external']
        printDebug("Attempting to set external subtitle stream")
    
        try:   
            if external:
                try:
                    printDebug ("External of type ["+external['codec']+"]")
                    if external['codec'] == "idx" or external['codec'] =="sub":
                        printDebug ("Skipping IDX/SUB pair - not supported yet")
                    else:    
                        xbmc.Player().setSubtitles(external['key'])
                        return True
                except: pass                    
            else:
                printDebug ("No external subtitles available. Will turn off subs")
        except:
            printDebug ("No External subs to set")
            
    xbmc.Player().showSubtitles(False)    
    return False
        
def codeToCountry( id ): # CHECKED
  languages = { "None": "none"              ,
                "alb" : "Albanian"          ,
                "ara" : "Arabic"            ,
                "arm" : "Belarusian"        ,
                "bos" : "Bosnian"           ,
                "bul" : "Bulgarian"         ,
                "cat" : "Catalan"           ,
                "chi" : "Chinese"           ,
                "hrv" : "Croatian"          ,
                "cze" : "Czech"             ,
                "dan" : "Danish"            ,
                "dut" : "Dutch"             ,
                "eng" : "English"           ,
                "epo" : "Esperanto"         ,
                "est" : "Estonian"          ,
                "per" : "Farsi"             ,
                "fin" : "Finnish"           ,
                "fre" : "French"            ,
                "glg" : "Galician"          ,
                "geo" : "Georgian"          ,
                "ger" : "German"            ,
                "ell" : "Greek"             ,
                "heb" : "Hebrew"            ,
                "hin" : "Hindi"             ,
                "hun" : "Hungarian"         ,
                "ice" : "Icelandic"         ,
                "ind" : "Indonesian"        ,
                "ita" : "Italian"           ,
                "jpn" : "Japanese"          ,
                "kaz" : "Kazakh"            ,
                "kor" : "Korean"            ,
                "lav" : "Latvian"           ,
                "lit" : "Lithuanian"        ,
                "ltz" : "Luxembourgish"     ,
                "mac" : "Macedonian"        ,
                "may" : "Malay"             ,
                "nor" : "Norwegian"         ,
                "oci" : "Occitan"           ,
                "pol" : "Polish"            ,
                "por" : "Portuguese"        ,
                "pob" : "Portuguese (Brazil)" ,
                "rum" : "Romanian"          ,
                "rus" : "Russian"           ,
                "scc" : "SerbianLatin"      ,
                "scc" : "Serbian"           ,
                "slo" : "Slovak"            ,
                "slv" : "Slovenian"         ,
                "spa" : "Spanish"           ,
                "swe" : "Swedish"           ,
                "syr" : "Syriac"            ,
                "tha" : "Thai"              ,
                "tur" : "Turkish"           ,
                "ukr" : "Ukrainian"         ,
                "urd" : "Urdu"              ,
                "vie" : "Vietnamese"        ,
                "all" : "All" }
  return languages[ id ]        
                 
def selectMedia( count, options, server ):   # CHECKED
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
           
def remove_html_tags( data ): # CHECKED
    p = re.compile(r'<.*?>')
    return p.sub('', data)

def monitorPlayback( id, server ): # CHECKED
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
    
def PLAY( url ): # CHECKED
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

def videoPluginPlay( vids, prefix=None ): # CHECKED
    '''
        Plays Plugin Videos, which do not require library feedback 
        but require further processing
        @input: url of video, plugin identifier
        @return: nothing. End of Script
    '''
    printDebug("== ENTER: videopluginplay with URL + " + vids + " ==", False)
           
    server=getServerFromURL(vids)
    
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
    
    #Everything else should be this
    #else:
    #    printDebug("Direct link")
    #    output=getURL(vids, type="HEAD", suppress=False)
    #    if not output:
    #        return
    #        
    #    printDebug(str(output))
    #    if ( output[0:4] == "http" ) or ( output[0:4] == "plex" ):
    #        printDebug("Redirect.  Getting new URL")
    #        vids=output
    #        printDebug("New URL is: "+ vids)
    #        parameters=get_params(vids)
    #        
    #        prefix=parameters.get("prefix",'')
    #        extraData={'key'        : vids ,
    #                   'identifier' : prefix }
    #
    #        vids=getLinkURL(vids, extraData ,server)  
    
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

def pluginTranscodeMonitor( sessionID, server ): # CHECKED
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
                
def get_params( paramstring ): # CHECKED
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
    printDebug("Returning: " + str(param))                        
    return param

def getContent( url ):  # CHECKED
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
            url=url+'&query='+text
        else:
            return
     
    html=getURL(url, suppress=False, popup=1 )
    
    if html is False:
        return
        
    tree=etree.fromstring(html)
 
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

def processDirectory( url, tree=None ): # CHECKED
    printDebug("== ENTER: processDirectory ==", False)
    printDebug("Processing secondary menus")
    xbmcplugin.setContent(pluginhandle, 'movies')

    server=getServerFromURL(url)
    
    for directory in tree:
        details={'title' : directory.get('title','Unknown').encode('utf-8') }
        extraData={'thumb'        : getThumb(directory, server) ,
                   'fanart_image' : getFanart(tree, server, False) } 
        
        if extraData['thumb'] == '':
            extraData['thumb']=extraData['fanart_image']
        
        u='%s&mode=%s' % ( getLinkURL(url,directory,server), _MODE_GETCONTENT )

        addGUIItem(u,details,extraData)
        
    xbmcplugin.endOfDirectory(pluginhandle)
   
def getMasterServer():
    discoverAllServers()
    possibleServers=[]
    for serverData in resolveAllServers():
        print str(serverData)
        if serverData['master'] == 1:
            possibleServers.append({'address' : serverData['address'] ,
                                    'discovery' : serverData['discovery'] })
    print str(possibleServers)
    if len(possibleServers) > 1:
        preferred="local"
        for serverData in possibleServers:
            if preferred == "any":
                return serverdata['address']
            else:
                if serverData['discovery'] == preferred:
                    return serverData['address']
                    
    return possibleServers[0]['address']                

def transcode( id, url, identifier=None ): # CHECKED
    printDebug("== ENTER: transcode ==", False)
 
    server=getServerFromURL(url)
    
    #Check for myplex user, which we need to alter to a master server
    if 'plexapp.com' in url:
        server=getMasterServer()
    
    printDebug("Using preferred transcosing server: " + server)
        
    filestream=urllib.quote_plus("/"+"/".join(url.split('/')[3:]))
  
    if identifier is not None:
        baseurl=url.split('url=')[1]
        myurl="/video/:/transcode/segmented/start.m3u8?url="+baseurl+"&webkit=1&3g=0&offset=0&quality="+g_quality+"&session="+g_sessionID+"&identifier="+identifier
    else:
  
        if g_transcodefmt == "m3u8":
            myurl = "/video/:/transcode/segmented/start.m3u8?identifier=com.plexapp.plugins.library&ratingKey=" + id + "&offset=0&quality="+g_quality+"&url=http%3A%2F%2Flocalhost%3A32400" + filestream + "&3g=0&httpCookies=&userAgent=&session="+g_sessionID
        elif g_transcodefmt == "flv":
            myurl="/video/:/transcode/generic.flv?format=flv&videoCodec=libx264&vpre=video-embedded-h264&videoBitrate=5000&audioCodec=libfaac&apre=audio-embedded-aac&audioBitrate=128&size=640x480&fakeContentLength=2000000000&url=http%3A%2F%2Flocalhost%3A32400"  + filestream + "&3g=0&httpCookies=&userAgent="
        else:
            printDebug( "Woah!!  Barmey settings error....Bale.....")
            return url
    
    now=str(int(round(time.time(),0)))
    
    msg = myurl+"@"+now
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
    fullURL="http://"+server+myurl+"&X-Plex-Access-Key="+publicKey+"&X-Plex-Access-Time="+str(now)+"&X-Plex-Access-Code="+urllib.quote_plus(token)+"&"+capability
       
    printDebug("Transcoded media location URL " + fullURL)
    
    return fullURL
     
def artist( url, tree=None ): # CHECKED
    '''
        Process artist XML and display data
        @input: url of XML page, or existing tree of XML page
        @return: nothing
    '''
    printDebug("== ENTER: artist ==", False)
    xbmcplugin.setContent(pluginhandle, 'artists')
    
    #Get the URL and server name.  Get the XML and parse
    if tree is None:      
        html=getURL(url)
        if html is False:
            return
   
        tree=etree.fromstring(html)
    
    server=getServerFromURL(url)
    
    ArtistTag=tree.findall('Directory')
    for artist in ArtistTag:
    
        details={'plot'    : artist.get('summary','') ,
                 'artist'  : artist.get('title','').encode('utf-8') }
        
        details['title']=details['artist']
          
        extraData={'type'         : "Music" ,
                   'thumb'        : getThumb(artist, server) ,
                   'fanart_image' : getFanart(artist, server) ,
                   'ratingKey'    : artist.get('title','') ,
                   'key'          : artist.get('key','') }

        url='http://%s%s&mode=%s' % (server, extraData['key'], str(_MODE_ALBUMS) )
        
        addGUIItem(url,details,extraData) 
        
    #End the listing    
    xbmcplugin.endOfDirectory(pluginhandle)

def albums( url, tree=None ): # CHECKED
    printDebug("== ENTER: albums ==", False)
    xbmcplugin.setContent(pluginhandle, 'albums')
   
    #Get the URL and server name.  Get the XML and parse
    if tree is None:
        html=getURL(url)
        if html is False:
            return
   
        tree=etree.fromstring(html)
    
    server=getServerFromURL(url)        
    sectionart=getFanart(tree, server)
    
    AlbumTags=tree.findall('Directory')
    for album in AlbumTags:
     
        details={'album'   : album.get('title','').encode('utf-8') ,
                 'year'    : int(album.get('year',0)) ,
                 'artist'  : tree.get('parentTitle', album.get('parentTitle','')) ,
                 'plot'    : album.get('summary','') }

        details['title']=details['album']

        extraData={'type'         : "Music" ,
                   'thumb'        : getThumb(album, server) ,
                   'fanart_image' : getFanart(album, server) ,
                   'key'          : album.get('key','') }

        if extraData['fanart_image'] == "":
            extraData['fanart_image']=sectionart
                                    
        url='http://%s%s&mode=%s' % (server, extraData['key'], str(_MODE_TRACKS) )

        addGUIItem(url,details,extraData) 
        
    xbmcplugin.endOfDirectory(pluginhandle)

def tracks( url,tree=None ): # CHECKED
    printDebug("== ENTER: tracks ==", False)
    xbmcplugin.setContent(pluginhandle, 'songs')
                
    if tree is None:       
        html=getURL(url)          
        if html is False:
            return
  
        tree=etree.fromstring(html)
    
    server=getServerFromURL(url)                               
    sectionart=getFanart(tree,server) 
    TrackTags=tree.findall('Track')      
    for track in TrackTags:
                    
        trackTag(server, tree, track)
    
    xbmcplugin.endOfDirectory(pluginhandle)

def PlexPlugins( url, tree=None ): # CHECKED
    '''
        Main function to parse plugin XML from PMS
        Will create dir or item links depending on what the 
        main tag is.
        @input: plugin page URL
        @return: nothing, creates XBMC GUI listing
    '''
    printDebug("== ENTER: PlexPlugins ==", False)
    xbmcplugin.setContent(pluginhandle, 'movies')
    server=getServerFromURL(url)
    if tree is None:

        html=getURL(url)
    
        if html is False:
            return

        tree=etree.fromstring(html)
    
    for plugin in tree:

        details={'title'   : plugin.get('title','Unknown').encode('utf-8') }

        if details['title'] == "Unknown":
            details['title']=plugin.get('name',"Unknown").encode('utf-8')

        extraData={'thumb'        : getThumb(plugin, server) , 
                   'fanart_image' : getFanart(plugin, server) ,
                   'identifier'   : tree.get('identifier','') ,
                   'type'         : "Video" ,
                   'key'          : plugin.get('key','') }
        
        if extraData['fanart_image'] == "":
            extraData['fanart_image']=getFanart(tree, server)
            
        p_url=getLinkURL(url, extraData, server)
      
        if plugin.tag == "Directory" or plugin.tag == "Podcast":
            addGUIItem(p_url+"&mode="+str(_MODE_PLEXPLUGINS), details, extraData)
                
        elif plugin.tag == "Video":
            addGUIItem(p_url+"&mode="+str(_MODE_VIDEOPLUGINPLAY), details, extraData, folder=False)

    xbmcplugin.endOfDirectory(pluginhandle)        

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
    if tree is None:

        html=getURL(url)
    
        if html is False:
            return

        tree=etree.fromstring(html)
    
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
            addGUIItem(p_url+"&mode="+str(_MODE_PROCESSXML), details, extraData)

        elif plugin.tag == "Track":
            trackTag(server, tree, plugin)
                
        elif tree.get('viewGroup') == "movie":
            Movies(url, tree)
            return

        elif tree.get('viewGroup') == "episode":
            TVEpisodes(url, tree)
            return
       
    xbmcplugin.endOfDirectory(pluginhandle) 

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
    details={'plot'      : movie.get('summary','') ,
             'title'     : movie.get('title','Unknown').encode('utf-8') ,
             'playcount' : int(movie.get('viewCount',0)) ,
             'rating'    : float(movie.get('rating',0)) ,
             'studio'    : movie.get('studio','') ,
             'mpaa'      : "Rated " + movie.get('contentRating', 'unknown') ,
             'year'      : int(movie.get('year',0)) ,
             'tagline'   : movie.get('tagline','') ,
             'duration'  : str(datetime.timedelta(seconds=duration)) ,
             'overlay'   : _OVERLAY_XBMC_UNWATCHED }
    
    #Extra data required to manage other properties
    extraData={'type'         : "Video" ,
               'thumb'        : getThumb(movie, server) ,
               'fanart_image' : getFanart(movie, server) ,
               'token'        : _PARAM_TOKEN ,
               'key'          : movie.get('key',''),
               'ratingKey'    : str(movie.get('ratingKey',0)) }

    #Determine what tupe of watched flag [overlay] to use
    if details['playcount'] > 0:
        if g_skinwatched == "xbmc":
            details['overlay']=_OVERLAY_XBMC_WATCHED
        elif g_skinwatched == "plexbmc":
            details['overlay']=_OVERLAY_PLEX_WATCHED
    elif details['playcount'] == 0: 
        if g_skinwatched == "plexbmc":
            details['overlay']=_OVERLAY_PLEX_UNWATCHED
    
    if g_skinwatched == "plexbmc" and int(view_offset) > 0:
        details['overlay'] = _OVERLAY_PLEX_PARTIAL
    
    #Extended Metadata
    if g_skipmetadata == "false":
        details['cast']     = tempcast
        details['director'] = " / ".join(tempdir)
        details['writer']   = " / ".join(tempwriter)
        details['genre']    = " / ".join(tempgenre)
         
    #Add extra media flag data
    if g_skipmediaflags == "false":
        extraData['VideoResolution'] = mediaarguments.get('videoResolution','')
        extraData['VideoCodec']      = mediaarguments.get('videoCodec','')
        extraData['AudioCodec']      = mediaarguments.get('audioCodec','')
        extraData['AudioChannels']   = mediaarguments.get('audioChannels','')
        extraData['VideoAspect']     = mediaarguments.get('aspectRatio','')

    #Build any specific context menu entries
    if g_skipcontext == "false":
        context=buildContextMenu(url, extraData)    
    else:
        context=None
    # http:// <server> <path> &mode=<mode> &id=<media_id> &t=<rnd>
    u="http://%s%s&mode=%s&id=%s&t=%s" % (server, extraData['key'], _MODE_PLAYLIBRARY, extraData['ratingKey'], randomNumber)
  
    addGUIItem(u,details,extraData,context,folder=False)        
    return
    
def trackTag( server, tree, track ): # CHECKED
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
             'album'       : track.get('parentTitle', tree.get('parentTitle','')) ,
             'artist'      : track.get('grandparentTitle', tree.get('grandparentTitle','')) ,
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

    u="%s&mode=%s&id=%s" % (url, str(_MODE_BASICPLAY), str(extraData['ratingKey']))
        
    addGUIItem(u,details,extraData,folder=False)        
        
def photo( url,tree=None ): # CHECKED
    printDebug("== ENTER: photos ==", False)
    server=url.split('/')[2]
    
    xbmcplugin.setContent(pluginhandle, 'photo')
    
    if tree is None:
        html=getURL(url)
        
        if html is False:
            return
        
        tree=etree.fromstring(html)
    
    sectionArt=getFanart(tree,server)
 
    for picture in tree:
        
        details={'title' : picture.get('title',picture.get('name','Unknown')).encode('utf-8') } 
        
        extraData={'thumb'        : getThumb(picture, server) ,
                   'fanart_image' : getFanart(picture, server) ,
                   'type'         : "Picture" }

        if extraData['fanart_image'] == "":
            extraData['fanart_image']=sectionArt

        u=getLinkURL(url, picture, server)   
                
        if picture.tag == "Directory":
            u=u+"&mode="+str(_MODE_PHOTOS)
            addGUIItem(u,details,extraData)
    
        elif picture.tag == "Photo":
        
            if tree.get('viewGroup','') == "photo":
                for photo in picture:
                    if photo.tag == "Media":
                        for images in photo:
                            if images.tag == "Part":
                                print "found part tag"
                                extraData['key']="http://"+server+images.get('key','')
                                u=extraData['key']
            
            addGUIItem(u,details,extraData,folder=False)

    xbmcplugin.endOfDirectory(pluginhandle)

def music( url, tree=None ): # CHECKED
    printDebug("== ENTER: music ==", False)
    xbmcplugin.setContent(pluginhandle, 'artists')

    server=getServerFromURL(url)
    
    if tree is None:
        html=getURL(url)
    
        if html is False:
            return
   
        tree=etree.fromstring(html)
  
    for grapes in tree:
       
        if grapes.get('key',None) is None:
            continue

        details={'genre'       : grapes.get('genre','') ,
                 'artist'      : grapes.get('artist','') ,
                 'year'        : int(grapes.get('year',0)) ,
                 'album'       : grapes.get('album','') ,
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
            
            details['title']=grapes.get('track','Unknown').encode('utf-8')
            details['duration']=int(int(grapes.get('totalTime',0))/1000)
    
            u=u+"&mode="+str(_MODE_BASICPLAY)
            addGUIItem(u,details,extraData,folder=False)

        else: 
        
            if grapes.tag == "Artist":
                printDebug("Artist Tag")
                xbmcplugin.setContent(pluginhandle, 'artists')
                details['title']=grapes.get('artist','Unknown')
             
            elif grapes.tag == "Album":
                printDebug("Album Tag")
                xbmcplugin.setContent(pluginhandle, 'albums')
                details['title']=grapes.get('album','Unknown')

            elif grapes.tag == "Genre":
                details['title']=grapes.get('genre','Unknown')
            
            else:
                printDebug("Generic Tag: " + grapes.tag)
                details['title']=grapes.get('title','Unknown')
            
            u=u+"&mode="+str(_MODE_MUSIC)
            addGUIItem(u,details,extraData)
        
    xbmcplugin.endOfDirectory(pluginhandle)    

def getThumb( data, server ): # CHECKED
    '''
        Simply take a URL or path and determine how to format for images
        @ input: elementTree element, server name
        @ return formatted URL
    '''
    thumbnail=data.get('thumb','').split('?t')[0]
    
    if thumbnail == '':
        return g_loc+'/resources/plex.png'
        
    elif thumbnail[0:4] == "http" :
        return thumbnail
    
    elif thumbnail[0] == '/':
        return 'http://'+server+thumbnail
    
    else: 
        return g_loc+'/resources/plex.png'

def getFanart( data, server, transcode=True ): # CHECKED
    '''
        Simply take a URL or path and determine how to format for fanart
        @ input: elementTree element, server name
        @ return formatted URL for photo resizing
    '''

    fanart=data.get('art','')
    
    if fanart == '':
        return ''

    elif fanart[0:4] == "http" :
        return fanart
        
    elif fanart[0] == '/':
        if transcode:
            return photoTranscode(server,'http://localhost:32400'+fanart)
        else:
            return 'http://%s%s' % (server, fanart)
        
    else:  
        return ''

def getServerFromURL( url ): # CHECKED
    '''
    Simply split the URL up and get the server portion, sans port
    @ input: url, woth or without protocol
    @ return: the URL server
    '''
    if url[0:4] == "http" or url[0:4] == "plex":
        return url.split('/')[2]
    else:
        return url.split('/')[0]

def getLinkURL( url, pathData, server ): # CHECKED
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
        
    #Any thing else is assumed to be a relative path and is built on existing url        
    else:
        printDebug("Detected relative link")
        return "%s/%s" % ( url, path )
     
    return url
    
def plexOnline( url ): # CHECKED
    printDebug("== ENTER: plexOnline ==")
    xbmcplugin.setContent(pluginhandle, 'files')

    server=getServerFromURL(url)
    
    html=getURL(url)
    
    if html is False:
        return
    
    tree=etree.fromstring(html)
        
    for plugin in tree:
       
        details={'title' : plugin.get('title',plugin.get('name','Unknown')).encode('utf-8') }
        extraData={'type'      : "Video" , 
                   'installed' : int(plugin.get('installed',2)) ,
                   'key'       : plugin.get('key','') ,
                   'thumb'     : getThumb(plugin,server)} 
                   
        mode=_MODE_CHANNELINSTALL
        
        if extraData['installed'] == 1:
            details['title']=details['title']+" (installed)"
            
        elif extraData['installed'] == 2:      
            mode=_MODE_PLEXONLINE
        
        u=getLinkURL(url, plugin, server)
        
        u=u+"&mode="+str(mode)+"&name="+urllib.quote_plus(details['title'])
        addGUIItem(u, details, extraData)

    xbmcplugin.endOfDirectory(pluginhandle)    
 
def install( url, name ): # CHECKED
    printDebug("== ENTER: install ==", False)
    html=getURL(url)
    if html is False:
        return
    tree = etree.fromstring(html)
    
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

def channelView( url ): # CHECKED
    printDebug("== ENTER: channelView ==", False)
    html=getURL(url)
    if html is False:
        return
    tree = etree.fromstring(html)    
    server=getServerFromURL(url)   
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
            mode=_MODE_PHOTOS
        elif suffix == "video":
            mode=_MODE_PLEXPLUGINS
        elif suffix == "music":
            mode=_MODE_MUSIC
        else:
            mode=_MODE_GETCONTENT
        
        addGUIItem(p_url+'&mode='+str(mode),details,extraData)
        
    xbmcplugin.endOfDirectory(pluginhandle)

def photoTranscode( server, url ): # CHECKED
        return 'http://%s/photo/:/transcode?url=%s&width=1280&height=720' % (server, urllib.quote_plus(url))
              
def skin( ): # CHECKED
    #Gather some data and set the window properties
    printDebug("== ENTER: skin() ==", False)
    #Get the global host variable set in settings
    WINDOW = xbmcgui.Window( 10000 )
  
    getAllSections()
    sectionCount=0
    serverCount=0
    
    #For each of the servers we have identified
    for section in g_sections:

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
    allservers=resolveAllServers()
    numOfServers=len(allservers)
    
    for server in allservers:
    
        if g_channelview == "true":
            WINDOW.setProperty("plexbmc.channel", "1")
            WINDOW.setProperty("plexbmc.%d.server.channel" % (serverCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=http://"+server['address']+"/system/plugins/all&mode=21"+aToken+",return)")
        else:
            WINDOW.clearProperty("plexbmc.channel")
            WINDOW.setProperty("plexbmc.%d.server.video" % (serverCount) , "http://"+server['address']+"/video&mode=7"+aToken)
            WINDOW.setProperty("plexbmc.%d.server.music" % (serverCount) , "http://"+server['address']+"/music&mode=17"+aToken)
            WINDOW.setProperty("plexbmc.%d.server.photo" % (serverCount) , "http://"+server['address']+"/photos&mode=16"+aToken)
                
        WINDOW.setProperty("plexbmc.%d.server.online" % (serverCount) , "http://"+server['address']+"/system/plexonline&mode=19"+aToken)

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

    return

def myPlexQueue(): # CHECKED

    if __settings__.getSetting('myplex_user') == '':
        xbmc.executebuiltin("XBMC.Notification(myplex not configured,)")      
        return

    html=getMyPlexURL('/pms/playlists/queue/all')
    tree=etree.fromstring(html)
    
    PlexPlugins('http://my.plexapp.com/playlists/queue/all', tree)
    return
    
def libraryRefresh( url ): # CHECKED
    printDebug("== ENTER: libraryRefresh ==", False)
    html=getURL(url)
    printDebug ("Library refresh requested")
    xbmc.executebuiltin("XBMC.Notification(\"PleXBMC\",Library Refresh started,100)")
    return

def watched( url ): # CHECKED
    printDebug("== ENTER: watched ==", False)

    if url.find("unscrobble") > 0:
        printDebug ("Marking as unwatched with: " + url)
    else:
        printDebug ("Marking as watched with: " + url)
    
    html=getURL(url)
    xbmc.executebuiltin("Container.Refresh")
    
    return
 
def displayServers( url ): # CHECKED
    printDebug("== ENTER: displayServers ==", False)
    type=url.split('/')[2]
    printDebug("Displaying entries for " + type)
    Servers = resolveAllServers()

    #For each of the servers we have identified
    for mediaserver in Servers:
    
        details={'title' : mediaserver.get('serverName','Unknown') }

        if type == "video":
            s_url='http://%s/video&mode=%s' % ( mediaserver.get('address','') , _MODE_PLEXPLUGINS )
            
        elif type == "online":
            s_url='http://%s/system/plexonline&mode=%s' % ( mediaserver.get('address','') , _MODE_PLEXONLINE )
            
        elif type == "music":
            s_url='http://%s/music&mode=%s' % ( mediaserver.get('address','') , _MODE_MUSIC )
            
        elif type == "photo":
            s_url='http://%s/photos&mode=%s' % ( mediaserver.get('address','') , _MODE_PHOTOS )
                
        addGUIItem(s_url, details, {} )

    xbmcplugin.endOfDirectory(pluginhandle)  
   
def getTranscodeSettings( override=False ): # CHECKED
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
        global g_transcodetype 
        global g_transcodefmt
        g_transcodetype = __settings__.getSetting('transcodefmt')
        if g_transcodetype == "0":
            g_transcodefmt="m3u8"
        elif g_transcodetype == "1":
            g_transcodefmt="flv"
        
        global g_quality
        g_quality = str(int(__settings__.getSetting('quality'))+3)
        printDebug( "Transcode format is " + g_transcodefmt)
        printDebug( "Transcode quality is " + g_quality)
        
        baseCapability="http-live-streaming,http-mp4-streaming,http-streaming-video,http-mp4-video"
        if int(g_quality) >= 3:
            baseCapability+=",http-streaming-video-240p,http-mp4-video-240p"
        if int(g_quality) >= 4:
            baseCapability+=",http-streaming-video-320p,http-mp4-video-320p"
        if int(g_quality) >= 5:
            baseCapability+=",http-streaming-video-480p,http-mp4-video-480p"
        if int(g_quality) >= 6:
            baseCapability+=",http-streaming-video-720p,http-mp4-video-720p"
        if int(g_quality) >= 9:
            baseCapability+=",http-streaming-video-1080p,http-mp4-video-1080p"
            
        g_audioOutput=__settings__.getSetting("audiotype")         
        if g_audioOutput == "0":
            audio="mp3,aac"
        elif g_audioOutput == "1":
            audio="mp3,aac,ac3"
        elif g_audioOutput == "2":
            audio="mp3,aac,ac3,dts"
    
        global capability   
        capability="X-Plex-Client-Capabilities="+urllib.quote_plus("protocols="+baseCapability+";videoDecoders=h264{profile:high&resolution:1080&level:51};audioDecoders="+audio)              
        printDebug("Plex Client Capability = " + capability)
        
        import uuid
        global g_sessionID
        g_sessionID=str(uuid.uuid4())
    
def deleteMedia( url ): # CHECKED
    printDebug("== ENTER: deleteMedia ==", False)
    printDebug ("deleteing media at: " + url)
    
    return_value = xbmcgui.Dialog().yesno("Confirm file delete?","Delete this item? This action will delete media and associated data files.")

    if return_value:
        printDebug("Deleting....")
        installed = getURL(url,type="DELETE")    
        xbmc.executebuiltin("Container.Refresh")
    
    return True

##So this is where we really start the plugin.
printDebug( "PleXBMC -> Script argument is " + str(sys.argv[1]), False)

try:
    params=get_params(sys.argv[2])
except:
    params={}
        
#Now try and assign some data to them
param_url=params.get('url',None)
param_name=urllib.unquote_plus(params.get('name',""))
mode=int(params.get('mode',-1))
param_id=params.get('id',None)
param_transcodeOverride=int(params.get('transcode',0))
param_identifier=params.get('identifier',None)
_PARAM_TOKEN=params.get('X-Plex-Token',None)

if str(sys.argv[1]) == "skin":
    discoverAllServers()
    skin()
elif sys.argv[1] == "update":
    url=sys.argv[2]
    libraryRefresh(url)
elif sys.argv[1] == "watch":
    url=sys.argv[2]
    watched(url)
elif sys.argv[1] == "setting":
    __settings__.openSettings()
elif sys.argv[1] == "delete":
    url=sys.argv[2]
    deleteMedia(url)
elif sys.argv[1] == "refresh":
    xbmc.executebuiltin("Container.Refresh")
else:
   
    pluginhandle = int(sys.argv[1])
                    
    if g_debug == "true":
        print "PleXBMC -> Mode: "+str(mode)
        print "PleXBMC -> URL: "+str(param_url)
        print "PleXBMC -> Name: "+str(param_name)
        print "PleXBMC -> ID: "+ str(param_id)
        print "PleXBMC -> identifier: " + str(param_identifier)
        print "PleXBMC -> token: " + str(_PARAM_TOKEN)

    #Run a function based on the mode variable that was passed in the URL       
    if ( mode == None ) or ( param_url == None ) or ( len(param_url)<1 ):
        discoverAllServers()
        displaySections()
    elif mode == 0:
        getContent(param_url)
    elif mode == 1:
        TVShows(param_url)
    elif mode == 2:
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
        Movies(param_url)
    elif mode == 3:
        artist(param_url)
    elif mode == 4:
        TVSeasons(param_url)
    elif mode == 5:
        playLibraryMedia(param_id,param_url)
    elif mode == 6:
        TVEpisodes(param_url)
    elif mode == 7:
        PlexPlugins(param_url)
    elif mode == _MODE_PROCESSXML:
        processXML(param_url)
    elif mode == 12:
        PLAY(param_url)
    elif mode == 14:
        albums(param_url)
    elif mode == 15:
        tracks(param_url)
    elif mode == 16:
        photo(param_url)
    elif mode == 17:
        music(param_url)
    elif mode == 18:
        videoPluginPlay(param_url,param_identifier)
    elif mode == 19:
        plexOnline(param_url)
    elif mode == 20:
        install(param_url,param_name)
    elif mode == 21:
        channelView(param_url)
    elif mode == 22:
        discoverAllServers()
        displayServers(param_url)
    elif mode == 23:
        playLibraryMedia(param_id,param_url,override=True)
    elif mode == 24:
        myPlexQueue()

print "===== PLEXBMC STOP ====="
   
#clear done and exit.        
sys.modules.clear()

'''
    @document   : default.py
    @package    : PleXBMC Helper add-on
    @author     : Hippojay (aka Dave Hawes-Johnson)
    @copyright  : 2013, Hippojay
    @version    : 3.0 (frodo)

    @license    : Gnu General Public License - see LICENSE.TXT
    @description: pleXBMC XBMC add-on

    This file is part of the XBMC PleXBMC Helper Script.

    PleXBMC Helper Script is free software: you can redistribute it and/or modify
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

import time
import sys
import socket
import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
import inspect
import os
import uuid
import json

__settings__ = xbmcaddon.Addon(id='script.plexbmc.helper')
__cwd__ = __settings__.getAddonInfo('path')
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
PLUGINPATH=xbmc.translatePath( os.path.join( __cwd__) )
sys.path.append(BASE_RESOURCE_PATH)
PLEXBMC_VERSION="0.0.1"

import Bonjour
from listener import *

def printDebug( msg, functionname=True ):
    if g_debug == "true":
        if functionname is False:
            print str(msg)
        else:
            print "PleXBMC Helper -> " + inspect.stack()[1][3] + ": " + str(msg)

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


print "===== PLEXBMC HELPER START ====="

print "PleXBMC Helper -> running Python: " + str(sys.version_info)
print "PleXBMC Helper -> running Version: " + str(PLEXBMC_VERSION)

#Check debug first...
g_debug = __settings__.getSetting('debug')
g_enabled = __settings__.getSetting('enable') == "true"

g_client_name = __settings__.getSetting('c_name')
if not g_client_name:
    g_client_name="PleXBMC Client"
    
g_identifier = __settings__.getSetting('uuid')
if not g_identifier:
    g_identifier=str(uuid.uuid4())
    __settings__.setSetting('uuid',g_identifier)


PLEXBMC_PLATFORM=getPlatform()
print "PleXBMC Helper -> Platform: " + str(PLEXBMC_PLATFORM)
print "PleXBMC Helper -> Enabled: " + str(g_enabled)
print "PleXBMC Helper -> UUID: " + str(g_identifier)

#Get PleXBMC version for client notification string
addon_dependancy=json.dumps({"id" : "1", "jsonrpc": "2.0", "method":"Addons.GetAddonDetails", "params" : {"addonid" : "plugin.video.plexbmc", "properties" : ["version"]}})
return_data=xbmc.executeJSONRPC(addon_dependancy)
result=json.loads(return_data)

if result:
    if result.get('error'):
        print "PleXBMC addon [plugin.video.plexbmc] not installed"
        xbmc.executebuiltin("XBMC.Notification(PleXBMC Helper: PlEXBMC not installed,)")
        plexbmc_version=None
    elif result.get('result').get('addon').get('version'):
        plexbmc_version=result.get('result').get('addon').get('version')
    else:
        plexbmc_version="Unknown"
else:
    plexbmc_version="Unknown"

#Not required for newer Plex
#client = Bonjour.Bonjour(name="test server", port=3000, regtype="_plexclient._tcp")
#client.run()

mcast_address = '239.0.0.250'
mcast_port = 32413
httpd_port = 3000
is_running=False

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)

registration_string=""" * HTTP/1.0
Content-Type: plex/media-player
Resource-Identifier: %s
Name: %s
Port: %s
Product: PleXBMC
Version: %s

""" % ( g_identifier, g_client_name, httpd_port, plexbmc_version )

printDebug("PleXBMC Helper -> registeration string is: %s " % registration_string)

socket.setdefaulttimeout(10)
server_class = ThreadedHTTPServer
httpd = server_class(('', httpd_port), MyHandler)

message_count=0
while (not xbmc.abortRequested):

    if __settings__.getSetting('enable') == "true":
        try:
            sock.sendto('HELLO'+registration_string, (mcast_address, mcast_port))
            httpd.handle_request()
            message_count+=1
            
            if message_count > 5:
                printDebug( "PlexBMC Helper still running on port %s" % httpd_port )
                message_count=0
            
            if not is_running:
                print "PleXBMC Helper -> PleXBMC Helper has started"
                xbmc.executebuiltin("XBMC.Notification(PleXBMC Helper has started,)")
                
            is_running=True
            time.sleep(3)
        except:
            pass
    else:
        if is_running:
            print "PleXBMC Helper -> PleXBMC Helper has been suspended"
            xbmc.executebuiltin("XBMC.Notification(PleXBMC Helper has been suspended,)")
        is_running=False
        time.sleep(20)

sock.sendto('BYE'+registration_string, (mcast_address, mcast_port))
time.sleep(1)
print "PleXBMC Helper -> PleXBMC Helper has been stopped"
xbmc.executebuiltin("XBMC.Notification(PleXBMC Helper has been stopped,)")

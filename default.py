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

#Not required for newer Plex
#client = Bonjour.Bonjour(name="test server", port=3000, regtype="_plexclient._tcp")
#client.run()

mcast_address = '239.0.0.250'
mcast_port = 32413
httpd_port = 3000
is_running=False

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)

data=""" * HTTP/1.0
Content-Type: plex/media-player
Resource-Identifier: %s
Name: %s
Port: %s
Product: PleXBMC
Version: 3.0.4

""" % ( g_identifier, g_client_name, httpd_port )

socket.setdefaulttimeout(10)
server_class = ThreadedHTTPServer
httpd = server_class(('', httpd_port), MyHandler)

while (not xbmc.abortRequested):

    if __settings__.getSetting('enable') == "true":
        try:
            sock.sendto('HELLO'+data, (mcast_address, mcast_port))
            print "sending mcast and listening on port %s" % (httpd_port,)
            httpd.handle_request()
            if not is_running:
                xbmc.executebuiltin("XBMC.Notification(PleXBMC Helper has started,)")
            is_running=True
            time.sleep(3)
        except:
            pass
    else:
        if is_running:
            xbmc.executebuiltin("XBMC.Notification(PleXBMC Helper has been suspended,)")
        is_running=False
        time.sleep(20)

sock.sendto('BYE'+data, (mcast_address, mcast_port))
time.sleep(1)
xbmc.executebuiltin("XBMC.Notification(PleXBMC Helper has been stopped,)")

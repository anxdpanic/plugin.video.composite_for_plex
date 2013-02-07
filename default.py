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
from xml.dom.minidom import parseString

__settings__ = xbmcaddon.Addon(id='script.plexbmc.helper')
__cwd__ = __settings__.getAddonInfo('path')
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
PLUGINPATH=xbmc.translatePath( os.path.join( __cwd__) )
sys.path.append(BASE_RESOURCE_PATH)
PLEXBMC_VERSION="3.1.0"

from listener import *
import plexgdm

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

def getAddonSetting(doc,id):
    test = doc.getElementsByTagName(id)
    data = test[0].toxml()   
    return data.replace('<%s>' % id, '').replace('</%s>' % id,'').replace('<%s/>' % id, '')       
            
print "===== PLEXBMC HELPER START ====="

print "PleXBMC Helper -> running Python: " + str(sys.version_info)
print "PleXBMC Helper -> running Version: " + str(PLEXBMC_VERSION)

#Check debug first...
g_debug = __settings__.getSetting('debug')
g_gdm_debug = __settings__.getSetting('gdm_debug')

#Read XBMC guisettings.xml file
g_pguisettings = xbmc.translatePath('special://userdata/guisettings.xml')

try:
    fguisettings = open(g_pguisettings, 'r')
    data = fguisettings.read()
    fguisettings.close
    guisettings = parseString(data)
except:
    print "PleXBMC Helper -> Unable to read guisettings.xml - suggest you use custom settings"
    
g_use_xbmc = __settings__.getSetting('use_xbmc_name')

if g_use_xbmc == "false":    
    g_client_name = __settings__.getSetting('c_name')
    if not g_client_name:
        g_client_name="PleXBMC Client"
else:
        g_client_name=getAddonSetting(guisettings, 'devicename')
           
if __settings__.getSetting('use_xbmc_net') == "false":   
    g_xbmc_port = __settings__.getSetting('xbmcport')
    if not g_xbmc_port:
        g_xbmc_port=80
    print "PleXBMC Helper -> Platform: " + str(PLEXBMC_PLATFORM)
    g_xbmc_user = __settings__.getSetting('xbmcuser')
else:
    xbmc_webserver = getAddonSetting(guisettings, 'webserver')
    if xbmc_webserver == "false":
        print "PleXBMC Helper -> XBMC Web server not enabled"
        xbmc.executebuiltin("XBMC.Notification(PleXBMC Helper - XBMC web server not running,)")
    g_xbmc_port = getAddonSetting(guisettings, 'webserverport')
    g_xbmc_user = getAddonSetting(guisettings, 'webserverusername')
    
g_identifier = __settings__.getSetting('uuid')
if not g_identifier:
    g_identifier=str(uuid.uuid4())
    __settings__.setSetting('uuid',g_identifier)
    
PLEXBMC_PLATFORM=getPlatform()
print "PleXBMC Helper -> Platform: " + str(PLEXBMC_PLATFORM)
print "PleXBMC Helper -> UUID: " + str(g_identifier)
print "PleXBMC Helper -> XBMC Web Port: " + str(g_xbmc_port)
if g_xbmc_user:
    print "PleXBMC Helper -> XBMC Web User: " + str(g_xbmc_user)


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

httpd_port = 3000
is_running=False

client=plexgdm.plexgdm(debug=int(g_gdm_debug))
client.clientDetails(g_identifier, g_client_name, httpd_port, "PleXBMC" , plexbmc_version)

printDebug("PleXBMC Helper -> registeration string is: %s " % client.getClientDetails() )

socket.setdefaulttimeout(10)
server_class = ThreadedHTTPServer

try:
    httpd = server_class(('', httpd_port), MyHandler)
except:
    print "PleXBMC Helper -> Cannot start helper server as the port 3000 is already in use"
    xbmc.executebuiltin("XBMC.Notification(PleXBMC Helper - Helper Web unable to start due to port clash,)")
    
client.start_all()

message_count=0
while (not xbmc.abortRequested):
    try:
        
        httpd.handle_request()
        message_count+=1
        
        if message_count > 2:
            if client.check_client_registration():
                printDebug("Client is still registered")
            else:
                printDebug("Client is no longer registered")
            printDebug( "PlexBMC Helper still running on port %s" % httpd_port )
            message_count=0
        
        if not is_running:
            print "PleXBMC Helper -> PleXBMC Helper has started"
            xbmc.executebuiltin("XBMC.Notification(PleXBMC Helper has started,)")
            
        is_running=True
    except:
        printDebug("Error in loop")
        time.sleep(3)   #Stop error loops from running away

        
client.stop_all()
print "PleXBMC Helper -> PleXBMC Helper has been stopped"
xbmc.executebuiltin("XBMC.Notification(PleXBMC Helper has been stopped,)")

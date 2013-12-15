'''
    @document   : default.py
    @package    : PleXBMC Helper add-on
    @author     : wickning (aka Nick Wing)
    @copyright  : 2013, wickning1
    @version    : 3.2.0 (frodo)

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
# system includes
import sys
import socket
import xbmc
import xbmcaddon
import os

# vitals
__addon__      = xbmcaddon.Addon()
__cwd__        = __addon__.getAddonInfo('path')
__version__    = __addon__.getAddonInfo('version')
__profile__    = xbmc.translatePath( __addon__.getAddonInfo('profile') )
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )

# local includes
sys.path.append (__resource__)
from settings import *
from functions import *
from subscribers import *
from listener import *
import plexgdm

print "===== PLEXBMC HELPER START ====="
print "PleXBMC Helper -> running Python: " + str(sys.version_info)
print "PleXBMC Helper -> running Version: " + __version__
print "PleXBMC Helper -> Platform: " + getPlatform()
print "PleXBMC Helper -> UUID: " + getSettings('uuid')
print "PleXBMC Helper -> XBMC Web Port: %i" % getSettings('port')
if getSettings('user'):
    print "PleXBMC Helper -> XBMC Web User: " + getSettings('user')

if not getPlexbmcVersion():
    xbmc.executebuiltin("XBMC.Notification(PleXBMC Helper: PleXBMC not installed.)")

httpd_port=3005

# Start GDM for server/client discovery
client=plexgdm.plexgdm(debug=getSettings('gdm_debug'))
client.clientDetails(getSettings('uuid'), getSettings('client_name'), httpd_port, "PleXBMC" , getPlexbmcVersion())
printDebug("PleXBMC Helper -> registration string is: %s " % client.getClientDetails() )

start_count=0
while True:
    try:
        httpd = ThreadedHTTPServer(('', httpd_port), MyHandler)
        httpd.timeout = 1.0
        break
    except:
        print "PleXBMC Helper -> Unable to start web helper.  Sleep and Retry..."
        __addon__.setSetting("replacement", "true")
    
    xbmc.sleep(3000)

    if start_count == 3:
        print "PleXBMC Helper -> Unable to start web helper. Giving up."
        xbmc.executebuiltin("XBMC.Notification(PleXBMC Helper - Helper Web unable to start due to port clash,)")
        httpd = False
        break
    
    start_count += 1

if httpd:
    client.start_all()
    __addon__.setSetting("replacement", "false")
    message_count=0
    is_running=False
    while (not xbmc.abortRequested and __addon__.getSetting("replacement") != "true"):
        try:
            
            httpd.handle_request()
            message_count+=1
            
            if message_count > 20:
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
            #if message_count % 4:
            #    getSubMgr().notify()
            setSettings('serverList', client.getServerList())
        except:
            printDebug("Error in loop")
            break
    
    httpd.socket.close()
    client.stop_all()
    print "PleXBMC Helper -> PleXBMC Helper has been stopped"
    xbmc.executebuiltin("XBMC.Notification(PleXBMC Helper has been stopped,)")

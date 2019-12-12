'''
    @document   : default.py
    @package    : PleXBMC Helper add-on
    @author     : wickning1 (aka Nick Wing)
    @author     : hippojay (aka Dave Hawes-Johnson)
    @copyright  : 2013, wickning1
    @version    : 3.2.0 (frodo)

    @license    : Gnu General Public License - see LICENSE.TXT
    @description: pleXBMC Helper XBMC add-on

    This is a significant overhaul of the plugin originally developed by
    Hippojay (https://github.com/hippojay/script.plexbmc.helper).

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
import traceback
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

from settings import settings
from httppersist import requests
from functions import *
from subscribers import subMgr
from listener import *
import plexgdm

print "===== PLEXBMC HELPER START ====="
print "PleXBMC Helper -> running Python: " + str(sys.version_info)
print "PleXBMC Helper -> running Version: " + __version__
print "PleXBMC Helper -> Platform: " + getPlatform()
print "PleXBMC Helper -> UUID: " + settings['uuid']

if not settings.get('plexbmc_version', False):
    xbmc.executebuiltin("XBMC.Notification(PleXBMC Helper: PleXBMC not installed,)")
else:
    # Start GDM for server/client discovery
    client=plexgdm.plexgdm(debug=settings['gdm_debug'])
    client.clientDetails(settings['uuid'], settings['client_name'], settings['myport'], "PleXBMC" , settings.get('plexbmc_version', '1.0'))
    printDebug("PleXBMC Helper -> registration string is: %s " % client.getClientDetails() )
    
    start_count=0
    while True:
        try:
            httpd = ThreadedHTTPServer(('', settings['myport']), MyHandler)
            httpd.timeout = 0.95
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
                
                if message_count > 30:
                    if client.check_client_registration():
                        printDebug("Client is still registered")
                    else:
                        printDebug("Client is no longer registered")
                    printDebug( "PlexBMC Helper still running on port %s" % settings['myport'])
                    message_count=0
                
                if not is_running:
                    print "PleXBMC Helper -> PleXBMC Helper has started"
                    xbmc.executebuiltin("XBMC.Notification(PleXBMC Helper has started,)")
                    
                is_running=True
                if message_count % 1 == 0:
                    subMgr.notify()
                settings['serverList'] = client.getServerList()
            except:
                printDebug("Error in loop, continuing anyway")
                print traceback.print_exc()
        
        try:
            httpd.socket.shutdown(socket.SHUT_RDWR)
        finally:
            httpd.socket.close()
        requests.dumpConnections()
        client.stop_all()
        print "PleXBMC Helper -> PleXBMC Helper has been stopped"
        xbmc.executebuiltin("XBMC.Notification(PleXBMC Helper has been stopped,)")

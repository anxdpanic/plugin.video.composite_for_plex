import uuid
import xbmc
import xbmcaddon
from xml.dom.minidom import parse

settings = {}
try:
    guidoc = parse(xbmc.translatePath('special://userdata/guisettings.xml'))
except:
    print "Unable to read XBMC's guisettings.xml"    

def get_kodi_setting(name):
    global guidoc
    if guidoc is None:
        return False
    try:
        return guidoc.getElementsByTagName(name)[0].firstChild.nodeValue
    except:
        return ""

addon = xbmcaddon.Addon()

settings['debug'] = addon.getSetting('debug') == "true"
settings['gdm_debug'] = addon.getSetting('gdm_debug') == "true"
if addon.getSetting('use_xbmc_name') == "true":
    settings['client_name'] = get_kodi_setting('devicename')
else:
    settings['client_name'] = addon.getSetting('devicename')
# KODI web server settings
settings['webserver_enabled'] = (get_kodi_setting('webserver') == "true")
settings['port'] = int(get_kodi_setting('webserverport'))
settings['user'] = get_kodi_setting('webserverusername')
settings['passwd'] = get_kodi_setting('webserverpassword')

settings['uuid'] = str(addon.getSetting('client_id')) or str(uuid.uuid4())
addon.setSetting('uuid', settings['client_id'])
settings['version'] = addon.getAddonInfo('version')
settings['plexbmc_version'] = addon.getAddonInfo('version')
settings['myplex_user'] = addon.getSetting('myplex_user')
settings['serverList'] = []
settings['myport'] = 3005

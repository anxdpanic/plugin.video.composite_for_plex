import uuid
import xbmc
import xbmcaddon
from xml.dom.minidom import parse

settings = {}
try:
    guidoc = parse(xbmc.translatePath('special://userdata/guisettings.xml'))
except:
    print "Unable to read XBMC's guisettings.xml"    

def getGUI(name):
    global guidoc
    if guidoc is None:
        return False
    return guidoc.getElementsByTagName(name)[0].nodeValue
    return False

addon = xbmcaddon.Addon()
plexbmc = xbmcaddon.Addon('plugin.video.plexbmc')

settings['debug'] = addon.getSetting('debug') == "true"
settings['gdm_debug'] = int(addon.getSetting('gdm_debug'))
if addon.getSetting('use_xbmc_name'):
    settings['client_name'] = getGUI('devicename')
else:
    settings['client_name'] = addon.getSetting('c_name')
settings['uuid'] = str(addon.getSetting('uuid')) or str(uuid.uuid4())
addon.setSetting('uuid', settings['uuid'])
settings['version'] = addon.getAddonInfo('version')
settings['myplex_user'] = plexbmc.getSetting('myplex_user')
settings['serverList'] = []
settings['myport'] = 3005

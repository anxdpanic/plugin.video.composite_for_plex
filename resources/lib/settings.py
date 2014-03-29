import uuid
import xbmc
import xbmcaddon
from xml.dom.minidom import parseString

settings = {}     
guidoc = False   
try:
    guifile = open(xbmc.translatePath('special://userdata/guisettings.xml'), 'r')
    guidoc = parseString(guifile.read())
    guifile.close()
except:
    print "Unable to read XBMC's guisettings.xml"

def getGUI(name, within=False):
    global guidoc
    if not guidoc:
        return False
    parent = guidoc
    if within:
        parent = guidoc.getElementsByTagName(within)[0]
    return parent.getElementsByTagName(name)[0].toxml().replace('<%s>' % name, '').replace('</%s>' % name,'').replace('<%s/>' % name, '')

addon = xbmcaddon.Addon()
plexbmc = xbmcaddon.Addon('plugin.video.plexbmc')

settings['webserver_enabled'] = (getGUI('webserver') == "true")
if addon.getSetting('use_xbmc_net') == "false":
    settings['port'] = int(addon.getSetting('xbmcport')) or 80
    settings['user'] = addon.getSetting('xbmcuser')
    settings['passwd'] = addon.getSetting('xbmcpass')
else:
    settings['port'] = int(getGUI('webserverport'))
    settings['user'] = getGUI('webserverusername')
    settings['passwd'] = getGUI('webserverpassword')
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
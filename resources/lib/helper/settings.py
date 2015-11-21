import uuid
import xbmc
import xbmcaddon
from resources.lib.common import *  # Needed first to setup import locations

settings = {}
addon = xbmcaddon.Addon()

#settings['debug'] = addon.getSetting('debug') == "true"
#settings['gdm_debug'] = addon.getSetting('gdm_debug') == "true"
#if addon.getSetting('use_xbmc_name') == "true":
#    settings['client_name'] = get_kodi_setting('devicename')
#else:
#    settings['client_name'] = addon.getSetting('devicename')
# KODI web server settings
#settings['webserver_enabled'] = (get_kodi_setting('webserver') == "true")
#settings['port'] = int(get_kodi_setting('webserverport'))
#settings['user'] = get_kodi_setting('webserverusername')
#settings['passwd'] = get_kodi_setting('webserverpassword')

#settings['uuid'] = str(addon.getSetting('client_id')) or str(uuid.uuid4())
#addon.setSetting('uuid', settings['client_id'])
#settings['version'] = addon.getAddonInfo('version')
#settings['plexbmc_version'] = addon.getAddonInfo('version')
#settings['myplex_user'] = addon.getSetting('myplex_user')
#settings['serverList'] = []
#settings['myport'] = 3005

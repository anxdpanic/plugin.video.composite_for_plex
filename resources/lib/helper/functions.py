import base64
import inspect
import json
import string

import xbmc
from resources.lib.helper.settings import settings
import resources.lib.CacheControl as CacheControl
from resources.lib.helper.httppersist import requests
from resources.lib.common import *
from resources.lib.plex.plex import Plex

log_print = PrintDebug("PleXBMC Helper", "functions")

helper_cache = CacheControl.CacheControl(GLOBAL_SETUP['__cachedir__']+"cache/servers", settings.get_setting('cache'))
helper_cache_name = "helper_server_list"

def xbmc_photo():
    return "photo"
def xbmc_video():
    return "video"
def xbmc_audio():
    return "audio"

def plex_photo():
    return "photo"
def plex_video():
    return "video"
def plex_audio():
    return "music"

def xbmc_type(plex_type):
    if plex_type == plex_photo():
        return xbmc_photo()
    elif plex_type == plex_video():
        return xbmc_video()
    elif plex_type == plex_audio():
        return xbmc_audio()
        
def plex_type(xbmc_type):
    if xbmc_type == xbmc_photo():
        return plex_photo()
    elif xbmc_type == xbmc_video():
        return plex_video()
    elif xbmc_type == xbmc_audio():
        return plex_audio()


""" communicate with XBMC """
def jsonrpc(action, arguments = {}):
    """ put some JSON together for the JSON-RPC APIv6 """
    if action.lower() == "sendkey":
        request=json.dumps({ "jsonrpc" : "2.0" , "method" : "Input.SendText", "params" : { "text" : self.arguments[0], "done" : False }} )
    elif action.lower() == "ping":
        request=json.dumps({ "jsonrpc" : "2.0",
                             "id" : 1 ,
                             "method"  : "JSONRPC.Ping" })
    elif action.lower() == "playmedia":
        fullurl=arguments[0]
        resume=arguments[1]
        xbmc.Player().play("plugin://plugin.video.plexbmc/?mode=5&force="+resume+"&url="+fullurl+"&helper=1")
        return True
    elif arguments:
        request=json.dumps({ "id" : 1,
                             "jsonrpc" : "2.0",
                             "method"  : action,
                             "params"  : arguments})
    else:
        request=json.dumps({ "id" : 1,
                             "jsonrpc" : "2.0",
                             "method"  : action})
    
    # log_print.debug_helper("Sending request to XBMC without network stack: %s" % request)
    result = parseJSONRPC(xbmc.executeJSONRPC(request))

    if not result and settings.get_kodi_setting('webserver_enabled'):
        # xbmc.executeJSONRPC appears to fail on the login screen, but going
        # through the network stack works, so let's try the request again
        result = parseJSONRPC(requests.post(
            "127.0.0.1",
            settings.get_kodi_setting('port'),
            "/jsonrpc",
            request,
            { 'Content-Type' : 'application/json',
              'Authorization' : 'Basic ' + string.strip(base64.encodestring(settings.get_kodi_setting('user') + ':' + settings.get_kodi_setting('passwd')))}))

    return result



def parseJSONRPC(jsonraw):
    if not jsonraw:
        # log_print.debug_helper("Empty response from XBMC")
        return {}
    else:
        # log_print.debug_helper("Response from XBMC: %s" % jsonraw)
        parsed=json.loads(jsonraw)
    if parsed.get('error', False):
        print "XBMC returned an error: %s" % parsed.get('error')
    return parsed.get('result', {})

def getXMLHeader():
    return '<?xml version="1.0" encoding="utf-8"?>'+"\r\n"

def getOKMsg():
    return getXMLHeader() + '<Response code="200" status="OK" />'

def getPlexHeaders():
    plex_network = Plex(load=False)
    h = {
      "Content-type": "application/x-www-form-urlencoded",
      "Access-Control-Allow-Origin": "*",
      "X-Plex-Version": GLOBAL_SETUP['__version__'],
      "X-Plex-Client-Identifier": settings.get_setting('client_id'),
      "X-Plex-Provides": "player",
      "X-Plex-Product": "PleXBMC",
      "X-Plex-Device-Name": settings.get_setting('devicename'),
      "X-Plex-Platform": "XBMC",
      "X-Plex-Model": get_platform(),
      "X-Plex-Device": "PC",
    }
    if plex_network.get_myplex_user():
        h["X-Plex-Username"] = plex_network.get_myplex_user()
    return h

def getServerByHost(host):
    validate, list = helper_cache.check_cache(helper_cache_name)
    log_print.debug_helper("Helper has loaded a server list:")
    if len(list) == 1:
        return list[0]
    for server in list:
        if server.get('serverName') in host or server.get('server') in host:
            return server
    return {}
    
def getPlayers():
    info = jsonrpc("Player.GetActivePlayers") or []
    ret = {}
    for player in info:
        player['playerid'] = int(player['playerid'])
        ret[player['type']] = player
    return ret
    
def getPlayerIds():
    ret = []
    for player in getPlayers().values():
        ret.append(player['playerid'])
    return ret
    
def getVideoPlayerId(players = False):
    if players is None:
        players = getPlayers()
    return players.get(xbmc_video(), {}).get('playerid', None)

def getAudioPlayerId(players = False):
    if players is None:
        players = getPlayers()
    return players.get(xbmc_audio(), {}).get('playerid', None)

def getPhotoPlayerId(players = False):
    if players is None:
        players = getPlayers()
    return players.get(xbmc_photo(), {}).get('playerid', None)
    
def getVolume():
    return str(jsonrpc('Application.GetProperties', { "properties": [ "volume" ] }).get('volume', 100))

def timeToMillis(time):
    return (time['hours']*3600 + time['minutes']*60 + time['seconds'])*1000 + time['milliseconds']

def millisToTime(t):
    millis = int(t)
    seconds = millis / 1000
    minutes = seconds / 60
    hours = minutes / 60
    seconds = seconds % 60
    minutes = minutes % 60
    millis = millis % 1000
    return {'hours':hours,'minutes':minutes,'seconds':seconds,'milliseconds':millis}

def textFromXml(element):
    return element.firstChild.data

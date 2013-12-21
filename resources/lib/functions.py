import base64
import inspect
import json
import platform
import requests
import string
import sys
import traceback
import uuid
import xbmc
import xbmcaddon
from settings import settings

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

def getPlatform():
    if xbmc.getCondVisibility('system.platform.osx'):
        return "MacOSX"
    elif xbmc.getCondVisibility('system.platform.atv2'):
        return "AppleTV2"
    elif xbmc.getCondVisibility('system.platform.ios'):
        return "iOS"
    elif xbmc.getCondVisibility('system.platform.windows'):
        return "Windows"
    elif xbmc.getCondVisibility('system.platform.raspberrypi'):
        return "RaspberryPi"
    elif xbmc.getCondVisibility('system.platform.linux'):
        return "Linux"
    elif xbmc.getCondVisibility('system.platform.android'): 
        return "Android"
    return "Unknown"
    
def printDebug( msg, functionname=True ):
    if settings['debug']:
        if functionname is False:
            print str(msg)
        else:
            print "PleXBMC Helper -> " + inspect.stack()[1][3] + ": " + str(msg)
            

rsess = requests.Session()
def http_post(host, port, path, body, header={}, protocol="http"):
    try:
        conn = rsess.post(url=protocol+'://'+host+':'+str(port)+path, data=body, headers=header)
        if int(conn.status_code) >= 400:
            print "HTTP response error: " + str(conn.status_code)
            # this should return false, but I'm hacking it since iOS returns 404 no matter what
            return conn.text or True
        else:      
            return conn.text or True
    except:
        print "Unable to connect to %s\nReason: %s" % (host, traceback.print_exc())
        return False
        
def http_get(host, port, path, header={}, protocol="http"):
    try:
        url = protocol+'://'+host+':'+port+path
        conn = rsess.get(url=url, headers=header)
        if int(conn.status_code) >= 400:
            print "HTTP response error: " + str(conn.status_code)
            return False
        else:      
            return conn.text or True
    except:
        print "Unable to connect to %s\nReason: %s" % (url, traceback.print_exc())
        return False

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
        request=json.dumps({ "id"      : 1,
                             "jsonrpc" : "2.0",
                             "method"  : "Player.Open",
                             "params"  : { "item"  :  {"file":"plugin://plugin.video.plexbmc/?mode=5&force="+resume+"&url="+fullurl } } })
    elif arguments:
        request=json.dumps({ "id" : 1,
                             "jsonrpc" : "2.0",
                             "method"  : action,
                             "params"  : arguments})
    else:
        request=json.dumps({ "id" : 1,
                             "jsonrpc" : "2.0",
                             "method"  : action})
    
    printDebug("Sending request to XBMC: %s" % request)
    jsonraw = http_post(
        "127.0.0.1", 
        settings['port'], 
        "/jsonrpc", 
        request, 
        { 'Content-Type' : 'application/json',
          'Authorization' : 'Basic ' + string.strip(base64.encodestring(settings['user'] + ':' + settings['passwd'])) })
                
    """ parse the request """
    if not jsonraw:
        printDebug("Empty response from XBMC")
        return False
    else:
        printDebug("Response from XBMC: %s" % jsonraw)
        parsed=json.loads(jsonraw)
        
    if parsed.get('error', False):
        print "XBMC returned an error: %s" % parsed.get('error')                

    return parsed.get('result', False)

def getXMLHeader():
    return '<?xml version="1.0" encoding="utf-8"?>'+"\r\n"

def getOKMsg():
    return getXMLHeader() + '<Response code="200" status="OK" />'

def getPlexHeaders():
    h = {
      "Content-type": "application/x-www-form-urlencoded",
      "Access-Control-Allow-Origin": "*",
      "X-Plex-Version": settings['version'],
      "X-Plex-Client-Identifier": settings['uuid'],
      "X-Plex-Provides": "player",
      "X-Plex-Product": "PleXBMC",
      "X-Plex-Device-Name": settings['client_name'],
      "X-Plex-Platform": "XBMC",
      "X-Plex-Model": getPlatform(),
      "X-Plex-Device": "PC",
    }
    if settings['myplex_user']:
        h["X-Plex-Username"] = settings['myplex_user']
    return h

def getServerByHost(host):
    list = settings['serverList']
    if len(list) == 1:
        return list[0]
    for server in list:
        if server.get('serverName') == host or server.get('server') == host:
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
    return players.get(xbmc_video(), {}).get('playerid', 0)

def getAudioPlayerId(players = False):
    if players is None:
        players = getPlayers()
    return players.get(xbmc_audio(), {}).get('playerid', 0)

def getPhotoPlayerId(players = False):
    if players is None:
        players = getPlayers()
    return players.get(xbmc_photo(), {}).get('playerid', 0)
    
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
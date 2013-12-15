import base64
import httplib
import inspect
import json
import platform
import string
import sys
import uuid
import xbmc
import xbmcaddon
from settings import *

plexbmc_version = False
def getPlexbmcVersion():
    global plexbmc_version
    if not plexbmc_version:
        plexbmc_version = jsonrpc("Addons.GetAddonDetails", {"addonid" : "plugin.video.plexbmc", "properties" : ["version"]})['addon']['version']
    return plexbmc_version

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
    if getSettings('debug'):
        if functionname is False:
            print str(msg)
        else:
            print "PleXBMC Helper -> " + inspect.stack()[1][3] + ": " + str(msg)
            

def http_post(host, port, path, body, header={}):
    try:        
        conn = httplib.HTTPConnection(host, port) 
        conn.request("POST", path, body, header) 
        data = conn.getresponse()
        if int(data.status) >= 400:
            print "HTTP response error: " + str(data.status) + " " + str(data.reason)
            return False
        else:      
            return data.read()
    except:
        print "Unable to connect to %s\nReason: %s" % (host, sys.exc_info()[0])
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
        getSettings('port'), 
        "/jsonrpc", 
        request, 
        { 'Content-Type' : 'application/json',
          'Authorization' : 'Basic ' + string.strip(base64.encodestring(getSettings('user') + ':' + getSettings('passwd'))) })
                
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

def getServerByHost(host):
    list = getSettings('serverList')
    if len(list) == 1:
        return list[0]
    for server in list:
        if server.get('serverName') == host or server.get('server') == host:
            return server
    return {}
    
def getPlayers():
    info = jsonrpc("Player.GetActivePlayers") or []
    ret = []
    for player in info:
        printDebug("found active %s player with id %i" % (player['type'], player['playerid']))
        player['playerid'] = int(player['playerid'])
        ret.append(player)
    return ret
    
def getPlayerIds():
    ret = []
    for player in getPlayers():
        ret.append(player['playerid'])
    return ret
    
def getVideoPlayerId():
    for player in getPlayers():
        if player['type'].lower() == "video":
            return player['playerid']
    return 0

def getAudioPlayerId():
    for player in getPlayers():
        if player['type'].lower() == "audio":
            return player['playerid']
    return 0

def getPicturePlayerId():
    for player in getPlayers():
        if "picture" in player['type'].lower():
            return player['playerid']
    return 0
    
def getVolume():
    return str(jsonrpc('Application.GetProperties', { "properties": [ "volume" ] }))

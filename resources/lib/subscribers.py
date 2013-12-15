import re
import threading
from functions import *
from settings import *

class SubscriptionManager:
    def __init__(self):
        self.subscribers = []
        self.info = {}

    def msg(self, sub):
        msg = "<MediaContainer commandID=\"%s\"" % sub.commandID
        if not self.info:
            # we must not be playing a video
            msg += " location=\"navigation\">"
            msg += "<Timeline controllable=\"%s\" />" % self.controllable()

        else:
            msg += " location=\"fullScreenVideo\">"
            msg += "<Timeline controllable=\"%s\"" % self.controllable()
            msg += " state=\"%s\"" % self.info['state']
            #msg += " key=\"%s\"" % self.info['key']
            msg += " time=\"%i\"" % self.info['time']
            msg += " duration=\"%i\"" % self.info['duration']
            msg += " volume=\"%s\"" % self.info['volume']
            msg += " />"
        msg += "</MediaContainer>"
        return msg

    def notify(self, action=""):
        if not self.subscribers:
            return True
        self.generateVideoInfo()
        with threading.RLock():
            for sub in self.subscribers:
                sub.send_update(self.msg(sub))
        return True
        
    def controllable(self):
        return "playPause,play,stop,skipPrevious,skipNext,volume,stepBack,stepForward,seekTo"
        
    def addSubscriber(self, host, port, id):
        sub = Subscriber(host, port, id)
        with threading.RLock():
            if sub not in self.subscribers:
                self.subscribers.append(sub)
        return sub
        
    def removeSubscriber(self, host, id):
        with threading.RLock():
            self.subscribers.remove(Subscriber(host, commandID=id))
            
    def generateVideoInfo(self):
        videoid = getVideoPlayerId()
        if videoid == 0:
            self.info = {}
            return
        
        # get info from the player
        props = jsonrpc("Player.GetProperties", {"playerid": videoid, "properties": ["percentage", "totaltime", "speed"]})
        duration = props['totaltime']['hours']*3600 + props['totaltime']['minutes']*60 + props['totaltime']['seconds']
        self.info = { "time": int(float(props['percentage'])*duration/100.0), "duration": duration }
        self.info['volume'] = getVolume()
        self.info['state'] = ("paused", "playing")[int(props['speed'])]
        
        # get info from the item in the player
        #props = jsonrpc("Player.GetItem", {"playerid": videoid, "properties": ["file"]})['item']
        #m = re.match(r"(/library/metadata/\d+)", props['file'])
        #self.info['key'] = m[1]

class Subscriber:
    def __init__(self, host, port=32400, commandID=0):
        self.host = str(host)
        self.port = str(port)
        self.commandID = str(commandID)
    def __eq__(self, other):
        return self.host == other.host and (self.commandID == other.commandID or self.commandID == 0)
    def tostr(self):
        return "%s:%s/timeline?commandID=%s" % (self.host, self.port, self.commandID)
    def send_update(self, msg):
        printDebug("sending xml to subscriber %s: %s" % (self.tostr(), msg))
        if not http_post(self.host, self.port, "/:/timeline", msg, self.headers()):
            getSubMgr().removeSubscriber(self.host, self.commandID)
    def headers(self):
        h = {
          "X-Plex-Version": getSettings('version'),
          "X-Plex-Client-Identifier": getSettings('uuid'),
          "X-Plex-Provides": "player",
          "X-Plex-Product": "PleXBMC",
          "X-Plex-Device-Name": getSettings('client_name'),
          "X-Plex-Platform": "XBMC",
          "X-Plex-Model": getPlatform(),
          "X-Plex-Device": getPlatform(),
          "X-Plex-Client-Capabilities": self.capabilities()
        }
        if getSettings('myplex_user'):
            h["X-Plex-Username"] = getSettings('myplex_user')
        return h
    def capabilities(self):
        protocols = "protocols=shoutcast,http-video;videoDecoders=h264{profile:high&resolution:1080&level:51};audioDecoders=mp3,aac"
        audiomode = int(getGUI('mode', within='audiooutput'))
        if audiomode == 1 or audiomode == 2:
            if getGUI('dtspassthrough', within='audiooutput') == "true":
                protocols += ",dts{bitrate:800000&channels:8}"
            if getGUI('ac3passthrough', within='audiooutput') == "true":
                protocols += ",ac3{bitrate:800000&channels:8}"
        return protocols
        
subMgr = SubscriptionManager()
def getSubMgr():
    global subMgr
    return subMgr
    

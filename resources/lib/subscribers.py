import re
import threading
from functions import *
from settings import *

class SubscriptionManager:
    def __init__(self):
        self.subscribers = {}
        self.info = {}
        self.lastkey = ""

    def msg(self, sub):
        msg = getXMLHeader()
        msg += "<MediaContainer commandID=\"%s\"" % sub.commandID
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

    def notify(self):
        if not self.subscribers:
            return True
        self.generateVideoInfo()
        with threading.RLock():
            for sub in self.subscribers.values():
                sub.send_update(self.msg(sub))
        return True
        
    def controllable(self):
        return "playPause,play,stop,skipPrevious,skipNext,volume,stepBack,stepForward,seekTo"
        
    def addSubscriber(self, protocol, host, port, uuid, commandID, poller=False):
        sub = Subscriber(protocol, host, port, uuid, commandID, poller)
        with threading.RLock():
            self.subscribers[sub.uuid] = sub
        return sub
                
    def removeSubscriber(self, uuid):
        with threading.RLock():
            for sub in self.subscribers.values():
                if sub.uuid == uuid or sub.host == uuid:
                    del self.subscribers[sub.uuid]
            
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
    def __init__(self, protocol, host, port, uuid, commandID, poller=False):
        self.protocol = protocol or "http"
        self.host = host
        self.port = port or 32400
        self.uuid = uuid or host
        self.commandID = int(commandID) or 0
        self.poller = poller
    def __eq__(self, other):
        return self.uuid == other.uuid
    def tostr(self):
        return "uuid=%s,commandID=%i" % (self.uuid, self.commandID)
    def send_update(self, msg):
        printDebug("sending xml to subscriber %s: %s" % (self.tostr(), msg))
        if not http_post(self.host, self.port, "/:/timeline", msg, getPlexHeaders(), self.protocol):
            getSubMgr().removeSubscriber(self.uuid)

subMgr = SubscriptionManager()
def getSubMgr():
    global subMgr
    return subMgr
    

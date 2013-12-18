import re
import threading
import xbmc
from xml.dom.minidom import parseString
from functions import *
from settings import settings

class SubscriptionManager:
    def __init__(self):
        self.subscribers = {}
        self.info = {}
        self.lastkey = ""
        self.volume = 0
        self.guid = ""
        self.server = ""
        self.protocol = "http"
        self.port = ""
        
    def getVolume(self):
        self.volume = getVolume()

    def msg(self):
        self.getVolume()
        players = getPlayers()
        msg = getXMLHeader()
        msg += '<MediaContainer commandID="INSERTCOMMANDID"'
        if players:
            maintype = plex_audio()
            for p in players.values():
                if p.get('type') == xbmc_video():
                    maintype = plex_video()
                elif p.get('type') == xbmc_photo():
                    maintype = plex_photo()
            self.mainlocation = "fullScreen" + maintype[0:1].upper() + maintype[1:].lower()
        else:
            self.mainlocation = "navigation"
        msg += ' location="%s">' % self.mainlocation
       
        msg += self.getTimelineXML(getAudioPlayerId(players), plex_audio())
        msg += self.getTimelineXML(getPhotoPlayerId(players), plex_photo())
        msg += self.getTimelineXML(getVideoPlayerId(players), plex_video())
        msg += "</MediaContainer>"
        return msg
        
    def getTimelineXML(self, playerid, ptype):
        if playerid > 0:
            info = self.getPlayerProperties(playerid)
            state = info['state']
            time = info['time']
        else:
            state = "stopped"
            time = 0
        ret = '<Timeline location="%s" state="%s" time="%s" type="%s"' % (self.mainlocation, state, time, ptype)
        if playerid > 0:
            ret += ' duration="%s"' % info['duration']
            ret += ' seekRange="0-%s"' % info['duration']
            ret += ' controllable="%s"' % self.controllable()
            ret += ' machineIdentifier="%s"' % settings['uuid']
            ret += ' protocol="%s"' % self.protocol
            ret += ' address="%s"' % self.server
            ret += ' port="%s"' % self.port
            ret += ' guid="%s"' % info['guid']
            ret += ' containerKey="%s"' % self.lastkey
            ret += ' key="%s"' % self.lastkey
            m = re.search(r'(\d+)$', self.lastkey)
            if m:
                ret += ' ratingKey="%s"' % m.group()
            ret += ' volume="%s"' % info['volume']
            ret += ' shuffle="%s"' % info['shuffle']
        
        ret += '/>'
        return ret
 
    def lookup(self, server, port):
        rawxml = http_get(server, port, self.lastkey)
        if rawxml:
          doc = parseString(rawxml)
          self.guid = doc.getElementsByTagName('Video')[0].getAttribute('guid')
          self.protocol = "http"
          self.server = server
          self.port = port
    
    def notify(self):
        if not self.subscribers:
            return True
        msg = self.msg()
        with threading.RLock():
            for sub in self.subscribers.values():
                sub.send_update(msg)
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
            
    def getPlayerProperties(self, playerid):
        info = {}
        try:
            # get info from the player
            props = jsonrpc("Player.GetProperties", {"playerid": playerid, "properties": ["time", "totaltime", "speed", "shuffled"]})
            info['time'] = timeToMillis(props['time'])
            info['duration'] = timeToMillis(props['totaltime'])
            info['state'] = ("paused", "playing")[int(props['speed'])]
            info['shuffle'] = ("0","1")[props.get('shuffled', False)]            
        except:
            info['time'] = 0
            info['duration'] = 0
            info['state'] = "stopped"
            info['shuffle'] = False
        # get the volume from the application
        info['volume'] = self.volume
        info['guid'] = self.guid

        return info

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
        msg = re.sub(r"INSERTCOMMANDID", str(self.commandID), msg)
        printDebug("sending xml to subscriber %s: %s" % (self.tostr(), msg))
        if not http_post(self.host, self.port, "/:/timeline", msg, getPlexHeaders(), self.protocol):
            subMgr.removeSubscriber(self.uuid)

subMgr = SubscriptionManager()    

import re
import socket
import traceback
from SocketServer import ThreadingMixIn
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from urlparse import urlparse, parse_qs
from functions import *
from subscribers import *

class MyHandler(BaseHTTPRequestHandler):
    def do_HEAD(s):
        printDebug( "Serving HEAD request..." )
        s.answer_request(0)

    def do_GET(s):
        printDebug( "Serving GET request..." )
        s.answer_request(1)

    def answer_request(s, sendData):
        try:
            request_path=s.path[1:]
            request_path=re.sub(r"\?.*","",request_path)
            printDebug ( "request path is: [%s]" % ( request_path,) )
            printDebug ( "request headers: %s" % s.headers )
            if request_path=="version":
                s.wfile.write("PleXBMC Helper Remote Redirector: Running\r\n")
                s.wfile.write("Version: 0.1")
            elif request_path=="verify":
                print "PleXBMC Helper -> listener -> detected remote verification request"
                command=jsonrpc("ping")
                result=command.send()
                s.wfile.write("XBMC JSON connection test:\r\n")
                s.wfile.write(result)
            elif "/subscribe" in request_path:
                url = urlparse(s.path)
                params = parse_qs(url.query)
                getSubMgr().addSubscriber(s.client_address[0], params['port'][0], params['commandID'][0])
                getSubMgr().notify()
            elif "/unsubscribe" in request_path:
                url = urlparse(s.path)
                params = parse_qs(url.query)
                getSubMgr().removeSubscriber(s.client_address[0], params['commandID'][0])
            elif request_path == "player/playback/setParameters":
                url = urlparse(s.path)
                params = parse_qs(url.query)
                if 'volume' in params:
                    volume = int(params['volume'][0])
                    printDebug("adjusting the volume to %s%%" % volume)
                    jsonrpc("Application.SetVolume", {"volume": volume})
                    getSubMgr().notify('volume');
            elif "/playMedia" in request_path:
                url = urlparse(s.path)
                params = parse_qs(url.query)
                resume = params.get('viewOffset', ["0"])[0]
                protocol = params.get('protocol', ["http"])[0]
                address = params.get('address', [s.client_address[0]])[0]
                printDebug("getServerByHost %s" % getSettings('serverList'))
                port = params.get('port', [getServerByHost(address).get('port', '32400')])[0]
                fullurl = protocol+"://"+address+":"+port+params['key'][0]
                printDebug("playMedia command -> fullurl: %s" % fullurl)
                jsonrpc("playmedia", [fullurl, resume])
                getSubMgr().notify('play');
            elif request_path == "player/playback/play":
                printDebug("received play command")
                for playerid in getPlayerIds():
                    jsonrpc("Player.PlayPause", {"playerid" : playerid, "play": True})
                getSubMgr().notify('play');
            elif request_path == "player/playback/pause":
                printDebug("received pause command")
                for playerid in getPlayerIds():
                    jsonrpc("Player.PlayPause", {"playerid" : playerid, "play": False})
                getSubMgr().notify('play');
            elif request_path == "player/playback/stop":
                printDebug("received stop command")
                for playerid in getPlayerIds():
                    jsonrpc("Player.Stop", {"playerid" : playerid})
                getSubMgr().notify('stop');
            elif request_path == "player/playback/stepForward":
                printDebug("received stepForward command")
                for playerid in getPlayerIds():
                    jsonrpc("Player.Seek", {"playerid":playerid, "value":"smallforward"})
                getSubMgr().notify('seek');
            elif request_path == "player/playback/stepBack":
                printDebug("received stepBack command")
                for playerid in getPlayerIds():
                    jsonrpc("Player.Seek", {"playerid":playerid, "value":"smallbackward"})
                getSubMgr().notify('seek');
            elif request_path == "player/playback/skipNext":
                printDebug("received stepForward command")
                for playerid in getPlayerIds():
                    jsonrpc("Player.Seek", {"playerid":playerid, "value":"bigforward"})
                getSubMgr().notify('seek');
            elif request_path == "player/playback/skipPrevious":
                printDebug("received stepBack command")
                for playerid in getPlayerIds():
                    jsonrpc("Player.Seek", {"playerid":playerid, "value":"bigbackward"})
                getSubMgr().notify('seek');
            
            s.send_response(200)
        except:
            traceback.print_exc()
        s.wfile.close()
    
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
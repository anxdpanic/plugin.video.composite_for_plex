import re
import socket
import traceback
from SocketServer import ThreadingMixIn
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from urlparse import urlparse, parse_qs
from settings import settings
from functions import *
from subscribers import subMgr

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
            url = urlparse(s.path)
            paramarrays = parse_qs(url.query)
            params = {}
            for key in paramarrays:
                params[key] = paramarrays[key][0]
            printDebug ( "request path is: [%s]" % ( request_path,) )
            printDebug ( "request headers: %s" % s.headers )
            s.send_response(200)
            headers = getPlexHeaders()
            for key in headers:
                s.send_header(key, headers[key])
            s.end_headers()
            if request_path=="version":
                s.wfile.write("PleXBMC Helper Remote Redirector: Running\r\n")
                s.wfile.write("Version: 0.1")
            elif request_path=="verify":
                print "PleXBMC Helper -> listener -> detected remote verification request"
                command=jsonrpc("ping")
                result=command.send()
                s.wfile.write("XBMC JSON connection test:\r\n")
                s.wfile.write(result)
            elif "resources" == request_path:
                resp = getXMLHeader()
                resp += "<MediaContainer>"
                resp += "<Player"
                resp += ' title="%s"' % settings['client_name']
                resp += ' protocol="plex"'
                resp += ' protocolVersion="1"'
                resp += ' protocolCapabilities="navigation,playback,timeline"'
                resp += ' machineIdentifier="%s"' % settings['uuid']
                resp += ' product="PleXBMC"'
                resp += ' platform="%s"' % getPlatform()
                resp += ' platformVersion="%s"' % settings['plexbmc_version']
                resp += ' deviceClass="pc"'
                resp += "/>"
                resp += "</MediaContainer>"
                printDebug("crafted resources response: %s" % resp)
                s.wfile.write(resp)
            elif "/subscribe" in request_path:
                s.wfile.write(getOKMsg())
                protocol = params.get('protocol', "")
                host = s.client_address[0]
                port = params.get('port', False)
                uuid = s.headers.get('X-Plex-Client-Identifier', "")
                commandID = params.get('commandID', 0)
                subMgr.addSubscriber(protocol, host, port, uuid, commandID)
            elif "/unsubscribe" in request_path:
                s.wfile.write(getOKMsg())
                uuid = s.headers.get('X-Plex-Client-Identifier', False) or s.client_address[0]
                subMgr.removeSubscriber(uuid)
            elif request_path == "player/playback/setParameters":
                s.wfile.write(getOKMsg())
                if 'volume' in params:
                    volume = int(params['volume'])
                    printDebug("adjusting the volume to %s%%" % volume)
                    jsonrpc("Application.SetVolume", {"volume": volume})
            elif "/playMedia" in request_path:
                s.wfile.write(getOKMsg())
                resume = params.get('viewOffset', params.get('offset', "0"))
                protocol = params.get('protocol', "http")
                address = params.get('address', s.client_address[0])
                server = getServerByHost(address)
                port = params.get('port', server.get('port', '32400'))
                fullurl = protocol+"://"+address+":"+port+params['key']
                printDebug("playMedia command -> fullurl: %s" % fullurl)
                jsonrpc("playmedia", [fullurl, resume])
                subMgr.lastkey = params['key']
                subMgr.lookup(address, port)
            elif request_path == "player/playback/play":
                s.wfile.write(getOKMsg())
                printDebug("received play command")
                for playerid in getPlayerIds():
                    jsonrpc("Player.PlayPause", {"playerid" : playerid, "play": True})
            elif request_path == "player/playback/pause":
                s.wfile.write(getOKMsg())
                printDebug("received pause command")
                for playerid in getPlayerIds():
                    jsonrpc("Player.PlayPause", {"playerid" : playerid, "play": False})
            elif request_path == "player/playback/stop":
                s.wfile.write(getOKMsg())
                printDebug("received stop command")
                for playerid in getPlayerIds():
                    jsonrpc("Player.Stop", {"playerid" : playerid})
            elif request_path == "player/playback/stepForward":
                s.wfile.write(getOKMsg())
                printDebug("received stepForward command")
                for playerid in getPlayerIds():
                    jsonrpc("Player.Seek", {"playerid":playerid, "value":"smallforward"})
            elif request_path == "player/playback/stepBack":
                s.wfile.write(getOKMsg())
                printDebug("received stepBack command")
                for playerid in getPlayerIds():
                    jsonrpc("Player.Seek", {"playerid":playerid, "value":"smallbackward"})
            elif request_path == "player/playback/skipNext":
                s.wfile.write(getOKMsg())
                printDebug("received stepForward command")
                for playerid in getPlayerIds():
                    jsonrpc("Player.Seek", {"playerid":playerid, "value":"bigforward"})
            elif request_path == "player/playback/skipPrevious":
                s.wfile.write(getOKMsg())
                printDebug("received stepBack command")
                for playerid in getPlayerIds():
                    jsonrpc("Player.Seek", {"playerid":playerid, "value":"bigbackward"})
        except:
            traceback.print_exc()
        s.wfile.close()
    
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
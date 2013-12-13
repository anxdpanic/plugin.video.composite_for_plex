"""
PleXBMC Remote Helper 0.2

Based on XBMCLocalProxy 0.1 Copyright 2011 Torben Gerkensmeyer

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
MA 02110-1301, USA.
"""

import base64
import re
import time
import urllib
import sys
import traceback
import socket
import httplib
from SocketServer import ThreadingMixIn
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from urllib import *
import json
import xbmcaddon
import xbmc
import base64
import string
import inspect
from xml.dom.minidom import parseString
from urlparse import urlparse
from urlparse import parse_qs

def getAddonSetting(doc,id):
    test = doc.getElementsByTagName(id)
    data = test[0].toxml()   
    return data.replace('<%s>' % id, '').replace('</%s>' % id,'').replace('<%s/>' % id, '')       


__settings__ = xbmcaddon.Addon(id='script.plexbmc.helper')
g_header={'Content-Type' : 'application/json'}  
g_pguisettings = xbmc.translatePath('special://userdata/guisettings.xml')

try:
    fguisettings = open(g_pguisettings, 'r')
    data = fguisettings.read()
    fguisettings.close
    guisettings = parseString(data)
except:
    print "PleXBMC Helper -> Unable to read guisettings.xml - suggest you use custom settings"

if __settings__.getSetting('use_xbmc_net') == "false":   
    g_xbmc_port = __settings__.getSetting('xbmcport')
    if not g_xbmc_port:
        g_xbmc_port=80
    g_xbmc_user = __settings__.getSetting('xbmcuser')
    g_xbmc_pass=__settings__.getSetting('xbmcpass')

else:
    xbmc_webserver = getAddonSetting(guisettings, 'webserver')
    if xbmc_webserver == "false":
        print "PleXBMC Helper -> XBMC Web server not enabled"
        xbmc.executebuiltin("XBMC.Notification(PleXBMC Helper - XBMC web server not running,)")
    g_xbmc_port = getAddonSetting(guisettings, 'webserverport')
    g_xbmc_user = getAddonSetting(guisettings, 'webserverusername')
    g_xbmc_pass = getAddonSetting(guisettings, 'webserverpassword')

if g_xbmc_user:
    auth = 'Basic ' + string.strip(base64.encodestring(g_xbmc_user + ':' + g_xbmc_pass))
    g_header['Authorization']=auth

g_debug = __settings__.getSetting('debug')
   
def printDebug( msg, functionname=True ):
    if g_debug == "true":
        if functionname is False:
            print str(msg)
        else:
            print "PleXBMC Helper -> " + inspect.stack()[1][3] + ": " + str(msg)
    

class MyHandler(BaseHTTPRequestHandler):
    """
        Serves a HEAD request
    """
    def do_HEAD(s):
        printDebug( "Serving HEAD request..." )
        s.answer_request(0)

    """
    Serves a GET request.
    """
    def do_GET(s):
        printDebug( "Serving GET request..." )
        s.answer_request(1)

    def answer_request(s, sendData):
        try:
            #s.send_response(200)
            request_path=s.path[1:]
            request_path=re.sub(r"\?.*","",request_path)
            printDebug ( "request path is: [%s]" % ( request_path,) )
            if request_path=="version":
                #s.end_headers()
                s.wfile.write("PleXBMC Helper Remote Redirector: Running\r\n")
                s.wfile.write("Version: 0.1")
                s.send_response(200)
            elif request_path=="verify":
                print "PleXBMC Helper -> listener -> detected remote verification request"
                command=XBMCjson("ping")
                result=command.send()
                s.wfile.write("XBMC JSON connection test:\r\n")
                s.wfile.write(result)
                s.send_response(200)
            elif request_path == "player/playback/playMedia":
                s.wfile.write("<html><li>OK</html>")
                s.send_response(200)
                url = urlparse(s.path)
                params = parse_qs(url.query)
                resume = ("0", "1")[int(params['viewOffset'][0]) > 0]                
                fullurl = params['protocol'][0]+"://"+params['address'][0]+":"+params['port'][0]+params['key'][0]
                printDebug("fullurl: %s" % fullurl)
                command=XBMCjson("playmedia", [fullurl, resume])
                command.send()
            elif request_path == "player/playback/stop":
                s.wfile.write("<html><li>OK</html>")
                s.send_response(200)
                printDebug("received stop command")
                command=XBMCjson("Player.Stop", {"playerid" : 1})
                command.send()
            else:
                s.send_response(200)
        except:
                traceback.print_exc()
                s.wfile.close()
                return
        try:
            s.wfile.close()
        except:
            pass   

    def address_string(self):
        host, port = self.client_address[:2]
        #return socket.getfqdn(host)
        return host            
            
class XBMCjson:

    def __init__(self,action,arguments):
    
        self.action = action
        self.arguments = arguments
        self.hostname = "127.0.0.1"
        self.port=g_xbmc_port
        self.url="/jsonrpc"
        self.header=g_header
        
    
    def send(self):
            
        if self.action.lower() == "sendkey":
            request=json.dumps({ "jsonrpc" : "2.0" , "method" : "Input.SendText", "params" : { "text" : self.arguments[0], "done" : False }} )
                        
        elif self.action.lower() == "ping":
            request=json.dumps({ "jsonrpc" : "2.0",
                                 "id" : 1 ,
                                 "method"  : "JSONRPC.Ping" })

        elif self.action.lower() == "setvolume":
            xbmc.executebuiltin( "XBMC.SetVolume(%d)" % ( int(self.arguments), ) )
            return True

        elif self.action.lower() == "playmedia":
            fullurl=self.arguments[0]
            resume=self.arguments[1]
            request=json.dumps({ "id"      : 1,
                                 "jsonrpc" : "2.0",
                                 "method"  : "Player.Open",
                                 "params"  : { "item"  :  {"file":"plugin://plugin.video.plexbmc/?mode=5&force="+resume+"&url="+fullurl } } } )
            printDebug("Sending Player.Open: %s" % request)
            
        else:
            request=json.dumps({ "id" : 1,
                                 "jsonrpc" : "2.0",
                                 "method"  : self.action,
                                 "params"  : self.arguments})
        
        html=self.getURL(request)

        if html is False:
            xbmc.executebuiltin("XBMC.Notification(PleXBMC Helper: Unable to complete remote play request.)")
            return False
        
        if html:
            printDebug("PleXBMC Helper -> listener -> request completed")
            help=json.loads(html)
            results=help.get('result',help.get('error'))
            printDebug ( str(results) )
            return help

            
    def getURL( self, urlData=""):
        try:        
            conn = httplib.HTTPConnection("%s:%s" % (self.hostname, self.port ) ) 
            conn.request("POST", self.url, urlData, self.header) 
            data = conn.getresponse() 
            if int(data.status) >= 400:
                error = "HTTP response error: " + str(data.status) + " " + str(data.reason)
                print error
                return False
            else:      
                link=data.read()
                print link
        except socket.gaierror :
            error = 'Unable to lookup host: ' + self.hostname + "\nCheck host name is correct"
            print error
            return False
        except socket.error, msg : 
            error="Unable to connect to " + self.hostname +"\nReason: " + str(msg)
            print error
            return False
        except:
            print "unknown error"
            return False
            
        return link
        
    
            
class Server(HTTPServer):
    """HTTPServer class with timeout."""

    def get_request(self):
        """Get the request and client address from the socket."""
        self.socket.settimeout(5.0)
        result = None
        while result is None:
            try:
                result = self.socket.accept()
            except socket.timeout:
                pass
        result[0].settimeout(1000)
        return result

class ThreadedHTTPServer(ThreadingMixIn, Server):
    """Handle requests in a separate thread."""

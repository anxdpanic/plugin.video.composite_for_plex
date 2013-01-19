"""
PleXBMC Remote Helper 0.1

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

__settings__ = xbmcaddon.Addon(id='script.plexbmc.helper')
g_xbmc_port = __settings__.getSetting('xbmcport')
if not g_xbmc_port:
    g_xbmc_port=80
    
g_header={'Content-Type' : 'application/json'}  
g_xbmc_user = __settings__.getSetting('xbmcuser')
if g_xbmc_user:
    g_xbmc_pass=__settings__.getSetting('xbmcpass')
    auth = 'Basic ' + string.strip(base64.encodestring(g_xbmc_user + ':' + g_xbmc_pass))
    g_header['Authorization']=auth


class MyHandler(BaseHTTPRequestHandler):
    """
        Serves a HEAD request
    """
    def do_HEAD(s):
        print "PleXBMC Helper: Serving HEAD request..."
        s.answer_request(0)

    """
    Serves a GET request.
    """
    def do_GET(s):
        print "PleXBMC Helper: Serving GET request..."
        s.answer_request(1)

    def answer_request(s, sendData):
        try:
            s.send_response(200)
            request_path=s.path[1:]
            request_path=re.sub(r"\?.*","",request_path)
            print "request path is: [%s]" % ( request_path,)
            if request_path=="version":
                s.send_response(200)
                s.end_headers()
                s.wfile.write("PleXBMC Helper Remote Redirector: Running\r\n")
                s.wfile.write("Version: 0.1")
            elif request_path == "xbmcCmds/xbmcHttp":
                s.send_response(200)
                print "Detected remote application request"
                print "Path: %s" % ( s.path , )
                command_path=s.path.split('?')[1]
                print "Request: %s " % (urllib.unquote(command_path),)
                if command_path.split('=')[0] == 'command':
                    print "Command: Sending a json to XBMC"
                    command=XBMCjson(urllib.unquote(command_path.split('=',1)[1]))
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

class XBMCjson:

    def __init__(self,command):
    
        self.action = command[0:command.find("(")]
        self.arguments = command[command.find("(")+1:command.find(")")]
        self.hostname = "127.0.0.1"
        self.port=g_xbmc_port
        self.url="/jsonrpc"
        print "remote object setup: [%s] [%s]" % ( self.action , self.arguments )
        self.header=g_header
        
    
    def send(self):
            
        if self.action.lower() == "sendkey":
            #request=json.dumps({ "jsonrpc" : "2.0" , "method" : "Input.SendText", "params" : { "text" : "a", "done" : False }} )
            request=json.dumps({ "jsonrpc" : "2.0",
                                 "method"  : "JSONRPC.Ping" })

        elif self.action.lower() == "playmedia":
        
            server=self.arguments.split(';')[0].split('/')[2]
            path=self.arguments.split(';')[1]
            resume=self.arguments.split(';')[4].strip()
                
            if not resume:
                resume=0
                
            resume_url="&force=%s" % (resume,)
        
            fullurl=urllib.quote_plus("http://%s%s" % (server, path))
        
            request=json.dumps({ "id"      : 1,
                                 "jsonrpc" : "2.0",
                                 "method"  : "Player.Open",
                                 "params"  : { "item"  :  {"file":"plugin://plugin.video.plexbmc/?url="+fullurl+"&mode=5"+resume_url } } } )
       
            print "JSON RQST: %s" % request
        else:
            request=json.dumps({ "jsonrpc" : "2.0",
                                 "method"  : "JSONRPC.Ping" })
        
        html=self.getURL(self.url, urlData=request)
        #html=xbmc.executeJSONRPC(request)

        if html is False:
            print "Problem with request"
            xbmc.executebuiltin("XBMC.Notification(PleXBMC Helper: Unable to complete remote play request,)")
            return
        
        if html:
            help=json.loads(html)
            results=help.get('result',help.get('error'))
            print str(results)

            
    def getURL( self, url , urlData=""):
        try:        
            conn = httplib.HTTPConnection("%s:%s" % (self.hostname, self.port ) ) 
            conn.request("POST", url, urlData, self.header) 
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
"""
XBMCLocalProxy 0.1
Copyright 2011 Torben Gerkensmeyer

Modified for PleXBMC transcoding by Hippojay

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
import os
from SocketServer import ThreadingMixIn
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from urllib import *

class MyHandler(BaseHTTPRequestHandler):
    """
    Serves a HEAD request
    """
    def do_HEAD(s):
        print "==== PROXY: " + str(s.client_address[1])+": XBMCLocalProxy: Serving HEAD request..."
        s.answer_request(0)

    """
    Serves a GET request.
    """
    def do_GET(s):
        print "==== PROXY: " + str(s.client_address[1])+": XBMCLocalProxy: Serving GET request..."
        s.answer_request(1)

    def answer_request(s, sendData):
        try:
            #print str(s.client_address[1])+": SendData is " + str(sendData)
            request_path=s.path[1:]
            request_path=re.sub(r"\?.*","",request_path)
            if request_path=="stop":
                print "==== PROXY: " + str(s.client_address[1])+": STOP request"
                s.send_response(200)
                s.end_headers()
                s.wfile.write("Stop detected.  Instructing parent")
                s.wfile.write("Creating file " + file)
                signal=open(file,'w')
                signal.write("STOP")
                signal.close()
                #sys.exit()
            elif request_path=="version":
                print "==== PROXY: " + str(s.client_address[1])+": Version request"
                s.send_response(200)
                s.end_headers()
                s.wfile.write("Proxy: Running\r\n")
                s.wfile.write("Version: 0.4")
            elif request_path[0:12]=="withheaders/":
                #print str(s.client_address[1])+": URL request"
                (realpath,additionalheaders)=request_path[12:].split("/")
                fURL=base64.b64decode(realpath)
                additionalhString=base64.b64decode(additionalheaders)
                #print str(s.client_address[1])+": using this data:"
                #print str(s.client_address[1])+": URL = " + fURL
                #print str(s.client_address[1])+": headers = " + additionalhString
                s.serveFile(fURL, additionalhString, sendData)
            else:
                s.send_response(403)
        except:
                traceback.print_exc()
                s.wfile.close()
                return
        try:
            s.wfile.close()
        except:
            pass

            
    """
    Sends the requested file and add additional headers.
    """
    def serveFile(s, fURL, additionalhstring, sendData):
            #check fURL for m3u8 playlist
            
            endbit=fURL.split('/')[-1]
            if endbit == "index.m3u8":
                print "==== PROXY: " + str(s.client_address[1])+": We have an m3u8 playlist to get."
                mode="m3u8"
            else:
                print "==== PROXY: " + str(s.client_address[1])+": This is not an m3u8 playlist"
                mode="std"
            
            server=fURL.split('/')[2]
            fURLpath="/".join(fURL.split('/')[:-1])+"/"
            
            additionalh=s.decodeHeaderString(additionalhstring)
            opener = FancyURLopener()
            opener.addheaders=[]
            d={}
            sheaders=s.decodeHeaderString("".join(s.headers.headers))
            #print str(s.client_address[1])+": Headers to go to server: "+ str(sheaders)
            for key in sheaders:
                if key == "Range": continue
                d[key]=sheaders[key]
                if (key!="Host"): opener.addheader(key,sheaders[key])
            for key in additionalh:
                d[key]=additionalh[key]
                opener.addheader(key,additionalh[key])
            response = opener.open(fURL)

            #print str(s.client_address[1])+": remote server response is " + str(response.code)
            
            #s.send_response(response.code)
            s.send_response(200)
            print "==== PROXY: " + str(s.client_address[1])+": XBMCLocalProxy: Sending headers..."
            headers=response.info()
            for key in headers:
                try:
                    #print str(s.client_address[1])+": Sending headers back to XBMC"
                    val=headers[key]
                    if key == "content-type" and mode == "m3u8":
                        #print str(s.client_address[1])+": Header: " + key + ": video/mpegts"
                        s.send_header(key, "video/mpegts")
                    elif key == "content-length" and mode == "m3u8":
                        #print str(s.client_address[1])+": Header: " + key + ": 20000000"
                        s.send_header(key, "200000000")
                    elif key == "connection" and mode == "m3u8":
                        #print str(s.client_address[1])+": Header: " + key + " keep-alive"
                        s.send_header(key, "keep-alive")
                    else:
                        #print str(s.client_address[1])+": STD Header: " + key + ": " + val
                        s.send_header(key, val)

 

                except Exception, e:
                    print e
                    pass
            s.end_headers()
            
            if (sendData):
                print "==== PROXY: " + str(s.client_address[1])+": XBMCLocalProxy: Sending data..."

                #If we have an m3u8 then lets check the tags
                if mode == "m3u8":
                    filelist={}
                    playlist=response.read()
                    #print "==============PLAYLIST==============="
                    #print playlist
                    #print "==============END PLAYLIST ==========="
                    #sList = (line for line in playlist.split(os.linesep))
                    sList=playlist.split('\n')
                    for items in sList:
                    
                        if items == "#EXTM3U":
                            print "==== PROXY: " + str(s.client_address[1])+": Found m3u8 start TAG"
                            start=1
                        elif items.startswith("#EXT-X-TARGETDURATION"):
                            duration = items.split(':')[1]
                            if start == 1:
                                print "==== PROXY: " + str(s.client_address[1])+": Found m3u8 duration tag. std Segment length is " + duration + " seconds"
                            if start == 0:
                                print "==== PROXY: " + str(s.client_address[1])+": Found out of sequence duration tag. std Segment length is " + duration + " seconds"
                        elif len(items.split('.')) == 2:
                            try:
                                if items.split('.')[1] == "ts":
                                    #take the file name, get the last bit split by / and then split that by a . to remove .ts.  integer
                                    index=int(items.split('/')[-1].split('.')[0])
                                    filelist[index]=fURLpath+items
                                    try:
                                        if sheaders['Range'] is not None:
                                            break
                                    except: pass
                            except:pass
                        elif items.startswith("#EXT-X-ENDLIST"):
                            print "==== PROXY: " + str(s.client_address[1])+": Found m3u8 END tag"
                            break
                
                    #print str(s.client_address[1])+": we have a file list with " + str(len(filelist)-1) + " segments"
                    #print str(s.client_address[1])+": Test item: " + str(filelist[0])        

                fileout=s.wfile
                try: 
                        buf="INIT"
                        try:
                            if mode == "m3u8":
                                #print str(s.client_address[1])+": this is a playlist, so going to get the segments"

                                s.getSegments(filelist, fileout, additionalhstring, buf )
                                    
                                #print str(s.client_address[1])+": Back in main program"
                            else:
                                while (buf!=None and len(buf)>0):
                                    buf=response.read(8*1024)
                                    fileout.write(buf)
                                    fileout.flush()
                                response.close()                            
                            
                            fileout.close()
                            print "==== PROXY: " + str(s.client_address[1])+": Closing connection" + str(time.asctime())
                        except socket.error, e:
                            print "==== PROXY: " + str(s.client_address[1])+": Client Closed the connection at " + str(time.asctime())
                            try:
                                response.close()
                                fileout.close()
                            except Exception, e:
                                return
                        except Exception,e:
                            traceback.print_exc(file=sys.stdout)
                            response.close()
                            fileout.close()
                except:
                    traceback.print_exc()
                    s.wfile.close()
                    return
            try:
                s.wfile.close()
            except:
                pass

    def decodeHeaderString(self,hs):
        di={}
        hss=hs.replace("\r","").split("\n")
        for line in hss:
            u=line.split(": ")
            try:
                di[u[0]]=u[1]
            except:
                pass
        return di
        
    def getSegments(s, files, output, headerstring, bufferstring):
        print str(s.client_address[1])+": ====PROXY: getSegments()===="
        #print str(s.client_address[1])+": ==== This playlist has " + str(len(files)) + " elements"
        i=0
        while i < len(files):
            #print str(s.client_address[1])+": For file at index " + str(i)
            additionalh=s.decodeHeaderString(headerstring)
            opener = FancyURLopener()
            opener.addheaders=[]
            d={}
            sheaders=s.decodeHeaderString("".join(s.headers.headers))
            for key in sheaders:
                d[key]=sheaders[key]
                if (key!="Host"): opener.addheader(key,sheaders[key])
            for key in additionalh:
                d[key]=additionalh[key]
                opener.addheader(key,additionalh[key])
            print "==== PROXY: " + str(s.client_address[1])+": Opening playlist URL " + files[i]
            response = opener.open(files[i])
            #print str(s.client_address[1])+": headers are: " + str(response.info())

            #print str(s.client_address[1])+": Start filewrite on back of " + str(response.code)
            #print str(s.client_address[1])+": buffer is " + str(len(bufferstring))
            #print str(s.client_address[1])+": and contains " + str(bufferstring)
            bufferstring="INIT"
            while (bufferstring!=None and len(bufferstring)>0):
                bufferstring=response.read(8*1024)
                output.write(bufferstring)
                output.flush()
            response.close()  
            print "==== PROXY: " + str(s.client_address[1])+": segment finished - getting next"
            i+=1
        
        print "==== PROXY: " + str(s.client_address[1])+": Finished all segments.  Last one was " + str(int(i-1))
        
        return


class Server(HTTPServer):
    """HTTPServer class with timeout."""

    def get_request(self):
        """Get the request and client address from the socket."""
        self.socket.settimeout(10.0)
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

HOST_NAME = '127.0.0.1'
PORT_NUMBER = 8087
RUN=True
file=sys.argv[1]
try:
    if sys.argv[2]:
        PORT_NUMBER=int(sys.argv[2])
except: pass
print "==== PROXY: Using signal file " + file
print "==== PROXY: Running on port " + str(PORT_NUMBER)

if __name__ == '__main__':    
        socket.setdefaulttimeout(10)
        server_class = ThreadedHTTPServer
        httpd = server_class((HOST_NAME, PORT_NUMBER), MyHandler)
        print "XBMCLocalProxy Starts - %s:%s" % (HOST_NAME, PORT_NUMBER)
        while(RUN):
            try:
                exists = open(file, 'r')
                exists.close()
                os.remove(file)
                break
            except: 
                httpd.handle_request()    
        httpd.server_close()
        print "XBMCLocalProxy Stops %s:%s" % (HOST_NAME, PORT_NUMBER)
        #sys.exit()


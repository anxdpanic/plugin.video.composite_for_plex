import urllib,urllib2,re,xbmcplugin,xbmcgui,xbmcaddon, httplib, socket
import sys,os,datetime, time, sha, inspect

__settings__ = xbmcaddon.Addon(id='plugin.video.plexbmc')
__cwd__ = __settings__.getAddonInfo('path')
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
PLUGINPATH=xbmc.translatePath( os.path.join( __cwd__) )
sys.path.append(BASE_RESOURCE_PATH)

print "running on " + str(sys.version_info)

try:
  from lxml import etree
  print("Running with lxml.etree")
except ImportError:
  try:
    # Python 2.5
    import xml.etree.cElementTree as etree
    print("running with cElementTree on Python 2.5+")
  except ImportError:
    try:
      # Python 2.5
      import xml.etree.ElementTree as etree
      print("running with ElementTree on Python 2.5+")
    except ImportError:
      try:
        # normal cElementTree install
        import cElementTree as etree
        print("running with cElementTree")
      except ImportError:
        try:
          # normal ElementTree install
          import elementtree.ElementTree as etree
          print("running with ElementTree")
        except ImportError: 
            try:
                import ElementTree as etree
                print("Using plugin elemenetree")
            except ImportError:    
                print("Failed to import ElementTree from any known place")

#Get the setting from the appropriate file.
print "===== PLEXBMC START ====="
DEFAULT_PORT="32400"
g_host = __settings__.getSetting('ipaddress')
g_port=__settings__.getSetting('port')
g_stream = __settings__.getSetting('streaming')
g_secondary = __settings__.getSetting('secondary')
g_debug = __settings__.getSetting('debug')
g_streamControl = __settings__.getSetting('streamControl')
g_channelview = __settings__.getSetting('channelview')
if not g_port:
    if g_debug == "true": print "PleXBMC -> No port defined.  Using default of " + DEFAULT_PORT
    g_host=g_host+":"+DEFAULT_PORT
else:
    g_host=g_host+":"+g_port

if g_debug == "true":
    print "PleXBMC -> Settings hostname and port: " + g_host
    print "PleXBMC -> Settings streaming: " + g_stream
    print "PleXBMC -> Setting secondary: " + g_secondary
    print "PleXBMC -> Setting debug to " + g_debug
    print "PleXBMC -> Setting stream Control to : " + g_streamControl
    
else:
    print "PleXBMC -> Debug is turned off.  Running silent"

g_multiple = int(__settings__.getSetting('multiple')) 
g_serverList=[]
if g_multiple > 0:
    if g_debug == "true": print "PleXBMC -> Multiple servers configured; found [" + str(g_multiple) + "]"
    for i in range(1,g_multiple+1):
        if g_debug == "true": print "PleXBMC -> Adding server [Server "+ str(i) +"] at [" + __settings__.getSetting('server'+str(i)) + "]"
        extraip = __settings__.getSetting('server'+str(i))
        if extraip == "":
            if g_debug == "true": print "PleXBMC -> Blank server detected.  Ignoring"
            continue
        try:
            extraip.split(':')[1]
        except:
            extraip=extraip+":"+DEFAULTPORT
        g_serverList.append(['Server '+str(i),extraip])

if g_debug == "true": print "PleXBMC -> serverList is " + str(g_serverList)
        
g_loc = "special://home/addon/plugin.video.plexbmc"

#Create the standard header structure and load with a User Agent to ensure we get back a response.
g_txheaders = {
              'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US;rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 ( .NET CLR 3.5.30729)',	
              }

#Set up the remote access authentication tokens
g_bonjour = __settings__.getSetting('bonjour')
XBMCInternalHeaders=""
if g_bonjour == "true":
    if g_debug == "true": print "PleXBMC -> local Bonjour discovery enabled."
    
g_authentication = __settings__.getSetting('remote')    
if g_authentication == "true":
    if g_debug == "true": print "PleXBMC -> Getting authentication settings."
    g_username= __settings__.getSetting('username')
    g_password =  __settings__.getSetting('password')
    if g_debug == "true": print "PleXBMC -> username is " + g_username
    
    #Compute the SHA1 just one time.
    msg=sha.new(g_password)
    msg2=sha.new(g_username.lower()+msg.hexdigest()).hexdigest()
            
    #Load the auth strings into the URL header structure.
    g_txheaders['X-Plex-User']=str(g_username)
    g_txheaders['X-Plex-Pass']=str(msg2)
    
    #Set up an internal XBMC header string, which is appended to all *XBMC* processed URLs.
    XBMCInternalHeaders="|X-Plex-User="+g_txheaders['X-Plex-User']+"&X-Plex-Pass="+g_txheaders['X-Plex-Pass']

################################ Common
# Connect to a server and retrieve the HTML page
def getURL( url ,title="Error", surpress=False):
    printDebug("== ENTER: getURL ==", False)
    try:
        printDebug("url = "+url)
        txdata = None
        
        server=url.split('/')[2]
        urlPath="/"+"/".join(url.split('/')[3:])
             
        params = "" 
        conn = httplib.HTTPConnection(server) 
        conn.request("GET", urlPath, headers=g_txheaders) 
        data = conn.getresponse() 
        if int(data.status) >= 400:
            error = "HTTP response error: " + str(data.status) + " " + str(data.reason)
            if surpress is False:
                xbmcgui.Dialog().ok(title,error)
            print error
            return False
        else:      
            link=data.read()
            printDebug("====== XML returned =======")
            printDebug(link, False)
            printDebug("====== XML finished ======")
    except socket.gaierror :
        error = 'Unable to lookup host: ' + server + "\nCheck host name is correct"
        if surpress is False:
            xbmcgui.Dialog().ok(title,error)
        print error
        return False
    except socket.error, msg : 
        error="Unable to connect to " + server +"\nReason: " + str(msg)
        if surpress is False:
            xbmcgui.Dialog().ok(title,error)
        print error
        return False
    else:
        return link
      
def mediaType(partproperties, server):
    printDebug("== ENTER: mediaType ==", False)
    
    #Passed a list of <Part /> tag attributes, select the appropriate media to play
    
    stream=partproperties['key']
    file=partproperties['file']
    
    
    
    # 0 is auto select.  basically check for local file first, then stream if not found
    if g_stream == "0":
        #check if the file can be found locally
        try:
            printDebug("Checking for local file")
            exists = open(file, 'r')
            exists.close()
            filelocation="file://"+server+file
        except:
            printDebug("No local file, defaulting to stream")
            filelocation="http://"+server+stream
        
    # 1 is stream no matter what
    elif g_stream == "1":
        printDebug( "Selecting stream")
        filelocation="http://"+server+stream
    # 2 is use SMB 
    elif g_stream == "2":
        printDebug( "Selecting smb")
        filelocation="smb:/"+file.replace("Volumes",server.split(':')[0])
    else:
        printDebug( "No option detected, streaming is safest to choose" )       
        filelocation="http://"+server+stream
    
    printDebug("Returning URL: " + filelocation)
    return filelocation
     
def printDebug(msg,functionname=True):
    if g_debug == "true":
        if functionname == False:
            print str(msg)
        else:
            print "PleXBMC -> " + inspect.stack()[1][3] + ": " + str(msg)
 
#Used to add playable media files to directory listing
#properties is a dictionary {} which contains a list of setInfo properties to apply
#Arguments is a dictionary {} which contains other arguments used in teh creation of the listing (such as name, resume time, etc)
def addLink(url,properties,arguments,context=None):
        printDebug("== ENTER: addLink ==", False)
        try:
            printDebug("Adding link for [" + properties['title'] + "]")
        except: pass
        printDebug("Passed arguments are " + str(arguments))
        printDebug("Passed properties are " + str(properties))
        
        try:
            type=arguments['type']
        except:
            type='Video'
            
        if type =="Picture":
             u=url
        else:
            u=sys.argv[0]+"?url="+str(url)
        
        ok=True
        
        printDebug("URL to use for listing: " + u)
        #Create ListItem object, which is what is displayed on screen
        try:
            liz=xbmcgui.ListItem(properties['title'], iconImage=arguments['thumb'], thumbnailImage=arguments['thumb']+XBMCInternalHeaders)
            printDebug("Setting thumbnail as " + arguments['thumb'])              
        except:
            liz=xbmcgui.ListItem(properties['title'], iconImage='', thumbnailImage='')
            
        #Set properties of the listitem object, such as name, plot, rating, content type, etc
        liz.setInfo( type=type, infoLabels=properties ) 
        
        try:
            liz.setProperty('Artist_Genre', properties['genre'])
            liz.setProperty('Artist_Description', properties['plot'])
        except: pass

            
        
        #Set the file as playable, otherwise setresolvedurl will fail
        liz.setProperty('IsPlayable', 'true')
                
        #Set the fanart image if it has been enabled
        try:
            if len(arguments['fanart_image'].split('/')[-1].split('.')) < 2:
                arguments['fanart_image']=str(arguments['fanart_image']+"/image.jpg")
            liz.setProperty('fanart_image', str(arguments['fanart_image']+XBMCInternalHeaders))
            printDebug( "Setting fan art as " + str(arguments['fanart_image']))
        except: pass
        
        if context is not None:
            printDebug("Building Context Menus")
            #transcodeURL="XBMC.RunPlugin("+u+"&transcode=1)"
            #print transcodeURL
            #transcode="Container.Update("+u+"&transcode=1)"
            #context.append(("Play trancoded", transcodeURL, ))
            liz.addContextMenuItems( context )
        
        #Finally add the item to the on screen list, with url created above
        ok=xbmcplugin.addDirectoryItem(handle=pluginhandle,url=u,listitem=liz)
        
        return ok

#Used to add directory item to the listing.  These are non-playable items.  They can be mixed with playable items created above.
#properties is a dictionary {} which contains a list of setInfo properties to apply
#Arguments is a dictionary {} which contains other arguments used in teh creation of the listing (such as name, resume time, etc)
def addDir(url,properties,arguments,context=None):
        printDebug("== ENTER: addDir ==", False)
        try:
            printDebug("Adding Dir for [" + properties['title'] + "]")
        except: pass

        printDebug("Passed arguments are " + str(arguments))
        printDebug("Passed properties are " + str(properties))
        
        #Create the URL to pass to the item
        u=sys.argv[0]+"?url="+str(url)
        ok=True
                
        #Create the ListItem that will be displayed
        try:
            liz=xbmcgui.ListItem(properties['title'], iconImage=arguments['thumb'], thumbnailImage=arguments['thumb']+XBMCInternalHeaders)
            printDebug("Setting thumbnail as " + arguments['thumb'])
        except:
            liz=xbmcgui.ListItem(properties['title'], iconImage='', thumbnailImage='')
        
            
        #Set the properties of the item, such as summary, name, season, etc
        try:
            liz.setInfo( type=arguments['type'], infoLabels=properties ) 
        except:
            liz.setInfo(type='Video', infoLabels=properties ) 

        printDebug("URL to use for listing: " + u)
        
        try:
            liz.setProperty('Artist_Genre', properties['genre'])
            liz.setProperty('Artist_Description', properties['plot'])
        except: pass
        
        #If we have set a number of watched episodes per season
        try:
            #Then set the number of watched and unwatched, which will be displayed per season
            liz.setProperty('WatchedEpisodes', str(arguments['WatchedEpisodes']))
            liz.setProperty('UnWatchedEpisodes', str(arguments['UnWatchedEpisodes']))
        except: pass
        
        #Set the fanart image if it has been enabled
        try:
            if len(arguments['fanart_image'].split('/')[-1].split('.')) < 2:
                arguments['fanart_image']=str(arguments['fanart_image']+"/image.jpg") 
            liz.setProperty('fanart_image', str(arguments['fanart_image']+XBMCInternalHeaders))
            printDebug( "Setting fan art as " + str(arguments['fanart_image']))
        except: pass

        if context is not None:
            printDebug("Building Context Menus")
            liz.addContextMenuItems( context )

        
        #Finally add the item to the on screen list, with url created above
        ok=xbmcplugin.addDirectoryItem(handle=pluginhandle,url=u,listitem=liz,isFolder=True)
        return ok

################################ Root listing
# Root listing is the main listing showing all sections.  It is used when these is a non-playable generic link content
def ROOT():
        printDebug("== ENTER: ROOT() ==", False)
        xbmcplugin.setContent(pluginhandle, 'movies')

        #Get the global host variable set in settings
        host=g_host
        
        Servers=[]
      
        #If we have a remote host, then don;t do local discovery as it won't work
        if g_bonjour == "true":
            #Get the HTML for the URL
            url = 'http://'+g_host+'/servers'
            html=getURL(url)
            
            if html is False:
                return
               
            #Pass HTML to BSS to convert it into a nice parasble tree.
            tree=etree.fromstring(html)
                
            #Now, find all those server tags
            LibraryTags=tree.findall('Server')        
       
            #Now, for each tag, pull out the name of the server and it's network name
            for object in LibraryTags:
                name=object.get('name').encode('utf-8')
                host=object.get('host')
                Servers.append([name,host])
        else:
            Servers.append(["remote",g_host])
            Servers += g_serverList
        #For each of the servers we have identified
        for server in Servers:
                                                            
            #dive into the library section     
            url='http://'+server[1]+'/system/library/sections'
            html=getURL(url)
            
            if html is False:
                continue
                
            tree = etree.fromstring(html)
            
            #Find all the directory tags, as they contain further levels to follow
            #For each directory tag we find, build an onscreen link to drill down into the library
            for object in tree.getiterator('Directory'):
                        
                #If section is not local then ignore
                if object.get('local') == "0":
                    continue
                
                arguments=dict(object.items())
                
                try:
                    if arguments['art'][0] == "/":
                        arguments['fanart_image']="http://"+server[1]+arguments['art']
                    else:
                        arguments['fanart_image']="http://"+server[1]+"/library/sections/"+arguments['art']
                except: pass
                    
                try:
                    if arguments['thumb'][0] == "/":
                        arguments['thumb']="http://"+server[1]+arguments['thumb'].split('?')[0]
                    else:
                        arguments['thumb']="http://"+server[1]+"/library/sections/"+arguments['thumb'].split('?')[0]
                except: 
                    try:
                        arguments['thumb']=arguments['fanart_image']
                    except:
                        arguments['thumb']=""
                    
                    
                #Set up some dictionaries with defaults that we are going to pass to addDir/addLink
                properties={}

                #Start pulling out information from the parsed XML output. Assign to various variables
                try:
                    if g_multiple == 0:
                        properties['title']=arguments['title']
                    else:
                        properties['title']=arguments['serverName']+": "+arguments['title']
                except:
                    properties['title']="unknown"
                
                #Determine what we are going to do process after a link is selected by the user, based on the content we find
                if arguments['type'] == 'show':
                    mode=1
                if  arguments['type'] == 'movie':
                    mode=2
                if  arguments['type'] == 'artist':
                    mode=3
                
                arguments['type']="Video"
                
                if g_secondary == "true":
                    s_url='http://'+server[1]+arguments['path']+"&mode=0"
                else:
                    #Build URL with the mode to use and key to further XML data in the library
                    s_url='http://'+server[1]+arguments['path']+'/all'+"&mode="+str(mode)
                
                context=[]
                refreshURL="http://"+server[1]+arguments['path']+"/refresh"
                libraryRefresh = "XBMC.RunScript(special://home/addons/plugin.video.plexbmc/default.py, update " + refreshURL + ")"
                context.append(('Refresh library section', libraryRefresh , ))
                
                #Build that listing..
                addDir(s_url, properties,arguments, context)
             
             
                #Plex plugin handling 
                #Simple check if any plugins are present.  
                #If so, create a link to drill down later. One link is created for each PMS server available
                #Plugin data is held in /videos directory (well, video data is anyway)
                #Create Photo plugin link
            if g_channelview == "false":

                if g_multiple == 0:
                    properties['title']="Video Plugins"
                else:
                    properties['title']=arguments['serverName']+": Video Plugins"
                arguments['type']="video"
                mode=7
                u="http://"+server[1]+"/video&mode="+str(mode)
                addDir(u,properties,arguments)
                                        
                #Create Photo plugin link
                if g_multiple == 0:
                    properties['title']="Photo Plugins"
                else:
                    properties['title']=arguments['serverName']+": Photo Plugins"
                arguments['type']="Picture"
                mode=16
                u="http://"+server[1]+"/photos&mode="+str(mode)
                addDir(u,properties,arguments)

                #Create music plugin link
                if g_multiple == 0:
                    properties['title']="Music Plugins"
                else:
                    properties['title']=arguments['serverName']+": Music Plugins"
                arguments['type']="Music"
                mode=17
                u="http://"+server[1]+"/music&mode="+str(mode)
                addDir(u,properties,arguments)
            else:
                if g_multiple == 0:
                    properties['title']="Channels"
                else:
                    properties['title']=arguments['serverName']+": Channels"
                arguments['type']="video"
                mode=21
                u="http://"+server[1]+"/system/plugins/all&mode="+str(mode)
                addDir(u,properties,arguments)
                
            #Create plexonline link
            if g_multiple == 0:
                properties['title']="Plex Online"
            else:
                properties['title']=arguments['serverName']+": Plex Online"
            arguments['type']="file"
            mode=19
            u="http://"+server[1]+"/system/plexonline&mode="+str(mode)
            addDir(u,properties,arguments)


            
        #All XML entries have been parsed and we are ready to allow the user to browse around.  So end the screen listing.
        xbmcplugin.endOfDirectory(pluginhandle)  

def Movies(url,tree=None):
        printDebug("== ENTER: Movies() ==", False)
        xbmcplugin.setContent(pluginhandle, 'movies')
        
        #xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
        
        #get the server name from the URL, which was passed via the on screen listing..
        if tree is None:
            #Get some XML and parse it
            html=getURL(url)
            
            if html is False:
                return
                
            tree = etree.fromstring(html)

        server=getServerFromURL(url)
            
        #Find all the video tags, as they contain the data we need to link to a file.
        MovieTags=tree.findall('Video')
        for movie in MovieTags:
            
            printDebug("---New Item---")
            arguments=dict(movie.items())
            tempgenre=[]
            tempcast=[]
            tempdir=[]
            tempwriter=[]
            mediacount=0
            
            #Lets grab all the info we can quickly through either a dictionary, or assignment to a list
            #We'll process it later
            for child in movie:
                if child.tag == "Media":
                    mediaarguments = dict(child.items())
                    mediacount+=1    
                elif child.tag == "Genre":
                    tempgenre.append(child.get('tag'))
                elif child.tag == "Writer":
                    tempwriter.append(child.get('tag'))
                elif child.tag == "Director":
                    tempdir.append(child.get('tag'))
                elif child.tag == "Role":
                    tempcast.append(child.get('tag'))
            
            printDebug("Media attributes are " + str(mediaarguments))
            
            #Create structure to pass to listitem/setinfo.  Set defaults
            properties={'overlay': 6, 'playcount': 0}   
               
            #Get name
            try:
                properties['title']=arguments['title'].encode('utf-8')
            except: pass
            
            #Get the Plot          
            try:
                properties['plot']=arguments['summary']
            except: pass
            
            #Get the watched status
            try:
                properties['playcount']=int(arguments['viewCount'])
                if properties['playcount'] > 0:
                    properties['overlay']=7
            except: pass
            
            #Get how good it is, based on your votes...
            try:
                properties['rating']=float(arguments['rating'])
            except: pass
            
            #Get the last played position  
            try:
                arguments['viewoffset']
            except:
                arguments['viewoffset']=0
                        
            #Get the studio 
            try:
                properties['studio']=arguments['studio']
            except: pass
                        
            #Get the Movie certificate, so you know if the kids can watch it.
            try:
                properties['mpaa']=arguments['contentrating']
            except: pass
            
            #year
            try:
                properties['year']=int(arguments['year'])
            except: pass
            
            #That memorable 6 word summary..
            try:
                properties['tagline']=arguments['tagline']
            except: pass
                
            #Set the film duration 
            try:
                arguments['duration']=mediaarguments['duration']
            except KeyError:
                try:
                    arguments['duration']
                except:
                    arguments['duration']=0
             
            arguments['duration']=int(arguments['duration'])/1000
            properties['duration']=str(datetime.timedelta(seconds=int(arguments['duration'])))
                        
            #Get Thumbnail            
            arguments['thumb']=getThumb(arguments, server)
                         
            #print art_url  
            arguments['fanart_image']=getFanart(arguments,server)
            
            #Set type
            arguments['type']="Video"
            
            #Assign standard metadata
            #Cast
            properties['cast']=tempcast
            
            #director
            properties['director']=" / ".join(tempdir)
            
            #Writer
            properties['writer']=" / ".join(tempwriter)
            
            #Genre        
            properties['genre']=" / ".join(tempgenre)                
                        
            #This is playable media, so link to a path to a play function
            mode=5
                             
            u='http://'+server+arguments['key']+"&mode="+str(mode)+"&name="+urllib.quote_plus(properties['title'])+"&resume="+str(arguments['viewoffset'])+"&id="+str(arguments['ratingKey'])+"&duration="+str(arguments['duration'])
            
            context=buildContextMenu(url, arguments)            
            
            #Right, add that link...and loop around for another entry
            addLink(u,properties,arguments,context)        
        
        #If we get here, then we've been through the XML and it's time to finish.
        xbmcplugin.endOfDirectory(pluginhandle)
 
def buildContextMenu(url, arguments):
    context=[]
    server=getServerFromURL(url)
    refreshURL=url.replace("/all", "/refresh")
    libraryRefresh = "XBMC.RunScript(special://home/addons/plugin.video.plexbmc/default.py, update, " + refreshURL + ")"
    context.append(('Refresh library section', libraryRefresh , ))
    
    try:
        if arguments[ratingKey]:
            ID=arguments[ratingKey]
    except:
        ID=arguments['key'].split('/')[3]
        
    unwatchURL="http://"+server+"/:/unscrobble?key="+ID+"&identifier=com.plexapp.plugins.library"
    unwatched="XBMC.RunScript(special://home/addons/plugin.video.plexbmc/default.py, watch, " + unwatchURL + ")"
    context.append(('Mark as UnWatched', unwatched , ))
            
    watchURL="http://"+server+"/:/scrobble?key="+ID+"&identifier=com.plexapp.plugins.library"
    watched="XBMC.RunScript(special://home/addons/plugin.video.plexbmc/default.py, watch, " + watchURL + ")"
    context.append(('Mark as Watched', watched , ))

    return context
    
################################ TV Show Listings
#This is the function use to parse the top level list of TV shows
def SHOWS(url,tree=None):
        printDebug("== ENTER: SHOWS() ==", False)
        xbmcplugin.setContent(pluginhandle, 'tvshows')

        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
        
        #Get the URL and server name.  Get the XML and parse
        if tree is None:
            html=getURL(url)
        
            if html is False:
                return

            tree=etree.fromstring(html)
 
        server=getServerFromURL(url)
 
        #For each directory tag we find
        ShowTags=tree.findall('Directory') # These type of calls seriously slow down plugins
        for show in ShowTags:

            arguments=dict(show.items())
        
            tempgenre=[]
            
            #Lets grab all the info we can quickly through either a dictionary, or assignment to a list
            #We'll process it later
            for child in show:
                try:
                    tempgenre.append(child.get('tag'))
                except:pass
                
            #Create the basic data structures to pass up
            properties={'overlay': 6, 'playcount': 0, 'season' : 0 , 'episode':0 }   #Create a dictionary for properties with some defaults(i.e. ListItem properties)
            
            #Get name
            try:
                properties['title']=properties['tvshowname']=arguments['title'].encode('utf-8')
            except: pass
            
            #Get the studio
            try:
                properties['studio']=arguments['studio']
            except:pass
            
            #Get the Plot          
            try:
                properties['plot']=arguments['summary']
            except: pass

            #Get the certificate to see how scary it is..
            try:
                properties['mpaa']=arguments['contentrating']
            except:pass
                
            #Get number of episodes in season
            try:
                 properties['episode']=int(arguments['leafCount'])
            except:pass
            
            #Get number of watched episodes
            try:
                watched=arguments['viewedLeafCount']
                arguments['WatchedEpisodes']=int(watched)
                arguments['UnWatchedEpisodes']=properties['episode']-arguments['WatchedEpisodes']
                if arguments['UnWatchedEpisodes'] <= 0:
                    properties['overlay']=7
            except:pass
            
            #get Genre
            try:
                properties['genre']=" / ".join(tempgenre)
            except:pass
                
            #get the air date
            try:
                properties['aired']=arguments['originallyAvailableAt']
            except:pass

            #Get the picture to use 
            arguments['thumb']=getThumb(arguments, server)
               
            #Get a nice big picture  
            arguments['fanart_image']=getFanart(arguments,server)
           
            #Set type
            arguments['type']="Video"

            mode=4 # grab season details
            url='http://'+server+arguments['key']+"&mode="+str(mode)
            
            context=buildContextMenu(url, arguments)
            
            addDir(url,properties,arguments, context) 
            
        #End the listing    
        xbmcplugin.endOfDirectory(pluginhandle)
 
################################ TV Season listing            
#Used to display the season data         
def Seasons(url):
        printDebug("== ENTER: season() ==", False)
        xbmcplugin.setContent(pluginhandle, 'seasons')

        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)

        
        #Get URL, XML and parse
        server=getServerFromURL(url)
        html=getURL(url)
        
        if html is False:
            return
       
        tree=etree.fromstring(html)
        
        sectionart=getFanart(dict(tree.items()), server)
       
        #For all the directory tags
        ShowTags=tree.findall('Directory')
        for show in ShowTags:
        
            PMSFLAG=""
            if url.find("?unwatched=1") > 0:
                #Temp work around until PMS data fixed.
                PMSFLAG="?unwatched=1"

        
            arguments=dict(show.items());
            #Build basic data structures
            properties={'overlay': 6, 'playcount': 0, 'season' : 0 , 'episode':0 }   #Create a dictionary for properties with some defaults(i.e. ListItem properties)
 
            #Get name
            try:
                properties['tvshowtitle']=properties['title']=arguments['title'].encode('utf-8')
            except: pass
       
            #Get the picture to use 
            arguments['thumb']=getThumb(arguments, server)
               
            #Get a nice big picture  
            arguments['fanart_image']=getFanart(arguments, server)
            try:
                if arguments['fanart_image'] == "":
                    arguments['fanart_image']=sectionart
            except:
                pass

            #Get number of episodes in season
            try:
                 properties['episode']=int(arguments['leafCount'])
            except:pass
            
            #Get number of watched episodes
            try:
                watched=arguments['viewedLeafCount']
                arguments['WatchedEpisodes']=int(watched)
                arguments['UnWatchedEpisodes']=properties['episode']-arguments['WatchedEpisodes']
                if arguments['UnWatchedEpisodes'] <= 0:
                    properties['overlay']=7
            except:pass
    
            #Get the Plot          
            try:
                properties['plot']=arguments['summary']
            except: pass

            #Set type
            arguments['type']="Video"

            #Set the mode to episodes, as that is what's next     
            mode=6
            
            if arguments['key'].find("allLeaves") > 0:
                PMSFLAG=""
            
            url='http://'+server+arguments['key']+PMSFLAG+"&mode="+str(mode)
        
            context=buildContextMenu(url, arguments)
            #Build the screen directory listing
            addDir(url,properties,arguments, context) 
            
        #All done, so end the listing
        xbmcplugin.endOfDirectory(pluginhandle)
 
################################ TV Episode listing 
#Displays the actual playable media
def EPISODES(url,tree=None):
        printDebug("== ENTER: EPISODES() ==", False)
        xbmcplugin.setContent(pluginhandle, 'episodes')
        
        #xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_EPISODE)
                
        if tree is None:
            #Get URL, XML and Parse
            html=getURL(url)
            
            if html is False:
                return
            
            tree=etree.fromstring(html)
        
        ShowTags=tree.findall('Video')
            
        server=getServerFromURL(url)
        
        #Get the end part of the URL, as we need to get different data if parsing "All Episodes"

        target=url.split('/')[-1]

        printDebug("target URL is " + target)

        try:
            displayShow = tree.get('mixedParents')
            printDebug("TV listing contains mixed shows")
        except: 
            displayShow = "0"
                        
        if displayShow == "0" or displayShow is None:
            #Name of the show
            try:
                showname=tree.get('grandparentTitle')
            except:
                showname=None
            
            #the kiddie rating
            try:
                certificate = tree.get('grandparentContentRating')
            except:
                certificate=None
            
            #the studio
            try:
                studio = tree.get('grandparentStudio')
            except:
                studio = None
              
              
            #If we are processing individual season, then get the season number, else we'll get it later
            try:
                season=tree.get('parentIndex')
            except:pass
        
        sectionart=getFanart(dict(tree.items()), server)
        
         
        #right, not for each show we find
        for show in ShowTags:
            
            arguments=dict(show.items())
            tempgenre=[]
            tempcast=[]
            tempdir=[]
            tempwriter=[]
            
            #Lets grab all the info we can quickly through either a dictionary, or assignment to a list
            #We'll process it later
            for child in show:
                if child.tag == "Media":
                    mediaarguments = dict(child.items())
                        
                    for babies in child:
                        if babies.tag == "Part":
                            partarguments=(dict(babies.items()))
                elif child.tag == "Genre":
                    tempgenre.append(child.get('tag'))
                elif child.tag == "Writer":
                    tempwriter.append(child.get('tag'))
                elif child.tag == "Director":
                    tempdir.append(child.get('tag'))
                elif child.tag == "Role":
                    tempcast.append(child.get('tag'))
            
            #required to grab to check if file is a .strm file
            #Can't play strm files, so lets not bother listing them. 
            if partarguments['file'].find('.strm')>0:
                print "Found unsupported .strm file.  Will not list"
                continue
           
            printDebug("Media attributes are " + str(mediaarguments))
            printDebug( "Part is " + str(partarguments))
            printDebug( "Extra info is " + str(tempgenre) + str(tempwriter) + str(tempcast) + str(tempdir))
            
            #Set basic structure with some defaults.  Overlay 6 is unwatched
            properties={'overlay': 6, 'playcount': 0, 'season' : 0}   #Create a dictionary for properties with some defaults(i.e. ListItem properties)
            #arguments={'type': "tvshows", 'viewoffset': 0, 'duration': 0, 'thumb':''}    #Create a dictionary for file arguments (i.e. stuff you need, but are no listitems)
            
            #Get the episode number
            try:
                properties['episode']=int(arguments['index'])
            except: pass

            #Get name
            try:
                properties['title']=str(properties['episode']).zfill(2)+". "+arguments['title'].encode('utf-8')
            except: 
                properties['title']="Unknown"
                       
            #Get the Plot          
            try:
                properties['plot']=arguments['summary']
            except: pass
            
            #Get the watched status
            try:
                properties['playcount']=int(arguments['viewCount'])
                if properties['playcount'] > 0:
                    properties['overlay']=7
            except: pass
            
            #Get how good it is, based on your votes...
            try:
                properties['rating']=float(arguments['rating'])
            except: pass
            
            #Get the last played position  
            try:
                arguments['viewOffset']=int(arguments['viewOffset'])/1000
            except:
                arguments['viewOffset']=0

                        
            #If we are processing an "All Episodes" directory, then get the season from the video tag
            
            try:
                if season:
                    properties['season']=int(season)
            except:
                try:
                    properties['season']=int(arguments['parentIndex'])
                except: pass
                
            #check if we got the kiddie rating from the main tag
            try:
                if certificate:
                    properties['mpaa']=certificate
            except:
                try:
                    properties['mpaa']=arguments['contentRating']
                except:pass    
                    
            #Check if we got the showname from the main tag        
            try:
                if showname:
                    properties['tvshowtitle']=showname
            except:
                try:
                    properties['tvshowtitle']=arguments['grandparentTitle']
                except: pass
            
            try:
                if displayShow == "1":
                    properties['title']=properties['tvshowtitle']+":"+properties['title']
            except: pass
            
            #check if we got the studio from the main tag.
            try:
                if studio:
                    properties['studio']=studio
            except:
                try:
                    properties['studio']=arguments['studio']
                except: pass
                
            #Get the picture to use
            arguments['thumb']=getThumb(arguments, server)
               
            #Get a nice big picture  
            arguments['fanart_image']=getFanart(arguments, server)
            try:
                if arguments['fanart_image'] == "":
                    arguments['fanart_image']=sectionart
            except:
                pass

            #Set type
            arguments['type']="Video"

            #Assign standard metadata
            #Cast
            properties['cast']=tempcast
            
            #director
            properties['director']=" / ".join(tempdir)
            
            #Writer
            properties['writer']=" / ".join(tempwriter)
            
            #Genre        
            properties['genre']=" / ".join(tempgenre) 
            
            #get the air date
            try:
                properties['aired']=arguments['originallyAvailableAt']
            except:pass
            
            #Set the film duration 
            try:
                arguments['duration']=mediaarguments['duration']
            except KeyError:
                try:
                    arguments['duration']
                except:
                    arguments['duration']=0
             
            arguments['duration']=int(arguments['duration'])/1000
            properties['duration']=str(datetime.timedelta(seconds=int(arguments['duration'])))
            
            #If we are streaming, then get the virtual location
            #url=
            #Set mode 5, which is play            
            mode=5

            u='http://'+server+arguments['key']+"&mode="+str(mode)+"&name="+urllib.quote_plus(properties['title'])+"&resume="+str(arguments['viewOffset'])+"&id="+str(arguments['ratingKey'])+"&duration="+str(arguments['duration'])
            context=buildContextMenu(url, arguments)
                
            #Build a file link and loop
            addLink(u,properties,arguments, context)        
        
        #End the listing
        xbmcplugin.endOfDirectory(pluginhandle)

def getAudioSubtitlesMedia(server,id):
    printDebug("== ENTER: getAudioSubtitlesMedia ==", False)
    printDebug("Gather media stream info" ) 
    #Using PMS settings for audio and subtitle display
            
    #get metadata for audio and subtitle
    suburl="http://"+server+"/library/metadata/"+id
            
    html=getURL(suburl)
    tree=etree.fromstring(html)

    parts=[]
    partsCount=0
    subtitle={}
    subCount=0
    audio={}
    audioCount=0
    external={}

    options = tree.getiterator('Part')    
    
    contents="type"
    
    #Get the Parts info for media type and source selection 
    for stuff in options:
        try:
            bits=stuff.get('key'), stuff.get('file')
            parts.append(bits)
            partsCount += 1
        except: pass
        
    if g_streamControl == "1" or g_streamControl == "2":

        contents="all"
        tags=tree.getiterator('Stream')
        
        
        for bits in tags:
            stream=dict(bits.items())
            if stream['streamType'] == '2':
                audioCount += 1
                try:
                    if stream['selected'] == "1":
                        printDebug("Found preferred audio id: " + str(stream['id']) ) 
                        audio=stream
                except: pass
                     
            elif stream['streamType'] == '3':
                try:
                    if stream['selected'] == "1":
                        printDebug( "Found preferred subtitles id : " + str(stream['id']))
                        subCount += 1
                        subtitle=stream
                except:
                    try:
                        if stream['key']:
                            printDebug( "Found external subtitles id : " + str(stream['id']))
                            external=stream
                            external['key']='http://'+server+external['key']
                    except: pass
          
    else:
            printDebug( "Stream selection is set OFF")
              
    
    printDebug( {'contents':contents,'audio':audio, 'audioCount': audioCount, 'subtitle':subtitle, 'subCount':subCount ,'external':external, 'parts':parts, 'partsCount':partsCount})
    return {'contents':contents,'audio':audio, 'audioCount': audioCount, 'subtitle':subtitle, 'subCount':subCount ,'external':external, 'parts':parts, 'partsCount':partsCount}
   
#Right, this is used to play PMS library data file.  This function will attempt to update PMS as well.
#Only use this to play stuff you want to update in the library        
def PLAYEPISODE(id,vids,seek, duration):
        printDebug("== ENTER: PLAYEPISODE ==", False)
        #Use this to play PMS library items that you want up dated (Movies, TV shows)
        url = vids
      
        server=url.split('/')[2]

        streams=getAudioSubtitlesMedia(server,id)     
        url=selectMedia(streams['partsCount'],streams['parts'], server)

        protocol=url.split('/')[0]


        urlPath="/"+"/".join(url.split('/')[3:])
  
        if protocol == "file:":
            printDebug( "We are playing a file")
            #Split out the path from the URL
            playurl=url.split(':')[1][-1:]
        elif protocol == "http:":
            printDebug( "We are playing a stream")
            if g_transcode == "true":
                printDebug( "We will be transcoding the stream")
                playurl=transcode(id,url)
                if g_proxy =="true":
                    printDebug("Building Transcode Proxy URL and starting proxy")
                    import base64
                    headers=base64.b64encode(XBMCInternalHeaders)
                    #newurl=base64.b64encode(url)
                    playurl="http://127.0.0.1:"+g_proxyport+"/withheaders/"+base64.b64encode(playurl)+"/"+headers
                    
                    identifier=proxyControl("start")
                    
                    if identifier is False:
                        printDebug("Error - proxy not running")
                        xbmcgui.Dialog().ok("Error","Transcoding proxy not running")

            else:
                playurl=url+XBMCInternalHeaders
        else:
            playurl=url
   
        
        printDebug( "Current resume is " + str(seek))
        resumeSetting=__settings__.getSetting('resume')
        printDebug("Stored setting for resume is " + str(resumeSetting))
        if len(resumeSetting) > 0:
            resumeid, resumetime = resumeSetting.split("|")
            if resumeid == id:
                printDebug ("ID match, using settings resume time")
                resume = int(resumetime)
            else:
                resume = seek
        else:
            resume = seek
        
        printDebug("Resume has been set to " + str(resume))
        
        #Build a listitem, based on the url of the file
        item = xbmcgui.ListItem(path=playurl)
        result=1
            
        #If we passed a positive resume time, then we need to display the dialog box to ask the user what they want to do    
        if resume > 0:
            resumeseconds = resume
            
            #Human readable time
            displayTime = str(datetime.timedelta(seconds=int(resumeseconds)))
            
            #Build the dialog text
            dialogOptions = [ "Resume from " + str(displayTime) , "Start from beginning"]
            printDebug( "We have part way through video.  Display resume dialog")
            
            #Create a dialog object
            startTime = xbmcgui.Dialog()
            
            #Box displaying resume time or start at beginning
            result = startTime.select('Resuming playback..',dialogOptions)
            
            #result contains an integer based on the selected text.
            if result == -1:
                #-1 is an exit without choosing, so end the function and start again when the user selects a new file.
                return
        
        printDebug("handle is " + str(pluginhandle))
        #ok - this will start playback for the file pointed to by the url
        start = xbmcplugin.setResolvedUrl(pluginhandle, True, item)
        
        #Set a loop to wait for positive confirmation of playback
        count = 0
        while not xbmc.Player().isPlaying():
            printDebug( "Not playing yet...sleep for 2")
            count = count + 2
            if count >= 20:
                #Waited 20 seconds and still no movie playing - assume it isn't going to..
                return
            else:
                time.sleep(2)
                   
        #If we get this far, then XBMC must be playing
        
        #If the user chose to resume...
        if result == 0:
            #Need to skip forward (seconds)
            printDebug("Seeking to " + str(resumeseconds))
            xbmc.Player().seekTime((resumeseconds)) 
    
        #Next Set audio and subs
        setAudioSubtitles(streams)
 
       
        #OK, we have a file, playing at the correct stop.  Now we need to monitor the file playback to allow updates into PMS
        monitorPlayback(id,server, resume, duration)
        
        return

def setAudioSubtitles(stream):
    printDebug("== ENTER: setAudioSubtitles ==", False)
    #printDebug ("Found " + str(audioCount) + " audio streams")
    
    if stream['contents'] == "type":
        printDebug ("No streams to process.")
        
        if g_streamControl == "3":
            xbmc.Player().disableSubtitles()    
            printDebug ("All subs disabled")
        
        return True

    
    if g_streamControl == "1" or  g_streamControl == "2":
        audio=stream['audio']
        printDebug("Setting Audio Stream")
        #Audio Stream first        
        if stream['audioCount'] == 1:
            printDebug ("Only one audio stream present - will leave as default")
        elif stream['audioCount'] > 1:
            printDebug ("Multiple audio stream. Attempting to set to local language")
            try:
                if audio['selected'] == "1":
                    printDebug ("Found preferred language at index " + str(int(audio['index'])-1))
                    xbmc.Player().setAudioStream(int(audio['index'])-1)
                    printDebug ("Audio set")
            except: pass
      
    #Try and set embedded subtitles
    if g_streamControl == "1":
        subtitle=stream['subtitle']
        printDebug("Setting Subtitle Stream", True)
        try:
            if stream['subCount'] > 0 and subtitle['languageCode']:
                printDebug ("Found embedded subtitle for local language" )
                printDebug ("Enabling embedded subtitles")
                xbmc.Player().disableSubtitles()
                xbmc.Player().setSubtitles("dummy")
                time.sleep(1)
                    
                done = "go"
                two = str(codeToCountry(subtitle['languageCode']))

                while done == "go":
                    one = str(xbmc.Player().getSubtitles())
                        
                    if one == two:
                        done = "stop"
                    
                    xbmc.executebuiltin("Action(NextSubtitle)")                              
                    time.sleep(1)
            else:
                printDebug ("No subtitles to set")
            return True
        except:
            printDebug("Unable to set subtitles")
  
    if g_streamControl == "1" or g_streamControl == "2":
        external=stream['external']
        printDebug("Setting External subtitle Stream")
    
        try:   
            if external:
                try:
                    printDebug ("External of type ["+external['codec']+"]")
                    if external['codec'] == "idx" or external['codec'] =="sub":
                        printDebug ("Skipping IDX/SUB pair - not supported yet")
                    else:    
                        xbmc.Player().setSubtitles(external['key'])
                except: 
                    xbmc.Player().disableSubtitles()    
                
                return True
            else:
                printDebug ("No external subtitles available. Will turn off subs")
        except:
            printDebug ("No External subs to set")
            
    xbmc.Player().disableSubtitles()    
    return False
        
def codeToCountry( id ):
  languages = { 
  	"None": "none",
    "alb" : "Albanian",
    "ara" : "Arabic"            ,
    "arm" : "Belarusian"        ,
    "bos" : "Bosnian"           ,
    "bul" : "Bulgarian"         ,
    "cat" : "Catalan"           ,
    "chi" : "Chinese"           ,
    "hrv" : "Croatian"          ,
    "cze" : "Czech"             ,
    "dan" : "Danish"            ,
    "dut" : "Dutch"             ,
    "eng" : "English"           ,
    "epo" : "Esperanto"         ,
    "est" : "Estonian"          ,
    "per" : "Farsi"             ,
    "fin" : "Finnish"           ,
    "fre" : "French"            ,
    "glg" : "Galician"          ,
    "geo" : "Georgian"          ,
    "ger" : "German"            ,
    "ell" : "Greek"             ,
    "heb" : "Hebrew"            ,
    "hin" : "Hindi"             ,
    "hun" : "Hungarian"         ,
    "ice" : "Icelandic"         ,
    "ind" : "Indonesian"        ,
    "ita" : "Italian"           ,
    "jpn" : "Japanese"          ,
    "kaz" : "Kazakh"            ,
    "kor" : "Korean"            ,
    "lav" : "Latvian"           ,
    "lit" : "Lithuanian"        ,
    "ltz" : "Luxembourgish"     ,
    "mac" : "Macedonian"        ,
    "may" : "Malay"             ,
    "nor" : "Norwegian"         ,
    "oci" : "Occitan"           ,
    "pol" : "Polish"            ,
    "por" : "Portuguese"        ,
    "pob" : "Portuguese (Brazil)" ,
    "rum" : "Romanian"          ,
    "rus" : "Russian"           ,
    "scc" : "SerbianLatin"      ,
    "scc" : "Serbian"           ,
    "slo" : "Slovak"            ,
    "slv" : "Slovenian"         ,
    "spa" : "Spanish"           ,
    "swe" : "Swedish"           ,
    "syr" : "Syriac"            ,
    "tha" : "Thai"              ,
    "tur" : "Turkish"           ,
    "ukr" : "Ukrainian"         ,
    "urd" : "Urdu"              ,
    "vie" : "Vietnamese"        ,
    "all" : "All"
  }
  return languages[ id ]        
        
def proxyControl(command):
    printDebug("======= ENTER: proxyControl() =======", False)
    import subprocess
    if command == "start":
        printDebug("Start proxy")
        filestring="XBMC.RunScript(special://home/addons/plugin.video.plexbmc/HLSproxy.py,\""+PLUGINPATH+"/terminate.proxy\","+g_proxyport+")"
        printDebug( str(filestring))
        xbmc.executebuiltin(filestring)
        time.sleep(2)
        
    elif command == "stop":
        printDebug("Stop proxy")
        time.sleep(2)
        done=getURL("http://127.0.0.1:"+g_proxyport+"/stop")
    else:
        printDebug("No proxy command specified")
        return False
    #check result
    
    html=getURL('http://127.0.0.1:'+g_proxyport+'/version', surpress=True)
    
    if command == "start":
        if html is False:
            #failure
            printDebug("Start Failure")
            return False
        else:
            printDebug("Start Success")        
            #success
            return True
    elif command == "stop":
        if html is False:
            #success
            printDebug("Stop Success")          
            return True
        else:
            #failure
            printDebug("Stop Failure")           
            return False
    
    return False    
           
def selectMedia(count, options, server):   
    printDebug("== ENTER: selectMedia ==", False)
    #if we have two or more files for the same movie, then present a screen
    result=0
    
    if count > 1:
    
        dialogOptions=[]
        for items in options:
            name=items[1].split('/')[-1]
            dialogOptions.append(name)
    
        #Build the dialog text
        printDebug("Create selection dialog box - we have a decision to make!")
            
        #Create a dialog object
        startTime = xbmcgui.Dialog()
            
        #Box displaying resume time or start at beginning
        result = startTime.select('Choose which file',dialogOptions)
            
        #result contains an integer based on the selected text.
        if result == -1:
            #-1 is an exit without choosing, so end the function and start again when the user selects a new file.
            return
        
   
    newurl=mediaType({'key': options[result][0] , 'file' : options[result][1]},server)
   
    printDebug("We have selected media at " + newurl)
    #PLAYEPISODE(id,newurl,seek, duration)
    return newurl
           
#Monitor function so we can update PMS
def monitorPlayback(id, server, resume, duration):
    printDebug("== ENTER: monitorPlayback ==", False)
    #Need to monitor the running playback, so we can determine a few things:
    #1. If the file has completed normally (i.e. the movie has finished)
    #2. If the file has been stopped halfway through - need to record the stop time.
    
    #Get the server name to update
    if len(server.split(':')) == 1:
        server=server
    
    #Get the current time (either the resumed time or 0)
    currentTime=int(resume)
    
    #If we didn;t get a duration time (for whatever reason) read it from the playing file
    if duration == 0 and xbmc.Player().isPlaying():
        #This sometimes fails.  Don't know why probably a timing issue
        duration = int(xbmc.Player().getTotalTime())
    
    monitorCount=0    
    #Whilst the file is playing back
    while xbmc.Player().isPlaying():
        #Get the current playback time
        currentTime = int(xbmc.Player().getTime())
                
        #Convert it into a percentage done, using the total length of the film
        progress = int((float(currentTime)/float(duration))*100) 

        #Now sleep for 5 seconds
        time.sleep(5)
        if g_debug == "true":
            monitorCount+=1
            if monitorCount == 5:
                printDebug ("Still monitoring")
                monitorCount=0
          
    #If we get this far, playback has stopped
    
    if g_transcode == "true" and g_proxy == "true":
        result = proxyControl("stop")
    
    printDebug( "Playback stopped at " + str(currentTime) + " which is " + str(progress) + "%.")
    if progress <= 5:
        #Then we hadn't watched enough to make any changes
        printDebug( "Less than 5% played, so do no store resume time but ensure that film is marked unwatched")
        updateURL="http://"+server+"/:/unscrobble?key="+id+"&identifier=com.plexapp.plugins.library"
        __settings__.setSetting('resume', "")
        
    elif progress >= 95:
        #Then we were 95% of the way through, so we mark the file as watched
        printDebug( "More than 95% completed, so mark as watched")
        updateURL="http://"+server+"/:/scrobble?key="+id+"&identifier=com.plexapp.plugins.library"
        __settings__.setSetting('resume', "")
    else:
        #we were more than 5% and less then 95% of the way through, store the resume time
        printDebug( "More than 5% and less than 95% of the way through, so store resume time")
        updateURL="http://"+server+"/:/progress?key="+id+"&identifier=com.plexapp.plugins.library&time="+str(currentTime*1000)
        printDebug("Creating a temporary new resume time of " + str(currentTime)) 
        __settings__.setSetting('resume', str(id)+"|"+str(currentTime))
        
    #Submit the update URL    
    output = getURL(updateURL, "Updating PMS...", True)
    printDebug("Update returned " + str(output))
    
     
    return
    
#Just a standard playback 
def PLAY(vids):
        printDebug("== ENTER: PLAY ==", False)
        #This is for playing standard non-PMS library files (such as Plugins)
        url = vids+XBMCInternalHeaders
        item = xbmcgui.ListItem(path=url)
        return xbmcplugin.setResolvedUrl(pluginhandle, True, item)

def videoPluginPlay(vids):
        printDebug("== ENTER: videopluginplay ==", False)
        #This is for playing standard non-PMS library files (such as Plugins)
        
        header=""
        if vids.split('/')[4] == "amt":
            printDebug("Adding headers for AMT")
            #Apple trailers - need a special UA header 
            uagent="QuickTime/7.6.5 (qtver=7.6.5;os=Windows NT 5.1Service Pack 3)"
            agentHeader="User-Agent="+urllib.quote_plus(uagent)
                                
            if XBMCInternalHeaders == "":
                header="|"+agentHeader
            else:
                header="&"+agentHeader

                
        #Pleader="&X-Plex-Client-Capabilities="+urllib.quote_plus("protocols=http-live-streaming,http-mp4-streaming,http-mp4-video,http-mp4-video-720p,http-streaming-video,http-streaming-video-720p,webkit;videoDecoders=h264{profile:high&resolution:1080&level:51};audioDecoders=mp3,aac")
        
        #if XBMCInternalHeaders == "":
        #    Pleader="|"+Pleader
        #else:
        #    Pleader="&"+Pleader
        
        url=vids+XBMCInternalHeaders+header#+Pleader
        
        item = xbmcgui.ListItem(path=url)
        return xbmcplugin.setResolvedUrl(pluginhandle, True, item)        
              
#Function to parse the arguments passed to the plugin..
def get_params():
        printDebug("== ENTER: get_params ==", False)
        param=[]
        paramstring=sys.argv[2]
        if len(paramstring)>=2:
                params=sys.argv[2]
                #Rather than replace ? with ' ' - I split of the first char, which is always a ? (hopefully)
                #Could always add a check as well..
                cleanedparams=params[1:] #.replace('?','')
                if (params[len(params)-1]=='/'):
                        params=params[0:len(params)-2]
                pairsofparams=cleanedparams.split('&')
                param={}
                for i in range(len(pairsofparams)):
                        splitparams={}
                        #Right, extended urls that contain = do not parse correctly and this tops plugins from working
                        #Need to think of a better way to do the split, at the moment i'm hacking this by gluing the
                        #two bits back togethers.. nasty...
                        splitparams=pairsofparams[i].split('=')
                        if (len(splitparams))==2:
                                param[splitparams[0]]=splitparams[1]
                        elif (len(splitparams))==3:
                                param[splitparams[0]]=splitparams[1]+"="+splitparams[2]
                                
        return param

def getContent(url):  
    printDebug("== ENTER: getContent ==", False)
    #We've been called at mode 0, by ROOT becuase we are going to traverse the secondary menus
        
    #First we need to peek at the XML, to see if we've hit any video links yet.
        
    server=url.split('/')[2]
    lastbit=url.split('/')[-1]
    secondtolast=url.split('/')[-2]
    
    if lastbit.startswith('search'):
        #Found search URL.  Bring up keyboard and get input for query string
        printDebug("This is a search URL.  Bringing up keyboard")
        kb = xbmc.Keyboard('', 'heading')
        kb.setHeading('Enter search term') # optional
        kb.doModal()
        if (kb.isConfirmed()):
            text = kb.getText()
            printDebug("Search term input: "+ text)
            url=url+'&query='+text
        else:
            return
     
    html=getURL(url)
    
    if html is False:
        return
        
    tree=etree.fromstring(html)
 
    if lastbit == "folder":
        processDirectory(url,tree, server)
        return
 
    arguments=dict(tree.items())
    
    if arguments['viewGroup'] == "movie":
        printDebug( "this is movie XML, passing to Movies")
        Movies(url, tree)
        return
    elif arguments['viewGroup'] == "show":
        printDebug( "This is tv show XML, passing to SHOW")
        SHOWS(url,tree)
        return
    elif arguments['viewGroup'] == "episode":
        printDebug("This is TV episode XML, passing to EPISODES")
        if lastbit.startswith("unwatched"):
            printDebug("PMS data error, contents is actually TV Shows.  Passing to SHOWS.")
            SHOWS(url,tree)
        else:    
            EPISODES(url,tree)
        return
    elif arguments['viewGroup'] == 'artist':
        printDebug( "This is music XML, passing to music")
        if lastbit.startswith('album') or secondtolast.startswith('decade') or secondtolast.startswith('year'):
            albums(url,tree)
        else:    
            artist(url, tree)
        return
    elif arguments['viewGroup'] == "track":
        printDebug("This is track XML - checking further")
        if lastbit.startswith('recentlyAdded'):
            printDebug("Passing to Albums")
            albums(url, tree)
        else:
            printDebug("Passing to Tracks")
            tracks(url, tree)
        return
    
    processDirectory(url,tree)
    return

def processDirectory(url,tree=None):
    printDebug("== ENTER: processDirectory ==", False)
    #else we have a secondary, which we'll process here
    printDebug("Processing secondary menus")
    xbmcplugin.setContent(pluginhandle, 'movies')

    server=getServerFromURL(url)
    
    try:
        fanart=tree.get('art').split('?')[0] #drops the guid from the fanart image
        art_url='http://'+server+fanart#.encode('utf-8')
        #art_url='http://'+server+g_port+'/photo/:/transcode?url='+art_url+'&width=1280&height=720'
    except:  
        art_url=None 

    
    for apple in tree:
        arguments=dict(apple.items())
        properties={}
        properties['title']=arguments['title']
        
        try:
            arguments['thumb']=art_url
            arguments['fanart_image']=arguments['thumb']
        except:
            arguments['thumb']=""

        try:
            if arguments['key'].split('/')[0] == "http:":
                p_url=arguments['key']
            elif arguments['key'][0] == '/':
                #The key begins with a slah, there is absolute
                p_url='http://'+server+str(arguments['key'])
            else:
                #Build the next level URL and add the link on screen
                p_url=url+'/'+str(arguments['key'])
        except: continue    
        #If we have a key error - then we don't add to the list.
        
        n_url=p_url+'&mode=0'

        addDir(n_url,properties,arguments)
        
    xbmcplugin.endOfDirectory(pluginhandle)

#Function that will return a m3u8 playlist URL from a PMS stream URL
def transcode(id,url):
    printDebug("== ENTER: transcode ==", False)
    # First get the time since Epoch
        
    #Had to use some customised modules to get hmac sha256 working on python 2.4
    import base64
    
    server=url.split('/')[2]
    filestream=urllib.quote_plus("/"+"/".join(url.split('/')[3:]))
  
    if g_transcodefmt == "m3u8":
        myurl = "/video/:/transcode/segmented/start.m3u8?identifier=com.plexapp.plugins.library&ratingKey=" + id + "&offset=0&quality="+g_quality+"&url=http%3A%2F%2Flocalhost%3A32400" + filestream + "&3g=0&httpCookies=&userAgent="
    elif g_transcodefmt == "flv":
        myurl="/video/:/transcode/generic.flv?format=flv&videoCodec=libx264&vpre=video-embedded-h264&videoBitrate=5000&audioCodec=libfaac&apre=audio-embedded-aac&audioBitrate=128&size=640x480&fakeContentLength=2000000000&url=http%3A%2F%2Flocalhost%3A32400"  + filestream + "&3g=0&httpCookies=&userAgent="
    else:
        printDebug( "Woah!!  Barmey settings error....Bale.....")
        return url

    now=str(int(round(time.time(),0)))
    
    msg = myurl+"@"+now
    printDebug("Message to hash is " + msg)
    
    #These are the DEV API keys - may need to change them on release
    publicKey="KQMIY6GATPC63AIMC4R2"
    privateKey = base64.decodestring("k3U6GLkZOoNIoSgjDshPErvqMIFdE0xMTx8kgsrhnC0=")
       
    #If python is > 2.4 then do this
    if sys.version_info[:2] > (2,4):
        import hashlib, hmac
        hash=hmac.new(privateKey,msg,digestmod=hashlib.sha256)
    else:
        import sha256, hmacsha256
        hash=hmacsha256.new(privateKey, msg, digestmod=sha256)
    
    printDebug("HMAC after hash is " + hash.hexdigest())
    
    #Encode the binary hash in base64 for transmission
    token=base64.b64encode(hash.digest())
    
    #Send as part of URL to avoid the case sensitive header issue.
    fullURL="http://"+server+myurl+"&X-Plex-Access-Key="+publicKey+"&X-Plex-Access-Time="+str(now)+"&X-Plex-Access-Code="+urllib.quote_plus(token)
    
    printDebug("Transcode URL is " + fullURL)
    
    if g_transcodefmt == "m3u8":
    
        printDebug("Getting m3u8 playlist")
        #Send request for transcode to PMS
        Treq = urllib2.Request(fullURL)
        Tresponse = urllib2.urlopen(Treq)
        Tlink=Tresponse.read()
        printDebug("Initial playlist is " + str(Tlink))
        Tresponse.close()   
    
        #tLink contains initual m3u8 playlist.  Pull out the last entry as the actual stream to use (am assuming only single stream)
    
        session=Tlink.split()[-1]
        printDebug("Getting bandwidth playlist " + session)
    
        #Append to URL to create link to m3u8 playlist containing the actual media.
        sessionurl="http://"+server+"/video/:/transcode/segmented/"+session
    else: 
        sessionurl=fullURL
    
   
    printDebug("Transcoded media location URL " + sessionurl)
    
    return sessionurl
     
def artist(url,tree=None):
        printDebug("== ENTER: artist ==", False)
        xbmcplugin.setContent(pluginhandle, 'artists')

        #xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
        
        #Get the URL and server name.  Get the XML and parse
        if tree is None:
        
            html=getURL(url)
            
            if html is False:
                return

        
            tree=etree.fromstring(html)
        
        server=getServerFromURL(url)
        
        #For each directory tag we find
        ShowTags=tree.findall('Directory') # These type of calls seriously slow down plugins
        for show in ShowTags:

            arguments=dict(show.items())
        
            tempgenre=[]
            
            #Lets grab all the info we can quickly through either a dictionary, or assignment to a list
            #We'll process it later
            for child in show:
                try:
                    tempgenre.append(child.get('tag'))
                except:pass
                
            #Create the basic data structures to pass up
            properties={}  #Create a dictionary for properties with some defaults(i.e. ListItem properties)
            
            #Get name
            try:
                properties['title']=properties['artist']=arguments['title'].encode('utf-8')
            except: pass
                        
            #Get the Plot          
            try:
                properties['plot']=arguments['summary']
            except: pass
                                        
            #get Genre
            try:
                properties['genre']=" / ".join(tempgenre)
            except:pass
                
            #Get the picture to use
            arguments['thumb']=getThumb(arguments, server)
               
            #Get a nice big picture  

            arguments['fanart_image']=getFanart(arguments, server)
           
            arguments['type']="Music"

            mode=14 # grab season details
            url='http://'+server+'/library/metadata/'+arguments['ratingKey']+'/children'+"&mode="+str(mode)
            
            addDir(url,properties,arguments) 
            
        #End the listing    
        xbmcplugin.endOfDirectory(pluginhandle)

def albums(url, tree=None):
        printDebug("== ENTER: albums ==", False)
        xbmcplugin.setContent(pluginhandle, 'albums')

        #xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
       
        #Get the URL and server name.  Get the XML and parse
        if tree is None:
        
            html=getURL(url)
            
            if html is False:
                return

        
            tree=etree.fromstring(html)
        
        server=getServerFromURL(url)
        
        try:
            treeargs=dict(tree.items())
            artist=treeargs['parentTitle']
        except: pass
        
        sectionart=getFanart(treeargs, server)
        
        #For all the directory tags
        ShowTags=tree.findall('Directory')
        for show in ShowTags:
        
            arguments=dict(show.items())
            #Build basic data structures
            properties={}   #Create a dictionary for properties with some defaults(i.e. ListItem properties)
 
            #Get name
            try:
                properties['title']=properties['album']=arguments['title'].encode('utf-8')
            except: pass
       

            #Get the picture to use
            arguments['thumb']=getThumb(arguments, server)
               
            #Get a nice big picture  

            arguments['fanart_image']=getFanart(arguments, server)
            try:
                if arguments['fanart_image'] == "":
                    arguments['fanart_image']=sectionart
            except:
                pass

            try:
                properties['artist']=artist
            except: 
                try:
                    properties['artist']=arguments['parentTitle']
                except:
                    pass
                        
            #Get number of watched episodes
            try:
                watched=arguments['viewedLeafCount']
                arguments['WatchedEpisodes']=int(watched)
                arguments['UnWatchedEpisodes']=properties['episode']-arguments['WatchedEpisodes']
                if arguments['UnWatchedEpisodes'] <= 0:
                    properties['overlay']=7
            except:pass
    
            #Get the Plot          
            try:
                properties['plot']=arguments['summary']
            except: pass

            arguments['type']="Music"
            mode=15
            
            try:
                properties['year']=int(arguments['year'])
            except: pass
            
            url='http://'+server+arguments['key']+"&mode="+str(mode)
            #Set the mode to episodes, as that is what's next 

            #Build the screen directory listing
            addDir(url,properties,arguments) 
            
        #All done, so end the listing
        xbmcplugin.endOfDirectory(pluginhandle)

def tracks(url,tree=None):
        printDebug("== ENTER: tracks ==", False)
        xbmcplugin.setContent(pluginhandle, 'songs')
        
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_TRACKNUM)
        
        #Get the server
        target=url.split('/')[-1]
        
        #Get the URL and server name.  Get the XML and parse
        if tree is None:
        
            html=getURL(url)
            
            if html is False:
                return

        
            tree=etree.fromstring(html)
        
        ShowTags=tree.findall('Track')
        
        server=getServerFromURL(url)
             
        treeargs=dict(tree.items()) 
 
        try: 
            if not target == "allLeaves":
                #Name of the show
                try:
                    artistname=tree.get('grandparentTitle')
                except: pass
                
                #the album
                try:
                    albumname = tree.get('parentTitle')
                except: pass
            
                try:
                    sectionthumb=getThumb(treeargs, server)
                except: pass
                
        except: pass
         
        sectionart=getFanart(treeargs,server) 
         
        #right, not for each show we find
        for show in ShowTags:
            #print show
            
            arguments=dict(show.items())
            tempgenre=[]
            
            #Lets grab all the info we can quickly through either a dictionary, or assignment to a list
            #We'll process it later
            for child in show:
                if child.tag == "Media":
                    mediaarguments = dict(child.items())
                        
                    for babies in child:
                        if babies.tag == "Part":
                            partarguments=(dict(babies.items()))
                elif child.tag == "Genre":
                    tempgenre.append(child.get('tag'))
            
            #required to grab to check if file is a .strm file
            #Can't play strm files, so lets not bother listing them. 
            if partarguments['file'].find('.strm')>0:
                print "Found unsupported .strm file.  Will not list"
                continue
           
            printDebug( "args is " + str(arguments))
            printDebug( "Media is " + str(mediaarguments))
            printDebug( "Part is " + str(partarguments))
            
            #Set basic structure with some defaults.  Overlay 6 is unwatched
            properties={}   #Create a dictionary for properties with some defaults(i.e. ListItem properties)
            
            #Get the tracknumber number
            try:
                properties['TrackNumber']=int(arguments['index'])
            except: pass

            #Get name
            try:
                properties['title']=arguments['title'].encode('utf-8')
            except: pass
                                    
            #Get how good it is, based on your votes...
            try:
                properties['rating']=float(arguments['rating'])
            except: pass
            
            #Get the last played position  
            try:
                arguments['viewOffset']=int(arguments['viewOffset'])/1000
            except:
                arguments['viewOffset']=0

                        
            #If we are processing an "All Episodes" directory, then get the season from the video tag
            
            try:
                properties['album']=albumname
            except: 
                properties['album']=arguments['parentTitle']
            
                    
            #Check if we got the showname from the main tag        
            try:
                properties['artist']=artistname
            except:
                properties['artist']=arguments['grandparentTitle']
                
            #Get the picture to use
            arguments['thumb']=getThumb(arguments, server)
            try:
                if arguments['thumb'].find('/resources/movie.png') > 0:
                    arguments['thumb']=sectionthumb
            except: pass
                
             

            #Get a nice big picture  
            arguments['fanart_image']=getFanart(arguments, server)  
            try:
                if arguments['fanart_image'] == "":
                    arguments['fanart_image']=sectionart
            except:
                pass
                
            #Assign standard metadata
            #Genre        
            properties['genre']=" / ".join(tempgenre) 
            
            
            #Set the film duration 
            try:
                arguments['duration']=mediaarguments['duration']
            except KeyError:
                try:
                    arguments['duration']
                except:
                    arguments['duration']=0
             
            arguments['duration']=int(arguments['duration'])/1000
            properties['duration']=arguments['duration']
            
            #set type
            arguments['type']="Music"
            
            #If we are streaming, then get the virtual location
            url=mediaType(partarguments,server)
            #Set mode 5, which is play            
            mode=12

            u=str(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(properties['title'])+"&resume="+str(arguments['viewOffset'])+"&id="+str(arguments['ratingKey'])+"&duration="+str(arguments['duration'])
                
            #Build a file link and loop
            addLink(u,properties,arguments)        
        
        #End the listing
        xbmcplugin.endOfDirectory(pluginhandle)

#What to do to process Plex video Plugin structures        
def PlexPlugins(url):
        printDebug("== ENTER: PlexPlugins ==", False)
        xbmcplugin.setContent(pluginhandle, 'movies')

        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)

        #get the serverm URL, XML and parse
        server=url.split('/')[2]
        html=getURL(url)
        
        if html is False:
            return

        tree=etree.fromstring(html)
        
        try:
            sectionArt=getFanart(dict(tree.items()),server)
        except: pass
               
        for orange in tree:
               
            arguments=dict(orange.items())

            #Set up the basic structures
            properties={'overlay':6}
                        
            try: 
                properties['title']=arguments['title'].encode('utf-8')
            except:
                try:
                    properties['title']=arguments['name'].encode('utf-8')
                except:
                    properties['title']="unknown"
                    
            arguments['thumb']=getThumb(arguments, server)
            
            arguments['fanart_image']=getFanart(arguments, server)
            try:
                if arguments['fanart_image'] == "":
                    arguments['fanart_image']=sectionArt
            except:
                pass

            p_url=getLinkURL(url, arguments, server)

            
            if orange.tag == "Directory" or orange.tag == "Podcast":
                #We have a directory tag, so come back into this function
                mode=7   
                s_url=p_url+"&mode="+str(mode)
                
                #Set type
                arguments['type']="Video"
                
                addDir(s_url, properties, arguments)
                    
            #If we have some video links as well
            elif orange.tag == "Video":
             
                #Set the mode to play them this time
                mode=18                       
                    
                #Build the URl and add a link to the file
                v_url=p_url+"&mode="+str(mode)    
                
                #Set type
                arguments['type']="Video"
               
                addLink(v_url, properties, arguments)

                
        #Ahh, end of the list   
        xbmcplugin.endOfDirectory(pluginhandle)        
        
def photo(url):
    printDebug("== ENTER: photos ==", False)
    server=url.split('/')[2]
    
    html=getURL(url)
    
    if html is False:
        return
    
    tree=etree.fromstring(html)
    
    try:
        sectionArt=getFanart(dict(tree.items()),server)
    except: pass
 
    for banana in tree:
        
        arguments=dict(banana.items())
        properties={}
        
        try:
            properties['title']=properties['name']=arguments['title'].encode('utf-8')
        except:
            properties['title']=properties['name']="Unknown"
            
        try: 
            properties['title']=arguments['title'].encode('utf-8')
        except:
            try:
                properties['title']=arguments['name'].encode('utf-8')
            except:
                properties['title']="unknown"
                 
        arguments['thumb']=getThumb(arguments, server)
        
        arguments['fanart_image']=getFanart(arguments, server)
        try:
            if arguments['fanart_image'] == "":
                arguments['fanart_image']=sectionArt
        except:
            pass

        u=getLinkURL(url, arguments, server)   
                
        if banana.tag == "Directory":
            mode=16
            u=u+"&mode="+str(mode)
            addDir(u,properties,arguments)
    
        elif banana.tag == "Photo":
        
            arguments['type']="Picture"
            addLink(u,properties,arguments)

    xbmcplugin.endOfDirectory(pluginhandle)

def music(url, tree=None):
    printDebug("== ENTER: music ==", False)
    xbmcplugin.setContent(pluginhandle, 'artists')

    server=getServerFromURL(url)
    
    if tree is None:
        html=getURL(url)
    
        if html is False:
            return
   
        tree=etree.fromstring(html)
 
    try:
        sectionArt=getFanart(dict(tree.items()),server)
    except: pass
 
    for grapes in tree:
       
        arguments=dict(grapes.items())
        arguments['type']="Music"        
        properties={}
        
        try:
            if arguments['key'] == "":
                continue
        except: pass
                          
        arguments['thumb']=getThumb(arguments, server)

        arguments['fanart_image']=getFanart(arguments, server)
        try:
            if arguments['fanart_image'] == "":
                arguments['fanart_image']=sectionArt
        except:
            pass
        
        try:
            properties['genre']=arguments['genre']
        except: pass

        try:
            properties['artist']=arguments['artist']
        except:pass
                
        try:
            properties['year']=int(arguments['year'])
        except:pass

        try:
            properties['album']=arguments['album']
        except:pass
        
        try: 
            properties['tracknumber']=int(arguments['index'])
        except:pass
        
        properties['title']="Unknown"
   
        u=getLinkURL(url, arguments, server)
        
        if grapes.tag == "Track":
            printDebug("Track Tag")
            xbmcplugin.setContent(pluginhandle, 'songs')
            #xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_TRACKNUM)
            
            try:
                properties['title']=arguments['track'].encode('utf-8')
            except: pass
            
                         
            #Set the track length 
            try:
                arguments['totalTime']=int(arguments['totalTime'])/1000
                properties['duration']=arguments['totalTime']
            except: pass
           
            mode=12
            u=u+"&mode="+str(mode)
            addLink(u,properties,arguments)

        else: 
        
            if grapes.tag == "Artist":
                printDebug("Artist Tag")
                xbmcplugin.setContent(pluginhandle, 'artists')
                try:
                    properties['title']=arguments['artist']
                except: 
                    properties['title']="Unknown"
             
            elif grapes.tag == "Album":
                printDebug("Album Tag")
                xbmcplugin.setContent(pluginhandle, 'albums')
                try:    
                    properties['title']=arguments['album']
                except: pass
            elif grapes.tag == "Genre":
                try:    
                    properties['title']=arguments['genre']
                except: pass
            
            else:
                printDebug("Generic Tag: " + grapes.tag)
                try:
                    properties['title']=arguments['title']
                except: pass
            
            mode=17
            u=u+"&mode="+str(mode)
            addDir(u,properties,arguments)
        
    xbmcplugin.endOfDirectory(pluginhandle)    

## Utilities    
    
def getThumb(arguments, server):
    thumbnail=""
    
    try:
        if arguments['thumb'].split('/')[0] == "http:":
            return arguments['thumb']
        else:    
            thumbnail='http://'+server+arguments['thumb'].split('?t')[0]
    except:
        thumbnail=g_loc+'/resources/movie.png'  
     
    return thumbnail

def getFanart(arguments, server):
    fanart=""

    try:
        if arguments['art'].split('/')[0] == "http:":
            return arguments['art']
        else:    
            fanart='http://'+server+arguments['art'].split('?t')[0]
    except:
        fanart=""  
     
    return fanart

def getServerFromURL(url):
    return url.split('/')[2]

def getLinkURL(url, arguments, server):
    try:
        if arguments['key'].split('/')[0] == "http:":
            return arguments['key']
        elif arguments['key'][0] == '/':
            #The key begins with a slash, there is absolute
            return 'http://'+server+str(arguments['key'])
        else:
            #Build the next level URL and add the link on screen
            return url+'/'+str(arguments['key'])
    except:pass
     
    return url
    
# Plex Plugin add/remove utilities    
def plexOnline(url):
    printDebug("== ENTER: plexOnline ==")
    xbmcplugin.setContent(pluginhandle, 'files')

    server=url.split('/')[2]
    
    html=getURL(url)
    
    if html is False:
        return
    
    tree=etree.fromstring(html)
        
    for lemons in tree:
       
        arguments=dict(lemons.items())
        arguments['type']="Video"        
        properties={}
        
        try:
            if arguments['key'] == "":
                continue
        except: pass
        
        try:
            properties['title']=arguments['title']
        except:
            try:
                properties['title']=arguments['name']
            except:
                properties['title']="Unknown"
        
        mode=19
        
        if arguments['key'][0] == '/':
            #The key begins with a slah, there is absolute
            u='http://'+server+str(arguments['key'])
        else:
            #Build the next level URL and add the link on screen
            u=url+'/'+str(arguments['key'])

        
        try:
            if arguments['installed'] == "1":
                properties['title']=properties['title']+" (installed)"
                mode=20
            elif arguments['installed'] == "0":
                mode=20
                
        except:pass 
        
        try:
            if not arguments['thumb'].split('/')[0] == "http:":
                arguments['thumb']='http://'+server+arguments['thumb'].encode('utf-8')
        except:
            thumb=g_loc+'/resources/movie.png'  
            arguments['thumb']=thumb

        properties['title']=properties['title'].encode('utf-8')    
            
        u=u+"&mode="+str(mode)+"&name="+urllib.quote_plus(properties['title'])
        addDir(u, properties, arguments)

    xbmcplugin.endOfDirectory(pluginhandle)    
   
def install(url, name):
    printDebug("== ENTER: install ==", False)
    html=getURL(url)
    if html is False:
        return
    tree = etree.fromstring(html)
    
    if tree.get('size') == "1":
        #This plugin is probably not install
        printDebug("Not installed.  Print dialog")
        ret = xbmcgui.Dialog().yesno("Plex Online","About to install " + name)

        if ret:
            printDebug("Installing....")
            installed = getURL(url+"/install")
            tree = etree.fromstring(installed)
    
            msg=tree.get('message')
            printDebug(msg)
            xbmcgui.Dialog().ok("Plex Online",msg)

    else:
        #This plugin is already installed
        printDebug("Already installed")
        operations={}
        i=0
        for plums in tree.findall('Directory'):
            operations[i]=plums.get('key').split('/')[-1]
            i+=1
        
        options=operations.values()
        
        ret = xbmcgui.Dialog().select("This plugin is already installed..",options)
        
        if ret == -1:
            printDebug("No option selected, cancelling")
            return
        
        printDebug("Option " + str(ret) + " selected.  Operation is " + operations[ret])
        u=url+"/"+operations[ret]

        action = getURL(u)
        tree = etree.fromstring(action)
    
        msg=tree.get('message')
        printDebug(msg)
        xbmcgui.Dialog().ok("Plex Online",msg)
   
    return   

def channelView(url):

    printDebug("== ENTER: channelView ==", False)
    html=getURL(url)
    if html is False:
        return
    tree = etree.fromstring(html)
    
    server=getServerFromURL(url)
    
    for channels in tree.getiterator('Directory'):
    
        try:
            if channels.get('local') == "0":
                continue
        except: pass
            
        arguments=dict(channels.items())

    
        arguments['fanart_image']=getFanart(arguments, server)

        arguments['thumb']=getThumb(arguments, server)
        
        properties={}
        properties['title']=arguments['title']

        suffix=arguments['path'].split('/')[1]
        
        try:
            if arguments['unique']=='0':
                properties['title']=properties['title']+" ("+suffix+")"
        except:
            pass
               
        try:
            if arguments['path'].split('/')[0] == "http:":
                p_url=arguments['path']
            elif arguments['path'][0] == '/':
                #The path begins with a slah, there is absolute
                p_url='http://'+server+str(arguments['path'])
            else:
                #Build the next level URL and add the link on screen
                p_url=url+'/'+str(arguments['path'])
        except: continue    
        #If we have a path error - then we don't add to the list.
        
        if suffix == "photos":
            mode=16
        elif suffix == "video":
            mode=7
        elif suffix == "music":
            mode=17
        else:
            mode=0
        
        n_url=p_url+'&mode='+str(mode)

        addDir(n_url,properties,arguments)
        
    xbmcplugin.endOfDirectory(pluginhandle)
                                
              
def skin():
    #Gather some data and set the window properties
    printDebug("== ENTER: skin() ==", False)
    #Get the global host variable set in settings
    host=g_host
    WINDOW = xbmcgui.Window( 10000 )
 
    Servers=[]
      
    #If we have a remote host, then don;t do local discovery as it won't work
    if g_bonjour == "true":
        #Get the HTML for the URL
        url = 'http://'+host+'/servers'
        html=getURL(url)
            
        if html is False:
            return
               
        #Pass HTML to BSS to convert it into a nice parasble tree.
        tree=etree.fromstring(html)
                
        #Now, find all those server tags
        LibraryTags=tree.findall('Server')        
       
        #Now, for each tag, pull out the name of the server and it's network name
        for object in LibraryTags:
            name=object.get('name').encode('utf-8')
            host=object.get('host')
            Servers.append([name,host])
    else:
        Servers.append(["remote",g_host])
        Servers += g_serverList
    
    #Propert to set total number of servers we are talking to
    WINDOW.setProperty("plexbmc.numServers", str(len(Servers)))
    printDebug("Number of servers for skin: " + str(len(Servers)))
    
    sectionCount=0
    serverCount=0
    #For each of the servers we have identified
    for server in Servers:
         

        if g_multiple > 0:

            #Get friendly name
            url='http://'+server[1]
            html=getURL(url)

            if html is False:
                continue

            tree=etree.fromstring(html)
            try:
                if not tree.get('friendlyName') == "":
                    server[0]=tree.get('friendlyName')
                else:
                    server[0]=server[1].split(':')[0]
            except:
                server[0]=server[1].split(':')[0]
           
        
        WINDOW.setProperty("plexbmc.%d.server" % (serverCount) , server[0].split(':')[0])
        WINDOW.setProperty("plexbmc.%d.server.video" % (serverCount) , "http://"+server[1]+"/video&mode=7")
        WINDOW.setProperty("plexbmc.%d.server.music" % (serverCount) , "http://"+server[1]+"/music&mode=17")
        WINDOW.setProperty("plexbmc.%d.server.photo" % (serverCount) , "http://"+server[1]+"/photos&mode=16")
        WINDOW.setProperty("plexbmc.%d.server.online" % (serverCount) , "http://"+server[1]+"/system/plexonline&mode=19")

        
        serverCount += 1
        
        #dive into the library section      
        url='http://'+server[1]+'/library/sections'
        html=getURL(url)
            
        if html is False:
            continue
                
        tree = etree.fromstring(html)
            
        #Find all the directory tags, as they contain further levels to follow
        #For each directory tag we find, build an onscreen link to drill down into the library
        SectionTags=tree.findall('Directory')
        for object in SectionTags:
            
            arguments=dict(object.items())
            try:
                arguments['thumb']="http://"+server[1]+arguments['thumb'].split('?')[0]
            except:    
                arguments['thumb']=""
            #Set up some dictionaries with defaults that we are going to pass to addDir/addLink
            properties={}

            #Start pulling out information from the parsed XML output. Assign to various variables
            try:
                properties['title']=arguments['title']
            except:
                properties['title']="unknown"

                
            try:
                if arguments['art'][0] == "/":
                    #Ammend URL
                    arguments['fanart_image']="http://"+server[1]+arguments['art']
                else:
                    arguments['fanart_image']="http://"+server[1]+"/library/sections/"+arguments['art']
            except: pass
           
            try:
                if len(arguments['fanart_image'].split('/')[-1].split('.')) < 2:
                    arguments['fanart_image']=str(arguments['fanart_image']+"/image.jpg")
            except:pass
                        
            #Determine what we are going to do process after a link is selected by the user, based on the content we find
            if arguments['type'] == 'show':
                window="VideoLibrary"
                mode=1
            if  arguments['type'] == 'movie':
                window="VideoLibrary"
                mode=2
            if  arguments['type'] == 'artist':
                window="MusicLibrary"
                mode=3
                             
            if g_secondary == "true":
                s_url='http://'+server[1]+'/library/sections/'+arguments['key']+"&mode=0"
            else:
                #Build URL with the mode to use and key to further XML data in the library
                s_url='http://'+server[1]+'/library/sections/'+arguments['key']+'/all'+"&mode="+str(mode)
                
            #Build that listing..
            WINDOW.setProperty("plexbmc.%d.title" % (sectionCount) , properties['title'])
            WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount), server[0])
            WINDOW.setProperty("plexbmc.%d.url" % (sectionCount), s_url )
            WINDOW.setProperty("plexbmc.%d.path" % (sectionCount), "plugins://plugin.video.plexbmc?url="+s_url)
            WINDOW.setProperty("plexbmc.%d.window" % (sectionCount), window )
            WINDOW.setProperty("plexbmc.%d.art" % (sectionCount), arguments['fanart_image'] )
            WINDOW.setProperty("plexbmc.%d.type" % (sectionCount) , arguments['type'])
            WINDOW.setProperty("plexbmc.%d.icon" % (sectionCount) , arguments['thumb'].split('?')[0])
            WINDOW.setProperty("plexbmc.%d.thumb" % (sectionCount) , arguments['thumb'].split('?')[0])


            printDebug("Building window properties index [" + str(sectionCount) + "] which is [" + properties['title'] + "]")
            
            sectionCount += 1
    
    try:
        printDebug("Clearing properties from [" + str(sectionCount) + "] to [" + WINDOW.getProperty("plexbmc.sectionCount") + "]")

        for i in range(sectionCount, int(WINDOW.getProperty("plexbmc.sectionCount"))+1):
            WINDOW.clearProperty("plexbmc.%d.title" % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.subtitle" % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.url" % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.path" % (i) )
            WINDOW.clearProperty("plexbmc.%d.window" % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.art" % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.type" % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.icon" % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.thumb" % ( i ) )
    except:
        pass

    printDebug("Total number of skin sections is [" + str(sectionCount) + "]")
    WINDOW.setProperty("plexbmc.sectionCount", str(sectionCount))

def libraryRefresh(url):
    printDebug("== ENTER: libraryRefresh ==", False)
    #Refreshing the library
    html=getURL(url)
    printDebug ("Library refresh requested")
    xbmc.executebuiltin("XBMC.Notification(\"PleXBMC\",Library Refresh started,100)")
    return

def watched(url):
    printDebug("== ENTER: watched ==", False)

    if url.find("unscrobble") > 0:
        printDebug ("Marking as unwatched with: " + url)
        string="Marked as unwatched"
    else:
        printDebug ("Marking as watched with: " + url)
        string="Marked as watched"
    
    html=getURL(url)
    #xbmc.executebuiltin("XBMC.Notification(\"PleXBMC\",\""+string+"\",60)")
    xbmc.executebuiltin("Container.Refresh")
    
    return
    
##So this is where we really start the plugin.

printDebug( "Script argument is " + str(sys.argv[1]))
if str(sys.argv[1]) == "skin":
    skin()
elif sys.argv[1] == "update":
    url=sys.argv[2]
    libraryRefresh(url)
elif sys.argv[1] == "watch":
    url=sys.argv[2]
    watched(url)
else:
    

        
    #pluginhandle = int(sys.argv[1])
    pluginhandle = 0    
    #first thing, parse the arguments, as this has the data we need to use.              
    params=get_params()
    if g_debug == "true": print "PleXBMC -> " + str(params)

    #Set up some variables
    url=None
    name=None
    mode=None
    resume=None
    id=None
    duration=None
    transcodeOverride=None

    #Now try and assign some data to them
    try:
            #url=urllib.unquote_plus(params["url"])
            url=params['url']
    except:
            pass
    try:
            name=urllib.unquote_plus(params["name"])
    except:
            pass
    try:
            mode=int(params["mode"])
    except:
            pass
    try:
            resume=int(params["resume"])
    except:
            resume=0
    try:
            id=params["id"]
    except:
            pass
    try:
            duration=params["duration"]
    except:
            duration=0
    try:
            transcodeOverride=int(params["transcode"])
    except:
            transcodeOverride=0

            
    if g_debug == "true":
        print "PleXBMC -> Mode: "+str(mode)
        print "PleXBMC -> URL: "+str(url)
        print "PleXBMC -> Name: "+str(name)
        print "PleXBMC -> ID: "+ str(id)
        print "PleXBMC -> Duration: " + str(duration)

    #Run a function based on the mode variable that was passed in the URL

    if mode!=5:
        __settings__.setSetting('resume', '')
        
    if mode==None or url==None or len(url)<1:
        ROOT()
    elif mode == 0:
        getContent(url)
    elif mode==1:
        SHOWS(url)
    elif mode==2:
        Movies(url)
    elif mode==3:
        artist(url)
    elif mode==4:
        Seasons(url)
    elif mode==5:
        #Check and set transcoding options
        g_transcode = __settings__.getSetting('transcode')

        if transcodeOverride == 1:
                if g_debug == "true": print "PleXBMC -> Transcode override.  Will play media with addon transcoding settings"
                g_transcode="true"

        if g_transcode == "true":
            #If transcode is set, ignore the stream setting for file and smb:
            g_stream = "1"
            if g_debug == "true": print "PleXBMC -> We are set to Transcode, overriding stream selection"
            g_transcodetype = __settings__.getSetting('transcodefmt')
            if g_transcodetype == "0":
                g_transcodefmt="m3u8"
            elif g_transcodetype == "1":
                g_transcodefmt="flv"
                
            g_quality = str(int(__settings__.getSetting('quality'))+3)

            if g_debug == "true": print "PleXBMC -> Transcode format is " + g_transcodefmt
            if g_debug == "true": print "PleXBMC -> Transcode quality is " + g_quality
            g_proxyport=__settings__.getSetting('proxyport')
         

            g_proxy = __settings__.getSetting('proxy')
            if g_debug == "true": print "PleXBMC -> proxy is " + g_proxy

        PLAYEPISODE(id,url,resume, duration)
    elif mode==6:
        EPISODES(url)
    elif mode==7:
        PlexPlugins(url)
    elif mode==12:
        PLAY(url)
    elif mode==13:
        selectMedia(id,url,resume,duration)
    elif mode ==14:
        albums(url)
    elif mode == 15:
        tracks(url)
    elif mode==16:
        photo(url)
    elif mode==17:
        music(url)
    elif mode==18:
        videoPluginPlay(url)
    elif mode==19:
        plexOnline(url)
    elif mode==20:
        install(url,name)
    elif mode==21:
        channelView(url)

print "===== PLEXBMC STOP ====="
   
#clear done and exit.        
sys.modules.clear()

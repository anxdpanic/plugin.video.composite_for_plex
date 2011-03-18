import urllib,urllib2,re,xbmcplugin,xbmcgui,xbmcaddon, httplib, socket
import sys,os,datetime, time, sha

__settings__ = xbmcaddon.Addon(id='plugin.video.plexbmc')
__cwd__ = __settings__.getAddonInfo('path')
BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
PLUGINPATH=xbmc.translatePath( os.path.join( __cwd__) )
sys.path.append(BASE_RESOURCE_PATH)

try:
    import elementtree.ElementTree as etree
except: 
    import ElementTree as etree

#Get the setting from the appropriate file.
print "===== PLEXBMC START ====="
g_host = __settings__.getSetting('ipaddress')
g_stream = __settings__.getSetting('streaming')
g_secondary = __settings__.getSetting('secondary')
g_debug = __settings__.getSetting('debug')
if g_debug == "true":
    print "PleXBMC -> Settings hostname: " + g_host
    print "PleXBMC -> Settings streaming: " + g_stream
    print "PleXBMC -> Setting secondary: " + g_secondary
    print "PleXBMC -> Setting debug to " + g_debug
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
        g_serverList.append(['Server '+str(i),extraip])

if g_debug == "true": print "PleXBMC -> serverList is " + str(g_serverList)
        

#Check and set transcoding options
g_transcode = __settings__.getSetting('transcode')
if g_transcode == "true":
    #If transcode is set, ignore the stream setting for file and smb:
    g_stream = "1"
    if g_debug == "true": print "PleXBMC -> We are set to Transcode"
    g_transcodetype = __settings__.getSetting('transcodefmt')
    if g_transcodetype == "0":
        g_transcodefmt="m3u8"
    elif g_transcodetype == "1":
        g_transcodefmt="flv"

    if g_debug == "true": print "PleXBMC -> Transcode format is " + g_transcodefmt

g_proxy = __settings__.getSetting('proxy')
if g_debug == "true": print "PleXBMC -> proxy is " + g_proxy

g_loc = "special://home/addon/plugin.video.plexbmc"

#Create the standard header structure and load with a User Agent to ensure we get back a response.
g_txheaders = {
              'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US;rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 ( .NET CLR 3.5.30729)'	
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
    msg=sha.new(g_password.lower())
    msg2=sha.new(g_username.lower()+msg.hexdigest()).hexdigest()
            
    #Load the auth strings into the URL header structure.
    g_txheaders['X-Plex-User']=str(g_username.lower())
    g_txheaders['X-Plex-Pass']=str(msg2)
    
    #Set up an internal XBMC header string, which is appended to all *XBMC* processed URLs.
    XBMCInternalHeaders="|X-Plex-User="+g_txheaders['X-Plex-User']+"&X-Plex-Pass="+g_txheaders['X-Plex-Pass']



################################ Common
# Connect to a server and retrieve the HTML page
def getURL( url ,title="Error", surpress=False):
    printDebug("== ENTER: getURL ==")
    try:
        printDebug("url = "+url, getURL.__name__)
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
            printDebug("====== XML returned =======",getURL.__name__)
            printDebug(link)
            printDebug("====== XML finished ======",getURL.__name__)
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
    printDebug("== ENTER: mediaType ==")
    
    #Passed a list of <Part /> tag attributes, select the appropriate media to play
    
    stream=partproperties['key']
    file=partproperties['file']
    
    # 0 is auto select.  basically check for local file first, then stream if not found
    if g_stream == "0":
        #check if the file can be found locally
        try:
            printDebug("Checking for local file",mediaType.__name__)
            exists = open(file, 'r')
            exists.close()
            filelocation="file://"+server+file
        except:
            printDebug("No local file, defaulting to stream", mediaType.__name__)
            filelocation="http://"+server+stream
        
    # 1 is stream no matter what
    elif g_stream == "1":
        printDebug( "Selecting stream", mediaType.__name__)
        filelocation="http://"+server+stream
    # 2 is use SMB 
    elif g_stream == "2":
        printDebug( "Selecting smb", mediaType.__name__)
        location=file.replace("Volumes",server)
        filelocation="smb:/"+location.replace(":32400","")
    else:
        printDebug( "No option detected, streaming is safest to choose" , mediaType.__name__)       
        filelocation="http://"+server+stream
    
    printDebug("Returning URL: " + filelocation, mediaType.__name__)
    return filelocation
    
    
def printDebug(msg,functionname=""):
    if g_debug == "true":
        if functionname == "":
            print str(msg)
        else:
            print "PleXBMC -> " + str(functionname) + ": " + str(msg)
 
#Used to add playable media files to directory listing
#properties is a dictionary {} which contains a list of setInfo properties to apply
#Arguments is a dictionary {} which contains other arguments used in teh creation of the listing (such as name, resume time, etc)
def addLink(url,properties,arguments):
        printDebug("== ENTER: addLink ==")
        try:
            printDebug("Adding link for [" + properties['title'] + "]", addLink.__name__)
        except: pass
        printDebug("Passed arguments are " + str(arguments), addLink.__name__)
        printDebug("Passed properties are " + str(properties), addLink.__name__)
        
        try:
            type=arguments['type']
        except:
            type='Video'
            
        if type =="Picture":
             u=url
        else:
            u=sys.argv[0]+"?url="+str(url)
        
        ok=True

        printDebug("URL to use for listing: " + u, addLink.__name__)
        #Create ListItem object, which is what is displayed on screen
        try:
            liz=xbmcgui.ListItem(properties['title'], iconImage=arguments['thumb'], thumbnailImage=arguments['thumb']+XBMCInternalHeaders)
            printDebug("Setting thumbnail as " + arguments['thumb'],addLink.__name__)              
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
            liz.setProperty('fanart_image', str(arguments['fanart_image']))
            printDebug( "Setting fan art as " + str(arguments['fanart_image']),addLink.__name__)
        except: pass
        
        #Finally add the item to the on screen list, with url created above
        ok=xbmcplugin.addDirectoryItem(handle=pluginhandle,url=u,listitem=liz)
        
        return ok

#Used to add directory item to the listing.  These are non-playable items.  They can be mixed with playable items created above.
#properties is a dictionary {} which contains a list of setInfo properties to apply
#Arguments is a dictionary {} which contains other arguments used in teh creation of the listing (such as name, resume time, etc)
def addDir(url,properties,arguments):
        printDebug("== ENTER: addDir ==")
        try:
            printDebug("Adding Dir for [" + properties['title'] + "]", addDir.__name__)
        except: pass

        printDebug("Passed arguments are " + str(arguments), addDir.__name__)
        printDebug("Passed properties are " + str(properties), addDir.__name__)
        
        #Create the URL to pass to the item
        u=sys.argv[0]+"?url="+str(url)
        ok=True
                
        #Create the ListItem that will be displayed
        try:
            liz=xbmcgui.ListItem(properties['title'], iconImage=arguments['thumb'], thumbnailImage=arguments['thumb']+XBMCInternalHeaders)
            printDebug("Setting thumbnail as " + arguments['thumb'],addDir.__name__)
        except:
            liz=xbmcgui.ListItem(properties['title'], iconImage='', thumbnailImage='')
        
            
        #Set the properties of the item, such as summary, name, season, etc
        try:
            liz.setInfo( type=arguments['type'], infoLabels=properties ) 
        except:
            liz.setInfo(type='Video', infoLabels=properties ) 

        printDebug("URL to use for listing: " + u, addDir.__name__)
        
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
            liz.setProperty('fanart_image', str(arguments['fanart_image']+XBMCInternalHeaders))
            printDebug( "Setting fan art as " + str(arguments['fanart_image']),addDir.__name__)
        except: pass

        #Finally add the item to the on screen list, with url created above
        ok=xbmcplugin.addDirectoryItem(handle=pluginhandle,url=u,listitem=liz,isFolder=True)
        return ok

################################ Root listing
# Root listing is the main listing showing all sections.  It is used when these is a non-playable generic link content
def ROOT():
        printDebug("== ENTER: ROOT() ==")
        #Get the global host variable set in settings
        host=g_host
        
        Servers=[]
      
        #If we have a remote host, then don;t do local discovery as it won't work
        if g_bonjour == "true":
            #Get the HTML for the URL
            url = 'http://'+host+':32400/servers'
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
                                      
            #Get friendly name
            url='http://'+server[1]+':32400'
            html=getURL(url)

            if html is False:
                continue

            tree=etree.fromstring(html)
            try:
                if not tree.get('friendlyName') == "":
                    server[0]=tree.get('friendlyName')
                else:
                    server[0]=server[1]
            except:
                server[0]=server[1]
            
            #dive into the library section with BS        
            url='http://'+server[1]+':32400/library/sections'
            html=getURL(url)
            
            if html is False:
                continue
                
            tree = etree.fromstring(html)
            
            #Find all the directory tags, as they contain further levels to follow
            #For each directory tag we find, build an onscreen link to drill down into the library
            SectionTags=tree.findall('Directory')
            for object in SectionTags:
            
                arguments=dict(object.items())
                arguments['thumb']=""
                #Set up some dictionaries with defaults that we are going to pass to addDir/addLink
                properties={}

                #Start pulling out information from the parsed XML output. Assign to various variables
                try:
                    if g_multiple == 0:
                        properties['title']=arguments['title']
                    else:
                        properties['title']=server[0]+": "+arguments['title']
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
                    s_url='http://'+server[1]+':32400/library/sections/'+arguments['key']+"&mode=0&name="+urllib.quote_plus(server[0])
                else:
                    #Build URL with the mode to use and key to further XML data in the library
                    s_url='http://'+server[1]+':32400/library/sections/'+arguments['key']+'/all'+"&mode="+str(mode)+"&name="+urllib.quote_plus(server[0])
                
                #Build that listing..
                addDir(s_url, properties,arguments)
                
			#Plex plugin handling 
            #Simple check if any plugins are present.  
            #If so, create a link to drill down later. One link is created for each PMS server available
            #Plugin data is held in /videos directory (well, video data is anyway)
            pluginurl='http://'+server[1]+':32400/video'
            pluginhtml=getURL(pluginurl)
            
            if pluginhtml is False:
                return
           
            plugintree=etree.fromstring(pluginhtml)

            #Check the number of items in the mediacontainer tag.
            try:
                items = int(plugintree.get('size'))
            except:
                items=0
            
            #If we have at least one item listed, then we have some plugin.  In which case, create a link
            if items > 0:
            
                arguments={'thumb':''}
                properties={}

                #URL contains the location of the server plugin.  We'll display the content later
                mode=7
                s_url=pluginurl+"&mode="+str(mode)+"&name="+urllib.quote_plus(server[0])
                if g_multiple == 0:
                    properties['title']="Video Plugins"
                else:
                    properties['title']=server[0]+": Video Plugins"

                arguments['type']="Video"

                    
                #Add an on screen link
                addDir(s_url, properties,arguments)
                
            #Create Photo plugin link
            if g_multiple == 0:
                properties['title']="Photo Plugins"
            else:
                properties['title']=server[0]+": Photo Plugins"
            arguments['type']="Picture"
            mode=16
            u="http://"+server[1]+":32400/photos&mode="+str(mode)
            addDir(u,properties,arguments)

            #Create music plugin link
            if g_multiple == 0:
                properties['title']="Music Plugins"
            else:
                properties['title']=server[0]+": Music Plugins"
            arguments['type']="Music"
            mode=17
            u="http://"+server[1]+":32400/music&mode="+str(mode)
            addDir(u,properties,arguments)
            
            #Create plexonline link
            if g_multiple == 0:
                properties['title']="Plex Online"
            else:
                properties['title']=server[0]+": Plex Online"
            arguments['type']="file"
            mode=19
            u="http://"+server[1]+":32400/system/plexonline&mode="+str(mode)
            addDir(u,properties,arguments)


            
        #All XML entries have been parsed and we are ready to allow the user to browse around.  So end the screen listing.
        xbmcplugin.endOfDirectory(pluginhandle)  
################################ Movies listing  
#Used by the skin to automatically start a movie listing.  Might not be needed now - copies functionality in ROOT          
def StartMovies():
        print '=========================='
        print 'Starting with Movies'
        host=g_host
        url = 'http://'+host+':32400/library/sections'
        html=getURL(url)
        
        if html is False:
            return
        
        tree=etree.fromstring(html)
        SectionTags=tree.findall('Directory')
        for object in SectionTags:
            key=object.get('key')
            name=object.get('title')
            type=object.get('type')
            if type== 'movie':
                url='http://'+host+':32400/library/sections/'+key+'/all'
                Movies(url)


################################ TV listing            
#Used by the skin to automatically start a TV listing.  Might not be needed now - copies functionality in ROOT          
def StartTV():
        print '=========================='
        print 'Starting with TV Shows'
        host=g_host
        url = 'http://'+host+':32400/library/sections'
        html=getURL(url)
        
        if html is False:
            return

        
        tree=etree.fromstring(html)
        SectionTags=tree.findall('Directory')
        for object in SectionTags:
            key=object.get('key')
            name=object.get('title')
            type=object.get('type')
            if type== 'show':
                url='http://'+host+':32400/library/sections/'+key+'/all'
                SHOWS(url)

################################ Movies listing            
# Used to display movie on screen.

def MoviesET(url='',tree=etree,server=''):
        printDebug("== ENTER: MoviesET() ==")
        xbmcplugin.setContent(pluginhandle, 'movies')
        
        #xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
        
        #get the server name from the URL, which was passed via the on screen listing..
        if not url == '':
            server=url.split('/')[2]
            #Get some XML and parse it
            html=getURL(url)
            
            if html is False:
                return
                
            tree = etree.fromstring(html)
                    
        #Find all the video tags, as they contain the data we need to link to a file.
        MovieTags=tree.findall('Video')
        for movie in MovieTags:
            
            printDebug("---New Item---", MoviesET.__name__)
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
                try:
                    print "Found unsupported .strm file for [" + arguments['title'].encode('utf-8') + "].  Will not list"
                except:
                    print "Found unsupported .strm file.  Will not list"
                continue
             
            printDebug("Media attributes are " + str(mediaarguments), MoviesET.__name__)
            printDebug("Part attributes are " + str(partarguments), MoviesET.__name__)
            
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
           
            #Get the picture to use
            try:
                arguments['thumb']='http://'+server+arguments['thumb']
            except:
                thumb=g_loc+'/resources/movie.png'  
                print thumb  
                arguments['thumb']=thumb
               
            #Get a nice big picture  
            try:
                fanart=arguments['art']#.split('?')[0] #drops the guid from the fanart image
                art_url='http://'+server+fanart#.encode('utf-8')
                #art_url='http://'+server+':32400/photo/:/transcode?url='+art_url+'&width=1280&height=720'
            except:  
                #or use a stock default one
                art_url=g_loc+'/resources/movie_art.jpg'
            
            #print art_url  
            arguments['fanart_image']=art_url
            
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
            
            #Decide what file type to play            
            url=mediaType(partarguments,server)
            
            #This is playable media, so link to a path to a play function
            mode=5
                             
            u=str(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(properties['title'])+"&resume="+str(arguments['viewoffset'])+"&id="+str(arguments['ratingKey'])+"&duration="+str(arguments['duration'])
 
            if mediacount > 1:
                #We have more than one media file to play.  Build link to go to selectMedia
                printDebug("We have a choice of " + str(mediacount) + " media files.", MoviesET.__name__)
                mode=13
                u='http://'+server+arguments['key']+"&mode="+str(mode)+"&name="+urllib.quote_plus(properties['title'])+"&resume="+str(arguments['viewoffset'])+"&id="+str(arguments['ratingKey'])+"&duration="+str(arguments['duration'])
                    
            #Right, add that link...and loop around for another entry
            addLink(u,properties,arguments)        
        
        #If we get here, then we've been through the XML and it's time to finish.
        xbmcplugin.endOfDirectory(pluginhandle)
    
################################ TV Show Listings
#This is the function use to parse the top level list of TV shows
def SHOWS(url='',tree=etree,server=''):
        printDebug("== ENTER: SHOWS() ==")
        xbmcplugin.setContent(pluginhandle, 'tvshows')

        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
        
        #Get the URL and server name.  Get the XML and parse
        if not url == '':
        
            server=url.split('/')[2]
            print server
            html=getURL(url)
        
            if html is False:
                return

        
            tree=etree.fromstring(html)
            
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
            try:
                arguments['thumb']='http://'+server+arguments['thumb']
            except:
                thumb=g_loc+'/resources/movie.png'  
                print thumb  
                arguments['thumb']=thumb
               
            #Get a nice big picture  
            try:
                fanart=arguments['art'].split('?')[0] #drops the guid from the fanart image
                art_url='http://'+server+fanart.encode('utf-8')
                art_url='http://'+server+':32400/photo/:/transcode?url='+art_url+'&width=1280&height=720'
            except:  
                #or use a stock default one
                art_url=g_loc+'/resources/movie_art.jpg' 

            arguments['fanart_image']=art_url
           
            #Set type
            arguments['type']="Video"


            mode=4 # grab season details
            url='http://'+server+'/library/metadata/'+arguments['ratingKey']+'/children'+"&mode="+str(mode)+"&name="+urllib.quote_plus(properties['title'])
            
            addDir(url,properties,arguments) 
            
        #End the listing    
        xbmcplugin.endOfDirectory(pluginhandle)
 
################################ TV Season listing            
#Used to display the season data         
def Seasons(url):
        printDebug("== ENTER: season() ==")
        xbmcplugin.setContent(pluginhandle, 'seasons')

        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
        
        #Get URL, XML and parse
        server=url.split('/')[2]
        html=getURL(url)
        
        if html is False:
            return

        
        tree= etree.fromstring(html)
        
        #For all the directory tags
        ShowTags=tree.findall('Directory')
        for show in ShowTags:
        
            arguments=dict(show.items());
            #Build basic data structures
            properties={'overlay': 6, 'playcount': 0, 'season' : 0 , 'episode':0 }   #Create a dictionary for properties with some defaults(i.e. ListItem properties)
 
            #Get name
            try:
                properties['tvshowtitle']=properties['title']=arguments['title'].encode('utf-8')
            except: pass
       

            #Get the picture to use
            try:
                arguments['thumb']='http://'+server+arguments['thumb']
            except:
                thumb=g_loc+'/resources/movie.png'  
                print thumb  
                arguments['thumb']=thumb
               
            #Get a nice big picture  
            try:
                fanart=arguments['art'].split('?')[0] #drops the guid from the fanart image
                art_url='http://'+server+fanart.encode('utf-8')
                art_url='http://'+server+':32400/photo/:/transcode?url='+art_url+'&width=1280&height=720'
            except:  
                #or use a stock default one
                art_url=g_loc+'/resources/movie_art.jpg' 

            arguments['fanart_image']=art_url

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
            
            url='http://'+server+arguments['key']+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
        
            #Build the screen directory listing
            addDir(url,properties,arguments) 
            
        #All done, so end the listing
        xbmcplugin.endOfDirectory(pluginhandle)
 
################################ TV Episode listing 
#Displays the actual playable media
def EPISODES(url='',tree=etree,server=''):
        printDebug("== ENTER: EPISODES() ==")
        xbmcplugin.setContent(pluginhandle, 'episodes')
        
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_EPISODE)
        
        #Get the server
        try:
            server=url.split('/')[2]
            #Get the end part of teh URL, as we need to get different data if parsing "All Episodes"
            target=url.split('/')[-1]
            printDebug("target URL is " + target, EPISODES.__name__)
        except: pass
        
        try:
            ShowTags=tree.findall('Video')
        except:
            #Get URL, XML and Parse
            html=getURL(url)
            
            if html is False:
                return
            
            tree=etree.fromstring(html)
            ShowTags=tree.findall('Video')
            
        #get a bit of metadata that sits inside the main mediacontainer
        #If it doesn't exist, we'll check later and get it from elsewhere
         
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
            
         
        #right, not for each show we find
        for show in ShowTags:
            #print show
            
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
           
            printDebug("Media attributes are " + str(mediaarguments), EPISODES.__name__)
            printDebug( "Part is " + str(partarguments), EPISODES.__name__)
            printDebug( "Extra info is " + str(tempgenre) + str(tempwriter) + str(tempcast) + str(tempdir), EPISODES.__name__)
            
            #Set basic structure with some defaults.  Overlay 6 is unwatched
            properties={'overlay': 6, 'playcount': 0, 'season' : 0}   #Create a dictionary for properties with some defaults(i.e. ListItem properties)
            #arguments={'type': "tvshows", 'viewoffset': 0, 'duration': 0, 'thumb':''}    #Create a dictionary for file arguments (i.e. stuff you need, but are no listitems)
            
            #Get the episode number
            try:
                properties['episode']=int(arguments['index'])
            except: pass

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
                arguments['viewOffset']=int(arguments['viewOffset'])/1000
            except:
                arguments['viewOffset']=0

                        
            #If we are processing an "All Episodes" directory, then get the season from the video tag
            
            try:
                if target == "allLeaves":
                    try:
                        properties['season']=int(arguments['parentIndex'])
                    except:pass
            except:    
                properties['season']=int(season)
             
            #check if we got the kiddie rating from the main tag
            if certificate is None:
                try:
                    properties['mpaa']=arguments['contentRating']
                except:pass
            else:
                properties['mpaa']=certificate
                    
            #Check if we got the showname from the main tag        
            if showname is None:
                try:
                    properties['tvshowtitle']=arguments['grandparentTitle']
                except: pass
            else:
                properties['tvshowtitle']=showname
            
            #check if we got the studio from the main tag.
            if studio is None:
                try:
                    properties['studio']=arguments['studio']
                except:pass
            else:
                properties['studio']=studio
            
                
            #Get the picture to use
            try:
                arguments['thumb']='http://'+server+arguments['thumb']
            except:
                thumb=g_loc+'/resources/movie.png'  
                print thumb  
                arguments['thumb']=thumb
               
            #Get a nice big picture  
            try:
                fanart=arguments['art'].split('?')[0] #drops the guid from the fanart image
                art_url='http://'+server+fanart.encode('utf-8')
                art_url='http://'+server+':32400/photo/:/transcode?url='+art_url+'&width=1280&height=720'
            except:  
                #or use a stock default one
                art_url=g_loc+'/resources/movie_art.jpg' 

            arguments['fanart_image']=art_url    

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
            url=mediaType(partarguments,server)
            #Set mode 5, which is play            
            mode=5

            u=str(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(properties['title'])+"&resume="+str(arguments['viewOffset'])+"&id="+str(arguments['ratingKey'])+"&duration="+str(arguments['duration'])
                
            #Build a file link and loop
            addLink(u,properties,arguments)        
        
        #End the listing
        xbmcplugin.endOfDirectory(pluginhandle)

#What to do to process Plex Plugin structures        
def PlexPlugins(url):
        printDebug("== ENTER: PlexPlugins ==")
        xbmcplugin.setContent(pluginhandle, 'movies')

        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)

        #get the serverm URL, XML and parse
        server=url.split('/')[2]
        html=getURL(url)
        
        if html is False:
            return

        tree=etree.fromstring(html)
               
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
                    
            try:
                if not arguments['thumb'].split('/')[0] == "http:":
                    arguments['thumb']='http://'+server+arguments['thumb']
            except:
                thumb=g_loc+'/resources/movie.png'  
                arguments['thumb']=thumb


            if arguments['key'].split('/')[0] == "http:":
                p_url=arguments['key']
            elif arguments['key'][0] == '/':
                #The key begins with a slah, there is absolute
                p_url='http://'+server+str(arguments['key'])
            else:
                #Build the next level URL and add the link on screen
                p_url=url+'/'+str(arguments['key'])

            
            if orange.tag == "Directory" or orange.tag == "Podcast":
                #We have a directory tag, so come back into this function
                mode=7   
                s_url=p_url+"&mode="+str(mode)+"&name="+urllib.quote_plus(properties['title'])
                
                #Set type
                arguments['type']="Video"
                
                addDir(s_url, properties, arguments)
                    
            #If we have some video links as well
            elif orange.tag == "Video":
             
                #Set the mode to play them this time
                mode=18                       
                    
                #Build the URl and add a link to the file
                v_url=p_url+"&mode="+str(mode)+"&name="+urllib.quote_plus(properties['title'])    
                
                #Set type
                arguments['type']="Video"
               
                addLink(v_url, properties, arguments)

                
        #Ahh, end of the list   
        xbmcplugin.endOfDirectory(pluginhandle)
        
#Right, this is used to play PMS library data file.  This function will attempt to update PMS as well.
#Only use this to play stuff you want to update in the library        
def PLAYEPISODE(id,vids,seek, duration):
        printDebug("== ENTER: PLAYEPISODE ==")
        #Use this to play PMS library items that you want up dated (Movies, TV shows)
        url = vids
      
        server=url.split('/')[2]
        protocol=url.split('/')[0]
        urlPath="/"+"/".join(url.split('/')[3:])
   
   
        if g_transcode == "true":
            printDebug("We are going to attempt to transcode this video", PLAYEPISODE.__name__)
            url=transcode(id,url)
            identifier=proxyControl("start")
            if identifier is False:
                printDebug("Error - proxy not running", PLAYEPISODE.__name__)
                xbmcgui.Dialog().ok("Error","Transcoding proxy not running")
   
        if protocol == "file:":
            printDebug( "We are playing a file", PLAYEPISODE.__name__)
            url=urlPath
        elif protocol == "http:":
            if g_transcode == "true" and g_proxy =="true":
                import base64
                headers=base64.b64encode(XBMCInternalHeaders)
                newurl=base64.b64encode(url)
                url="http://127.0.0.1:8087/withheaders/"+newurl+"/"+headers


            else:
                url=url+XBMCInternalHeaders
        
        printDebug( "Current resume is " + str(seek), PLAYEPISODE.__name__)
       
        resumeSetting=__settings__.getSetting('resume')
        printDebug("Stored setting for resume is " + str(resumeSetting), PLAYEPISODE.__name__)
        if len(resumeSetting) > 0:
            resumeid, resumetime = resumeSetting.split("|")
            if resumeid == id:
                printDebug ("ID match, using settings resume time", PLAYEPISODE.__name__)
                resume = int(resumetime)
            else:
                resume = seek
        else:
            resume = seek
        
        printDebug("Resume has been set to " + str(resume), PLAYEPISODE.__name__)
        
        #Build a listitem, based on the url of the file
        item = xbmcgui.ListItem(path=url)
        result=1
            
        #If we passed a positive resume time, then we need to display the dialog box to ask the user what they want to do    
        if resume > 0:
            resumeseconds = resume
            
            #Human readable time
            displayTime = str(datetime.timedelta(seconds=int(resumeseconds)))
            
            #Build the dialog text
            dialogOptions = [ "Resume from " + str(displayTime) , "Start from beginning"]
            printDebug( "We have part way through video.  Display resume dialog", PLAYEPISODE.__name__)
            
            #Create a dialog object
            startTime = xbmcgui.Dialog()
            
            #Box displaying resume time or start at beginning
            result = startTime.select('Resuming playback..',dialogOptions)
            
            #result contains an integer based on the selected text.
            if result == -1:
                #-1 is an exit without choosing, so end the function and start again when the user selects a new file.
                return
        
        #ok - this will start playback for the file pointed to by the url
        start = xbmcplugin.setResolvedUrl(pluginhandle, True, item)
        
        #Set a loop to wait for positive confirmation of playback
        count = 0
        while not xbmc.Player().isPlaying():
            printDebug( "Not playing yet...sleep for 2", PLAYEPISODE.__name__)
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
            xbmc.Player().seekTime((resumeseconds)) 
        
        #OK, we have a file, playing at the correct stop.  Now we need to monitor the file playback to allow updates into PMS
        monitorPlayback(id,server, resume, duration)
        
        return

def proxyControl(command):
    printDebug("======= ENTER: proxyControl() =======")
    import subprocess
    if command == "start":
        printDebug("Start proxy", proxyControl.__name__)
        #execfile("HLSproxy.py")
        #child=subprocess.Popen([sys.executable, "HLSproxy.py"], shell=True)
        filestring="XBMC.RunScript(special://home/addons/plugin.video.plexbmc/HLSproxy.py,\""+PLUGINPATH+"/terminate.proxy\")"
        print str(filestring)
        xbmc.executebuiltin(filestring)
        #xbmc.executebuiltin("XBMC.RunScript(special://home/addons/plugin.video.plexbmc/HLSproxy.py,\"PLUGINPATH\")")
        time.sleep(2)
        
    elif command == "stop":
        printDebug("Stop proxy", proxyControl.__name__)
        time.sleep(2)
        done=getURL("http://127.0.0.1:8087/stop")
    else:
        printDebug("No proxy command specified", proxyControl.__name__)
        return False
    #check result
    
    html=getURL('http://127.0.0.1:8087/version', surpress=True)
    
    if command == "start":
        if html is False:
            #failure
            printDebug("Start Failure", proxyControl.__name__)
            return False
        else:
            printDebug("Start Success", proxyControl.__name__)        
            #success
            return True
    elif command == "stop":
        if html is False:
            #success
            printDebug("Stop Success", proxyControl.__name__)          
            return True
        else:
            #failure
            printDebug("Stop Failure", proxyControl.__name__)           
            return False
    
    return False    
    
        
def selectMedia(id,url,seek,duration):
    printDebug("== ENTER: selectMedia ==")
    #if we have two or more files for the same movie, then present a screen

    options=[]
    server=url.split('/')[2]
    html=getURL(url)
    
    if html is False:
        return

    
    newtree=etree.fromstring(html)
       
    video=newtree.findall('Video')
    
    #Nasty code - but can;t for the life of me work out how to get the Part Tags only!!!!
    for file in video:
    
        for crap in file:
            if crap.tag == "Media":
                for stuff in crap:
                    if stuff.tag == "Part":
                        bits=stuff.get('key'), stuff.get('file')
                        options.append(bits)
            
    dialogOptions=[]
    for items in options:
        name=items[1].split('/')[-1]
        dialogOptions.append(name)
    
    #Build the dialog text
    printDebug("Create selection dialog box - we have a decision to make!", selectMedia.__name__)
            
    #Create a dialog object
    startTime = xbmcgui.Dialog()
            
    #Box displaying resume time or start at beginning
    result = startTime.select('Choose which file',dialogOptions)
            
    #result contains an integer based on the selected text.
    if result == -1:
        #-1 is an exit without choosing, so end the function and start again when the user selects a new file.
        return
    else:
   
        newurl=mediaType({'key': options[result][0] , 'file' : options[result][1]},server)
   
    printDebug("We have selected media at " + newurl, selectMedia.__name__)
    PLAYEPISODE(id,newurl,seek, duration)
    return
           
#Monitor function so we can update PMS
def monitorPlayback(id, server, resume, duration):
    printDebug("== ENTER: monitorPlayback ==")
    #Need to monitor the running playback, so we can determine a few things:
    #1. If the file has completed normally (i.e. the movie has finished)
    #2. If the file has been stopped halfway through - need to record the stop time.
    
    #Get the server name to update
    if len(server.split(':')) == 1:
        server=server+":32400"
    
    #Get the current time (either the resumed time or 0)
    currentTime=int(resume)
    
    #If we didn;t get a duration time (for whatever reason) read it from the playing file
    if duration == 0 and xbmc.Player().isPlaying():
        #This sometimes fails.  Don't know why probably a timing issue
        duration = int(xbmc.Player().getTotalTime())
    
    #Whilst the file is playing back
    while xbmc.Player().isPlaying():
        #Get the current playback time
        currentTime = int(xbmc.Player().getTime())
        
        #Convert it into a percentage done, using the total length of the film
        progress = int((float(currentTime)/float(duration))*100)
        
        #Now sleep for 5 seconds
        time.sleep(5)
          
    #If we get this far, playback has stopped
    
    if g_transcode == "true" and g_proxy == "true":
        result = proxyControl("stop")
    
    printDebug( "Playback stopped at " + str(currentTime) + " which is " + str(progress) + "%.", monitorPlayback.__name__)
    if progress <= 5:
        #Then we hadn't watched enough to make any changes
        printDebug( "Less than 5% played, so do no store resume time but ensure that film is marked unwatched", monitorPlayback.__name__)
        updateURL="http://"+server+"/:/unscrobble?key="+id+"&identifier=com.plexapp.plugins.library"
    elif progress >= 95:
        #Then we were 95% of the way through, so we mark the file as watched
        printDebug( "More than 95% completed, so mark as watched", monitorPlayback.__name__)
        updateURL="http://"+server+"/:/scrobble?key="+id+"&identifier=com.plexapp.plugins.library"
    else:
        #we were more than 5% and less then 95% of the way through, store the resume time
        printDebug( "More than 5% and less than 95% of the way through, so store resume time", monitorPlayback.__name__)
        updateURL="http://"+server+"/:/progress?key="+id+"&identifier=com.plexapp.plugins.library&time="+str(currentTime*1000)
        
    #Submit the update URL    
    output = getURL(updateURL, "Updating PMS...", True)
    printDebug("Update returned " + str(output), monitorPlayback.__name__)
    
    printDebug("Creating a temporary new resume time of " + str(currentTime), monitorPlayback.__name__) 
    __settings__.setSetting('resume', str(id)+"|"+str(currentTime))
     
    return
    
#Just a standard playback 
def PLAY(vids):
        printDebug("== ENTER: PLAY ==")
        #This is for playing standard non-PMS library files (such as Plugins)
        url = vids+XBMCInternalHeaders
        item = xbmcgui.ListItem(path=url)
        return xbmcplugin.setResolvedUrl(pluginhandle, True, item)

def videoPluginPlay(vids):
        printDebug("== ENTER: videopluginplay ==")
        #This is for playing standard non-PMS library files (such as Plugins)
        
        header=""
        if vids.split('/')[4] == "amt":
            printDebug("Adding headers for AMT", videoPluginPlay.__name__)
            #Apple trailers - need a special UA header 
            uagent="QuickTime/7.6.5 (qtver=7.6.5;os=Windows NT 5.1Service Pack 3)"
            agentHeader="User-Agent="+urllib.quote_plus(uagent)
                                
            if XBMCInternalHeaders == "":
                header="|"+agentHeader
            else:
                header="&"+agentHeader
            
        url=vids+XBMCInternalHeaders+header
        
        item = xbmcgui.ListItem(path=url)
        return xbmcplugin.setResolvedUrl(pluginhandle, True, item)        
        
        
#Function to parse the arguments passed to the plugin..
def get_params():
        printDebug("== ENTER: get_params ==")
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

def getDirectory(url):  
    printDebug("== ENTER: getDirectory ==")
    #We've been called at mode 0, by ROOT becuase we are going to traverse the secondary menus
        
    #First we need to peek at the XML, to see if we've hit any video links yet.
        
    server=url.split('/')[2]
    lastbit=url.split('/')[-1]
    secondtolast=url.split('/')[-2]
    
    if lastbit.startswith('search'):
        #Found search URL.  Bring up keyboard and get input for query string
        printDebug("This is a search URL.  Bringing up keyboard", getDirectory.__name__)
        kb = xbmc.Keyboard('', 'heading')
        kb.setHeading('Enter search term') # optional
        kb.doModal()
        if (kb.isConfirmed()):
            text = kb.getText()
            printDebug("Search term input: "+query, getDirectory.__name__)
            url=url+'&query='+text
        else:
            return
     
    html=getURL(url)
    
    if html is False:
        return
        
    tree=etree.fromstring(html)
 
    arguments=dict(tree.items())
    
    if arguments['viewGroup'] == "movie":
        printDebug( "this is movie XML, passing to MoviesET", getDirectory.__name__)
        MoviesET(tree=tree,server=server)
        return
    elif arguments['viewGroup'] == "show":
        printDebug( "This is tv show XML, passing to SHOW", getDirectory.__name__)
        SHOWS(tree=tree,server=server)
        return
    elif arguments['viewGroup'] == "episode":
        printDebug("This is TV episode XML, passing to EPISODES", getDirectory.__name__)
        if lastbit.startswith("unwatched"):
            printDebug("PMS data error, contents is actually TV Shows.  Passing to SHOWS.", getDirectory.__name__)
            SHOWS(tree=tree,server=server)
        else:    
            EPISODES(url=url,tree=tree,server=server)
        return
    elif arguments['viewGroup'] == 'artist':
        printDebug( "This is music XML, passing to music", getDirectory.__name__)
        if lastbit.startswith('album') or secondtolast.startswith('decade') or secondtolast.startswith('year'):
            albums(tree=tree, server=server)
        else:    
            artist(tree=tree,server=server)
        return
    elif arguments['viewGroup'] == "track":
        printDebug("This is track XML - checking further", getDirectory.__name__)
        if lastbit.startswith('recentlyAdded'):
            printDebug("Passing to Albums", getDirectory.__name__)
            albums(tree=tree, server=server)
        else:
            printDebug("Passing to Tracks", getDirectory.__name__)
            tracks(tree=tree, server=server)
        return
         
    #else we have a secondary, which we'll process here
    printDebug("Processing secondary menus", getDirectory.__name__)
    
    for apple in tree:
        arguments=dict(apple.items())
        properties={}
        properties['title']=arguments['title']
        
        n_url=url+'/'+arguments['key']+'&mode=0'

        addDir(n_url,properties,arguments)
        
    xbmcplugin.endOfDirectory(pluginhandle)

#Function that will return a m3u8 playlist URL from a PMS stream URL
def transcode(id,url):
    printDebug("== ENTER: transcode ==")
    # First get the time since Epoch
        
    #Had to use some customised modules to get hmac sha256 working on python 2.4
    import base64
    
    server=url.split('/')[2]
    filestream=urllib.quote_plus("/"+"/".join(url.split('/')[3:]))
  
    if g_transcodefmt == "m3u8":
        myurl = "/video/:/transcode/segmented/start.m3u8?identifier=com.plexapp.plugins.library&ratingKey=" + id + "&offset=0&quality=5&url=http%3A%2F%2Flocalhost%3A32400" + filestream + "&3g=0&httpCookies=&userAgent="
    elif g_transcodefmt == "flv":
        myurl="/video/:/transcode/generic.flv?format=flv&videoCodec=libx264&vpre=video-embedded-h264&videoBitrate=5000&audioCodec=libfaac&apre=audio-embedded-aac&audioBitrate=128&size=640x480&fakeContentLength=2000000000&url=http%3A%2F%2Flocalhost%3A32400"  + filestream + "&3g=0&httpCookies=&userAgent="
    else:
        printDebug( "Woah!!  Barmey settings error....Bale.....", transcode.__name__)
        return url

    now=str(int(round(time.time(),0)))
    
    msg = myurl+"@"+now
    printDebug("Message to hash is " + msg, transcode.__name__)
    
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
    
    printDebug("HMAC after hash is " + hash.hexdigest(), transcode.__name__)
    
    #Encode the binary hash in base64 for transmission
    token=base64.b64encode(hash.digest())
    
    #Send as part of URL to avoid the case sensitive header issue.
    fullURL="http://"+server+myurl+"&X-Plex-Access-Key="+publicKey+"&X-Plex-Access-Time="+str(now)+"&X-Plex-Access-Code="+urllib.quote_plus(token)
    
    printDebug("Transcode URL is " + fullURL, transcode.__name__)
    
    if g_transcodefmt == "m3u8":
    
        printDebug("Getting m3u8 playlist", transcode.__name__)
        #Send request for transcode to PMS
        Treq = urllib2.Request(fullURL)
        Tresponse = urllib2.urlopen(Treq)
        Tlink=Tresponse.read()
        printDebug("Initial playlist is " + str(Tlink), transcode.__name__)
        Tresponse.close()   
    
        #tLink contains initual m3u8 playlist.  Pull out the last entry as the actual stream to use (am assuming only single stream)
    
        session=Tlink.split()[-1]
        printDebug("Getting bandwidth playlist " + session, transcode.__name__)
    
        #Append to URL to create link to m3u8 playlist containing the actual media.
        sessionurl="http://"+server+"/video/:/transcode/segmented/"+session
    else: 
        sessionurl=fullURL
    
   
    printDebug("Transcoded media location URL " + sessionurl, transcode.__name__)
    
    return sessionurl
     
def artist(url='',tree=etree,server=''):
        printDebug("== ENTER: artist ==")
        xbmcplugin.setContent(pluginhandle, 'artists')

        #xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
        
        #Get the URL and server name.  Get the XML and parse
        if not url == '':
        
            server=url.split('/')[2]
            print server
            html=getURL(url)
            
            if html is False:
                return

        
            tree=etree.fromstring(html)
            
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
            try:
                arguments['thumb']='http://'+server+arguments['thumb']
            except:
                thumb=g_loc+'/resources/movie.png'  
                print thumb  
                arguments['thumb']=thumb
               
            #Get a nice big picture  
            try:
                fanart=arguments['art'].split('?')[0] #drops the guid from the fanart image
                art_url='http://'+server+fanart.encode('utf-8')
                art_url='http://'+server+':32400/photo/:/transcode?url='+art_url+'&width=1280&height=720'
            except:  
                #or use a stock default one
                art_url=g_loc+'/resources/movie_art.jpg' 

            arguments['fanart_image']=art_url
           
            arguments['type']="Music"

            mode=14 # grab season details
            url='http://'+server+'/library/metadata/'+arguments['ratingKey']+'/children'+"&mode="+str(mode)+"&name="+urllib.quote_plus(properties['title'])
            
            addDir(url,properties,arguments) 
            
        #End the listing    
        xbmcplugin.endOfDirectory(pluginhandle)

def albums(url='', tree=etree, server=''):
        printDebug("== ENTER: albums ==")
        xbmcplugin.setContent(pluginhandle, 'albums')

        #xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
       
        if not url == '':
        
           #Get URL, XML and parse
            server=url.split('/')[2]
            print server
            html=getURL(url)
            
            if html is False:
                return

            
            tree= etree.fromstring(html)
        
        try:
            treeargs=dict(tree.items())
            artist=treeargs['parentTitle']
        except: pass
        
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
            try:
                arguments['thumb']='http://'+server+arguments['thumb']
            except:
                thumb=g_loc+'/resources/movie.png'  
                print thumb  
                arguments['thumb']=thumb
               
            #Get a nice big picture  
            try:
                fanart=arguments['art'].split('?')[0] #drops the guid from the fanart image
                art_url='http://'+server+fanart.encode('utf-8')
                art_url='http://'+server+':32400/photo/:/transcode?url='+art_url+'&width=1280&height=720'
            except:  
                #or use a stock default one
                art_url=g_loc+'/resources/movie_art.jpg' 

            arguments['fanart_image']=art_url

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

def tracks(url='',tree=etree,server=''):
        printDebug("== ENTER: tracks ==")
        xbmcplugin.setContent(pluginhandle, 'songs')
        
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_TRACKNUM)
        
        #Get the server
        try:
            server=url.split('/')[2]
            #Get the end part of thd URL, as we need to get different data if parsing "All Episodes"
            target=url.split('/')[-1]
            printDebug("URL target is " + target, tracks.__name__)
        except: pass
        
        try:
            ShowTags=tree.findall('Track')
        except:
            #Get URL, XML and Parse
            html=getURL(url)
            
            if html is False:
                return

            
            tree=etree.fromstring(html)
            ShowTags=tree.findall('Track')
            
        #get a bit of metadata that sits inside the main mediacontainer
        #If it doesn't exist, we'll check later and get it from elsewhere
        #MainTag=tree.findAll('mediacontainer')[0]
         
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
                    thumb=tree.get('thumb')
                except: pass
                
        except: pass
         
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
           
            print "args is " + str(arguments)
            print "Media is " + str(mediaarguments)
            print "Part is " + str(partarguments)
            
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
            if thumb is None:
                try:
                    arguments['thumb']='http://'+server+arguments['thumb']
                except:
                    arguments['thumb']=g_loc+'/resources/movie.png'
            else:
                arguments['thumb']='http://'+server+thumb

            #Get a nice big picture  
            try:
                fanart=arguments['art'].split('?')[0] #drops the guid from the fanart image
                art_url='http://'+server+fanart.encode('utf-8')
                art_url='http://'+server+':32400/photo/:/transcode?url='+art_url+'&width=1280&height=720'
            except:  
                #or use a stock default one
                art_url=g_loc+'/resources/movie_art.jpg' 

            arguments['fanart_image']=art_url    
                
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

def photo(url):
    printDebug("== ENTER: photos ==")
    server=url.split('/')[2]
    
    html=getURL(url)
    
    if html is False:
        return
    
    tree=etree.fromstring(html)
    
    
    for banana in tree.findall('Directory'):
        
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
                
        try:
            if not arguments['thumb'].split('/')[0] == "http:":
                arguments['thumb']='http://'+server+arguments['thumb']
        except:
            thumb=g_loc+'/resources/movie.png'  
            arguments['thumb']=thumb

            
        if arguments['key'][0] == '/':
            #The key begins with a slah, there is absolute
            u='http://'+server+str(arguments['key'])
        else:
            #Build the next level URL and add the link on screen
            u=url+'/'+str(arguments['key'])
        
        mode=16
        u=u+"&mode="+str(mode)
        addDir(u,properties,arguments)
    
    for coconuts in tree.findall('Photo'):
    
        arguments=dict(coconuts.items())
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
                
        try:
            if not arguments['thumb'].split('/')[0] == "http:":
                arguments['thumb']='http://'+server+arguments['thumb']
        except:
            thumb=g_loc+'/resources/movie.png'  
            arguments['thumb']=thumb

           
        if arguments['key'].split('/')[0] == "http:":
            u=arguments['key']
        elif arguments['key'][0] == '/':
            #The key begins with a slah, there is absolute
            u='http://'+server+str(arguments['key'])
        else:
            #Build the next level URL and add the link on screen
            u=url+'/'+str(arguments['key'])
        
        arguments['type']="Picture"
        addLink(u,properties,arguments)

    xbmcplugin.endOfDirectory(pluginhandle)

def music(url):
    printDebug("== ENTER: music ==")
    xbmcplugin.setContent(pluginhandle, 'artists')


    server=url.split('/')[2]
    
    html=getURL(url)
    
    if html is False:
        return

    
    tree=etree.fromstring(html)
    
    
    for grapes in tree:
       
        arguments=dict(grapes.items())
        arguments['type']="Music"        
        properties={}
        
        try:
            if arguments['key'] == "":
                continue
        except: pass
                        
        try:
            if not arguments['thumb'].split('/')[0] == "http:":
                arguments['thumb']='http://'+server+arguments['thumb']
        except:
            thumb=g_loc+'/resources/movie.png'  
            arguments['thumb']=thumb

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
   
        if arguments['key'][0] == '/':
            #The key begins with a slah, there is absolute
            u='http://'+server+str(arguments['key'])
        else:
            #Build the next level URL and add the link on screen
            u=url+'/'+str(arguments['key'])
        
        if grapes.tag == "Track":
            printDebug("Track Tag", music.__name__)
            xbmcplugin.setContent(pluginhandle, 'songs')
            #xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_TRACKNUM)
            
            try:
                properties['title']=arguments['track'].encode('utf-8')
            except:
                properties['title']="Unknown"
            
                         
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
                printDebug("Artist Tag", music.__name__)
                xbmcplugin.setContent(pluginhandle, 'artists')
                try:
                    properties['title']=arguments['artist']
                except: 
                    properties['title']="Unknown"
             
            elif grapes.tag == "Album":
                printDebug("Album Tag", music.__name__)
                xbmcplugin.setContent(pluginhandle, 'albums')
                try:    
                    properties['title']=arguments['album']
                except: 
                    properties['title']="Unknown"
            elif grapes.tag == "Genre":
                try:    
                    properties['title']=arguments['genre']
                except: 
                    properties['title']="Unknown"
            
            else:
                printDebug("Generic Tag: " + grapes.tag , music.__name__)
                try:
                    properties['title']=arguments['title']
                except:
                    properties['title']="Unknown"
            
            mode=17
            u=u+"&mode="+str(mode)
            addDir(u,properties,arguments)
        
    xbmcplugin.endOfDirectory(pluginhandle)    

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
    printDebug("== ENTER: install ==")
    html=getURL(url)
    tree = etree.fromstring(html)
    
    if tree.get('size') == "1":
        #This plugin is probably not install
        printDebug("Not installed.  Print dialog", install.__name__)
        ret = xbmcgui.Dialog().yesno("Plex Online","About to install " + name)

        if ret:
            printDebug("Installing....", install.__name__)
            installed = getURL(url+"/install")
            tree = etree.fromstring(installed)
    
            msg=tree.get('message')
            printDebug(msg, install.__name__)
            xbmcgui.Dialog().ok("Plex Online",msg)

    else:
        #This plugin is already installed
        printDebug("Already installed", install.__name__)
        operations={}
        i=0
        for plums in tree.findall('Directory'):
            operations[i]=plums.get('key').split('/')[-1]
            i+=1
        
        options=operations.values()
        
        ret = xbmcgui.Dialog().select("This plugin is already installed..",options)
        
        if ret == -1:
            printDebug("No option selected, cancelling", install.__name__)
            return
        
        printDebug("Option " + str(ret) + " selected.  Operation is " + operations[ret], install.__name__)
        u=url+"/"+operations[ret]

        action = getURL(u)
        tree = etree.fromstring(action)
    
        msg=tree.get('message')
        printDebug(msg, install.__name__)
        xbmcgui.Dialog().ok("Plex Online",msg)

        
        
    return
   
def skin():
    #Gather some data and set the windo properties
    printDebug("== ENTER: skin() ==")
    #Get the global host variable set in settings
    host=g_host
    WINDOW = xbmcgui.Window( 10000 )
 
    Servers=[]
      
    #If we have a remote host, then don;t do local discovery as it won't work
    if g_bonjour == "true":
        #Get the HTML for the URL
        url = 'http://'+host+':32400/servers'
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
    printDebug("Number of servers for skin: " + str(len(Servers)), skin.__name__)
    
    sectionCount=0
    
    #For each of the servers we have identified
    for server in Servers:
                                      
        #Get friendly name
        url='http://'+server[1]+':32400'
        html=getURL(url)

        if html is False:
            continue

        tree=etree.fromstring(html)
        try:
            if not tree.get('friendlyName') == "":
                server[0]=tree.get('friendlyName')
            else:
                server[0]=server[1]
        except:
            server[0]=server[1]
            
        #dive into the library section with BS        
        url='http://'+server[1]+':32400/library/sections'
        html=getURL(url)
            
        if html is False:
            continue
                
        tree = etree.fromstring(html)
            
        #Find all the directory tags, as they contain further levels to follow
        #For each directory tag we find, build an onscreen link to drill down into the library
        SectionTags=tree.findall('Directory')
        for object in SectionTags:
            
            arguments=dict(object.items())
            arguments['thumb']=""
            #Set up some dictionaries with defaults that we are going to pass to addDir/addLink
            properties={}

            #Start pulling out information from the parsed XML output. Assign to various variables
            try:
                properties['title']=arguments['title']
            except:
                properties['title']="unknown"
             
            try:
                arguments['art']="http://"+server[1]+":32400"+arguments['art']
            except: pass
            
            print "art is " + arguments['art']
            
            #Determine what we are going to do process after a link is selected by the user, based on the content we find
            if arguments['type'] == 'show':
                window="VideoFiles"
                mode=1
            if  arguments['type'] == 'movie':
                window="VideoFiles"
                mode=2
            if  arguments['type'] == 'artist':
                window="MusicLibrary"
                mode=3
                             
            if g_secondary == "true":
                s_url='http://'+server[1]+':32400/library/sections/'+arguments['key']+"&mode=0&name="+urllib.quote_plus(server[0])
            else:
                #Build URL with the mode to use and key to further XML data in the library
                s_url='http://'+server[1]+':32400/library/sections/'+arguments['key']+'/all'+"&mode="+str(mode)+"&name="+urllib.quote_plus(server[0])
                
            #Build that listing..
            WINDOW.setProperty("plexbmc.%d.title" % (sectionCount) , properties['title'])
            WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount), server[0])
            WINDOW.setProperty("plexbmc.%d.url" % (sectionCount), s_url )
            WINDOW.setProperty("plexbmc.%d.mode" % (sectionCount), str(mode) )
            WINDOW.setProperty("plexbmc.%d.window" % (sectionCount), window )
            WINDOW.setProperty("plexbmc.%d.art" % (sectionCount), arguments['art'] )
            
            printDebug("Building window properties index [" + str(sectionCount) + "] which is [" + properties['title'] + "]", skin.__name__)
            
            sectionCount += 1
    
    try:
        printDebug("Clearing properties from [" + str(sectionCount) + "] to [" + WINDOW.getProperty("plexbmc.sectionCount") + "]", skin.__name__)

        for i in range(sectionCount, int(WINDOW.getProperty("plexbmc.sectionCount"))+1):
            WINDOW.clearProperty("plexbmc.%d.title" % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.subtitle" % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.url" % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.mode" % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.window" % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.art" % ( i ) )
    except:
        pass

    printDebug("Total number of skin sections is [" + str(sectionCount) + "]", skin.__name__)
    WINDOW.setProperty("plexbmc.sectionCount", str(sectionCount))

   
##So this is where we really start the plugin.

print "Script argument is " + str(sys.argv[1])
if str(sys.argv[1]) == "skin":
    skin()
    sys.exit()
else:
    pluginhandle = int(sys.argv[1])

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
        getDirectory(url)
elif mode==1:
        SHOWS(url)
elif mode==2:
        MoviesET(url)
elif mode==3:
        artist(url)
elif mode==4:
        Seasons(url)
elif mode==5:
        PLAYEPISODE(id,url,resume, duration)
elif mode==6:
        EPISODES(url)
elif mode==7:
        PlexPlugins(url)
elif mode==10:
        StartMovies()
elif mode==11:
        StartTV()
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

print "===== PLEXBMC STOP ====="
   
#clear done and exit.        
sys.modules.clear()

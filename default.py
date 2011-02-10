import urllib,urllib2,re,xbmcplugin,xbmcgui,xbmcaddon
import os,datetime, time
import  elementtree.ElementTree as etree

#Get the setting from the appropriate file.
__settings__ = xbmcaddon.Addon(id='plugin.video.plexbmc')
g_host = __settings__.getSetting('ipaddress')
g_stream = __settings__.getSetting('streaming')
g_extended = __settings__.getSetting('extended')
g_secondary = __settings__.getSetting('secondary')
g_loc = "special://home/addon/plugin.video.plexbmc"

print "Settings hostname: " + g_host
print "Settings streaming: " + g_stream
print "Setting secondary: " + g_secondary
pluginhandle = int(sys.argv[1])

################################ Common
# Connect to a server and retrieve the HTML page
def getURL( url ):
    try:
        
        print 'PleXBMC--> getURL :: url = '+url
        print "getting URL"
        txdata = None
        txheaders = {
                    'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US;rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 ( .NET CLR 3.5.30729)'	
                    }
        req = urllib2.Request(url, txdata, txheaders)
        response = urllib2.urlopen(req)
        link=response.read()
        print "URL done"
        response.close()
    except urllib2.URLError, e:
        error = 'Error code: '+ str(e.code)
        xbmcgui.Dialog().ok(error,error)
        print 'Error code: ', e.code
        return False
    else:
        return link
        
#Used to add playable media files to directory listing
#properties is a dictionary {} which contains a list of setInfo properties to apply
#Arguments is a dictionary {} which contains other arguments used in teh creation of the listing (such as name, resume time, etc)
def addLink(id,name,url,mode,properties,arguments):       
        u=sys.argv[0]+"?url="+str(url)
        ok=True

        print 'harley:'+ u

        #Create ListItem object, which is what is displayed on screen
        liz=xbmcgui.ListItem(properties['title'], iconImage="DefaultFolder.png", thumbnailImage=arguments['thumb'])
        
        print "Setting thumbnail as " + arguments['thumb']              
        print "Property is " + str(properties)
        
        #Set properties of the listitem object, such as name, plot, rating, content type, etc
        liz.setInfo( type="Video", infoLabels=properties ) 
        
        #Set the file as playable, otherwise setresolvedurl will fail
        liz.setProperty('IsPlayable', 'true')
        
        #Set the fanart image if it has been enabled
        try:
            liz.setProperty('fanart_image', str(arguments['fanart_image']))
            print "Setting fan art"
        except: pass
        
        #Finally add the item to the on screen list, with url created above
        ok=xbmcplugin.addDirectoryItem(handle=pluginhandle,url=u,listitem=liz)
        
        return ok

#Used to add directory item to the listing.  These are non-playable items.  They can be mixed with playable items created above.
#properties is a dictionary {} which contains a list of setInfo properties to apply
#Arguments is a dictionary {} which contains other arguments used in teh creation of the listing (such as name, resume time, etc)
def addDir(name,url,mode,properties,arguments):

        #Create the URL to pass to the item
        u=sys.argv[0]+"?url="+str(url)
        ok=True
        
        #Create the ListItem that will be displayed
        try:
            liz=xbmcgui.ListItem(properties['title'], iconImage="DefaultFolder.png", thumbnailImage=arguments['thumb'])
        except:
            liz=xbmcgui.ListItem(properties['title'], iconImage="DefaultFolder.png", thumbnailImage='')

            #Set the properties of the item, such as summary, name, season, etc
        liz.setInfo( type="Video", infoLabels=properties ) 
        
        print 'harley:'+ u
        
        #If we have set a number of watched episodes per season
        try:
            #Then set the number of watched and unwatched, which will be displayed per season
            liz.setProperty('WatchedEpisodes', str(arguments['WatchedEpisodes']))
            liz.setProperty('UnWatchedEpisodes', str(arguments['UnWatchedEpisodes']))
        except: pass
        
        #Set the fanart image if it has been enabled
        try:
            liz.setProperty('fanart_image', str(arguments['fanart_image']))
            print "Setting fan art"
        except: pass

        #Finally add the item to the on screen list, with url created above
        ok=xbmcplugin.addDirectoryItem(handle=pluginhandle,url=u,listitem=liz,isFolder=True)
        return ok

################################ Root listing
# Root listing is the main listing showing all sections.  It is used when these is a non-playable generic link content
def ROOT():
        
        #Get the global host variable set in settings
        host=g_host
        
        #Get the HTML for the URL
        url = 'http://'+host+':32400/servers'
        html=getURL(url)
        
        #Pass HTML to BSS to convert it into a nice parasble tree.
        tree=etree.fromstring(html)
                
        #Now, find all those server tags
        LibraryTags=tree.findall('Server')
        print tree
        print LibraryTags
        Servers=[]
        Sections=[]
        
       
        #Now, for each tag, pull out the name of the server and it's network name
        for object in LibraryTags:
            name=object.get('name').encode('utf-8')
            host=object.get('host')
            Servers.append([name,host])
        
        #For each of the servers we have identified
        for server in Servers:
                    
            #dive into the library section with BS        
            url='http://'+server[1]+':32400/library/sections'
            html=getURL(url)
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
                except:pass
                
                #Determine what we are going to do process after a link is selected by the user, based on the content we find
                if arguments['type'] == 'show':
                    mode=1
                if  arguments['type'] == 'movie':
                    mode=2
                if  arguments['type'] == 'artist':
                    mode=3
                
                if g_secondary == "true":
                    s_url='http://'+server[1]+':32400/library/sections/'+arguments['key']+"&mode=0&name="+urllib.quote_plus(name)
                else:
                    #Build URL with the mode to use and key to further XML data in the library
                    s_url='http://'+server[1]+':32400/library/sections/'+arguments['key']+'/all'+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
                
                #Build that listing..
                addDir(arguments['title'],s_url,mode, properties,arguments)
                
			#Plex plugin handling 
            #Simple check if any plugins are present.  
            #If so, create a link to drill down later. One link is created for each PMS server available
            #Plugin data is held in /videos directory (well, video data is anyway)
            pluginurl='http://'+server[1]+':32400/video'
            pluginhtml=getURL(pluginurl)
            plugintree=etree.fromstring(pluginhtml)

            #Check the number of items in the mediacontainer tag.
            try:
                items = plugintree.get('size')
            except:
                items=0
            
            #If we have at least one item listed, then we have some plugin.  In which case, create a link
            if items > 0:
            
                arguments={'thumb':''}
                properties={}

                #URL contains the location of the server plugin.  We'll display the content later
                mode=7
                s_url=pluginurl+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
                properties['title']="Plex Plugins: "+ server[0]
                
                #Add an on screen link
                addDir(properties['title'], s_url, mode, properties,arguments)
		
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
        xbmcplugin.setContent(pluginhandle, 'movies')
        
        print '=============='
        print 'Getting Movies'
        #xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
        
        print "url is " + str(url)
        print "tree is " + str(tree)
        print "server is " + str(server)

        #get the server name from the URL, which was passed via the on screen listing..
        if not url == '':
            print "we have no tree passed.."
            server=url.split('/')[2]
            print server
            #Get some XML and parse it
            html=getURL(url)
            tree = etree.fromstring(html)
                    
        #Find all the video tags, as they contain the data we need to link to a file.
        MovieTags=tree.findall('Video')
        for movie in MovieTags:
            
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
                print "Found unsupported .strm file.  Will not list"
                continue
             
            print "args is " + str(movie.items())
            print "Media is " + str(mediaarguments)
            print "Part is " + str(partarguments)
            
            #Create structure to pass to listitem/setinfo.  Set defaults
            properties={'overlay': 6, 'playcount': 0}   
   
            print "Arguments are " + str(arguments)
            
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
                fanart=arguments['art'].split('?')[0] #drops the guid from the fanart image
                art_url='http://'+server+fanart.encode('utf-8')
                art_url='http://'+server+':32400/photo/:/transcode?url='+art_url+'&width=1280&height=720'
            except:  
                #or use a stock default one
                art_url=g_loc+'/resources/movie_art.jpg'
            
            #print art_url  
            arguments['fanart_image']=art_url
            
            #Assign standard metadata
            #Cast
            properties['cast']=tempcast
            
            #director
            properties['director']=" / ".join(tempdir)
            
            #Writer
            properties['writer']=" / ".join(tempwriter)
            
            #Genre        
            properties['genre']=" / ".join(tempgenre)                
            
            #If the streaming option is true, then get the virtual listing
            if g_stream == "true":
                try:
                    #print "location is " + str(partarguments['key']) 
                    url='http://'+server+str(partarguments['key'])
                except:
                    print "Error: no stream location"
                    continue
            else:
                #Else get the actual location, and use this via SMB if configured
                try:
                    location=str(partarguments['file'])
                    location=location.replace("Volumes",server)
                    location=location.replace(":32400","")
                    url='smb:/'+location
                except:
                    print "Error: No file location"
                    continue
            
            #This is playable media, so link to a path to a play function
            mode=5
            
            print '============='        
            print "properties is " + str(properties)
            print "arguments is " + str(arguments)    
                 
            u=str(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(properties['title'])+"&resume="+str(arguments['viewoffset'])+"&id="+str(arguments['ratingKey'])+"&duration="+str(arguments['duration'])
 
            if mediacount > 1:
                #We have more than one media file to play.  Build link to go to selectMedia
                mode=13
                u='http://'+server+arguments['key']+"&mode="+str(mode)+"&name="+urllib.quote_plus(properties['title'])+"&resume="+str(arguments['viewoffset'])+"&id="+str(arguments['ratingKey'])+"&duration="+str(arguments['duration'])
                    
            print "url is " + u
            #Right, add that link...and loop around for another entry
            addLink(arguments['ratingKey'],properties['title'],u,mode,properties,arguments)        
        
        #If we get here, then we've been through the XML and it's time to finish.
        xbmcplugin.endOfDirectory(pluginhandle)
    

		
    
################################ TV Show Listings
#This is the function use to parse the top level list of TV shows
def SHOWS(url='',tree=etree,server=''):
        xbmcplugin.setContent(pluginhandle, 'tvshows')

        print '=============='
        print 'Getting TV Shows'
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
        
        #Get the URL and server name.  Get the XML and parse
        if not url == '':
        
            server=url.split('/')[2]
            print server
            html=getURL(url)
        
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
           

            mode=4 # grab season details
            url='http://'+server+'/library/metadata/'+arguments['ratingKey']+'/children'+"&mode="+str(mode)+"&name="+urllib.quote_plus(properties['title'])
            
            addDir(properties['title'],url,mode,properties,arguments) 
            
        #End the listing    
        xbmcplugin.endOfDirectory(pluginhandle)
 
################################ TV Season listing            
#Used to display the season data         
def Seasons(url):
        xbmcplugin.setContent(pluginhandle, 'seasons')

        print '=============='
        print 'Getting TV Seasons'
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
        
        #Get URL, XML and parse
        server=url.split('/')[2]
        print server
        html=getURL(url)
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
            except:pass
    
            #Get the Plot          
            try:
                properties['plot']=arguments['summary']
            except: pass

            mode=6
            
            url='http://'+server+arguments['key']+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
            #Set the mode to episodes, as that is what's next 
        
    
            print '============='
            print "properties is " + str(properties)
            print "arguments are " + str(arguments)
            
         

            #Build the screen directory listing
            addDir(properties['title'],url,mode,properties,arguments) 
            
        #All done, so end the listing
        xbmcplugin.endOfDirectory(pluginhandle)
 
################################ TV Episode listing 
#Displays the actual playable media
def EPISODES(url='',tree=etree,server=''):
        xbmcplugin.setContent(pluginhandle, 'episodes')

        print '=============='
        print url
        print 'Getting TV Episodes'
        
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_EPISODE)
        
        #Get the server
        try:
            server=url.split('/')[2]
            #Get the end part of teh URL, as we need to get different data if parsing "All Episodes"
            target=url.split('/')[-1]
            print server
            print target
        except: pass
        
        try:
            ShowTags=tree.findall('Video')
        except:
            print "no tree, so create from html"
            #Get URL, XML and Parse
            html=getURL(url)
            tree=etree.fromstring(html)
            ShowTags=tree.findall('Video')
            
        #get a bit of metadata that sits inside the main mediacontainer
        #If it doesn't exist, we'll check later and get it from elsewhere
        #MainTag=tree.findAll('mediacontainer')[0]
         
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
        #if target != "allLeaves":
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
           
            print "args is " + str(arguments)
            print "Media is " + str(mediaarguments)
            print "Part is " + str(partarguments)
            print "Extra info is " + str(tempgenre) + str(tempwriter) + str(tempcast) + str(tempdir)
            
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
                arguments['viewoffset']
            except:
                arguments['viewoffset']=0

                        
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
            if g_stream == "true":
                try:
                    url='http://'+server+str(partarguments['key'])
                except:
                    print "Error: no stream location"
                    continue
            else:
                #Else get the actual location, and use this via SMB if configured
                try:
                    location=str(partarguments['file'])
                    location=location.replace("Volumes",server)
                    location=location.replace(":32400","")
                    url='smb:/'+location
                except:
                    print "Error: No file location"
                    continue
                            
            #Set mode 5, which is play            
            mode=5
            print '============='        
            print "properties is " + str(properties)
            print "arguments is " + str(arguments)    

            u=str(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(properties['title'])+"&resume="+str(arguments['viewoffset'])+"&id="+str(arguments['ratingKey'])+"&duration="+str(arguments['duration'])
                
            #Build a file link and loop
            addLink(id,arguments['title'],url,mode,properties,arguments)        
        
        #End the listing
        xbmcplugin.endOfDirectory(pluginhandle)

#What to do to process Plex Plugin structures        
def PlexPlugins(url):
        xbmcplugin.setContent(pluginhandle, 'movies')

        print '=============='
        print 'Getting Plugin Details'
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)

        #get the serverm URL, XML and parse
        server=url.split('/')[2]
        print server
        html=getURL(url)
        tree=etree.fromstring(html)
		        
                
        print html        
        for orange in tree:
               
            arguments=dict(orange.items())
            print "arguments is " + str(arguments)

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
                arguments['thumb']='http://'+server+arguments['thumb']
            except:
                thumb=g_loc+'/resources/movie.png'  
                print thumb  
                arguments['thumb']=thumb

            
            if arguments['key'][0] == '/':
                #The key begins with a slah, there is absolute
                p_url='http://'+server+str(arguments['key'])
            else:
                #Build the next level URL and add the link on screen
                p_url=url+'/'+str(arguments['key'])

            
            if orange.tag == "Directory":
                #We have a directory tag, so come back into this function
                mode=7   
                s_url=p_url+"&mode="+str(mode)+"&name="+urllib.quote_plus(properties['title'])
                

                print "properties is " + str(properties)
                
                addDir(properties['title'], s_url, mode, properties, arguments)
                    
            #If we have some video links as well
            elif orange.tag == "Video":
             
                #Set the mode to play them this time
                mode=12                       
                    
                #Build the URl and add a link to the file
                v_url=p_url+"&mode="+str(mode)+"&name="+urllib.quote_plus(properties['title'])    

                print "properties is " + str(properties)
                
                addLink(id,properties['title'], v_url, mode, properties, arguments)
        
        #Ahh, end of the list   
        xbmcplugin.endOfDirectory(pluginhandle)
        
#Right, this is used to play PMS library data file.  This function will attempt to update PMS as well.
#Only use this to play stuff you want to update in the library        
def PLAYEPISODE(id,vids,seek, duration):
        #Use this to play PMS library items that you want up dated (Movies, TV shows)
        url = vids
       
        print "current resume is " + str(seek)
       
        resumeSetting=__settings__.getSetting('resume')
        print "resumeSetting is " + str(resumeSetting)
        if len(resumeSetting) > 0:
            resumeid, resumetime = resumeSetting.split("|")
            print "resumeid = " + resumeid
            print "resumetime = " + resumetime
            if resumeid == id:
                print "matching IDs, setting nee resume"
                resume = int(resumetime)
            else:
                resume = seek
        else:
            resume = seek
        
        print "resume set to " + str(resume)
        
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
            print "We are part way through this video!"
            
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
            print "not playing yet...sleep for 2"
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
        monitorPlayback(id,url, resume, duration)
        
        return

def selectMedia(id,url,seek,duration):
    #if we have two or more files for teh same movie, then present a screen

    options=[]
    server=url.split('/')[2]
    html=getURL(url)
    newtree=etree.fromstring(html)
       
    video=newtree.findall('Video')
    
    #Nasty code - but can;t for the life of me work out how to get the Part Tags only!!!!
    for file in video:
    
        print file.tag
        for crap in file:
            print str(crap.tag)
            if crap.tag == "Media":
                print "havce foud media"
                for stuff in crap:
                    print str(stuff.tag)
                    if stuff.tag == "Part":
                        print "have found Part"
                        bits=stuff.get('key'), stuff.get('file')
                        print "bit is " + str(bits)
                        options.append(bits)
            
    
    dialogOptions=[]
    for items in options:
        print "item is " + str(items)
        name=items[1].split('/')[-1]
        dialogOptions.append(name)
    
    #Build the dialog text
    print "we have a decision to make!"
            
    #Create a dialog object
    startTime = xbmcgui.Dialog()
            
    #Box displaying resume time or start at beginning
    result = startTime.select('Choose which file',dialogOptions)
            
    #result contains an integer based on the selected text.
    if result == -1:
        #-1 is an exit without choosing, so end the function and start again when the user selects a new file.
        return
    else:
        if g_stream == "true":
            play=options[result][0]
            newurl='http://'+server+str(play)
        else:
            play=options[result][1]
            play=play.replace("Volumes",server)
            play=play.replace(":32400","")
            newurl='smb://'+play
    
    print "url is " + newurl
    PLAYEPISODE(id,newurl,seek, duration)
    return
    
    
    
        
#Monitor function so we can update PMS
def monitorPlayback(id, url, resume, duration):
    #Need to monitor the running playback, so we can determine a few things:
    #1. If the file has completed normally (i.e. the movie has finished)
    #2. If the file has been stopped halfway through - need to record the stop time.
    
    #Get the server name to update
    server=url.split('/')[2]
    
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
    print "Playback stopped at " + str(currentTime) + " which is " + str(progress) + "%."
    if progress <= 5:
        #Then we hadn't watched enough to make any changes
        print "Less than 5% played, so do no store resume time but ensure that film is marked unwatched"
        updateURL="http://"+server+"/:/unscrobble?key="+id+"&identifier=com.plexapp.plugins.library"
        print "updateURL = " + updateURL
    elif progress >= 95:
        #Then we were 95% of the way through, so we mark the file as watched
        print "More than 95% completed, so mark as watched"
        updateURL="http://"+server+"/:/scrobble?key="+id+"&identifier=com.plexapp.plugins.library"
        print "updateURL = " + updateURL
    else:
        #we were more than 5% and less then 95% of the way through, store the resume time
        print "More than 5% and less than 95% of the way through, so store resume time"
        updateURL="http://"+server+"/:/progress?key="+id+"&identifier=com.plexapp.plugins.library&time="+str(currentTime*1000)
        print "updateURL = " + updateURL
        
    #Submit the update URL    
    output = getURL(updateURL)
    print "output is " + str(output)
    
    print "Creating a temporary new resume time"
    __settings__.setSetting('resume', str(id)+"|"+str(currentTime*1000))
     
    return
    
#Just a standard playback 
def PLAY(vids):
        #This is for playing standard non-PMS library files (such as Plugins)
        url = vids
        item = xbmcgui.ListItem(path=url)
        return xbmcplugin.setResolvedUrl(pluginhandle, True, item)

#Function to parse the arguments passed to the plugin..
def get_params():
        param=[]
        paramstring=sys.argv[2]
        print "param string is " + paramstring
        if len(paramstring)>=2:
                print "param bigger than 2"
                params=sys.argv[2]
                #Rather than replace ? with ' ' - I split of the first char, which is always a ? (hopefully)
                #Could always add a check as well..
                cleanedparams=params[1:] #.replace('?','')
                print "Cleaned params is " + cleanedparams
                if (params[len(params)-1]=='/'):
                        print "not sure what this does"
                        params=params[0:len(params)-2]
                pairsofparams=cleanedparams.split('&')
                print "pair of params" + str(pairsofparams)
                param={}
                for i in range(len(pairsofparams)):
                        print "i is " + str(i)
                        splitparams={}
                        #Right, extended urls that contain = do not parse correctly and this tops plugins from working
                        #Need to think of a better way to do the split, at the moment i'm hacking this by gluing the
                        #two bits back togethers.. nasty...
                        splitparams=pairsofparams[i].split('=')
                        print "spilt is " + str(splitparams)
                        if (len(splitparams))==2:
                                param[splitparams[0]]=splitparams[1]
                        elif (len(splitparams))==3:
                                param[splitparams[0]]=splitparams[1]+"="+splitparams[2]
                                
        return param

def getDirectory(url):  
    #We've been called at mode 0, by ROOT becuase we are going to traverse the secondary menus
    
    #print "We are going down the " + str(type) + " path...."
    
    #First we need to peek at the XML, to see if we've hit any video links yet.
    
    print "process by getDirectory"
    
    server=url.split('/')[2]
    lastbit=url.split('/')[-1]
    
    if lastbit.startswith('search'):
        #Found search URL.  Bring up keyboard and get input for query string
        print "Found a search URL."
        kb = xbmc.Keyboard('', 'heading')
        kb.setHeading('Enter search term') # optional
        kb.doModal()
        if (kb.isConfirmed()):
            text = kb.getText()
            url=url+'&query='+text
        else:
            return
     
    
    html=getURL(url)
    tree=etree.fromstring(html)
    
    
    
    arguments=dict(tree.items())
    
    if arguments['viewGroup'] == "movie":
        print "this is a movie XML, passing to MoviesET"
        MoviesET(tree=tree,server=server)
        return
    elif arguments['viewGroup'] == "show":
        print "this is a tv show XML, passing to SHOW"
        SHOWS(tree=tree,server=server)
        return
    elif arguments['viewGroup'] == "episode":
        EPISODES(url=url,tree=tree,server=server)
        return
    elif arguments['viewGroup'] == 'artist':
        print "this is music XML, passing to music"
        music(tree=tree,server=server)
        return
        
    #else we have a secondary, which we'll process here
    print "We must have some secondaries to process"
    
    for apple in tree:
        arguments=dict(apple.items())
        properties={}
        properties['title']=arguments['title']
        
        n_url=url+'/'+arguments['key']+'&mode=0'

        addDir(properties['title'],n_url,0,properties,arguments)
        
    xbmcplugin.endOfDirectory(pluginhandle)
                  
    
##So this is where we really start the plugin.

#first thing, parse the arguments, as this has the data we need to use.              
params=get_params()
print params

#Set up some variables
url=None
name=None
mode=None
resume=None
id=None
duration=None

#Now try and assign some data to them
try:
        url=urllib.unquote_plus(params["url"])
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
        thumbnail=urllib.unquote_plus(params["thumbnail"])
except:
        thumbnail=''
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
        
print "Mode: "+str(mode)
print "URL: "+str(url)
print "Name: "+str(name)
print "ID: "+ str(id)
print "Duration: " + str(duration)

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
        Artist(name,url)
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
        
#clear done and exit.        
sys.modules.clear()

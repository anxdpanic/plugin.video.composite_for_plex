import urllib,urllib2,re,xbmcplugin,xbmcgui,xbmcaddon
import os,datetime, time
from BeautifulSoup import BeautifulStoneSoup
__settings__ = xbmcaddon.Addon(id='plugin.video.plexbmc')
g_host = __settings__.getSetting('ipaddress')
g_stream = __settings__.getSetting('streaming')
print "Settings hostname: " + g_host
print "Settings streaming: " + g_stream
pluginhandle = int(sys.argv[1])

################################ Common
def getURL( url ):
    try:
        
        print 'PleXBMC--> getURL :: url = '+url
        txdata = None
        txheaders = {
                    'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US;rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 ( .NET CLR 3.5.30729)'	
                    }
        req = urllib2.Request(url, txdata, txheaders)
        response = urllib2.urlopen(req)
        link=response.read()
        response.close()
    except urllib2.URLError, e:
        error = 'Error code: '+ str(e.code)
        xbmcgui.Dialog().ok(error,error)
        print 'Error code: ', e.code
        return False
    else:
        return link

def addLink(id,name,url,mode,properties,arguments):       
        url=urllib.quote(str(url))
            
        u=sys.argv[0]+"?url="+str(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)+"&resume="+str(arguments['resume'])+"&id="+id+"&duration="+str(arguments['duration'])
        ok=True
          
        if properties['playcount'] > 0:
            #we have a watched film.  I can't see a way of displaying a partial like Plex, which uses resume time to decide.
            print "Watched file, setting overlay to 7"
            properties['overlay']=7 # watched icon
            
        print "Setting up ListItem"
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=arguments['thumb'])
        
        print "Setting thumbnail as " + arguments['thumb']              
        print "Property is " + str(properties)
        
        liz.setInfo( type="Video", infoLabels=properties ) 
        
        print "setting as a Playable file"
        liz.setProperty('IsPlayable', 'true')
        print "Adding to list"
        
        ok=xbmcplugin.addDirectoryItem(handle=pluginhandle,url=u,listitem=liz)
        print "Done setting, return was " + str(ok)
        return ok

def addDir(name,url,mode,iconimage='',plot='', episodes=0, aired='', genre=''):
        u=sys.argv[0]+"?url="+str(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name,
                                                "Plot": plot, 
                                                "episode": episodes,
                                                "aired": aired,
                                                "Genre": genre})
        print 'harley:'+ u
        ok=xbmcplugin.addDirectoryItem(handle=pluginhandle,url=u,listitem=liz,isFolder=True)
        return ok

################################ Root listing
def ROOT():
        #xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
        
        host=g_host
        
        url = 'http://'+host+':32400/servers'
        html=getURL(url)
        tree=BeautifulStoneSoup(html, convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
        LibraryTags=tree.findAll('server')
        print tree
        print LibraryTags
        Servers=[]
        Sections=[]
        for object in LibraryTags:
            name=object.get('name').encode('utf-8')
            host=object.get('host')
            Servers.append([name,host])
        
        for server in Servers:
            url='http://'+server[1]+':32400/library/sections'
            html=getURL(url)
            tree=BeautifulStoneSoup(html, convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
            SectionTags=tree.findAll('directory')
            for object in SectionTags:
                key=object.get('key')
                name=object.get('title')
                type=object.get('type')
                if type == 'show':
                    mode=1
                if type == 'movie':
                    mode=2
                if type == 'artist':
                    mode=3
                s_url='http://'+server[1]+':32400/library/sections/'+key+'/all'
                addDir(name,s_url,mode)
                
			#Add Plex plugin handling - Simply check if plugin are present.  If so, create a link to drill down later.
			#One link is created for each PMS server available
            pluginurl='http://'+server[1]+':32400/video'
            pluginhtml=getURL(pluginurl)
            plugintree=BeautifulStoneSoup(pluginhtml, convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
            head = plugintree.find('mediacontainer')

            items = head['size']
			
            if items > 0:
                s_url=pluginurl
                mode=7
                name="Plex Plugins: "+ server[0]
                addDir(name, s_url, mode)
		
		
        xbmcplugin.endOfDirectory(pluginhandle)  
################################ Movies listing            
def StartMovies():
        print '=========================='
        print 'Starting with Movies'
        host=g_host
        url = 'http://'+host+':32400/library/sections'
        html=getURL(url)
        tree=BeautifulStoneSoup(html, convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
        SectionTags=tree.findAll('directory')
        for object in SectionTags:
            key=object.get('key')
            name=object.get('title')
            type=object.get('type')
            if type== 'movie':
                url='http://'+host+':32400/library/sections/'+key+'/all'
                Movies(url)


################################ Movies listing            
def StartTV():
        print '=========================='
        print 'Starting with TV Shows'
        host=g_host
        url = 'http://'+host+':32400/library/sections'
        html=getURL(url)
        tree=BeautifulStoneSoup(html, convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
        SectionTags=tree.findAll('directory')
        for object in SectionTags:
            key=object.get('key')
            name=object.get('title')
            type=object.get('type')
            if type== 'show':
                url='http://'+host+':32400/library/sections/'+key+'/all'
                SHOWS(url)

################################ Movies listing            
def Movies(url):
        xbmcplugin.setContent(pluginhandle, 'movies')
        
        print '=============='
        print 'Getting Movies'
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)

        server=url.split('/')[2]
        print server
        html=getURL(url)
        tree= BeautifulStoneSoup(html, convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
        MovieTags=tree.findAll('video')
        for movie in MovieTags:
        
            properties={'overlay': 6, 'playcount': 0}   #Create a dictionary for properties (i.e. ListItem properties)
            arguments={'type': "movies", 'resume': 0, 'duration': 0}    #Create a dictionary for file arguments (i.e. stuff you need, but are no listitems)
   
            id=movie.get('ratingkey')
            arguments['id']=id
            
            name=movie.get('title')
            arguments['name']=name.encode('utf-8')
            if  arguments['name'].find('&apos;') >0:
                arguments['name'] = arguments['name'].replace("&apos;","'")
            
            properties['title']=arguments['name']
            
            plot=movie.get('summary')
            if plot is not None:
                properties['plot']=plot.encode('utf-8')
                if  properties['plot'].find('&apos;') >0:
                    properties['plot'] = properties['plot'].replace("&apos;","'")
          
            playcount=movie.get('viewcount')
            if playcount is not None:
                properties['playcount']=int(playcount)
            
            rating=movie.get('rating')
            if rating is not None:
                properties['rating']=float(rating)
            
            resume=movie.get('viewoffset')
            if resume is not None:
                arguments['resume']=resume
            
            studio=movie.get('studio') 
            if studio is not None:
                properties['studio']=studio.encode('utf-8')
            
            certificate=movie.get('contentrating')
            if certificate is not None:
                properties['certificate'] = certificate
            
            year=movie.get('year')
            if year is not None:           
                properties['year']=int(year)
            
            tagline=movie.get('tagline')
            if tagline is not None:
                properties['tagline']=tagline.encode('utf-8')
            
            duration=movie.findAll('media')[0].get('duration')
            if duration is not None:           
                arguments['duration']=int(duration)/1000
                properties['duration']=str(datetime.timedelta(milliseconds=int(duration)))
            else:
                #Fall back to the standard duration as discovered by PMS
                duration=movie.get('duration')
                if duration is not None:           
                    arguments['duration']=int(duration)/1000
                    properties['duration']=str(datetime.timedelta(milliseconds=int(duration)))
                
            thumb='http://'+server+movie.get('thumb').encode('utf')
            if thumb is not None:
                arguments['thumb']=thumb
            
            genreList=[]
            try:
                tempgenres=movie.findAll('genre')  #.encode('utf-8')
                for item in tempgenres:
                    genreList.append(item.get('tag'))
            except: pass
      
            genre = " / ".join(genreList)
            properties['genre']=genre
            
            if g_stream == "true":
                location=movie.findAll('part')[0].get('key')
                url='http://'+server+location
            else:
                location=movie.findAll('part')[0].get('file')
                location=location.replace("Volumes",server)
                location=location.replace(":32400","")
                url='smb:/'+location
				
            mode=5
            strUrl=str(url)
            print strUrl
            if strUrl.find('.strm') >0:
                continue
            else:
                print '============='        
                print "properties is " + str(properties)
                print "arguments is " + str(arguments)    
                 
                addLink(id,arguments['name'],url,mode,properties,arguments)        
        xbmcplugin.endOfDirectory(pluginhandle)
    
################################ TV Shows listing            

def SHOWS(url):
        xbmcplugin.setContent(pluginhandle, 'tvshows')

        print '=============='
        print 'Getting TV Shows'
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
        server=url.split('/')[2]
        print server
        html=getURL(url)
        tree=BeautifulStoneSoup(html, convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
        ShowTags=tree.findAll('directory')
        for show in ShowTags:

            arguments={}
        
            id=show.get('ratingkey').encode('utf-8')
            
            name=show.get('title')
            arguments['name']=name.encode('utf-8')
            if  arguments['name'].find('&apos;') >0:
                arguments['name'] = arguments['name'].replace("&apos;","'")
            
            name=arguments['name']
            
            #try:name=show.get('title').encode('utf-8')
            #except:pass
            try:studio=show.get('studio').encode('utf-8')
            except:pass
            summary=show.get('summary').encode('utf-8')
            try:
                contentrating=show.get('contentrating').encode('utf-8')
            except:pass
            
            try: episodes=int(show.get('leafcount'))
            except: episodes=0
            
            genreList=[]
            
            try:
                tempgenres=show.findAll('genre')  #.encode('utf-8')
                for item in tempgenres:
                    genreList.append(item.get('tag'))
            except: pass
      
            genre = " / ".join(genreList)

            try:aired=show.get('originallyavailableat')
            except:pass
            try:thumb='http://'+server+show.get('thumb').encode('utf-8')
            except:pass
            url='http://'+server+'/library/metadata/'+id+'/children'
            mode=4
            season=0
            #episode=0
            showname=name
            print '============='
            print "name: " + name
            print "url: " + url
            print "thumb: " + thumb
            print "summary: " + summary
            print "Episodes: " + str(episodes)
            print "Aired: "+ aired
            print "Genre: " + genre
            strUrl=str(url)
            print strUrl
            
            addDir(name,url,mode,thumb,summary, episodes, aired, genre)
        xbmcplugin.endOfDirectory(pluginhandle)
 
################################ TV Season listing            
         
def Seasons(url):
        xbmcplugin.setContent(pluginhandle, 'tvshows')

        print '=============='
        print 'Getting TV Seasons'
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
        server=url.split('/')[2]
        print server
        html=getURL(url)
        tree=BeautifulStoneSoup(html, convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
        ShowTags=tree.findAll('directory')
        for show in ShowTags:
            id=show.get('key').encode('utf-8')
            try:name=show.get('title').encode('utf-8')
            except:pass
            try:thumb='http://'+server+show.get('thumb').encode('utf-8')
            except:thumb=''
            try: episodes=int(show.get('leafcount'))
            except: episodes=0
            url='http://'+server+id
            mode=6
            season=0
            showname=name
            summary=""
            print '============='
            print name
            print url
            print thumb
            addDir(name,url,mode,thumb,summary, episodes)
        xbmcplugin.endOfDirectory(pluginhandle)
 
################################ TV Episode listing 
def EPISODES(url):
        xbmcplugin.setContent(pluginhandle, 'episodes')

        print '=============='
        print url
        print 'Getting TV Episodes'
        
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_EPISODE)
        
        server=url.split('/')[2]
        target=url.split('/')[-1]
        print server
        print target
        html=getURL(url)
        tree=BeautifulStoneSoup(html, convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
        ShowTags=tree.findAll('video')
        print "using Tags: " + str(ShowTags)
        MainTag=tree.findAll('mediacontainer')[0]
         
        showname=MainTag.get('grandparenttitle')
        certificate = MainTag.get('grandparentcontentrating')
        studio = MainTag.get('grandparentstudio')

        if target != "allLeaves":
            season=MainTag.get('parentindex')

        
        for show in ShowTags:
            print show
            
            properties={'overlay': 6, 'playcount': 0, 'season' : 0}   #Create a dictionary for properties with some defaults(i.e. ListItem properties)
            arguments={'type': "tvshows", 'resume': 0, 'duration': 0}    #Create a dictionary for file arguments (i.e. stuff you need, but are no listitems)
            
            id=show.get('ratingkey')
            arguments['id']=id
            
            episode=show.get('index')
            if episode is not None:
                properties['episode']=int(episode)

            name=show.get('title')
            arguments['name']=name.encode('utf-8')
            if  arguments['name'].find('&apos;') >0:
                arguments['name'] = arguments['name'].replace("&apos;","'")
            properties['title']=arguments['name']

            plot=show.get('summary')
            if plot is not None:
                properties['plot']=plot.encode('utf-8')
                if  properties['plot'].find('&apos;') >0:
                    properties['plot'] = properties['plot'].replace("&apos;","'")
            
            if target == "allLeaves":
                season = show.get('parentindex')
                if season is not None:
                    properties['season']=int(season)
            else:    
                properties['season']=int(season)
                
            if certificate:
                properties['mpaa']=certificate
            else:
                print "cert not set"
                certificate = show.get('contentrating')
                if certificate is not None:
                    properties['mpaa']=certificate
                    
                    
            if showname:
                properties['showname']=showname
            else:
                print "showname not set"
                showname = show.get('grandparenttitle')
                if certificate is not None:
                    properties['showname']=showname
            
            if studio:
                properties['studio']=studio
            else:
                print "studio not set"
                studio = show.get('studio')
                if studio is not None:
                    properties['studio']=studio
            
            resume=show.get('viewoffset')
            if resume is not None:
                arguments['resume']=resume
                
            thumb='http://'+server+show.get('thumb').encode('utf')
            if thumb is not None:
                arguments['thumb']=thumb

            rating=show.get('rating')
            if rating is not None:
                properties['rating']=float(rating)
            
            aired=show.get('originallyavailableat')
            if aired is not None:
                properties['aired']=aired
			            
            duration=show.findAll('media')[0].get('duration')
            if duration is not None:           
                arguments['duration']=int(duration)/1000
                properties['duration']=str(datetime.timedelta(milliseconds=int(duration)))
                     
            if g_stream == "true":
                location=show.findAll('part')[0].get('key')
                url='http://'+server+location
            else:	
                location=show.findAll('part')[0].get('file')
                location=location.replace("Volumes",server)
                location=location.replace(":32400","")
                url='smb:/'+location
			            
            mode=5
            strUrl=str(url)
            print strUrl
            if strUrl.find('.strm') >0:
                continue
            else:
                print '============='        
                print "properties is " + str(properties)
                print "arguments is " + str(arguments)    

                addLink(id,arguments['name'],url,mode,properties,arguments)        

        xbmcplugin.endOfDirectory(pluginhandle)
        
def PlexPlugins(url):
        xbmcplugin.setContent(pluginhandle, 'video')

        print '=============='
        print 'Getting Plugin Details'
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)

        server=url.split('/')[2]
        print server
        html=getURL(url)
        tree= BeautifulStoneSoup(html, convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
        head = tree.find('mediacontainer')
        print "head " + str(head)
		
        try:
            #Look for plugin content
            content = head.get('content')
        except:
            content = "None"
		
        print "content is " + str(content)
        
        if content == "plugins":
            #then we have found an initial plugin list
            print "Found plugin list"
            DirectoryTags=tree.findAll('directory')
            for links in DirectoryTags:
                id=links.get('key')
                name=links.get('title').encode('utf-8')
                mode=7
                try:thumb='http://'+server+links.get('thumb').encode('utf-8')
                except:pass	
                d_url=url+'/'+id
                addDir(name, d_url, mode, thumb)
        else:
            print "Found plugin details"
            #this is either a list of plugin menus (directory) or a list of plugin video (or a mix)
            DirectoryTags=tree.findAll('directory')
            VideoTags=tree.findAll('video')
            print "Found some dirs: " + str(DirectoryTags)
            print "Found some videos: " + str(VideoTags)
            
            if DirectoryTags:
                #We have directories, in which case process as adddirs
                for tags in DirectoryTags:
                    print str(tags)
                    id=tags.get('key')
                    name=tags.get('name').encode('utf-8')
                    mode=7
                    try:thumb='http://'+server+tags.get('thumb').encode('utf')
                    except:pass	
                    d_url='http://'+server+id
                    print "url is " + d_url
                    addDir(name, d_url, mode, thumb)
            
            if VideoTags:
                #We have video items, that we need to addlinks for 
                for tags in VideoTags:
                    
                    properties={'overlay': 6, 'playcount': 0}   #Create a dictionary for properties with some defaults(i.e. ListItem properties)
                    arguments={'type': "video", 'resume': 0, 'duration': 0}    #Create a dictionary for file arguments (i.e. stuff you need, but are no listitems)
                    
                    id=tags.get('key')
                    
                    name=tags.get('title')
                    arguments['name']=name.encode('utf-8')
                    if  arguments['name'].find('&apos;') >0:
                        arguments['name'] = arguments['name'].replace("&apos;","'")
                    properties['title']=arguments['name']

                    mode=12
                    
                    thumb='http://'+server+tags.get('thumb')
                    if thumb is not None:
                        arguments['thumb']=thumb.encode('utf')
                    
                    v_url='http://'+server+id    
            
                    addLink(id,name, v_url, mode, properties, arguments)
           
        xbmcplugin.endOfDirectory(pluginhandle)
         
def PLAYEPISODE(id,vids,seek, duration):
        #Use this to play PMS library items that you want up dated (Movies, TV shows)
        url = vids
        resume = seek
        item = xbmcgui.ListItem(path=url)
        result=1
            
        if resume > 0:
            resumeseconds = resume/1000
            displayTime = str(datetime.timedelta(seconds=int(resumeseconds)))
            dialogOptions = [ "Resume from " + str(displayTime) , "Start from beginning"]
            print "We are part way through this video!"
            startTime = xbmcgui.Dialog()
            result = startTime.select('',dialogOptions)
            if result == -1:
                return
        
        start = xbmcplugin.setResolvedUrl(pluginhandle, True, item)
        
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
        
        if result == 0:
            #Need to skip forward (seconds)
            xbmc.Player().seekTime((resumeseconds)) 
        
        #OK, we have a file, playing at the correct stop.  Now we need to monitor the file playback to allow updates into PMS
        monitorPlayback(id,url, resume, duration)
        
        return

def monitorPlayback(id, url, resume, duration):
    #Need to monitor the running playback, so we can determine a few things:
    #1. If the file has completed normally (i.e. the movie has finished)
    #2. If the file has been stopped halfway through - need to record the stop time.
    
    server=url.split('/')[2]
    currentTime=int(resume)
    
    if duration == 0 and xbmc.Player().isPlaying():
        duration = int(xbmc.Player().getTotalTime())
    
    while xbmc.Player().isPlaying():
        currentTime = int(xbmc.Player().getTime())
        progress = int((float(currentTime)/float(duration))*100)
        #print "Progress: " + str(progress) + "% completed"
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
    
    #Execute a refresh so that the new resume time/watched status shows immediately.  
    #Would be better if we could refesh this one listing. possible?
    xbmc.executebuiltin("Container.refresh") 
    #Can we reselect the previous object?
     
    return
    
def PLAY(vids):
        #This is for playing standard non-PMS library files (such as Plugins)
        url = vids
        item = xbmcgui.ListItem(path=url)
        return xbmcplugin.setResolvedUrl(pluginhandle, True, item)


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

              
params=get_params()
print params
url=None
name=None
mode=None
resume=None
id=None
duration=None

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

if mode==None or url==None or len(url)<1:
        ROOT()
elif mode==1:
        SHOWS(url)
elif mode==2:
        Movies(url)
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
        
sys.modules.clear()

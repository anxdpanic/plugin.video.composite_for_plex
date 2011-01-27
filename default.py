import urllib,urllib2,re,xbmcplugin,xbmcgui,xbmcaddon
import os,datetime
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

def addLink(name,url,mode,iconimage='',plot='',season=0,episode=0,showname=''):
        u=sys.argv[0]+"?url="+str(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name,
                                                "Plot":plot,
                                                "Season":season,
                                                "Episode":episode,
                                                "TVShowTitle":showname})
        liz.setProperty('IsPlayable', 'true')
        ok=xbmcplugin.addDirectoryItem(handle=pluginhandle,url=u,listitem=liz)
        return ok

def addDir(name,url,mode,iconimage='',plot=''):
        u=sys.argv[0]+"?url="+str(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
        ok=True
        liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
        liz.setInfo( type="Video", infoLabels={ "Title": name, "Plot":plot})
        print 'harley:'+ u
        ok=xbmcplugin.addDirectoryItem(handle=pluginhandle,url=u,listitem=liz,isFolder=True)
        return ok

################################ Root listing
def ROOT():
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
        
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
            name=object.get('name')
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
        xbmcplugin.endOfDirectory(pluginhandle)  
                
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
            id=movie.get('ratingKey')
            name=movie.get('title').encode('utf-8')
            summary=movie.get('summary').encode('utf-8')
            try:thumb='http://'+server+movie.get('thumb').encode('utf')
            except:pass
            try:
                genres=[]
                tempgenres=movie.findAll('genres').encode('utf-8')
                for item in tempgenres:
                    genres.append(item.get('tag'))
            except:genres=[]
            
            if g_stream == "true":
                location=movie.findAll('part')[0].get('key')
                url='http://'+server+":32400"+location
            else:
                location=movie.findAll('part')[0].get('file')
                location=location.replace("Volumes",server)
                location=location.replace(":32400","")
                url='smb:/'+location
				
            mode=5
            seasonNum=0
            episodeNum=0
            showname=""
            strUrl=str(url)
            print strUrl
            if strUrl.find('.strm') >0:
                continue
            else:
                print '============='
                print name
                print url
                print thumb
                print summary
                addLink(name,url,mode,thumb,summary,seasonNum,episodeNum,showname)
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
            id=show.get('ratingkey').encode('utf-8')
            try:name=show.get('title').encode('utf-8')
            except:pass
            try:studio=show.get('studio').encode('utf-8')
            except:pass
            summary=show.get('summary').encode('utf-8')
            try:
                contentrating=show.get('contentrating').encode('utf-8')
            except:pass
            try:
                genres=[]
                tempgenres=show.findAll('genres').encode('utf-8')
                for item in tempgenres:
                    genres.append(item.get('tag'))
            except:genres=[]
            try:aired=show.get('originallyavailableat')
            except:pass
            try:thumb='http://'+server+show.get('thumb').encode('utf-8')
            except:pass
            url='http://'+server+'/library/metadata/'+id+'/children'
            mode=4
            season=0
            episode=0
            showname=name
            print '============='
            print name
            print url
            print thumb
            print summary
            strUrl=str(url)
            print strUrl
            
            addDir(name,url,mode,thumb,summary)
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
            except:pass
            url='http://'+server+id
            mode=6
            season=0
            episode=0
            showname=name
            summary=""
            print '============='
            print name
            print url
            print thumb
            addDir(name,url,mode,thumb,summary)
        xbmcplugin.endOfDirectory(pluginhandle)
 
################################ TV Episode listing 
def EPISODES(url):
        xbmcplugin.setContent(pluginhandle, 'episodes')

        print '=============='
        print 'Getting TV Episodes'
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_EPISODE)
        server=url.split('/')[2]
        print server
        html=getURL(url)
        tree=BeautifulStoneSoup(html, convertEntities=BeautifulStoneSoup.HTML_ENTITIES)
        ShowTags=tree.findAll('video')
        season=tree.findAll('mediacontainer')[0].get('parentindex')
        showname=tree.findAll('mediacontainer')[0].get('grandparenttitle')
        for show in ShowTags:
            id=show.get('key')
            episode=show.get('index')
            name=show.get('title').encode('utf-8')
            summary=show.get('summary').encode('utf-8')
            try:thumb='http://'+server+show.get('thumb').encode('utf')
            except:pass
            rating=show.get('rating')
            aired=show.get('originallyavailableat')
			
            if g_stream == "true":
                location=show.findAll('part')[0].get('key')
                url='http://'+server+':32400'+location
            else:	
                location=show.findAll('part')[0].get('file')
                location=location.replace("Volumes",server)
                location=location.replace(":32400","")
                url='smb:/'+location
				
            mode=5
            season=int(season)
            episode=int(episode)
            strUrl=str(url)
            print strUrl
            if strUrl.find('.strm') >0:
                continue
            else:
                print '============='
                print name
                print url
                print thumb
                print summary
                addLink(name,url,mode,thumb,summary,season,episode,showname)

        xbmcplugin.endOfDirectory(pluginhandle)
        
        
        
        
        
        
def PLAYEPISODE(vids):
        url = vids
        item = xbmcgui.ListItem(path=url)
        return xbmcplugin.setResolvedUrl(pluginhandle, True, item)
    
def PLAY(vid):
        url = vids
        item = xbmcgui.ListItem(path=url)
        return xbmcplugin.setResolvedUrl(pluginhandle, True, item)


def get_params():
        param=[]
        paramstring=sys.argv[2]
        if len(paramstring)>=2:
                params=sys.argv[2]
                cleanedparams=params.replace('?','')
                if (params[len(params)-1]=='/'):
                        params=params[0:len(params)-2]
                pairsofparams=cleanedparams.split('&')
                param={}
                for i in range(len(pairsofparams)):
                        splitparams={}
                        splitparams=pairsofparams[i].split('=')
                        if (len(splitparams))==2:
                                param[splitparams[0]]=splitparams[1]
                                
        return param

              
params=get_params()
print params
url=None
name=None
mode=None

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

print "Mode: "+str(mode)
print "URL: "+str(url)
print "Name: "+str(name)


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
        PLAYEPISODE(url)
elif mode==6:
        EPISODES(url)
        
sys.modules.clear()

'''
    @document   : default.py
    @package    : PleXBMC add-on
    @author     : Hippojay (aka Dave Hawes-Johnson)
    @copyright  : 2011-2012, Hippojay
    @version    : 3.0 (frodo)

    @license    : Gnu General Public License - see LICENSE.TXT
    @description: pleXBMC XBMC add-on

    This file is part of the XBMC PleXBMC Plugin.

    PleXBMC Plugin is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 2 of the License, or
    (at your option) any later version.

    PleXBMC Plugin is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with PleXBMC Plugin.  If not, see <http://www.gnu.org/licenses/>.

'''

import urllib
import urlparse
import re
import xbmcplugin
import xbmcgui
import httplib
import socket
import sys
import os
import time
import random
import xbmc
import datetime
import xml.etree.ElementTree as etree
from common import *  #Needed first to setup import locations
from settings import addonSettings
import plex


#Get the setting from the appropriate file.
_MODE_GETCONTENT=0
_MODE_TVSHOWS=1
_MODE_MOVIES=2
_MODE_ARTISTS=3
_MODE_TVSEASONS=4
_MODE_PLAYLIBRARY=5
_MODE_TVEPISODES=6
_MODE_PLEXPLUGINS=7
_MODE_PROCESSXML=8
_MODE_CHANNELSEARCH=9
_MODE_CHANNELPREFS=10
_MODE_PLAYSHELF=11
_MODE_BASICPLAY=12
_MODE_SHARED_MOVIES=13
_MODE_ALBUMS=14
_MODE_TRACKS=15
_MODE_PHOTOS=16
_MODE_MUSIC=17
_MODE_VIDEOPLUGINPLAY=18
_MODE_PLEXONLINE=19
_MODE_CHANNELINSTALL=20
_MODE_CHANNELVIEW=21
_MODE_PLAYLIBRARY_TRANSCODE=23
_MODE_DISPLAYSERVERS=22
_MODE_MYPLEXQUEUE=24
_MODE_SHARED_SHOWS=25
_MODE_SHARED_MUSIC=26
_MODE_SHARED_PHOTOS=27
_MODE_DELETE_REFRESH=28
_MODE_SHARED_ALL=29
_MODE_PLAYLISTS=30

_SUB_AUDIO_XBMC_CONTROL="0"
_SUB_AUDIO_PLEX_CONTROL="1"
_SUB_AUDIO_NEVER_SHOW="2"


def mediaType( partData, server, dvdplayback=False ):
    printDebug.debug("== ENTER ==")
    stream=partData['key']
    file=partData['file']

    if ( file is None ) or ( settings.get_stream() == "1" ):
        printDebug.debug( "Selecting stream")
        return server.get_formatted_url(stream)

    #First determine what sort of 'file' file is

    if file[0:2] == "\\\\":
        printDebug.debug("Looks like a UNC")
        type="UNC"
    elif file[0:1] == "/" or file[0:1] == "\\":
        printDebug.debug("looks like a unix file")
        type="nixfile"
    elif file[1:3] == ":\\" or file[1:2] == ":/":
        printDebug.debug("looks like a windows file")
        type="winfile"
    else:
        printDebug.debug("unknown file type")
        printDebug.debug(str(file))
        type="notsure"

    # 0 is auto select.  basically check for local file first, then stream if not found
    if settings.get_stream() == "0":
        #check if the file can be found locally
        if type == "nixfile" or type == "winfile":
            try:
                printDebug.debug("Checking for local file")
                exists = open(file, 'r')
                printDebug.debug("Local file found, will use this")
                exists.close()
                return "file:"+file
            except: pass

        printDebug.debug("No local file")
        if dvdplayback:
            printDebug.debug("Forcing SMB for DVD playback")
            settings.set_stream("2")
        else:
            return server.get_formatted_url(stream)


    # 2 is use SMB
    elif settings.get_stream() == "2" or settings.get_stream() == "3":
    
        #first off, lets remove URL encoding
        file=urllib.unquote(file)
    
        if settings.get_stream() == "2":
            protocol="smb"
        else:
            protocol="afp"

        printDebug.debug( "Selecting smb/unc")
        if type=="UNC":
            filelocation="%s:%s" % (protocol, file.replace("\\","/"))
        else:
            #Might be OSX type, in which case, remove Volumes and replace with server
            server=server.get_location().split(':')[0]
            loginstring=""

            if settings.get_setting('nasoverride'):
                if settings.get_setting('nasoverrideip'):
                    server=settings.get_setting('nasoverrideip')
                    printDebug.debug("Overriding server with: %s" % server)

                if settings.get_setting('nasuserid'):
                    loginstring="%s:%s@" % (settings.get_setting('nasuserid'), settings.get_setting('naspass'))
                    printDebug.debug("Adding AFP/SMB login info for user: %s" % settings.get_setting('nasuserid'))


            if file.find('Volumes') > 0:
                filelocation="%s:/%s" % (protocol, file.replace("Volumes",loginstring+server))
            else:
                if type == "winfile":
                    filelocation=("%s://%s%s/%s" % (protocol, loginstring, server, file[3:].replace("\\","/")))
                else:
                    #else assume its a file local to server available over smb/samba (now we have linux PMS).  Add server name to file path.
                    filelocation=protocol+"://"+loginstring+server+file

        if settings.get_setting('nasoverride') and settings.get_setting('nasroot'):
            #Re-root the file path
            printDebug.debug("Altering path %s so root is: %s" % (filelocation, settings.get_setting('nasroot')))
            if '/'+settings.get_setting('nasroot')+'/' in filelocation:
                components = filelocation.split('/')
                index = components.index(settings.get_setting('nasroot'))
                for i in range(3,index):
                    components.pop(3)
                filelocation='/'.join(components)
    else:
        printDebug.debug( "No option detected, streaming is safest to choose" )
        filelocation=server.get_formatted_url(stream)

    printDebug.debug("Returning URL: %s " % filelocation)
    return filelocation
    
def addGUIItem(url, details, extraData, context=None, folder=True):

        item_title = details.get('title', 'Unknown')

        printDebug.debug("== ENTER ==")
        printDebug.debug("Adding Dir for [%s]" % item_title)
        printDebug.debug("Passed details: %s" % details)
        printDebug.debug("Passed extraData: %s" % extraData)

        mode="&mode=%s" % extraData.get('mode',0)

        #Create the URL to pass to the item
        if not folder and extraData['type'] == "image" :
            u=url
        elif url.startswith('http') or url.startswith('file'):
            u=sys.argv[0]+"?url="+urllib.quote(url)+mode
        else:
            u=sys.argv[0]+"?url="+str(url)+mode
            
        if extraData.get('parameters'):
            for argument, value in extraData.get('parameters').items():
                u = "%s&%s=%s" % (u, argument, urllib.quote(value))

        printDebug.debug("URL to use for listing: %s" % u)

        liz=xbmcgui.ListItem(item_title, thumbnailImage=extraData.get('thumb', ''))

        printDebug.debug("Setting thumbnail as %s" % extraData.get('thumb', ''))

        #Set the properties of the item, such as summary, name, season, etc
        liz.setInfo(type=extraData.get('type','Video'), infoLabels=details )

        #Music related tags
        if extraData.get('type','').lower() == "music":
            liz.setProperty('Artist_Genre', details.get('genre',''))
            liz.setProperty('Artist_Description', extraData.get('plot',''))
            liz.setProperty('Album_Description', extraData.get('plot',''))

        #For all end items    
        if not folder:
            liz.setProperty('IsPlayable', 'true')

            if extraData.get('type','video').lower() == "video":
                liz.setProperty('TotalTime', str(extraData.get('duration')))
                liz.setProperty('ResumeTime', str(extraData.get('resume')))

                if not settings.get_setting('skipmediaflags'):
                    printDebug.debug("Setting VrR as : %s" % extraData.get('VideoResolution',''))
                    liz.setProperty('VideoResolution', extraData.get('VideoResolution',''))
                    liz.setProperty('VideoCodec', extraData.get('VideoCodec',''))
                    liz.setProperty('AudioCodec', extraData.get('AudioCodec',''))
                    liz.setProperty('AudioChannels', extraData.get('AudioChannels',''))
                    liz.setProperty('VideoAspect', extraData.get('VideoAspect',''))

                    video_codec={}
                    if extraData.get('xbmc_VideoCodec'): video_codec['codec'] = extraData.get('xbmc_VideoCodec')
                    if extraData.get('xbmc_VideoAspect') : video_codec['aspect'] = float(extraData.get('xbmc_VideoAspect'))
                    if extraData.get('xbmc_height') : video_codec['height'] = int(extraData.get('xbmc_height'))
                    if extraData.get('xbmc_width') : video_codec['width'] = int(extraData.get('xbmc_width'))
                    if extraData.get('duration') : video_codec['duration'] = int(extraData.get('duration'))

                    audio_codec={}
                    if extraData.get('xbmc_AudioCodec') : audio_codec['codec'] = extraData.get('xbmc_AudioCodec')
                    if extraData.get('xbmc_AudioChannels') : audio_codec['channels'] = int(extraData.get('xbmc_AudioChannels'))

                    liz.addStreamInfo('video', video_codec )
                    liz.addStreamInfo('audio', audio_codec )
                
        
        if extraData.get('source') == 'tvshow' or extraData.get('source') =='tvseasons':
            #Then set the number of watched and unwatched, which will be displayed per season
            liz.setProperty('TotalEpisodes', str(extraData['TotalEpisodes']))
            liz.setProperty('WatchedEpisodes', str(extraData['WatchedEpisodes']))
            liz.setProperty('UnWatchedEpisodes', str(extraData['UnWatchedEpisodes']))
            
            #Hack to show partial flag for TV shows and seasons
            if extraData.get('partialTV') == 1:            
                liz.setProperty('TotalTime', '100')
                liz.setProperty('ResumeTime', '50')
                
        #fanart is nearly always available, so exceptions are rare.
        try:
            liz.setProperty('fanart_image', extraData.get('fanart_image'))
            printDebug.debug("Setting fan art as %s" % extraData.get('fanart_image'))
        except:
            printDebug.debug("Skipping fanart as None found")

        if extraData.get('banner'):
            bannerImg = str(extraData.get('banner', ''))

            liz.setProperty('banner', bannerImg)
            printDebug.debug("Setting banner as %s" % bannerImg)

        if extraData.get('season_thumb'):
            seasonImg = str(extraData.get('season_thumb', ''))

            liz.setProperty('seasonThumb', seasonImg)
            printDebug.debug("Setting season Thumb as %s" % seasonImg)

        #almost always have context menus
        try:
            if not folder and extraData.get('type','video').lower() == "video":
                #Play Transcoded
                context.insert(0,('Play Transcoded', "XBMC.PlayMedia(%s&transcode=1)" % u , ))
                printDebug.debug("Setting transcode options to [%s&transcode=1]" % u)
            printDebug.debug("Building Context Menus")
            liz.addContextMenuItems( context, settings.get_setting('contextreplace') )
        except: 
            printDebug.error("Context Menu Error: %s" % str(sys.exc_info()))
            
        return xbmcplugin.addDirectoryItem(handle=pluginhandle,url=u,listitem=liz,isFolder=folder)

def displaySections( filter=None, display_shared=False ):
        printDebug.debug("== ENTER ==")
        xbmcplugin.setContent(pluginhandle, 'files')

        server_list=plex_network.get_server_list()
        printDebug.debug( "Using list of %s servers: %s" % ( len(server_list), server_list))
        
        for server in server_list:
        
            server.discover_sections()
        
            for section in server.get_sections():

                if display_shared and server.is_owned():
                    continue

                details={'title' : section.get_title() }

                if len(server_list) > 1:
                    details['title']="%s: %s" % (server.get_name(), details['title'])

                extraData={ 'fanart_image' : server.get_fanart(section),
                            'type'         : "Video",
                            'thumb'        : g_thumb}

                #Determine what we are going to do process after a link is selected by the user, based on the content we find

                path=section.get_path()

                if section.is_show():
                    mode=_MODE_TVSHOWS
                    if (filter is not None) and (filter != "tvshows"):
                        continue

                elif section.is_movie():
                    mode=_MODE_MOVIES
                    if (filter is not None) and (filter != "movies"):
                        continue

                elif section.is_artist():
                    mode=_MODE_ARTISTS
                    if (filter is not None) and (filter != "music"):
                        continue

                elif section.is_photo():
                    mode=_MODE_PHOTOS
                    if (filter is not None) and (filter != "photos"):
                        continue
                else:
                    printDebug.debug("Ignoring section %s of type %s as unable to process" % ( details['title'], section.get_type() ) )
                    continue

                if settings.get_setting('secondary'):
                    mode=_MODE_GETCONTENT
                else:
                    path=path+'/all'

                extraData['mode']=mode
                section_url='%s%s' % ( server.get_url_location(), path)

                if not settings.get_setting('skipcontext'):
                    context=[]
                    context.append(('Refresh library section', 'RunScript(plugin.video.plexbmc, update, %s, %s)' % (server.get_uuid(), section.get_key()) ))
                else:
                    context=None

                #Build that listing..
                addGUIItem(section_url, details,extraData, context)

        if display_shared:
            xbmcplugin.endOfDirectory(pluginhandle, cacheToDisc=True)
            return
                    
        #For each of the servers we have identified            
        if __settings__.getSetting('myplex_user') != '':
            addGUIItem('http://myplexqueue', {'title': 'myplex Queue'}, {'thumb': g_thumb, 'type': 'Video', 'mode': _MODE_MYPLEXQUEUE})

        for server in server_list:
        
            if server.is_offline() or server.is_secondary():
                continue
        
            #Plex plugin handling
            if (filter is not None) and (filter != "plugins"):
                continue

            if len(server_list) > 1:
                prefix=server.get_name()+": "
            else:
                prefix=""

            details={'title' : prefix+"Channels" }
            extraData={'type' : "Video",
                       'thumb' : g_thumb}

            extraData['mode']=_MODE_CHANNELVIEW
            u="%s/system/plugins/all" % server.get_url_location()
            addGUIItem(u,details,extraData)

            #Create plexonline link
            details['title']=prefix+"Plex Online"
            extraData['type'] = "file"
            extraData['thumb'] = g_thumb
            extraData['mode'] = _MODE_PLEXONLINE

            u="%s/system/plexonline" % server.get_url_location()            
            addGUIItem(u,details,extraData)
            
            #create playlist link
            details['title']=prefix+"Playlists"
            extraData['type'] = "file"
            extraData['thumb'] = g_thumb
            extraData['mode'] = _MODE_PLAYLISTS

            u="%s/system/playlists" % server.get_url_location()            
            addGUIItem(u,details,extraData)
            
            
        if __settings__.getSetting("cache") == "true":
            details = {'title' : "Refresh Data"}
            extraData = {}
            extraData['type']="file"

            extraData['mode']= _MODE_DELETE_REFRESH

            u="http://nothing"
            addGUIItem(u,details,extraData)


        #All XML entries have been parsed and we are ready to allow the user to browse around.  So end the screen listing.
        xbmcplugin.endOfDirectory(pluginhandle, cacheToDisc=False)

def enforceSkinView(mode):

    '''
    Ensure that the views are consistance across plugin usage, depending
    upon view selected by user
    @input: User view selection
    @return: view id for skin
    '''

    printDebug.debug("== ENTER ==")

    if __settings__.getSetting('skinoverride') == "false":
        return None

    skinname = __settings__.getSetting('skinname')

    current_skin_name = xbmc.getSkinDir()

    skin_map = { '2' : 'skin.confluence' ,
                 '0' : 'skin.quartz' ,
                 '1' : 'skin.quartz3' ,
                 '3' : 'skin.amber' }
    
    if skin_map[skinname] not in current_skin_name:
        printDebug.debug("Do not have the correct skin [%s] selected in settings [%s] - ignoring" % (current_skin_name, skin_map[skinname]))
        return None
    
    if mode == "movie":
        printDebug.debug("Looking for movie skin settings")
        viewname = __settings__.getSetting('mo_view_%s' % skinname)

    elif mode == "tv":
        printDebug.debug("Looking for tv skin settings")
        viewname = __settings__.getSetting('tv_view_%s' % skinname)

    elif mode == "music":
        printDebug.debug("Looking for music skin settings")
        viewname = __settings__.getSetting('mu_view_%s' % skinname)

    elif mode == "episode":
        printDebug.debug("Looking for music skin settings")
        viewname = __settings__.getSetting('ep_view_%s' % skinname)

    elif mode == "season":
        printDebug.debug("Looking for music skin settings")
        viewname = __settings__.getSetting('se_view_%s' % skinname)

    else:
        viewname = "None"

    printDebug.debug("view name is %s" % viewname)

    if viewname == "None":
        return None

    QuartzV3_views={ 'List' : 50,
                     'Big List' : 51,
                     'MediaInfo' : 52,
                     'MediaInfo 2' : 54,
                     'Big Icons' : 501,
                     'Icons': 53,
                     'Panel' : 502,
                     'Wide' : 55,
                     'Fanart 1' : 57,
                     'Fanart 2' : 59,
                     'Fanart 3' : 500 }

    Quartz_views={ 'List' : 50,
                   'MediaInfo' : 51,
                   'MediaInfo 2' : 52,
                   'Icons': 53,
                   'Wide' : 54,
                   'Big Icons' : 55,
                   'Icons 2' : 56 ,
                   'Panel' : 57,
                   'Fanart' : 58,
                   'Fanart 2' : 59 }

    Confluence_views={ 'List' : 50,
                       'Big List' : 51,
                       'Thumbnail' : 500,
                       'Poster Wrap': 501,
                       'Fanart' : 508,
                       'Media Info' : 504,
                       'Media Info 2' : 503,
                       'Media Info 3' : 515,
                       'Wide Icons' : 505 }
    
    Amber_views = {  'List' : 50,
                       'Big List' : 52,
                       'Panel': 51,
                       'Low List' : 54,
                       'Icons' : 53,
                       'Big Panel' : 55,
                       'Fanart' : 59 }

    skin_list={"0" : Quartz_views ,
               "1" : QuartzV3_views,
               "2" : Confluence_views,
               "3" : Amber_views }

    printDebug.debug("Using skin view: %s" % skin_list[skinname][viewname])

    try:
        return skin_list[skinname][viewname]
    except:
        print "PleXBMC -> skin name or view name error"
        return None

def Movies( url, tree=None ):
    printDebug.debug("== ENTER ==")
    xbmcplugin.setContent(pluginhandle, 'movies')
    
    xbmcplugin.addSortMethod(pluginhandle, 37 ) #maintain original plex sorted
    xbmcplugin.addSortMethod(pluginhandle, 25 ) #video title ignore THE
    xbmcplugin.addSortMethod(pluginhandle, 19 )  #date added
    xbmcplugin.addSortMethod(pluginhandle, 3 )  #date
    xbmcplugin.addSortMethod(pluginhandle, 18 ) #rating
    xbmcplugin.addSortMethod(pluginhandle, 17 ) #year
    xbmcplugin.addSortMethod(pluginhandle, 29 ) #runtime
    xbmcplugin.addSortMethod(pluginhandle, 28 ) #by MPAA
    
    #get the server name from the URL, which was passed via the on screen listing..

    server=plex_network.get_server_from_url(url)

    tree=getXML(url,tree)
    if tree is None:
        return

    setWindowHeading(tree)
    randomNumber=str(random.randint(1000000000,9999999999))
    
    #Find all the video tags, as they contain the data we need to link to a file.
    start_time=time.time()
    count=0
    for movie in tree:

        if movie.tag == "Video":
            movieTag(url, server, tree, movie, randomNumber)
            count+=1
        
    printDebug.info("PROCESS: It took %s seconds to process %s items" % (time.time()-start_time, count))
    printDebug.debug("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('movie')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle)

def buildContextMenu( url, itemData, server ):
    context=[]
    url_parts = urlparse.urlparse(url)
    section=url_parts.path.split('/')[3]  
    ID=itemData.get('ratingKey','0')

    #Mark media unwatched
    context.append(('Mark as Unwatched', 'RunScript(plugin.video.plexbmc, watch, %s, %s, %s)' % ( server.get_uuid(), ID, 'unwatch' ) ))
    context.append(('Mark as Watched', 'RunScript(plugin.video.plexbmc, watch, %s, %s, %s)' % ( server.get_uuid(), ID, 'watch' ) ))
    context.append(('Rescan library section', 'RunScript(plugin.video.plexbmc, update, %s, %s)' % ( server.get_uuid(), section ) ))
    context.append(('Delete media', "RunScript(plugin.video.plexbmc, delete, %s, %s)" % ( server.get_uuid(), ID) ))
    context.append(('Reload Section', 'RunScript(plugin.video.plexbmc, refresh)' ))
    context.append(('Select Audio', "RunScript(plugin.video.plexbmc, audio, %s, %s)" % ( server.get_uuid(), ID) ))
    context.append(('Select Subtitle', "RunScript(plugin.video.plexbmc, subs, %s, %s)" % ( server.get_uuid(), ID) ))

    printDebug.debug("Using context menus: %s" % context)

    return context

def TVShows( url, tree=None ):
    printDebug.debug("== ENTER ==")
    xbmcplugin.setContent(pluginhandle, 'tvshows')
    xbmcplugin.addSortMethod(pluginhandle, 25 ) #video title ignore THE
    xbmcplugin.addSortMethod(pluginhandle, 3 )  #date
    xbmcplugin.addSortMethod(pluginhandle, 18 ) #rating
    xbmcplugin.addSortMethod(pluginhandle, 17 ) #year
    xbmcplugin.addSortMethod(pluginhandle, 28 ) #by MPAA

    #Get the URL and server name.  Get the XML and parse
    tree=getXML(url,tree)
    if tree is None:
        return

    server=plex_network.get_server_from_url(url)

    setWindowHeading(tree)
    #For each directory tag we find
    ShowTags=tree.findall('Directory')
    for show in ShowTags:

        tempgenre=[]

        for child in show:
            if child.tag == "Genre":
                        tempgenre.append(child.get('tag',''))

        watched = int(show.get('viewedLeafCount',0))

        #Create the basic data structures to pass up
        details={'title'      : show.get('title','Unknown').encode('utf-8') ,
                 'sorttitle'  : show.get('titleSort', show.get('title','Unknown')).encode('utf-8') ,
                 'tvshowname' : show.get('title','Unknown').encode('utf-8') ,
                 'studio'     : show.get('studio','').encode('utf-8') ,
                 'plot'       : show.get('summary','').encode('utf-8') ,
                 'season'     : 0 ,
                 'episode'    : int(show.get('leafCount',0)) ,
                 'mpaa'       : show.get('contentRating','') ,
                 'aired'      : show.get('originallyAvailableAt','') ,
                 'genre'      : " / ".join(tempgenre) }

        extraData={'type'              : 'video' ,
                   'source'            : 'tvshows',
                   'UnWatchedEpisodes' : int(details['episode']) - watched,
                   'WatchedEpisodes'   : watched,
                   'TotalEpisodes'     : details['episode'],
                   'thumb'             : getThumb(show, server) ,
                   'fanart_image'      : getFanart(show, server) ,
                   'key'               : show.get('key','') ,
                   'ratingKey'         : str(show.get('ratingKey',0)) }

        #banner art
        if show.get('banner',None) is not None:
            extraData['banner'] = server.get_url_location()+show.get('banner')
        else:
            extraData['banner'] = g_thumb

        #Set up overlays for watched and unwatched episodes
        if extraData['WatchedEpisodes'] == 0:
            details['playcount'] = 0
        elif extraData['UnWatchedEpisodes'] == 0:
            details['playcount'] = 1
        else:
            extraData['partialTV'] = 1

        #Create URL based on whether we are going to flatten the season view
        if settings.get_setting('flatten') == "2":
            printDebug.debug("Flattening all shows")
            extraData['mode']=_MODE_TVEPISODES
            u='%s%s'  % ( server.get_url_location(), extraData['key'].replace("children","allLeaves"))
        else:
            extraData['mode']=_MODE_TVSEASONS
            u='%s%s'  % ( server.get_url_location(), extraData['key'])

        if not settings.get_setting('skipcontext'):
            context=buildContextMenu(url, extraData, server)
        else:
            context=None

        addGUIItem(u,details,extraData, context)

    printDebug ("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('tv')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle, cacheToDisc=True)

def TVSeasons( url ):
    printDebug.debug("== ENTER ==")
    xbmcplugin.setContent(pluginhandle, 'seasons')

    #Get URL, XML and parse
    server=plex_network.get_server_from_url(url)
    tree=getXML(url)
    if tree is None:
        return

    willFlatten=False
    if settings.get_setting('flatten') == "1":
        #check for a single season
        if int(tree.get('size',0)) == 1:
            printDebug.debug("Flattening single season show")
            willFlatten=True

    sectionart=getFanart(tree, server)
    banner=tree.get('banner')
    setWindowHeading(tree)
    #For all the directory tags
    SeasonTags=tree.findall('Directory')
    for season in SeasonTags:

        if willFlatten:
            url=server.get_url_location()+season.get('key')
            TVEpisodes(url)
            return

        watched=int(season.get('viewedLeafCount',0))

        #Create the basic data structures to pass up
        details={'title'      : season.get('title','Unknown').encode('utf-8') ,
                 'tvshowname' : season.get('title','Unknown').encode('utf-8') ,
                 'sorttitle'  : season.get('titleSort', season.get('title','Unknown')).encode('utf-8') ,
                 'studio'     : season.get('studio','').encode('utf-8') ,
                 'plot'       : season.get('summary','').encode('utf-8') ,
                 'season'     : 0 ,
                 'episode'    : int(season.get('leafCount',0)) ,
                 'mpaa'       : season.get('contentRating','') ,
                 'aired'      : season.get('originallyAvailableAt','') }

        if season.get('sorttitle'): details['sorttitle'] = season.get('sorttitle')

        extraData={'type'              : 'video' ,
                   'source'            : 'tvseasons',
                   'TotalEpisodes'     : details['episode'],
                   'WatchedEpisodes'   : watched ,
                   'UnWatchedEpisodes' : details['episode'] - watched ,
                   'thumb'             : getThumb(season, server) ,
                   'fanart_image'      : getFanart(season, server) ,
                   'key'               : season.get('key','') ,
                   'ratingKey'         : str(season.get('ratingKey',0)) ,
                   'mode'              : _MODE_TVEPISODES }

        if banner:
            extraData['banner']=server.get_url_location()+banner
                   
        if extraData['fanart_image'] == "":
            extraData['fanart_image']=sectionart

        #Set up overlays for watched and unwatched episodes
        if extraData['WatchedEpisodes'] == 0:
            details['playcount'] = 0
        elif extraData['UnWatchedEpisodes'] == 0:
            details['playcount'] = 1
        else:
            extraData['partialTV'] = 1

        url='%s%s' % ( server.get_url_location() , extraData['key'] )

        if not settings.get_setting('skipcontext'):
            context=buildContextMenu(url, season, server)
        else:
            context=None

        #Build the screen directory listing
        addGUIItem(url,details,extraData, context)

    printDebug.debug("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('season')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=True)

def TVEpisodes( url, tree=None ):
    printDebug.debug("== ENTER ==")
    xbmcplugin.setContent(pluginhandle, 'episodes')
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_EPISODE )  #episode
    xbmcplugin.addSortMethod(pluginhandle, 3 )  #date
    xbmcplugin.addSortMethod(pluginhandle, 25 ) #video title ignore THE
    xbmcplugin.addSortMethod(pluginhandle, 19 )  #date added
    xbmcplugin.addSortMethod(pluginhandle, 18 ) #rating
    xbmcplugin.addSortMethod(pluginhandle, 17 ) #year
    xbmcplugin.addSortMethod(pluginhandle, 29 ) #runtime
    xbmcplugin.addSortMethod(pluginhandle, 28 ) #by MPAA

    tree=getXML(url,tree)
    if tree is None:
        return

    setWindowHeading(tree)

    #get banner thumb
    banner = tree.get('banner')

    #get season thumb for SEASON NODE
    season_thumb = tree.get('thumb', '')

    ShowTags=tree.findall('Video')
    server=plex_network.get_server_from_url(url)

    if not settings.get_setting('skipimages'):
        sectionart=getFanart(tree, server)

    randomNumber=str(random.randint(1000000000,9999999999))

    for episode in ShowTags:

        printDebug.debug("---New Item---")
        tempgenre=[]
        tempcast=[]
        tempdir=[]
        tempwriter=[]

        for child in episode:
            if child.tag == "Media":
                mediaarguments = dict(child.items())
            elif child.tag == "Genre" and not settings.get_setting('skipmetadata'):
                tempgenre.append(child.get('tag'))
            elif child.tag == "Writer"  and not settings.get_setting('skipmetadata'):
                tempwriter.append(child.get('tag'))
            elif child.tag == "Director"  and not settings.get_setting('skipmetadata'):
                tempdir.append(child.get('tag'))
            elif child.tag == "Role"  and not settings.get_setting('skipmetadata'):
                tempcast.append(child.get('tag'))

        printDebug.debug("Media attributes are %s" % mediaarguments)

        #Gather some data
        view_offset=episode.get('viewOffset',0)
        duration=int(mediaarguments.get('duration',episode.get('duration',0)))/1000

        #Required listItem entries for XBMC
        details={'plot'        : episode.get('summary','').encode('utf-8') ,
                 'title'       : episode.get('title','Unknown').encode('utf-8') ,
                 'sorttitle'   : episode.get('titleSort', episode.get('title','Unknown')).encode('utf-8')  ,
                 'rating'      : float(episode.get('rating',0)) ,
                 'studio'      : episode.get('studio',tree.get('studio','')).encode('utf-8') ,
                 'mpaa'        : episode.get('contentRating', tree.get('grandparentContentRating','')) ,
                 'year'        : int(episode.get('year',0)) ,
                 'tagline'     : episode.get('tagline','').encode('utf-8') ,
                 'episode'     : int(episode.get('index',0)) ,
                 'aired'       : episode.get('originallyAvailableAt','') ,
                 'tvshowtitle' : episode.get('grandparentTitle',tree.get('grandparentTitle','')).encode('utf-8') ,
                 'season'      : int(episode.get('parentIndex',tree.get('parentIndex',0))) }

        if episode.get('sorttitle'):
            details['sorttitle'] = episode.get('sorttitle').encode('utf-8')

        if tree.get('mixedParents','0') == '1':
            details['title'] = "%s - %sx%s %s" % ( details['tvshowtitle'], details['season'], str(details['episode']).zfill(2), details['title'] )
        #else:
        #    details['title'] = str(details['episode']).zfill(2) + ". " + details['title']


        #Extra data required to manage other properties
        extraData={'type'         : "Video" ,
                   'source'       : 'tvepisodes',
                   'thumb'        : getThumb(episode, server) ,
                   'fanart_image' : getFanart(episode, server) ,
                   'key'          : episode.get('key',''),
                   'ratingKey'    : str(episode.get('ratingKey',0)),
                   'duration'     : duration,
                   'resume'       : int(int(view_offset)/1000) }

        if extraData['fanart_image'] == "" and not settings.get_setting('skipimages'):
            extraData['fanart_image'] = sectionart

        if season_thumb:
            extraData['season_thumb'] = server.get_url_location() + season_thumb

        #get ALL SEASONS thumb
        if not season_thumb and episode.get('parentThumb', ""):
            extraData['season_thumb'] = "%s%s" % (server.get_url_location(), episode.get('parentThumb', ""))

        if banner:
            extraData['banner'] = "%s%s" % (server.get_url_location(), banner)
            
        #Determine what tupe of watched flag [overlay] to use
        if int(episode.get('viewCount',0)) > 0:
            details['playcount'] = 1
        else: 
            details['playcount'] = 0

        #Extended Metadata
        if not settings.get_setting('skipmetadata'):
            details['cast']     = tempcast
            details['director'] = " / ".join(tempdir)
            details['writer']   = " / ".join(tempwriter)
            details['genre']    = " / ".join(tempgenre)

        #Add extra media flag data
        if not settings.get_setting('skipmediaflags'):
            extraData.update(getMediaData(mediaarguments))

        #Build any specific context menu entries
        if not settings.get_setting('skipcontext'):
            context=buildContextMenu(url, extraData,server)
        else:
            context=None

        extraData['mode']=_MODE_PLAYLIBRARY
        separator = "?"
        if "?" in extraData['key']:
            separator = "&"
        u="%s%s%st=%s" % (server.get_url_location(), extraData['key'], separator, randomNumber)

        addGUIItem(u,details,extraData, context, folder=False)

    printDebug.debug("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('episode')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=True)

def getAudioSubtitlesMedia( server, tree, full=False ):
    '''
        Cycle through the Parts sections to find all "selected" audio and subtitle streams
        If a stream is marked as selected=1 then we will record it in the dict
        Any that are not, are ignored as we do not need to set them
        We also record the media locations for playback decision later on
    '''
    printDebug.debug("== ENTER ==")
    printDebug.debug("Gather media stream info" )

    parts=[]
    partsCount=0
    subtitle={}
    subCount=0
    audio={}
    audioCount=0
    media={}
    subOffset=-1
    audioOffset=-1
    selectedSubOffset=-1
    selectedAudioOffset=-1
    full_data={}
    contents="type"
    media_type="unknown"
    extra={}
    
    timings = tree.find('Video')
    if timings is not None:
        media_type="video"
        extra['path']=timings.get('key')
    else:
        timings = tree.find('Track')
        if timings:
            media_type="music"
            extra['path']=timings.get('key')
        else:
            timings = tree.find('Photo')
            if timings:
                media_type="picture"
                extra['path']=timings.get('key')
            else:
                printDebug.debug("No Video data found")
                return {}

    media['viewOffset']=timings.get('viewOffset',0)    
    media['duration']=timings.get('duration',12*60*60)

    if full:
        if media_type == "video":
            full_data={ 'plot'      : timings.get('summary','').encode('utf-8') ,
                        'title'     : timings.get('title','Unknown').encode('utf-8') ,
                        'sorttitle' : timings.get('titleSort', timings.get('title','Unknown')).encode('utf-8') ,
                        'rating'    : float(timings.get('rating',0)) ,
                        'studio'    : timings.get('studio','').encode('utf-8'),
                        'mpaa'      : timings.get('contentRating', '').encode('utf-8'),
                        'year'      : int(timings.get('year',0)) ,
                        'tagline'   : timings.get('tagline','') ,
                        'thumbnailImage': getThumb(timings,server) }
                        
            if timings.get('type') == "episode":
                full_data['episode']     = int(timings.get('index',0)) 
                full_data['aired']       = timings.get('originallyAvailableAt','') 
                full_data['tvshowtitle'] = timings.get('grandparentTitle',tree.get('grandparentTitle','')).encode('utf-8') 
                full_data['season']      = int(timings.get('parentIndex',tree.get('parentIndex',0))) 

        elif media_type == "music":
                        
            full_data={'TrackNumber' : int(timings.get('index',0)) ,
                       'title'       : str(timings.get('index',0)).zfill(2)+". "+timings.get('title','Unknown').encode('utf-8') ,
                       'rating'      : float(timings.get('rating',0)) ,
                       'album'       : timings.get('parentTitle', tree.get('parentTitle','')).encode('utf-8') ,
                       'artist'      : timings.get('grandparentTitle', tree.get('grandparentTitle','')).encode('utf-8') ,
                       'duration'    : int(timings.get('duration',0))/1000 ,
                       'thumbnailImage': getThumb(timings,server) }

            extra['album']=timings.get('parentKey')
            extra['index']=timings.get('index')                       
                       
    details = timings.findall('Media')
        
    media_details_list=[]
    for media_details in details:
                
        resolution=""        
        try:       
            if media_details.get('videoResolution') == "sd":
                resolution="SD"
            elif int(media_details.get('videoResolution',0)) >= 1080:
                resolution="HD 1080"
            elif int(media_details.get('videoResolution',0)) >= 720:
                resolution="HD 720"
            elif int(media_details.get('videoResolution',0)) < 720:
                resolution="SD"
        except:
            pass
        
        media_details_temp = { 'bitrate'          : round(float(media_details.get('bitrate',0))/1000,1) ,
                               'videoResolution'  : resolution ,
                               'container'        : media_details.get('container','unknown') }
                                                  
        options = media_details.findall('Part')
        
        #Get the media locations (file and web) for later on
        for stuff in options:

            try:
                bits=stuff.get('key'), stuff.get('file')
                parts.append(bits)
                media_details_list.append(media_details_temp)
                partsCount += 1
            except: pass

    #if we are deciding internally or forcing an external subs file, then collect the data
    if media_type == "video" and settings.get_setting('streamControl') == _SUB_AUDIO_PLEX_CONTROL:

        contents="all"
        tags=tree.getiterator('Stream')

        for bits in tags:
            stream=dict(bits.items())
            
            #Audio Streams
            if stream['streamType'] == '2':
                audioCount += 1
                audioOffset += 1
                if stream.get('selected') == "1":
                    printDebug.debug("Found preferred audio id: %s " % stream['id'] )
                    audio=stream
                    selectedAudioOffset=audioOffset
            
            #Subtitle Streams
            elif stream['streamType'] == '3':
            
                if subOffset == -1:
                    subOffset = int(stream.get('index',-1))
                elif stream.get('index',-1) > 0 and stream.get('index',-1) < subOffset:
                    subOffset = int(stream.get('index',-1))
                    
                if stream.get('selected') == "1":
                    printDebug.debug( "Found preferred subtitles id : %s " % stream['id'])
                    subCount += 1
                    subtitle=stream
                    if stream.get('key'):
                        subtitle['key'] = server.get_formatted_url(stream['key'])
                    else:
                        selectedSubOffset=int( stream.get('index') ) - subOffset
                    
    else:
            printDebug.debug( "Stream selection is set OFF")

    streamData={'contents'   : contents ,                #What type of data we are holding
                'audio'      : audio ,                   #Audio data held in a dict
                'audioCount' : audioCount ,              #Number of audio streams
                'subtitle'   : subtitle ,                #Subtitle data (embedded) held as a dict
                'subCount'   : subCount ,                #Number of subtitle streams
                'parts'      : parts ,                   #The differet media locations
                'partsCount' : partsCount ,              #Number of media locations
                'media'      : media ,                   #Resume/duration data for media
                'details'    : media_details_list ,      #Bitrate, resolution and container for each part
                'subOffset'  : selectedSubOffset ,       #Stream index for selected subs
                'audioOffset': selectedAudioOffset ,     #STream index for select audio
                'full_data'  : full_data ,               #Full metadata extract if requested
                'type'       : media_type ,              #Type of metadata
                'extra'      : extra }                   #Extra data
            
    printDebug.debug( streamData )
    return streamData

def playPlaylist ( server, data ):    
    printDebug.debug("== ENTER ==")
    printDebug.debug("Creating new playlist")
    playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
    playlist.clear()
    
    tree = getXML(server.get_url_location()+data['extra'].get('album')+"/children")
    
    if tree is None:
        return
        
    TrackTags=tree.findall('Track')
    for track in TrackTags:

        printDebug.debug("Adding playlist item")
    
        url, item = trackTag(server, tree, track, listing = False)
        
        liz=xbmcgui.ListItem(item.get('title','Unknown'), iconImage=data['full_data'].get('thumbnailImage','') , thumbnailImage=data['full_data'].get('thumbnailImage',''))

        liz.setInfo( type='music', infoLabels=item )        
        playlist.add(url, liz)
    
    index = int(data['extra'].get('index',0)) - 1
    printDebug.debug("Playlist complete.  Starting playback from track %s [playlist index %s] " % (data['extra'].get('index',0), index ))
    xbmc.Player().playselected( index )   
    
    return
    
def playLibraryMedia( vids, override=False, force=None, full_data=False, shelf=False ):
   
    session=None
    if settings.get_setting('transcode'):
        override=True
    
    if override:
        full_data = True
    
    server=plex_network.get_server_from_url(vids)

    id=vids.split('?')[0].split('&')[0].split('/')[-1]

    tree=getXML(vids)
    if tree is None:
        return
            
    if force:
        full_data = True
        
    streams=getAudioSubtitlesMedia(server,tree, full_data)  
    
    if force and streams['type'] == "music":
        playPlaylist(server, streams)
        return
    
    url=selectMedia(streams, server)

    if url is None:
        return

    protocol=url.split(':',1)[0]

    if protocol == "file":
        printDebug.debug( "We are playing a local file")
        playurl=url.split(':',1)[1]
    elif protocol == "http":
        printDebug.debug( "We are playing a stream")
        if override:
            printDebug.debug( "We will be transcoding the stream")
            if settings.get_setting('transcode_type') == "universal":
                session, playurl=server.get_universal_transcode(streams['extra']['path'])
            elif settings.get_setting('transcode_type') == "legacy":
                session, playurl=server.get_legacy_transcode(id,url)
                
        else:
            playurl=server.get_formatted_url(url)
    else:
        playurl=url

    resume=int(int(streams['media']['viewOffset'])/1000)
    duration=int(int(streams['media']['duration'])/1000)

    if not resume == 0 and shelf:
        printDebug.debug("Shelf playback: display resume dialog")
        displayTime = str(datetime.timedelta(seconds=resume))
        display_list = [ "Resume from %s" % displayTime , "Start from beginning"]
        resumeScreen = xbmcgui.Dialog()
        result = resumeScreen.select('Resume',display_list)
        if result == -1:
            return False
            
        if result == 1:
           resume=0

    printDebug.debug("Resume has been set to %s " % resume)

    item = xbmcgui.ListItem(path=playurl)

    if streams['full_data']:
        item.setInfo( type=streams['type'], infoLabels=streams['full_data'] )
        item.setThumbnailImage(streams['full_data'].get('thumbnailImage',''))
        item.setIconImage(streams['full_data'].get('thumbnailImage',''))
    
    if force:
        
        if int(force) > 0:
            resume=int(int(force)/1000)
        else:
            resume=force
        
    if force or shelf:    
        if resume:
            item.setProperty('ResumeTime', str(resume) )
            item.setProperty('TotalTime', str(duration) )
            printDebug.info("Playback from resume point: %s" % resume)

            
    if streams['type'] == "picture":
        import json
        request=json.dumps({ "id"      : 1,
                             "jsonrpc" : "2.0",
                             "method"  : "Player.Open",
                             "params"  : { "item"  :  {"file": playurl } } } )
        html=xbmc.executeJSONRPC(request)
        return
    else:
        start = xbmcplugin.setResolvedUrl(pluginhandle, True, item)

    # record the playing file and server in the home window
    # so that plexbmc helper can find out what is playing
    WINDOW = xbmcgui.Window( 10000 )
    WINDOW.setProperty('plexbmc.nowplaying.server', server.get_location())
    WINDOW.setProperty('plexbmc.nowplaying.id', id)

    #Set a loop to wait for positive confirmation of playback
    count = 0
    while not xbmc.Player().isPlaying():
        printDebug.debug( "Not playing yet...sleep for 2")
        count = count + 2
        if count >= 20:
            return
        else:
            time.sleep(2)

    if not override:
        setAudioSubtitles(streams)

    if streams['type'] == "video":
        monitorPlayback(id,server, session)

    return

def setAudioSubtitles( stream ):
    '''
        Take the collected audio/sub stream data and apply to the media
        If we do not have any subs then we switch them off
    '''

    printDebug.debug("== ENTER ==")

    #If we have decided not to collect any sub data then do not set subs
    if stream['contents'] == "type":
        printDebug.info("No audio or subtitle streams to process.")

        #If we have decided to force off all subs, then turn them off now and return
        if settings.get_setting('streamControl') == _SUB_AUDIO_NEVER_SHOW :
            xbmc.Player().showSubtitles(False)
            printDebug ("All subs disabled")

        return True

    #Set the AUDIO component
    if settings.get_setting('streamControl') == _SUB_AUDIO_PLEX_CONTROL:
        printDebug.debug("Attempting to set Audio Stream")

        audio = stream['audio']
        
        if stream['audioCount'] == 1:
            printDebug.info("Only one audio stream present - will leave as default")

        elif audio:
            printDebug.debug("Attempting to use selected language setting: %s" % audio.get('language',audio.get('languageCode','Unknown')).encode('utf8'))
            printDebug.info("Found preferred language at index %s" % stream['audioOffset'])
            try:
                xbmc.Player().setAudioStream(stream['audioOffset'])
                printDebug.debug("Audio set")
            except:
                printDebug.info("Error setting audio, will use embedded default stream")

    #Set the SUBTITLE component
    if settings.get_setting('streamControl') == _SUB_AUDIO_PLEX_CONTROL:
        printDebug.debug("Attempting to set preferred subtitle Stream")
        subtitle=stream['subtitle']
        if subtitle:
            printDebug.debug("Found preferred subtitle stream" )
            try:
                xbmc.Player().showSubtitles(False)
                if subtitle.get('key'):
                    xbmc.Player().setSubtitles(subtitle['key'])                
                else:
                    printDebug.info("Enabling embedded subtitles at index %s" % stream['subOffset'])
                    xbmc.Player().setSubtitleStream(int(stream['subOffset']))

                xbmc.Player().showSubtitles(True)      
                return True
            except:
                printDebug.info("Error setting subtitle")

        else:
            printDebug.info("No preferred subtitles to set")
            xbmc.Player().showSubtitles(False)

    return False

def selectMedia( data, server ):
    printDebug.debug("== ENTER ==")
    #if we have two or more files for the same movie, then present a screen
    result=0
    dvdplayback=False

    count=data['partsCount']
    options=data['parts']
    details=data['details']
    
    if count > 1:

        dialogOptions=[]
        dvdIndex=[]
        indexCount=0
        for items in options:

            if items[1]:
                name=items[1].split('/')[-1]
                #name="%s %s %sMbps" % (items[1].split('/')[-1], details[indexCount]['videoResolution'], details[indexCount]['bitrate'])
            else:
                name="%s %s %sMbps" % (items[0].split('.')[-1], details[indexCount]['videoResolution'], details[indexCount]['bitrate'])
                
            if settings.get_setting('forcedvd'):
                if '.ifo' in name.lower():
                    printDebug.debug( "Found IFO DVD file in " + name )
                    name="DVD Image"
                    dvdIndex.append(indexCount)

            dialogOptions.append(name)
            indexCount+=1

        printDebug.debug("Create selection dialog box - we have a decision to make!")
        startTime = xbmcgui.Dialog()
        result = startTime.select('Select media to play',dialogOptions)
        if result == -1:
            return None

        if result in dvdIndex:
            printDebug.debug( "DVD Media selected")
            dvdplayback=True

    else:
        if settings.get_setting('forcedvd'):
            if '.ifo' in options[result]:
                dvdplayback=True

    newurl=mediaType({'key': options[result][0] , 'file' : options[result][1]},server,dvdplayback)

    printDebug.debug("We have selected media at %s" % newurl)
    return newurl

def monitorPlayback( id, server, session=None ):
    printDebug.debug("== ENTER ==")

    if session:
        printDebug.debug("We are monitoring a transcode session")
    
    if __settings__.getSetting('monitoroff') == "true":
        return
        
    monitorCount=0
    progress = 0
    complete = 0
    playedTime = 0
    #Whilst the file is playing back
    while xbmc.Player().isPlaying():
        #Get the current playback time

        currentTime = int(xbmc.Player().getTime())
        totalTime = int(xbmc.Player().getTotalTime())
        try:
            progress = int(( float(currentTime) / float(totalTime) ) * 100)
        except:
            progress = 0

        if currentTime < 30:
            printDebug.debug("Less that 30 seconds, will not set resume")

        #If we are less than 95% completem, store resume time
        elif progress < 95:
            printDebug.debug( "Movies played time: %s secs of %s @ %s%%" % ( currentTime, totalTime, progress) )
            server.report_playback_progress(id,currentTime*1000)
            complete=0
            playedTime = currentTime

        #Otherwise, mark as watched
        else:
            if complete == 0:
                printDebug.debug( "Movie marked as watched. Over 95% complete")
                server.mark_item_watched(id)
                complete=1
                # playedTime = 0 in order to avoid a bug of tract plex plugin (check on completed tv episode when time==duration)
                playedTime = 0

        xbmc.sleep(5000)

    #If we get this far, playback has stopped
    printDebug.debug("Playback Stopped")

    # The follwing progress:stopped update is necessary only for plugin trakt to 'cancel watching' on trakt.tv server, otherwise it will keep status 'watching' for about 15min
    server.report_playback_progress(id,playedTime*1000, state='stopped')

    if session is not None:
        printDebug.debug("Stopping PMS transcode job with session %s" % session)
        server.stop_transcode_session(session)

    return

def PLAY( url ):
        printDebug.debug("== ENTER ==")

        if url.startswith('file'):
            printDebug.debug( "We are playing a local file")
            #Split out the path from the URL
            playurl=url.split(':',1)[1]
        elif url.startswith('http'):
            printDebug.debug( "We are playing a stream")
            if '?' in url:
                server=plex_network.get_server_from_url(url)
                playurl=server.get_formatted_url(url)
        else:
            playurl=url

        item = xbmcgui.ListItem(path=playurl)
        return xbmcplugin.setResolvedUrl(pluginhandle, True, item)

def videoPluginPlay(vids, prefix=None, indirect=None, transcode=False ):
    server=plex_network.get_server_from_url(vids)
    if "node.plexapp.com" in vids:
        server=getMasterServer()

    if indirect:
        #Probably should transcode this
        if vids.startswith('http'):
            vids='/'+vids.split('/',3)[3]
            transcode=True
            
        session, vids=server.get_universal_transcode(vids)
          
    '''#If we find the url lookup service, then we probably have a standard plugin, but possibly with resolution choices
    if '/services/url/lookup' in vids:
        printDebug.debug("URL Lookup service")
        tree=getXML(vids)
        if not tree:
            return

        mediaCount=0
        mediaDetails=[]
        for media in tree.getiterator('Media'):
            mediaCount+=1
            tempDict={'videoResolution' : media.get('videoResolution',"Unknown")}

            for child in media:
                tempDict['key']=child.get('key','')

            tempDict['identifier']=tree.get('identifier','')
            mediaDetails.append(tempDict)

        printDebug.debug( str(mediaDetails) )

        #If we have options, create a dialog menu
        result=0
        if mediaCount > 1:
            printDebug ("Select from plugin video sources")
            dialogOptions=[x['videoResolution'] for x in mediaDetails ]
            videoResolution = xbmcgui.Dialog()

            result = videoResolution.select('Select resolution..',dialogOptions)

            if result == -1:
                return

        videoPluginPlay(getLinkURL('',mediaDetails[result],server))
        return
    
    
    #Check if there is a further level of XML required
    if indirect or '&indirect=1' in vids:
        printDebug.debug("Indirect link")
        tree=getXML(vids)
        if not tree:
            return

        for bits in tree.getiterator('Part'):
            videoPluginPlay(getLinkURL(vids,bits,server))
            break

        return
    '''
    #if we have a plex URL, then this is a transcoding URL
    if 'plex://' in vids:
        printDebug.debug("found webkit video, pass to transcoder")
        if not (prefix):
            prefix="system"
            if settings.get_setting('transcode_type') == "universal":
                session, vids=server.get_universal_transcode(vids)
            elif settings.get_setting('transcode_type') == "legacy":
                session, vids=server.get_legacy_transcode(0,vids,prefix)
                
        #Workaround for XBMC HLS request limit of 1024 byts
        if len(vids) > 1000:
            printDebug.debug("XBMC HSL limit detected, will pre-fetch m3u8 playlist")
            
            playlist = getXML(vids)
            
            if not playlist or not "#EXTM3U" in playlist:
            
                printDebug.debug("Unable to get valid m3u8 playlist from transcoder")
                return
            
            server=plex_network.get_server_from_url(vids)
            session=playlist.split()[-1]
            vids="%s/video/:/transcode/segmented/%s?t=1" % (server.get_url_location(), session)
            
    printDebug.debug("URL to Play: %s " % vids)
    printDebug.debug("Prefix is: %s" % prefix)

    #If this is an Apple movie trailer, add User Agent to allow access
    if 'trailers.apple.com' in vids:
        url=vids+"|User-Agent=QuickTime/7.6.5 (qtver=7.6.5;os=Windows NT 5.1Service Pack 3)"
    else:
        url=vids

    printDebug.debug("Final URL is: %s" % url)

    item = xbmcgui.ListItem(path=url)
    start = xbmcplugin.setResolvedUrl(pluginhandle, True, item)

    if transcode:
        try:
            pluginTranscodeMonitor(session,server)
        except:
            printDebug.debug("Unable to start transcode monitor")
    else:
        printDebug.debug("Not starting monitor")

    return

def pluginTranscodeMonitor( sessionID, server ):
    printDebug.debug("== ENTER ==")

    #Logic may appear backward, but this does allow for a failed start to be detected
    #First while loop waiting for start

    if __settings__.getSetting('monitoroff') == "true":
        return
   
    count=0
    while not xbmc.Player().isPlaying():
        printDebug.debug( "Not playing yet...sleep for 2")
        count = count + 2
        if count >= 40:
            #Waited 20 seconds and still no movie playing - assume it isn't going to..
            return
        else:
            time.sleep(2)

    while xbmc.Player().isPlaying():
        printDebug.debug("Waiting for playback to finish")
        time.sleep(4)

    printDebug.debug("Playback Stopped")
    printDebug.debug("Stopping PMS transcode job with session: %s" % sessionID)
    server.stop_transcode_session(sessionID)

    return

def get_params( paramstring ):
    printDebug.debug("== ENTER ==")
    printDebug.debug("Parameter string: %s" % paramstring)
    param={}
    if len(paramstring)>=2:
            params=paramstring

            if params[0] == "?":
                cleanedparams=params[1:]
            else:
                cleanedparams=params

            if (params[len(params)-1]=='/'):
                    params=params[0:len(params)-2]

            pairsofparams=cleanedparams.split('&')
            for i in range(len(pairsofparams)):
                    splitparams={}
                    splitparams=pairsofparams[i].split('=')
                    if (len(splitparams))==2:
                            param[splitparams[0]]=splitparams[1]
                    elif (len(splitparams))==3:
                            param[splitparams[0]]=splitparams[1]+"="+splitparams[2]
    print "PleXBMC -> Detected parameters: " + str(param)
    return param

def channelSearch (url, prompt):
    '''
        When we encounter a search request, branch off to this function to generate the keyboard
        and accept the terms.  This URL is then fed back into the correct function for
        onward processing.
    '''
    printDebug.debug("== ENTER ==")

    if prompt:
        prompt=urllib.unquote(prompt)
    else:
        prompt="Enter Search Term..."

    kb = xbmc.Keyboard('', 'heading')
    kb.setHeading(prompt)
    kb.doModal()
    if (kb.isConfirmed()):
        text = kb.getText()
        printDebug.debug("Search term input: %s" % text)
        url=url+'&query='+urllib.quote(text)
        PlexPlugins( url )
    return

def getContent( url ):
    '''
        This function takes teh URL, gets the XML and determines what the content is
        This XML is then redirected to the best processing function.
        If a search term is detected, then show keyboard and run search query
        @input: URL of XML page
        @return: nothing, redirects to another function
    '''
    printDebug.debug("== ENTER ==")

    server=plex_network.get_server_from_url(url)
    lastbit=url.split('/')[-1]
    printDebug.debug("URL suffix: %s" % lastbit)

    #Catch search requests, as we need to process input before getting results.
    if lastbit.startswith('search'):
        printDebug.debug("This is a search URL.  Bringing up keyboard")
        kb = xbmc.Keyboard('', 'heading')
        kb.setHeading('Enter search term')
        kb.doModal()
        if (kb.isConfirmed()):
            text = kb.getText()
            printDebug.debug("Search term input: %s" % text)
            url=url+'&query='+urllib.quote(text)
        else:
            return

    tree = server.processed_xml(url)

    setWindowHeading(tree)

    if lastbit == "folder" or lastbit == "playlists":
        processXML(url,tree)
        return

    view_group=tree.get('viewGroup',None)

    if view_group == "movie":
        printDebug.debug( "This is movie XML, passing to Movies")
        Movies(url, tree)
    elif view_group == "show":
        printDebug.debug( "This is tv show XML")
        TVShows(url,tree)
    elif view_group == "episode":
        printDebug.debug("This is TV episode XML")
        TVEpisodes(url,tree)
    elif view_group == 'artist':
        printDebug.debug( "This is music XML")
        artist(url, tree)
    elif view_group== 'album' or view_group == 'albums':
        albums(url,tree)
    elif view_group == 'track':
        printDebug.debug("This is track XML")
        tracks(url, tree) #sorthing is handled here
    elif view_group =="photo":
        printDebug.debug("This is a photo XML")
        photo(url,tree)
    else:
        processDirectory(url,tree)

    return

def processDirectory( url, tree=None ):
    printDebug.debug("== ENTER ==")
    printDebug.debug("Processing secondary menus")
    xbmcplugin.setContent(pluginhandle, "")

    server = plex_network.get_server_from_url(url)
    setWindowHeading(tree)
    for directory in tree:
        details={'title' : directory.get('title','Unknown').encode('utf-8') }
        extraData={'thumb'        : getThumb(tree, server) ,
                   'fanart_image' : getFanart(tree, server) }

        extraData['mode'] = _MODE_GETCONTENT
        u='%s' % (getLinkURL(url, directory, server))

        addGUIItem(u, details, extraData)

    xbmcplugin.endOfDirectory(pluginhandle, cacheToDisc=True)

def getMasterServer(all=False):
    printDebug.debug("== ENTER ==")

    possibleServers=[]
    current_master=settings.get_setting('masterserver')
    for serverData in plex_network.get_server_list():
        printDebug.debug( str(serverData) )
        if serverData.get_master() == 1:
            possibleServers.append(serverData)
    printDebug.debug( "Possible master servers are: %s" % possibleServers )

    if all:
        return possibleServers

    if len(possibleServers) > 1:
        preferred="local"
        for serverData in possibleServers:
            if serverData.get_name == current_master:
                printDebug.debug("Returning current master")
                return serverData
            if preferred == "any":
                printDebug.debug("Returning 'any'")
                return serverData
            else:
                if serverData.get_discovery() == preferred:
                    printDebug.debug("Returning local")
                    return serverData
    elif len(possibleServers) == 0:
        return 
    
    return possibleServers[0]



def artist( url, tree=None ):
    '''
        Process artist XML and display data
        @input: url of XML page, or existing tree of XML page
        @return: nothing
    '''
    printDebug.debug("== ENTER ==")
    xbmcplugin.setContent(pluginhandle, 'artists')
    xbmcplugin.addSortMethod(pluginhandle, 12 ) #artist title ignore THE
    xbmcplugin.addSortMethod(pluginhandle, 34 ) #last played
    xbmcplugin.addSortMethod(pluginhandle, 17 ) #year
 
    #Get the URL and server name.  Get the XML and parse
    tree=getXML(url,tree)
    if tree is None:
        return

    server=plex_network.get_server_from_url(url)
    setWindowHeading(tree)
    ArtistTag=tree.findall('Directory')
    for artist in ArtistTag:

        details={'artist'  : artist.get('title','').encode('utf-8') }

        details['title']=details['artist']

        extraData={'type'         : "Music" ,
                   'thumb'        : getThumb(artist, server) ,
                   'fanart_image' : getFanart(artist, server) ,
                   'ratingKey'    : artist.get('title','') ,
                   'key'          : artist.get('key','') ,
                   'mode'         : _MODE_ALBUMS ,
                   'plot'         : artist.get('summary','') }

        url='%s%s' % (server.get_url_location(), extraData['key'] )

        addGUIItem(url,details,extraData)

    printDebug.debug("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('music')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=True)

def albums( url, tree=None ):
    printDebug.debug("== ENTER ==")
    xbmcplugin.setContent(pluginhandle, 'albums')
    xbmcplugin.addSortMethod(pluginhandle, 24 ) #album title ignore THE
    xbmcplugin.addSortMethod(pluginhandle, 12 )  #artist ignore THE
    xbmcplugin.addSortMethod(pluginhandle, 34 ) #last played
    xbmcplugin.addSortMethod(pluginhandle, 17 ) #year
    
    #Get the URL and server name.  Get the XML and parse
    tree=getXML(url,tree)
    if tree is None:
        return

    server=plex_network.get_server_from_url(url)
    sectionart=getFanart(tree, server)
    setWindowHeading(tree)
    AlbumTags=tree.findall('Directory')
    for album in AlbumTags:

        details={'album'   : album.get('title','').encode('utf-8') ,
                 'year'    : int(album.get('year',0)) ,
                 'artist'  : tree.get('parentTitle', album.get('parentTitle','')).encode('utf-8') }

        details['title']=details['album']

        extraData={'type'         : "Music" ,
                   'thumb'        : getThumb(album, server) ,
                   'fanart_image' : getFanart(album, server) ,
                   'key'          : album.get('key',''),
                   'mode'         : _MODE_TRACKS ,
                   'plot'         : album.get('summary','')}

        if extraData['fanart_image'] == "":
            extraData['fanart_image']=sectionart

        url='%s%s' % (server.get_url_location(), extraData['key'] )

        addGUIItem(url,details,extraData)

    printDebug.debug("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('music')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=True)

def tracks( url,tree=None ):
    printDebug.debug("== ENTER ==")
    xbmcplugin.setContent(pluginhandle, 'songs')
    xbmcplugin.addSortMethod(pluginhandle, 10 ) #title title ignore THE
    xbmcplugin.addSortMethod(pluginhandle, 8 ) #duration
    xbmcplugin.addSortMethod(pluginhandle, 27 ) #song rating
    xbmcplugin.addSortMethod(pluginhandle, 7 ) #track number

    tree=getXML(url,tree)
    if tree is None:
        return

    playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
    playlist.clear()
     
    server=plex_network.get_server_from_url(url)
    sectionart=getFanart(tree, server)
    sectionthumb=getThumb(tree, server)
    setWindowHeading(tree)
    TrackTags=tree.findall('Track')
    for track in TrackTags:
        if track.get('thumb'):
            sectionthumb=getThumb(track, server)

        trackTag(server, tree, track, sectionart, sectionthumb)

    printDebug.debug("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('music')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=True)

def getXML (url, tree=None):
    printDebug.debug("== ENTER ==")

    if tree is None:
        tree=plex_network.get_processed_xml(url)

    if tree.get('message'):
        xbmcgui.Dialog().ok(tree.get('header','Message'),tree.get('message',''))
        return None

    return tree

def PlexPlugins(url, tree=None):
    '''
        Main function to parse plugin XML from PMS
        Will create dir or item links depending on what the
        main tag is.
        @input: plugin page URL
        @return: nothing, creates XBMC GUI listing
    '''
    printDebug.debug("== ENTER ==")
    xbmcplugin.setContent(pluginhandle, 'addons')
    server=plex_network.get_server_from_url(url)
    tree = getXML(url,tree)
    if tree is None:
        return

    myplex_url=False
    if (tree.get('identifier') != "com.plexapp.plugins.myplex") and ( "node.plexapp.com" in url ) :
        myplex_url=True
        printDebug.debug("This is a myplex URL, attempting to locate master server")
        server=getMasterServer()

    for plugin in tree:

        details={'title'   : plugin.get('title','Unknown').encode('utf-8') }

        if details['title'] == "Unknown":
            details['title']=plugin.get('name',"Unknown").encode('utf-8')
            
        if plugin.get('summary'):
            details['plot']=plugin.get('summary')

        extraData={'thumb'        : getThumb(plugin, server) ,
                   'fanart_image' : getFanart(plugin, server) ,
                   'identifier'   : tree.get('identifier','') ,
                   'type'         : "Video" ,
                   'key'          : plugin.get('key','') }

        if myplex_url:
            extraData['key']=extraData['key'].replace('node.plexapp.com:32400',server.get_location())
              
        if extraData['fanart_image'] == "":
            extraData['fanart_image']=getFanart(tree, server)

        p_url=getLinkURL(url, extraData, server)

        if plugin.tag == "Directory" or plugin.tag == "Podcast":

            if plugin.get('search') == '1':
                extraData['mode']=_MODE_CHANNELSEARCH
                extraData['parameters']={'prompt' : plugin.get('prompt',"Enter Search Term").encode('utf-8') }
            else:
                extraData['mode']=_MODE_PLEXPLUGINS

            addGUIItem(p_url, details, extraData)

        elif plugin.tag == "Video":
            extraData['mode']=_MODE_VIDEOPLUGINPLAY
            
            for child in plugin:
                if child.tag == "Media":
                    extraData['parameters'] = {'indirect' : child.get('indirect','0')}            
            
            addGUIItem(p_url, details, extraData, folder=False)

        elif plugin.tag == "Setting":

            if plugin.get('option') == 'hidden':
                value="********"
            elif plugin.get('type') == "text":
                value=plugin.get('value')
            elif plugin.get('type') == "enum":
                value=plugin.get('values').split('|')[int(plugin.get('value',0))]
            else:
                value=plugin.get('value')

            details['title']= "%s - [%s]" % (plugin.get('label','Unknown').encode('utf-8'), value)
            extraData['mode']=_MODE_CHANNELPREFS
            extraData['parameters']={'id' : plugin.get('id') }
            addGUIItem(url, details, extraData)


    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=True)

def channelSettings ( url, settingID ):
    '''
        Take the setting XML and parse it to create an updated
        string with the new settings.  For the selected value, create
        a user input screen (text or list) to update the setting.
        @ input: url
        @ return: nothing
    '''
    printDebug.debug("== ENTER ==")
    printDebug.debug("Setting preference for ID: %s" % settingID )

    if not settingID:
        printDebug.debug("ID not set")
        return

    tree=getXML(url)
    if tree is None:
        return

    setWindowHeading(tree)
    setString=None
    for plugin in tree:

        if plugin.get('id') == settingID:
            printDebug.debug("Found correct id entry for: %s" % settingID)
            id=settingID

            label=plugin.get('label',"Enter value")
            option=plugin.get('option')
            value=plugin.get('value')

            if plugin.get('type') == "text":
                printDebug.debug("Setting up a text entry screen")
                kb = xbmc.Keyboard(value, 'heading')
                kb.setHeading(label)

                if option == "hidden":
                    kb.setHiddenInput(True)
                else:
                    kb.setHiddenInput(False)

                kb.doModal()
                if (kb.isConfirmed()):
                    value = kb.getText()
                    printDebug.debug("Value input: %s " % value)
                else:
                    printDebug.debug("User cancelled dialog")
                    return False

            elif plugin.get('type') == "enum":
                printDebug.debug("Setting up an enum entry screen")

                values=plugin.get('values').split('|')

                settingScreen = xbmcgui.Dialog()
                value = settingScreen.select(label,values)
                if value == -1:
                    printDebug.debug("User cancelled dialog")
                    return False
            else:
                printDebug.debug('Unknown option type: %s' % plugin.get('id') )

        else:
            value=plugin.get('value')
            id=plugin.get('id')

        if setString is None:
            setString='%s/set?%s=%s' % (url, id, value)
        else:
            setString='%s&%s=%s' % (setString, id, value)

    printDebug.debug("Settings URL: %s" % setString )
    plex_network.talk_to_server(setString)
    xbmc.executebuiltin("Container.Refresh")

    return False

def processXML( url, tree=None ):
    '''
        Main function to parse plugin XML from PMS
        Will create dir or item links depending on what the
        main tag is.
        @input: plugin page URL
        @return: nothing, creates XBMC GUI listing
    '''
    printDebug.debug("== ENTER ==")
    xbmcplugin.setContent(pluginhandle, 'movies')
    server=plex_network.get_server_from_url(url)
    tree=getXML(url,tree)
    if tree is None:
        return
    setWindowHeading(tree)
    for plugin in tree:

        details={'title'   : plugin.get('title','Unknown').encode('utf-8') }

        if details['title'] == "Unknown":
            details['title']=plugin.get('name',"Unknown").encode('utf-8')

        extraData={'thumb'        : getThumb(plugin, server) ,
                   'fanart_image' : getFanart(plugin, server) ,
                   'identifier'   : tree.get('identifier','') ,
                   'type'         : "Video" }

        if extraData['fanart_image'] == "":
            extraData['fanart_image']=getFanart(tree, server)

        p_url=getLinkURL(url, plugin, server)

        if plugin.tag == "Directory" or plugin.tag == "Podcast":
            extraData['mode']=_MODE_PROCESSXML
            addGUIItem(p_url, details, extraData)

        elif plugin.tag == "Track":
            trackTag(server, tree, plugin)

        elif plugin.tag == "Playlist":
            playlistTag(url, server, tree, plugin)
            
        elif tree.get('viewGroup') == "movie":
            Movies(url, tree)
            return

        elif tree.get('viewGroup') == "episode":
            TVEpisodes(url, tree)
            return

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=True)

def movieTag(url, server, tree, movie, randomNumber):

    printDebug.debug("---New Item---")
    tempgenre=[]
    tempcast=[]
    tempdir=[]
    tempwriter=[]

    #Lets grab all the info we can quickly through either a dictionary, or assignment to a list
    #We'll process it later
    for child in movie:
        if child.tag == "Media":
            mediaarguments = dict(child.items())
        elif child.tag == "Genre" and not settings.get_setting('skipmetadata'):
            tempgenre.append(child.get('tag'))
        elif child.tag == "Writer"  and not settings.get_setting('skipmetadata'):
            tempwriter.append(child.get('tag'))
        elif child.tag == "Director"  and not settings.get_setting('skipmetadata'):
            tempdir.append(child.get('tag'))
        elif child.tag == "Role"  and not settings.get_setting('skipmetadata'):
            tempcast.append(child.get('tag'))

    printDebug.debug("Media attributes are %s" % mediaarguments)

    #Gather some data
    view_offset=movie.get('viewOffset',0)
    duration=int(mediaarguments.get('duration',movie.get('duration',0)))/1000
    #if movie.get('originallyAvailableAt') is not None:
    #    release_date = time.strftime('%d.%m.%Y',(time.strptime(movie.get('originallyAvailableAt'), '%Y-%m-%d')))
    #else:
    #    release_date = ""

    #Required listItem entries for XBMC
    details={'plot'      : movie.get('summary','').encode('utf-8') ,
             'title'     : movie.get('title','Unknown').encode('utf-8') ,
             'sorttitle' : movie.get('titleSort', movie.get('title','Unknown')).encode('utf-8') ,
             'rating'    : float(movie.get('rating',0)) ,
             'studio'    : movie.get('studio','').encode('utf-8'),
             'mpaa'      : movie.get('contentRating', '').encode('utf-8'),
             'year'      : int(movie.get('year',0)),
             'date'      : movie.get('originallyAvailableAt','1970-01-01'),
             'tagline'   : movie.get('tagline',''), 
             'DateAdded' : str(datetime.datetime.fromtimestamp(int(movie.get('addedAt',0))))}

    #Extra data required to manage other properties
    extraData={'type'         : "Video" ,
               'source'       : 'movies',
               'thumb'        : getThumb(movie, server) ,
               'fanart_image' : getFanart(movie, server) ,
               'key'          : movie.get('key',''),
               'ratingKey'    : str(movie.get('ratingKey',0)),
               'duration'     : duration,
               'resume'       : int (int(view_offset)/1000) }

    #Determine what type of watched flag [overlay] to use
    if int(movie.get('viewCount',0)) > 0:
        details['playcount'] = 1
    elif int(movie.get('viewCount',0)) == 0:
        details['playcount'] = 0

    #Extended Metadata
    if not settings.get_setting('skipmetadata'):
        details['cast']     = tempcast
        details['director'] = " / ".join(tempdir)
        details['writer']   = " / ".join(tempwriter)
        details['genre']    = " / ".join(tempgenre)

    if movie.get('primaryExtraKey') is not None:
        details['trailer'] = "plugin://plugin.video.plexbmc/?url=%s%s?t=%s&mode=%s" % (server.get_url_location(), movie.get('primaryExtraKey', ''), randomNumber, _MODE_PLAYLIBRARY)
        printDebug.debug('Trailer plugin url added: %s' % details['trailer'])
        
    #Add extra media flag data
    if not settings.get_setting('skipmediaflags'):
        extraData.update(getMediaData(mediaarguments))

    #Build any specific context menu entries
    if not settings.get_setting('skipcontext'):
        context=buildContextMenu(url, extraData, server)
    else:
        context=None
    # http:// <server> <path> &mode=<mode> &t=<rnd>
    extraData['mode']=_MODE_PLAYLIBRARY
    separator = "?"
    if "?" in extraData['key']:
        separator = "&"
    u="%s%s%st=%s" % (server.get_url_location(), extraData['key'], separator, randomNumber)

    addGUIItem(u,details,extraData,context,folder=False)
    return
    
def getMediaData ( tag_dict ):
    '''
        Extra the media details from the XML
        @input: dict of <media /> tag attributes
        @output: dict of required values
    '''
    printDebug.debug("== ENTER ==")

    return     {'VideoResolution'    : tag_dict.get('videoResolution','') ,
                'VideoCodec'         : tag_dict.get('videoCodec','') ,
                'AudioCodec'         : tag_dict.get('audioCodec','') ,
                'AudioChannels'      : tag_dict.get('audioChannels','') ,
                'VideoAspect'        : tag_dict.get('aspectRatio','') ,
                'xbmc_height'        : tag_dict.get('height') ,
                'xbmc_width'         : tag_dict.get('width') ,
                'xbmc_VideoCodec'    : tag_dict.get('videoCodec') ,
                'xbmc_AudioCodec'    : tag_dict.get('audioCodec') ,
                'xbmc_AudioChannels' : tag_dict.get('audioChannels') ,
                'xbmc_VideoAspect'   : tag_dict.get('aspectRatio') }

def trackTag( server, tree, track, sectionart="", sectionthumb="", listing=True ):
    printDebug.debug("== ENTER ==")
    xbmcplugin.setContent(pluginhandle, 'songs')

    for child in track:
        for babies in child:
            if babies.tag == "Part":
                partDetails=(dict(babies.items()))

    printDebug.debug( "Part is %s" % partDetails)

    details={'TrackNumber' : int(track.get('index',0)) ,
             'title'       : str(track.get('index',0)).zfill(2)+". "+track.get('title','Unknown').encode('utf-8') ,
             'rating'      : float(track.get('rating',0)) ,
             'album'       : track.get('parentTitle', tree.get('parentTitle','')).encode('utf-8') ,
             'artist'      : track.get('grandparentTitle', tree.get('grandparentTitle','')).encode('utf-8') ,
             'duration'    : int(track.get('duration',0))/1000 
             }

    extraData={'type'         : "Music" ,
               #'fanart_image' : getFanart(track, server) ,
               #'thumb'        : getThumb(track, server) ,
               'fanart_image' : sectionart ,
               'thumb'      : sectionthumb ,
               'ratingKey'    : track.get('key','') }


    #If we are streaming, then get the virtual location
    url=mediaType(partDetails,server)

    extraData['mode']=_MODE_BASICPLAY
    u="%s" % (url)

    if listing:
        addGUIItem(u,details,extraData,folder=False)
    else:
        return ( url, details )

def playlistTag(url, server, tree, track, sectionart="", sectionthumb="", listing=True ):
    printDebug.debug("== ENTER ==")

    details={'title'       : track.get('title','Unknown').encode('utf-8') ,
             'duration'    : int(track.get('duration',0))/1000 
             }

    extraData={'type'         : track.get('playlistType', ''),
               'thumb'      : getThumb({'thumb' : track.get('composite', '')},server)} 

    if extraData['type'] == "video":
        extraData['mode'] = _MODE_MOVIES
    elif extraData['type'] == "audio":
        extraData['mode'] = _MODE_TRACKS
    else:
        extraData['mode']=_MODE_GETCONTENT
    
    u=getLinkURL(url, track, server)

    if listing:
        addGUIItem(u,details,extraData,folder=True)
    else:
        return ( url, details )

def photo( url,tree=None ):
    printDebug.debug("== ENTER ==")
    server=url.split('/')[2]

    xbmcplugin.setContent(pluginhandle, 'photo')

    tree=getXML(url,tree)
    if tree is None:
        return

    sectionArt=getFanart(tree,server)
    setWindowHeading(tree)
    for picture in tree:

        details={'title' : picture.get('title',picture.get('name','Unknown')).encode('utf-8') }

        if not details['title']:
            details['title'] = "Unknown"
        
        extraData={'thumb'        : getThumb(picture, server) ,
                   'fanart_image' : getFanart(picture, server) ,
                   'type'         : "image" }

        if extraData['fanart_image'] == "":
            extraData['fanart_image']=sectionArt

        u=getLinkURL(url, picture, server)

        if picture.tag == "Directory":
            extraData['mode']=_MODE_PHOTOS
            addGUIItem(u,details,extraData)

        elif picture.tag == "Photo":

            if tree.get('viewGroup','') == "photo":
                for photo in picture:
                    if photo.tag == "Media":
                        for images in photo:
                            if images.tag == "Part":
                                extraData['key']="http://"+server+images.get('key','')
                                details['size']=int(images.get('size',0))
                                u=extraData['key']

            addGUIItem(u,details,extraData,folder=False)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=True)

def music( url, tree=None ):
    printDebug.debug("== ENTER ==")
    xbmcplugin.setContent(pluginhandle, 'artists')
 
    server=plex_network.get_server_from_url(url) 

    tree=getXML(url,tree)
    if tree is None:
        return

    setWindowHeading(tree)
    for grapes in tree:

        if grapes.get('key',None) is None:
            continue

        details={'genre'       : grapes.get('genre','').encode('utf-8') ,
                 'artist'      : grapes.get('artist','').encode('utf-8') ,
                 'year'        : int(grapes.get('year',0)) ,
                 'album'       : grapes.get('album','').encode('utf-8') ,
                 'tracknumber' : int(grapes.get('index',0)) ,
                 'title'       : "Unknown" }


        extraData={'type'        : "Music" ,
                   'thumb'       : getThumb(grapes, server) ,
                   'fanart_image': getFanart(grapes, server) }

        if extraData['fanart_image'] == "":
            extraData['fanart_image']=getFanart(tree, server)

        u=getLinkURL(url, grapes, server)

        if grapes.tag == "Track":
            printDebug.debug("Track Tag")
            xbmcplugin.setContent(pluginhandle, 'songs')

            details['title']=grapes.get('track',grapes.get('title','Unknown')).encode('utf-8')
            details['duration']=int(int(grapes.get('totalTime',0))/1000)

            extraData['mode']=_MODE_BASICPLAY
            addGUIItem(u,details,extraData,folder=False)

        else:

            if grapes.tag == "Artist":
                printDebug.debug("Artist Tag")
                xbmcplugin.setContent(pluginhandle, 'artists')
                details['title']=grapes.get('artist','Unknown').encode('utf-8')

            elif grapes.tag == "Album":
                printDebug.debug("Album Tag")
                xbmcplugin.setContent(pluginhandle, 'albums')
                details['title']=grapes.get('album','Unknown').encode('utf-8')

            elif grapes.tag == "Genre":
                details['title']=grapes.get('genre','Unknown').encode('utf-8')

            else:
                printDebug.debug("Generic Tag: %s" % grapes.tag)
                details['title']=grapes.get('title','Unknown').encode('utf-8')

            extraData['mode']=_MODE_MUSIC
            addGUIItem(u,details,extraData)

    printDebug.debug("Skin override is: %s" % __settings__.getSetting('skinoverride'))
    view_id = enforceSkinView('music')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=True)

def getThumb(data, server, width=720, height=720):
    '''
        Simply take a URL or path and determine how to format for images
        @ input: elementTree element, server name
        @ return formatted URL
    '''

    if settings.get_setting('skipimages'):
        return ''

    thumbnail=data.get('thumb','').split('?t')[0].encode('utf-8')

    if thumbnail == '':
        return g_thumb

    elif thumbnail.startswith("http") :
        return thumbnail

    elif thumbnail.startswith('/'):
        if settings.get_setting('fullres_thumbnails'):
            return server.get_formatted_url(thumbnail)
        else:
            return server.get_formatted_url('/photo/:/transcode?url=%s&width=%s&height=%s' % (urllib.quote_plus('http://localhost:32400' + thumbnail), width, height))
    else:
        return g_thumb

def getShelfThumb(data, server, seasonThumb=0, width=400, height=400):
    '''
        Simply take a URL or path and determine how to format for images
        @ input: elementTree element, server name
        @ return formatted URL
    '''

    if seasonThumb == 1:
        thumbnail=data.get('grandparentThumb','').split('?t')[0].encode('utf-8')    
    
    else:
        thumbnail=data.get('thumb','').split('?t')[0].encode('utf-8')

    if thumbnail == '':
        return g_thumb

    elif thumbnail.startswith("http"):
        return thumbnail

    elif thumbnail.startswith('/'):
        if settings.get_setting('fullres_thumbnails'):
            return server.get_formatted_url(thumbnail)
        else:
            return server.get_formatted_url('/photo/:/transcode?url=%s&width=%s&height=%s' % (urllib.quote_plus('http://localhost:32400' + thumbnail), width, height))

    else:
        return g_thumb

def getFanart(data, server, width=1280, height=720):
    '''
        Simply take a URL or path and determine how to format for fanart
        @ input: elementTree element, server name
        @ return formatted URL for photo resizing
    '''
    if settings.get_setting('skipimages'):
        return ''
        
    fanart=data.get('art','').encode('utf-8')

    if fanart == '':
        return ''

    elif fanart.startswith('http') :
        return fanart

    elif fanart.startswith('/'):
        if settings.get_setting('fullres_fanart'):
            return server.get_formatted_url(fanart)
        else:
            return server.get_formatted_url('/photo/:/transcode?url=%s&width=%s&height=%s' % (urllib.quote_plus('http://localhost:32400' + fanart), width, height))

    else:
        return ''
        
def getLinkURL(url, pathData, server, season_shelf=False):
    if not season_shelf:
        path = pathData.get('key', '')
    else:
        path = pathData.get('parentKey', '') + "/children"
        
    printDebug.debug("Path is %s" % path)

    if path == '':
        printDebug.debug("Empty Path")
        return

    #If key starts with http, then return it
    if path.startswith('http'):
        printDebug.debug("Detected http link")
        return path

    #If key starts with a / then prefix with server address
    elif path.startswith('/'):
        printDebug.debug("Detected base path link")
        return '%s%s' % (server.get_url_location(), path)

    #If key starts with plex:// then it requires transcoding
    elif path.startswith("plex:") :
        printDebug.debug("Detected plex link")
        components = path.split('&')
        for i in components:
            if 'prefix=' in i:
                del components[components.index(i)]
                break
        if pathData.get('identifier',None):
            components.append('identifier='+pathData['identifier'])

        path='&'.join(components)
        return 'plex://'+server.get_location()+'/'+'/'.join(path.split('/')[3:])
        
    elif path.startswith("rtmp"):
        printDebug.debug("Detected RTMP link")
        return path

    #Any thing else is assumed to be a relative path and is built on existing url
    else:
        printDebug.debug("Detected relative link")
        return "%s/%s" % (url, path)

    return url

def plexOnline( url ):
    printDebug.debug("== ENTER ==")
    xbmcplugin.setContent(pluginhandle, 'addons')

    server=plex_network.get_server_from_url(url)

    tree=server.processed_xml(url)
    if tree is None:
        return

    for plugin in tree:

        details={'title' : plugin.get('title',plugin.get('name','Unknown')).encode('utf-8') }
        extraData={'type'      : "Video" ,
                   'installed' : int(plugin.get('installed',2)) ,
                   'key'       : plugin.get('key','') ,
                   'thumb'     : getThumb(plugin,server)}

        extraData['mode']=_MODE_CHANNELINSTALL

        if extraData['installed'] == 1:
            details['title']=details['title']+" (installed)"

        elif extraData['installed'] == 2:
            extraData['mode']=_MODE_PLEXONLINE

        u=getLinkURL(url, plugin, server)

        extraData['parameters']={'name' : details['title'] }
        
        addGUIItem(u, details, extraData)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=True)

def install( url, name ):
    printDebug.debug("== ENTER ==")
    server=plex_network.get_server_from_url(url)
    tree=server.processed_xml(url)
    if tree is None:
        return

    operations={}
    i=0
    for plums in tree.findall('Directory'):
        operations[i]=plums.get('title')

        #If we find an install option, switch to a yes/no dialog box
        if operations[i].lower() == "install":
            printDebug.debug("Not installed.  Print dialog")
            ret = xbmcgui.Dialog().yesno("Plex Online","About to install " + name)

            if ret:
                printDebug.debug("Installing....")
                tree = server.processed_xml(url+"/install")

                msg=tree.get('message','(blank)')
                printDebug.debug(msg)
                xbmcgui.Dialog().ok("Plex Online",msg)
            return

        i+=1

    #Else continue to a selection dialog box
    ret = xbmcgui.Dialog().select("This plugin is already installed..",operations.values())

    if ret == -1:
        printDebug.debug("No option selected, cancelling")
        return

    printDebug.debug("Option %s selected.  Operation is %s" % (ret, operations[ret]))
    u=url+"/"+operations[ret].lower()
    tree = server.processed_xml(u)

    msg=tree.get('message')
    printDebug.debug(msg)
    xbmcgui.Dialog().ok("Plex Online",msg)
    xbmc.executebuiltin("Container.Refresh")


    return

def channelView( url ):
    printDebug.debug("== ENTER ==")
    server=plex_network.get_server_from_url(url)
    tree=server.processed_xml(url)
    
    if tree is None:
        return
    
    setWindowHeading(tree)
    for channels in tree.getiterator('Directory'):

        if channels.get('local','') == "0":
            continue

        arguments=dict(channels.items())

        extraData={'fanart_image' : getFanart(channels, server) ,
                   'thumb'        : getThumb(channels, server) }

        details={'title' : channels.get('title','Unknown') }

        suffix=channels.get('path').split('/')[1]

        if channels.get('unique','')=='0':
            details['title']="%s (%s)" % ( details['title'], suffix )

        #Alter data sent into getlinkurl, as channels use path rather than key
        p_url=getLinkURL(url, {'key': channels.get('path',None), 'identifier' : channels.get('path',None)} , server)

        if suffix == "photos":
            extraData['mode']=_MODE_PHOTOS
        elif suffix == "video":
            extraData['mode']=_MODE_PLEXPLUGINS
        elif suffix == "music":
            extraData['mode']=_MODE_MUSIC
        else:
            extraData['mode']=_MODE_GETCONTENT

        addGUIItem(p_url,details,extraData)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=True)

def skin( server_list=None, type=None ):
    #Gather some data and set the window properties
    printDebug.debug("== ENTER ==")
    #Get the global host variable set in settings
    WINDOW = xbmcgui.Window( 10000 )

    sectionCount=0
    serverCount=0
    sharedCount=0
    shared_flag={}
    hide_shared = __settings__.getSetting('hide_shared')

    if server_list is None:
        server_list=plex_network.get_server_list()

    for server in server_list:
    
        server.discover_sections()
    
        for section in server.get_sections():

            extraData={ 'fanart_image' : server.get_fanart(section) ,
                        'thumb'        : server.get_fanart(section) }

            #Determine what we are going to do process after a link is selected by the user, based on the content we find

            path=section.get_path()

            if section.is_show():
                if hide_shared == "true" and not server.is_owned():
                    shared_flag['show']=True
                    continue
                window="VideoLibrary"
                mode=_MODE_TVSHOWS
            if  section.is_movie():
                if hide_shared == "true" and not server.is_owned():
                    shared_flag['movie']=True
                    continue
                window="VideoLibrary"
                mode=_MODE_MOVIES
            if  section.is_artist():
                if hide_shared == "true" and not server.is_owned():
                    shared_flag['artist']=True
                    continue
                window="MusicFiles"
                mode=_MODE_ARTISTS
            if  section.is_photo():
                if hide_shared == "true" and not server.is_owned():
                    shared_flag['photo']=True
                    continue
                window="Pictures"
                mode=_MODE_PHOTOS

            if settings.get_setting('secondary'):
                mode=_MODE_GETCONTENT
            else:
                path=path+'/all'

            s_url='%s%s&mode=%s' % ( server.get_url_location(), path, mode)

            #Build that listing..
            WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , section.get_title())
            WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , server.get_name())
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s,return)" % (window, s_url))
            WINDOW.setProperty("plexbmc.%d.art"      % (sectionCount) , extraData['fanart_image'])
            WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , section.get_type())
            WINDOW.setProperty("plexbmc.%d.icon"     % (sectionCount) , extraData['thumb'])
            WINDOW.setProperty("plexbmc.%d.thumb"    % (sectionCount) , extraData['thumb'])
            WINDOW.setProperty("plexbmc.%d.partialpath" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s" % (window, server.get_url_location(), section.get_path()))
            WINDOW.setProperty("plexbmc.%d.search" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/search?type=1", mode) )
            WINDOW.setProperty("plexbmc.%d.recent" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/recentlyAdded", mode) )
            WINDOW.setProperty("plexbmc.%d.all" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/all", mode, ) )
            WINDOW.setProperty("plexbmc.%d.viewed" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/recentlyViewed", mode) )
            WINDOW.setProperty("plexbmc.%d.ondeck" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/onDeck", mode) )
            WINDOW.setProperty("plexbmc.%d.released" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/newest", mode) )
            WINDOW.setProperty("plexbmc.%d.shared"     % (sectionCount) , "false")

            if section['type'] == "artist":
                WINDOW.setProperty("plexbmc.%d.album" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/albums", mode) )
                WINDOW.setProperty("plexbmc.%d.search" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/search?type=10", mode) )
            elif section['type'] == "photo":
                WINDOW.setProperty("plexbmc.%d.year" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/year", mode) )
            elif section['type'] == "show":
                WINDOW.setProperty("plexbmc.%d.search" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/search?type=4", mode) )
            elif section['type'] == "movie":
                WINDOW.setProperty("plexbmc.%d.search" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/search?type=1", mode) )
            
            printDebug.debug("Building window properties index [%s] which is [%s]" % (sectionCount, section.get_title()))
            printDebug.debug("PATH in use is: ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s,return)" % (window, s_url))
            sectionCount += 1

   
    if type == "nocat":
        WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared...")
        WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
        WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=/&mode=%s,return)" % _MODE_SHARED_ALL )
        WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "movie")
        WINDOW.setProperty("plexbmc.%d.shared"   % (sectionCount) , "true")
        sectionCount += 1
    
    else:
   
        if shared_flag.get('movie'):
            WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared...")
            WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=/&mode=%s,return)" % _MODE_SHARED_MOVIES )
            WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "movie")
            WINDOW.setProperty("plexbmc.%d.shared"   % (sectionCount) , "true")
            sectionCount += 1

        if shared_flag.get('show'):
            WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared...")
            WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=/&mode=%s,return)" % _MODE_SHARED_SHOWS)
            WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "show")
            WINDOW.setProperty("plexbmc.%d.shared"   % (sectionCount) , "true")
            sectionCount += 1
            
        if shared_flag.get('artist'):
            WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared...")
            WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(MusicFiles,plugin://plugin.video.plexbmc/?url=/&mode=%s,return)" % _MODE_SHARED_MUSIC)
            WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "artist")
            WINDOW.setProperty("plexbmc.%d.shared"     % (sectionCount) , "true")
            sectionCount += 1
            
        if shared_flag.get('photo'):
            WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared...")
            WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(Pictures,plugin://plugin.video.plexbmc/?url=/&mode=%s,return)" % _MODE_SHARED_PHOTOS)
            WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "photo")
            WINDOW.setProperty("plexbmc.%d.shared"     % (sectionCount) , "true")
            sectionCount += 1
        
        
    #For each of the servers we have identified
    numOfServers=len(server_list)

    for server in server_list:
    
        if server.is_secondary():
            continue
            
        if settings.channelview:
            WINDOW.setProperty("plexbmc.channel", "1")
            WINDOW.setProperty("plexbmc.%d.server.channel" % (serverCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=%s/system/plugins/all&mode=21,return)" % server.get_url_location())
        else:
            WINDOW.clearProperty("plexbmc.channel")
            WINDOW.setProperty("plexbmc.%d.server.video" % (serverCount) , "%s/video&mode=7" % server.get_url_location() )
            WINDOW.setProperty("plexbmc.%d.server.music" % (serverCount) , "%s/music&mode=17" % server.get_url_location() )
            WINDOW.setProperty("plexbmc.%d.server.photo" % (serverCount) , "%s/photos&mode=16" % server.get_url_location() )

        WINDOW.setProperty("plexbmc.%d.server.online" % (serverCount) , "%s/system/plexonline&mode=19" % server.get_url_location() )

        WINDOW.setProperty("plexbmc.%d.server" % (serverCount) , server.get_name())

        serverCount+=1

    #Clear out old data
    try:
        printDebug.debug("Clearing properties from [%s] to [%s]" % (sectionCount, WINDOW.getProperty("plexbmc.sectionCount")))

        for i in range(sectionCount, int(WINDOW.getProperty("plexbmc.sectionCount"))+1):
            WINDOW.clearProperty("plexbmc.%d.uuid"     % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.title"    % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.subtitle" % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.url"      % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.path"     % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.window"   % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.art"      % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.type"     % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.icon"     % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.thumb"    % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.recent"   % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.all"      % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.search"   % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.viewed"   % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.ondeck"   % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.released" % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.shared"   % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.album"    % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.year"     % ( i ) )

    except:
        pass

    printDebug.debug("Total number of skin sections is [%s]" % sectionCount )
    printDebug.debug("Total number of servers is [%s]" % numOfServers)
    WINDOW.setProperty("plexbmc.sectionCount", str(sectionCount))
    WINDOW.setProperty("plexbmc.numServers", str(numOfServers))
    if __settings__.getSetting('myplex_user') != '':
        WINDOW.setProperty("plexbmc.queue" , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=http://myplexqueue&mode=24,return)")
        WINDOW.setProperty("plexbmc.myplex",  "1" )
    else:
        WINDOW.clearProperty("plexbmc.myplex")

    return

def amberskin():
    #Gather some data and set the window properties
    printDebug.debug("== ENTER ==")
    #Get the global host variable set in settings
    WINDOW = xbmcgui.Window( 10000 )

    sectionCount=0
    serverCount=0
    sharedCount=0
    shared_flag={}
    hide_shared = __settings__.getSetting('hide_shared')

    server_list=plex_network.get_server_list()
    printDebug.debug("Using list of %s servers: %s " % (len(server_list), server_list))

    for server in server_list:
    
        server.discover_sections()
    
        for section in server.get_sections():

            printDebug.debug("=Enter amberskin section=")
            printDebug.debug(str(section.__dict__))
            printDebug.debug("=/section=")

            extraData = {'fanart_image': server.get_fanart(section), 
                         'thumb': g_thumb}

            #Determine what we are going to do process after a link is selected by the user, based on the content we find
            path = section.get_path()

            if section.is_show():
                if hide_shared == "true" and not server.is_owned():
                    shared_flag['show']=True
                    sharedCount += 1
                    continue
                window="VideoLibrary"
                mode=_MODE_TVSHOWS
            elif section.is_movie():
                if hide_shared == "true" and not server.is_owned():
                    shared_flag['movie']=True
                    sharedCount += 1
                    continue
                window="VideoLibrary"
                mode=_MODE_MOVIES
            elif section.is_artist():
                if hide_shared == "true" and not server.is_owned():
                    shared_flag['artist']=True
                    sharedCount += 1
                    continue
                window="MusicFiles"
                mode=_MODE_ARTISTS
            elif  section.is_photo():
                if hide_shared == "true" and not server.is_owned():
                    shared_flag['photo']=True
                    sharedCount += 1
                    continue
                window="Pictures"
            else:
                if hide_shared == "true" and not server.is_owned():
                    shared_flag['movie']=True
                    sharedCount += 1
                    continue
                window="Videos"
                mode=_MODE_PHOTOS

            if settings.get_setting('secondary'):
                mode=_MODE_GETCONTENT
            else:
                path=path+'/all'

            #Build that listing..
            WINDOW.setProperty("plexbmc.%d.uuid" % (sectionCount) , section.get_uuid())
            WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , section.get_title())
            WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , server.get_name())
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s&mode=%s,return)" % ( window, server.get_url_location(), path, mode))
            WINDOW.setProperty("plexbmc.%d.art"      % (sectionCount) , extraData['fanart_image'])
            WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , section.get_type())
            WINDOW.setProperty("plexbmc.%d.icon"     % (sectionCount) , extraData['thumb'])
            WINDOW.setProperty("plexbmc.%d.thumb"    % (sectionCount) , extraData['thumb'])
            WINDOW.setProperty("plexbmc.%d.partialpath" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s" % (window, server.get_url_location(),section.get_path()))
            WINDOW.setProperty("plexbmc.%d.search" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/search?type=1", mode) )
            WINDOW.setProperty("plexbmc.%d.recent" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/recentlyAdded", mode) )
            WINDOW.setProperty("plexbmc.%d.all" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/all", mode) )
            WINDOW.setProperty("plexbmc.%d.viewed" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/recentlyViewed", mode) )
            WINDOW.setProperty("plexbmc.%d.ondeck" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/onDeck", mode) )
            WINDOW.setProperty("plexbmc.%d.released" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/newest", mode) )
            WINDOW.setProperty("plexbmc.%d.shared"     % (sectionCount) , "false")

            if section.is_artist():
                WINDOW.setProperty("plexbmc.%d.album" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/albums", mode) )
                WINDOW.setProperty("plexbmc.%d.search" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/search?type=10", mode) )
            elif section.is_photo():
                WINDOW.setProperty("plexbmc.%d.year" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/year", mode) )
            elif section.is_show():
                WINDOW.setProperty("plexbmc.%d.search" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/search?type=4", mode) )
            elif section.is_movie():
                WINDOW.setProperty("plexbmc.%d.search" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/search?type=1", mode) )

            printDebug.debug("Building window properties index [%s] which is [%s]" % (sectionCount, section.get_title()))
            printDebug.debug("PATH in use is: ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s&mode=%s,return)" % ( window, server.get_url_location(), path, mode))
            sectionCount += 1


    if __settings__.getSetting('myplex_user') != '' and hide_shared == 'true' and sharedCount != 0:
        WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared Content")
        WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
        WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=/&mode=%s,return)" % _MODE_SHARED_ALL)
        WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "shared")
        WINDOW.setProperty("plexbmc.%d.shared"     % (sectionCount) , "true")
        sectionCount += 1

    elif sharedCount != 0:

        if shared_flag.get('movie'):
            WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared...")
            WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=/&mode=%s,return)" % _MODE_SHARED_MOVIES)
            WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "shared")
            WINDOW.setProperty("plexbmc.%d.shared"     % (sectionCount) , "true")
            sectionCount += 1

        if shared_flag.get('show'):
            WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared...")
            WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=/&mode=%s,return)" % _MODE_SHARED_SHOWS)
            WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "shared")
            WINDOW.setProperty("plexbmc.%d.shared"     % (sectionCount) , "true")
            sectionCount += 1

        if shared_flag.get('artist'):
            WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared...")
            WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(MusicFiles,plugin://plugin.video.plexbmc/?url=/&mode=%s,return)"% _MODE_SHARED_MUSIC)
            WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "shared")
            WINDOW.setProperty("plexbmc.%d.shared"     % (sectionCount) , "true")
            sectionCount += 1

        if shared_flag.get('photo'):
            WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared...")
            WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(Pictures,plugin://plugin.video.plexbmc/?url=/&mode=%s,return)" % _MODE_SHARED_PHOTOS)
            WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "shared")
            WINDOW.setProperty("plexbmc.%d.shared"     % (sectionCount) , "true")
            sectionCount += 1

    else:
        pass

    #For each of the servers we have identified
    numOfServers=len(server_list)
    shelfChannel (server_list)

    for server in server_list:

        printDebug.debug(server.get_details())
    
        if server.is_secondary():
            continue

        if settings.get_setting('channelview'):
            WINDOW.setProperty("plexbmc.channel", "1")
            WINDOW.setProperty("plexbmc.%d.server.channel" % (serverCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=%s%s&mode=%s, return" % (server.get_url_location(), "/system/plugins/all", _MODE_CHANNELVIEW ))
        else:
            WINDOW.clearProperty("plexbmc.channel")
            WINDOW.setProperty("plexbmc.%d.server.video" % (serverCount) , "%s%s&mode=%s" % (server.get_url_location(), "/video", _MODE_PLEXPLUGINS ))
            WINDOW.setProperty("plexbmc.%d.server.music" % (serverCount) , "%s%s&mode=%s" % (server.get_url_location(), "/music", _MODE_MUSIC ))
            WINDOW.setProperty("plexbmc.%d.server.photo" % (serverCount) , "%s%s&mode=%s" % (server.get_url_location(), "/photos", _MODE_PHOTOS ))

        WINDOW.setProperty("plexbmc.%d.server.online" % (serverCount) , "%s%s&mode=%s" % (server.get_url_location(), "/system/plexonline", _MODE_PLEXONLINE ))

        WINDOW.setProperty("plexbmc.%d.server" % (serverCount) , server.get_name())

        serverCount+=1

    #Clear out old data
    try:
        printDebug.debug("Clearing properties from [%s] to [%s]" % (sectionCount, WINDOW.getProperty("plexbmc.sectionCount")))

        for i in range(sectionCount, int(WINDOW.getProperty("plexbmc.sectionCount"))+1):
            WINDOW.clearProperty("plexbmc.%d.uuid"    % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.title"    % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.subtitle" % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.url"      % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.path"     % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.window"   % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.art"      % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.type"     % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.icon"     % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.thumb"    % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.recent"    % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.all"    % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.search"    % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.viewed"    % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.ondeck" % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.released" % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.shared"     % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.album"     % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.year"     % ( i ) )

    except:
        pass

    printDebug.debug("Total number of skin sections is [%s]" % sectionCount )
    printDebug.debug("Total number of servers is [%s]" % numOfServers)
    WINDOW.setProperty("plexbmc.sectionCount", str(sectionCount))
    WINDOW.setProperty("plexbmc.numServers", str(numOfServers))

    if __settings__.getSetting('myplex_user') != '':
        WINDOW.setProperty("plexbmc.queue" , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=http://myplexqueue&mode=24,return)")
        WINDOW.setProperty("plexbmc.myplex",  "1" )

        #Now let's populate queue shelf items since we have MyPlex login
        if __settings__.getSetting('homeshelf') != '3':
            printDebug.debug("== ENTER ==")

            root = plex_network.get_myplex_queue()
            server_address = getMasterServer()
            queue_count = 1

            for media in root:
                printDebug.debug("Found a queue item entry: [%s]" % (media.get('title', '').encode('UTF-8') , ))
                m_url = "plugin://plugin.video.plexbmc?url=%s&mode=%s&indirect=%s" % (getLinkURL(server_address.get_url_location(), media, server_address), 18, 1)
                m_thumb = getShelfThumb(media, server_address, seasonThumb=0)

                try:
                    movie_runtime = str(int(float(media.get('duration'))/1000/60))
                except:
                    movie_runtime = ""

                WINDOW.setProperty("Plexbmc.Queue.%s.Path" % queue_count, m_url)
                WINDOW.setProperty("Plexbmc.Queue.%s.Title" % queue_count, media.get('title', 'Unknown').encode('UTF-8'))
                WINDOW.setProperty("Plexbmc.Queue.%s.Year" % queue_count, media.get('originallyAvailableAt', '').encode('UTF-8'))
                WINDOW.setProperty("Plexbmc.Queue.%s.Duration" % queue_count, movie_runtime)
                WINDOW.setProperty("Plexbmc.Queue.%s.Thumb" % queue_count, m_thumb)

                queue_count += 1

                printDebug.debug("Building Queue item: %s" % media.get('title', 'Unknown').encode('UTF-8'))
                printDebug.debug("Building Queue item url: %s" % m_url)
                printDebug.debug("Building Queue item thumb: %s" % m_thumb)

            clearQueueShelf(queue_count)

    else:
        WINDOW.clearProperty("plexbmc.myplex")

    fullShelf (server_list)
    
def fullShelf(server_list={}):
    #Gather some data and set the window properties
    printDebug.debug("== ENTER ==")

    if __settings__.getSetting('homeshelf') == '3' or ((__settings__.getSetting('movieShelf') == "false" and __settings__.getSetting('tvShelf') == "false" and __settings__.getSetting('musicShelf') == "false")):
        printDebug.debug("Disabling all shelf items")
        clearShelf()
        clearOnDeckShelf()
        return

    #Get the global host variable set in settings
    WINDOW = xbmcgui.Window( 10000 )

    recentMovieCount=1
    recentSeasonCount=1
    recentMusicCount=1
    recentPhotoCount=1
    ondeckMovieCount=1
    ondeckSeasonCount=1
    recent_list=[]
    ondeck_list=[]
    full_count=0

    if server_list == {}:
        xbmc.executebuiltin("XBMC.Notification(Unable to see any media servers,)")
        clearShelf(0, 0, 0, 0)
        return

    randomNumber = str(random.randint(1000000000,9999999999))

    for server_details in server_list:

        if not server_details.is_owned():
            continue

        for section in server_details.get_sections():
        
            if __settings__.getSetting('homeshelf') == '0' or __settings__.getSetting('homeshelf') == '2':
                
                tree = server_details.get_recently_added(section=section.get_key(), size=15)

                if tree is None:
                    printDebug.debug("PLEXBMC -> RecentlyAdded items not found on: %s" % server_details.get_url_location())
                    continue

                libraryuuid = tree.get("librarySectionUUID",'').encode('utf-8')

                ep_helper = {}  # helper season counter
                for eachitem in tree:

                    if eachitem.get("type", "") == "episode":
                        key = int(eachitem.get("parentRatingKey"))  # season identifier

                        if key in ep_helper or ((__settings__.getSetting('hide_watched_recent_items') == 'true' and int(eachitem.get("viewCount", 0)) > 0)):
                            continue

                        ep_helper[key] = key  # use seasons as dict key so we can check

                    recent_list.append((eachitem, server_details, libraryuuid))

            if __settings__.getSetting('homeshelf') == '1' or __settings__.getSetting('homeshelf') == '2':
                
                tree = server_details.get_ondeck(section=section.get_key(),size=15)
                
                if tree is None:
                    print ("PLEXBMC -> OnDeck items not found on: " + server_details.get_url_location(), False)
                    continue

                for eachitem in tree:
                    ondeck_list.append((eachitem, server_details, libraryuuid))

    printDebug.debugplus("Recent object is: %s" % recent_list)
    printDebug.debugplus("ondeck object is: %s" % ondeck_list)
                    
    #For each of the servers we have identified
    for media, source_server, libuuid in recent_list:

        if media.get('type',None) == "movie":

            if __settings__.getSetting('movieShelf') == "false":
                WINDOW.clearProperty("Plexbmc.LatestMovie.1.Path" )
                continue

            title_name=media.get('title','Unknown').encode('UTF-8')
            printDebug.debug("Found a recent movie entry: [%s]" % title_name)

            if __settings__.getSetting('hide_watched_recent_items') == 'false' or media.get("viewCount", 0) == 0:

                title_url="plugin://plugin.video.plexbmc?url=%s&mode=%s&t=%s" % ( getLinkURL(source_server.get_url_location(),media,source_server), _MODE_PLAYSHELF, randomNumber)
                title_thumb = getShelfThumb(media,source_server,seasonThumb=0)

                if media.get('duration') > 0:
                    #movie_runtime = media.get('duration', '0')
                    movie_runtime = str(int(float(media.get('duration'))/1000/60))
                else:
                    movie_runtime = ""

                if media.get('rating') > 0:
                    movie_rating = str(round(float(media.get('rating')), 1))
                else:
                    movie_rating = ''

                WINDOW.setProperty("Plexbmc.LatestMovie.%s.Path" % recentMovieCount, title_url)
                WINDOW.setProperty("Plexbmc.LatestMovie.%s.Title" % recentMovieCount, title_name)
                WINDOW.setProperty("Plexbmc.LatestMovie.%s.Year" % recentMovieCount, media.get('year', '').encode('UTF-8'))
                WINDOW.setProperty("Plexbmc.LatestMovie.%s.Rating" % recentMovieCount, movie_rating)
                WINDOW.setProperty("Plexbmc.LatestMovie.%s.Duration" % recentMovieCount, movie_runtime)
                WINDOW.setProperty("Plexbmc.LatestMovie.%s.Thumb" % recentMovieCount, title_thumb)
                WINDOW.setProperty("Plexbmc.LatestMovie.%s.uuid" % recentMovieCount, libuuid)
                WINDOW.setProperty("Plexbmc.LatestMovie.%s.Plot" % recentMovieCount, media.get('summary', '').encode('UTF-8'))

                m_genre = []

                for child in media:
                    if child.tag == "Genre":
                        m_genre.append(child.get('tag'))
                    else:
                        continue

                WINDOW.setProperty("Plexbmc.LatestMovie.%s.Genre" % recentMovieCount, ", ".join(m_genre).encode('UTF-8'))

                recentMovieCount += 1

            else:
                continue

        elif media.get('type',None) == "season":

            title_name=media.get('parentTitle','Unknown').encode('UTF-8')
            printDebug.debug("Found a recent season entry [%s]" % title_name)

            if __settings__.getSetting('tvShelf') == "false":
                WINDOW.clearProperty("Plexbmc.LatestEpisode.1.Path" )
                continue

            title_url="ActivateWindow(VideoLibrary, plugin://plugin.video.plexbmc?url=%s&mode=%s, return)" % ( getLinkURL(source_server.get_url_location(),media,source_server), _MODE_TVEPISODES)
            title_thumb=getShelfThumb(media,source_server,seasonThumb=0)

            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.Path" % recentSeasonCount, title_url )
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeTitle" % recentSeasonCount, '')
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeSeason" % recentSeasonCount, media.get('title','').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.ShowTitle" % recentSeasonCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.Thumb" % recentSeasonCount, title_thumb)
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.uuid" % recentSeasonCount, media.get('librarySectionUUID','').encode('UTF-8'))

            recentSeasonCount += 1

        elif media.get('type') == "album":

            if __settings__.getSetting('musicShelf') == "false":
                WINDOW.clearProperty("Plexbmc.LatestAlbum.1.Path" )
                continue

            title_name=media.get('parentTitle','Unknown').encode('UTF-8')
            title_url="ActivateWindow(MusicFiles, plugin://plugin.video.plexbmc?url=%s&mode=%s, return)" % ( getLinkURL(source_server.get_url_location(),media,source_server), _MODE_TRACKS)
            title_thumb=getShelfThumb(media,source_server,seasonThumb=0)

            printDebug.debug("Found a recent album entry: [%s]" % title_name)
            
            WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Path" % recentMusicCount, title_url )
            WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Title" % recentMusicCount, media.get('title','Unknown').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Artist" % recentMusicCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Thumb" % recentMusicCount, title_thumb)

            recentMusicCount += 1

        elif media.get('type') == "photo":


            title_name=media.get('title','Unknown').encode('UTF-8')
            title_url="ActivateWindow(Pictures, plugin://plugin.video.plexbmc/?url=%s%s&mode=%s,return" % ( source_server.get_url_location(), "/recentlyAdded", _MODE_PHOTOS)
            title_thumb = getShelfThumb(media, source_server, seasonThumb=0)

            printDebug.debug("Found a recent photo entry: [%s]" % title_name)

            WINDOW.setProperty("Plexbmc.LatestPhoto.%s.Path" % recentPhotoCount, title_url)
            WINDOW.setProperty("Plexbmc.LatestPhoto.%s.Title" % recentPhotoCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestPhoto.%s.Thumb" % recentPhotoCount, title_thumb)

            recentPhotoCount += 1

        elif media.get('type',None) == "episode":

            title_name=media.get('title','Unknown').encode('UTF-8')
            printDebug.debug("Found an Recent episode entry [%s]" % title_name)

            if __settings__.getSetting('tvShelf') == "false":
                WINDOW.clearProperty("Plexbmc.LatestEpisode.1.Path" )
                continue

            title_url="ActivateWindow(Videos, plugin://plugin.video.plexbmc?url=%s&mode=%s, return)" % ( getLinkURL(source_server.get_url_location(), media, source_server, season_shelf=True), _MODE_TVEPISODES)
            title_thumb = getShelfThumb(media, source_server, seasonThumb=1)

            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.Path" % recentSeasonCount, title_url)
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeTitle" % recentSeasonCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeNumber" % recentSeasonCount, media.get('index','').encode('utf-8'))
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeSeason" % recentSeasonCount, media.get('parentIndex','').encode('UTF-8')+'.'+media.get('index','Unknown').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeSeasonNumber" % recentSeasonCount, media.get('parentIndex','').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.ShowTitle" % recentSeasonCount, media.get('grandparentTitle','').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.Thumb" % recentSeasonCount, title_thumb)
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.uuid" % recentSeasonCount, libuuid)

            recentSeasonCount += 1

        printDebug.debug(" Building Recent window title: %s\n    Building Recent window url: %s\n    Building Recent window thumb: %s" % (title_name, title_url, title_thumb))
        
    clearShelf(recentMovieCount, recentSeasonCount, recentMusicCount, recentPhotoCount)

    #For each of the servers we have identified
    for media, source_server, libuuid in ondeck_list:

        if media.get('type',None) == "movie":

            title_name=media.get('title','Unknown').encode('UTF-8')
            printDebug.debug("Found a OnDeck movie entry: [%s]" % title_name)

            if __settings__.getSetting('movieShelf') == "false":
                WINDOW.clearProperty("Plexbmc.OnDeckMovie.1.Path" )
                continue

            title_url = "plugin://plugin.video.plexbmc?url=%s&mode=%s&t=%s" % ( getLinkURL(source_server.get_url_location(),media,source_server), _MODE_PLAYSHELF, randomNumber)
            title_thumb = getShelfThumb(media,source_server,seasonThumb=0)

            if media.get('duration') > 0:
                #movie_runtime = media.get('duration', '0')
                movie_runtime = str(int(float(media.get('duration'))/1000/60))
            else:
                movie_runtime = ""

            if media.get('rating') > 0:
                title_rating = str(round(float(media.get('rating')), 1))
            else:
                title_rating = ''

            WINDOW.setProperty("Plexbmc.OnDeckMovie.%s.Path" % ondeckMovieCount, title_url)
            WINDOW.setProperty("Plexbmc.OnDeckMovie.%s.Title" % ondeckMovieCount, title_name)
            WINDOW.setProperty("Plexbmc.OnDeckMovie.%s.Year" % ondeckMovieCount, media.get('year','').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.OnDeckMovie.%s.Rating" % ondeckMovieCount, title_rating)
            WINDOW.setProperty("Plexbmc.OnDeckMovie.%s.Duration" % ondeckMovieCount, movie_runtime)
            WINDOW.setProperty("Plexbmc.OnDeckMovie.%s.Thumb" % ondeckMovieCount, title_thumb)
            WINDOW.setProperty("Plexbmc.OnDeckMovie.%s.uuid" % ondeckMovieCount, libuuid)

            ondeckMovieCount += 1

        elif media.get('type',None) == "season":

            title_name=media.get('parentTitle','Unknown').encode('UTF-8')
            printDebug.debug("Found a OnDeck season entry [%s]" % title_name)

            if __settings__.getSetting('tvShelf') == "false":
                WINDOW.clearProperty("Plexbmc.OnDeckEpisode.1.Path" )
                continue

            title_url="ActivateWindow(VideoLibrary, plugin://plugin.video.plexbmc?url=%s&mode=%s, return)" % ( getLinkURL(source_server.get_url_location(),media,source_server), _MODE_TVEPISODES)
            title_thumb=getShelfThumb(media,source_server,seasonThumb=0)

            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.Path" % ondeckSeasonCount, title_url )
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.EpisodeTitle" % ondeckSeasonCount, '')
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.EpisodeSeason" % ondeckSeasonCount, media.get('title','').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.ShowTitle" % ondeckSeasonCount, title_name)
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.Thumb" % ondeckSeasonCount, title_thumb)

            ondeckSeasonCount += 1

        elif media.get('type',None) == "episode":

            title_name=media.get('title','Unknown').encode('UTF-8')
            printDebug.debug("Found an onDeck episode entry [%s]" % title_name)

            if __settings__.getSetting('tvShelf') == "false":
                WINDOW.clearProperty("Plexbmc.OnDeckEpisode.1.Path" )
                continue

            title_url="PlayMedia(plugin://plugin.video.plexbmc?url=%s&mode=%s&t=%s)" % (getLinkURL(source_server.get_url_location(), media, source_server), _MODE_PLAYSHELF, randomNumber)
            title_thumb=getShelfThumb(media, source_server, seasonThumb=1)

            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.Path" % ondeckSeasonCount, title_url)
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.EpisodeTitle" % ondeckSeasonCount, title_name)
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.EpisodeNumber" % ondeckSeasonCount, media.get('index','').encode('utf-8'))
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.EpisodeSeason" % ondeckSeasonCount, media.get('grandparentTitle','Unknown').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.EpisodeSeasonNumber" % ondeckSeasonCount, media.get('parentIndex','').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.ShowTitle" % ondeckSeasonCount, title_name)
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.Thumb" % ondeckSeasonCount, title_thumb)
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.uuid" % ondeckSeasonCount, libuuid)

            ondeckSeasonCount += 1

        printDebug.debug(" Building onDeck window title: %s\n    Building onDeck window url: %s\n    Building onDeck window thumb: %s" % (title_name, title_url, title_thumb))

    clearOnDeckShelf(ondeckMovieCount, ondeckSeasonCount)

    if __settings__.getSetting('channelShelf') == "true" or __settings__.getSetting('homeshelf') != '3':
        shelfChannel(server_list)

    else:
        printDebug.debug("Disabling channel shelf items")
        clearChannelShelf()

def displayContent( acceptable_level, content_level ):

    '''
        Takes a content Rating and decides whether it is an allowable
        level, as defined by the content filter
        @input: content rating
        @output: boolean
    '''

    printDebug.info("Checking rating flag [%s] against [%s]" % (content_level, acceptable_level))

    if acceptable_level == "Adults":
        printDebug.debug("OK to display")
        return True

    content_map = { 'Kids' : 0 ,
                    'Teens' : 1 ,
                    'Adults' : 2 }

    rating_map= { 'G' : 0 ,       # MPAA Kids
                  'PG' : 0 ,      # MPAA Kids
                  'PG-13' : 1 ,   # MPAA Teens
                  'R' : 2 ,       # MPAA Adults
                  'NC-17' : 2 ,   # MPAA Adults
                  'NR' : 2 ,      # MPAA Adults
                  'Unrated' : 2 , # MPAA Adults

                  'U' : 0 ,       # BBFC Kids
                  'PG' : 0 ,      # BBFC Kids
                  '12' : 1 ,      # BBFC Teens
                  '12A' : 1 ,     # BBFC Teens
                  '15' : 1 ,      # BBFC Teens
                  '18' : 2 ,      # BBFC Adults
                  'R18' : 2 ,     # BBFC Adults

                  'E' : 0 ,       #ACB Kids (hopefully)
                  'G' : 0 ,       #ACB Kids
                  'PG' : 0 ,      #ACB Kids
                  'M' : 1 ,       #ACB Teens
                  'MA15+' : 2 ,   #ADC Adults
                  'R18+' : 2 ,    #ACB Adults
                  'X18+' : 2 ,    #ACB Adults

                  'TV-Y'  : 0 ,   # US TV - Kids
                  'TV-Y7' : 0 ,   # US TV - Kids
                  'TV -G' : 0 ,   # Us TV - kids
                  'TV-PG' : 1 ,   # US TV - Teens
                  'TV-14' : 1 ,   # US TV - Teens
                  'TV-MA' : 2 ,   # US TV - Adults

                  'G' :  0 ,      # CAN - kids
                  'PG' : 0 ,      # CAN - kids
                  '14A' : 1 ,     # CAN - teens
                  '18A' : 2 ,     # CAN - Adults
                  'R' : 2 ,       # CAN - Adults
                  'A' : 2 }       # CAN - Adults

    if content_level is None or content_level == "None":
        printDebug.debug("Setting [None] rating as %s" % ( __settings__.getSetting('contentNone') , ))
        if content_map[__settings__.getSetting('contentNone')] <= content_map[acceptable_level]:
            printDebug.debug("OK to display")
            return True
    else:
        try:
            if rating_map[content_level] <= content_map[acceptable_level]:
                printDebug.debug("OK to display")
                return True
        except:
            print "Unknown rating flag [%s] whilst lookuing for [%s] - will filter for now, but needs to be added" % (content_level, acceptable_level)

    printDebug.debug("NOT OK to display")
    return False

def shelf( server_list=None ):
    #Gather some data and set the window properties
    printDebug.debug("== ENTER ==")

    if (__settings__.getSetting('movieShelf') == "false" and __settings__.getSetting('tvShelf') == "false" and\
                    __settings__.getSetting('musicShelf') == "false") or __settings__.getSetting('homeshelf') == '3':
        printDebug.debug("Disabling all shelf items")
        clearShelf()
        return

    #Get the global host variable set in settings
    WINDOW = xbmcgui.Window( 10000 )

    movieCount=1
    seasonCount=1
    musicCount=1
    added_list={}    
    direction=True
    full_count=0
    
    if server_list is None:
        server_list=plex_network.get_server_list()

    if server_list == {}:
        xbmc.executebuiltin("XBMC.Notification(Unable to see any media servers,)")
        clearShelf(0,0,0)
        return

    randomNumber=str(random.randint(1000000000,9999999999))
        
    for server_details in server_list():

        if server_details.is_secondary() or not server_details.is_owned():
            continue
            
        if __settings__.getSetting('homeshelf') == '0' or __settings__.getSetting('homeshelf') == '2':
            tree=server_details.get_server_recentlyadded()
        else:
            direction=False
            tree=server_details.get_server_ondeck()

        if tree is None:
            xbmc.executebuiltin("XBMC.Notification(Unable to contact server: %s,)" % server_details.get_name() )
            clearShelf()
            return

        for eachitem in tree:

            if direction:
                added_list[int(eachitem.get('addedAt',0))] = (eachitem, server_details )
            else:
                added_list[full_count] = (eachitem, server_details)
                full_count += 1

    library_filter = __settings__.getSetting('libraryfilter')
    acceptable_level = __settings__.getSetting('contentFilter')

    #For each of the servers we have identified
    for media, server in sorted(added_list, reverse=direction):

        if media.get('type',None) == "movie":

            title_name=media.get('title','Unknown').encode('UTF-8')

            printDebug.debug("Found a recent movie entry: [%s]" % title_name )

            if __settings__.getSetting('movieShelf') == "false":
                WINDOW.clearProperty("Plexbmc.LatestMovie.1.Path" )
                continue

            if not displayContent( acceptable_level , media.get('contentRating') ):
                continue

            if media.get('librarySectionID') == library_filter:
                printDebug.debug("SKIPPING: Library Filter match: %s = %s " % (library_filter, media.get('librarySectionID')))
                continue

            title_url="plugin://plugin.video.plexbmc?url=%s&mode=%s&t=%s" % ( getLinkURL(server.get_url_location(),media,server), _MODE_PLAYSHELF, randomNumber)
            title_thumb=getThumb(media,server)

            WINDOW.setProperty("Plexbmc.LatestMovie.%s.Path" % movieCount, title_url)
            WINDOW.setProperty("Plexbmc.LatestMovie.%s.Title" % movieCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestMovie.%s.Thumb" % movieCount, title_thumb)

            movieCount += 1

        elif media.get('type',None) == "season":

            printDebug.debug("Found a recent season entry [%s]" % ( media.get('parentTitle','Unknown').encode('UTF-8') , ))

            if __settings__.getSetting('tvShelf') == "false":
                WINDOW.clearProperty("Plexbmc.LatestEpisode.1.Path" )
                continue

            title_name=media.get('parentTitle','Unknown').encode('UTF-8')
            title_url="ActivateWindow(VideoLibrary, plugin://plugin.video.plexbmc?url=%s&mode=%s, return)" % ( getLinkURL(server.get_url_location(),media,server), _MODE_TVEPISODES)
            title_thumb=getThumb(media,server)

            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.Path" % seasonCount, title_url )
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeTitle" % seasonCount, '')
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeSeason" % seasonCount, media.get('title','').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.ShowTitle" % seasonCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.Thumb" % seasonCount, title_thumb)
            seasonCount += 1

        elif media.get('type') == "album":

            if __settings__.getSetting('musicShelf') == "false":
                WINDOW.clearProperty("Plexbmc.LatestAlbum.1.Path" )
                continue
            
            printDebug.debug("Found a recent album entry")

            title_name=media.get('parentTitle','Unknown').encode('UTF-8')
            title_url="ActivateWindow(MusicFiles, plugin://plugin.video.plexbmc?url=%s&mode=%s, return)" % ( getLinkURL(server.get_url_location(),media,server), _MODE_TRACKS)
            title_thumb=getThumb(media,server)

            WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Path" % musicCount, title_url )
            WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Title" % musicCount, media.get('title','Unknown').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Artist" % musicCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Thumb" % musicCount, title_thumb)
            musicCount += 1

        elif media.get('type',None) == "episode":

            title_name=media.get('title','Unknown').encode('UTF-8')
            printDebug.debug("Found an onDeck episode entry [%s]" % title_name)

            if __settings__.getSetting('tvShelf') == "false":
                WINDOW.clearProperty("Plexbmc.LatestEpisode.1.Path" )
                continue

            title_url="PlayMedia(plugin://plugin.video.plexbmc?url=%s&mode=%s%s)" % ( getLinkURL(server.get_url_location(),media,server), _MODE_PLAYSHELF)
            title_thumb=server.get_formatted_url(media.get('grandparentThumb',''))

            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.Path" % seasonCount, title_url )
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeTitle" % seasonCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeSeason" % seasonCount, media.get('grandparentTitle','Unknown').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.ShowTitle" % seasonCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.Thumb" % seasonCount, title_thumb)
            seasonCount += 1

        printDebug.debug(" Building Recent window title: %s\n        Building Recent window url: %s\n        Building Recent window thumb: %s" % (title_name, title_url, title_thumb))
     
    clearShelf( movieCount, seasonCount, musicCount)

def clearShelf (movieCount=0, seasonCount=0, musicCount=0, photoCount=0):
    #Clear out old data
    WINDOW = xbmcgui.Window( 10000 )
    printDebug.debug("Clearing unused properties")

    try:
        for i in range(movieCount, 50+1):
            WINDOW.clearProperty("Plexbmc.LatestMovie.%s.Path"   % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestMovie.%s.Title"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestMovie.%s.Year"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestMovie.%s.Rating"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestMovie.%s.Duration"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestMovie.%s.Thumb"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestMovie.%s.uuid"  % ( i ) )
        printDebug.debug("Done clearing movies")
    except: pass

    try:
        for i in range(seasonCount, 50+1):
            WINDOW.clearProperty("Plexbmc.LatestEpisode.%s.Path"           % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestEpisode.%s.EpisodeTitle"   % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestEpisode.%s.EpisodeSeason"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestEpisode.%s.ShowTitle"      % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestEpisode.%s.Thumb"          % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestEpisode.%s.uuid"  % ( i ) )
        printDebug.debug("Done clearing tv")
    except: pass

    try:
        for i in range(musicCount, 25+1):
            WINDOW.clearProperty("Plexbmc.LatestAlbum.%s.Path"   % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestAlbum.%s.Title"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestAlbum.%s.Artist" % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestAlbum.%s.Thumb"  % ( i ) )
        printDebug.debug("Done clearing music")
    except: pass

    try:
        for i in range(photoCount, 25+1):
            WINDOW.clearProperty("Plexbmc.LatestPhoto.%s.Path"   % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestPhoto.%s.Title"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestPhoto.%s.Thumb"  % ( i ) )
        printDebug.debug("Done clearing photos")
    except: pass

    return

def clearOnDeckShelf (movieCount=0, seasonCount=0):
    #Clear out old data
    WINDOW = xbmcgui.Window( 10000 )
    printDebug.debug("Clearing unused On Deck properties")

    try:
        for i in range(movieCount, 60+1):
            WINDOW.clearProperty("Plexbmc.OnDeckMovie.%s.Path"   % ( i ) )
            WINDOW.clearProperty("Plexbmc.OnDeckMovie.%s.Title"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.OnDeckMovie.%s.Thumb"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.OnDeckMovie.%s.Rating"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.OnDeckMovie.%s.Duration"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.OnDeckMovie.%s.Year"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.OnDeckMovie.%s.uuid"  % ( i ) )
        printDebug.debug("Done clearing On Deck movies")
    except: pass

    try:
        for i in range(seasonCount, 60+1):
            WINDOW.clearProperty("Plexbmc.OnDeckEpisode.%s.Path"           % ( i ) )
            WINDOW.clearProperty("Plexbmc.OnDeckEpisode.%s.EpisodeTitle"   % ( i ) )
            WINDOW.clearProperty("Plexbmc.OnDeckEpisode.%s.EpisodeSeason"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.OnDeckEpisode.%s.ShowTitle"      % ( i ) )
            WINDOW.clearProperty("Plexbmc.OnDeckEpisode.%s.Thumb"          % ( i ) )
            WINDOW.clearProperty("Plexbmc.OnDeckEpisode.%s.uuid"  % ( i ) )
        printDebug.debug("Done clearing On Deck tv")
    except: pass


    return

def shelfChannel(server_list = None):
    #Gather some data and set the window properties
    printDebug.debug("== ENTER ==")
    
    if __settings__.getSetting('channelShelf') == "false" or __settings__.getSetting('homeshelf') == '3':
        printDebug.debug("Disabling channel shelf")
        clearChannelShelf()
        return
        
    #Get the global host variable set in settings
    WINDOW = xbmcgui.Window( 10000 )

    channelCount=1
    
    if server_list is None:
        server_list=plex_network.get_server_list()
    
    if not server_list:
        xbmc.executebuiltin("XBMC.Notification(Unable to see any media servers,)")
        clearChannelShelf()
        return
    
    for server_details in server_list:

        if server_details.is_secondary() or not server_details.is_owned():
            continue
        
        if __settings__.getSetting('channelShelf') == "false" or __settings__.getSetting('homeshelf') == '3':
            WINDOW.clearProperty("Plexbmc.LatestChannel.1.Path" )
            return

        tree=server_details.get_channel_recentlyviewed()
        if tree is None:
            xbmc.executebuiltin("XBMC.Notification(Unable to contact server: %s, )" % server_details.get_name())
            clearChannelShelf(0)
            return

        #For each of the servers we have identified
        for media in tree:

            printDebug.debug("Found a recent channel entry")
            suffix=media.get('key').split('/')[1]

            if suffix == "photos":
                mode=_MODE_PHOTOS
                channel_window = "Pictures"

            elif suffix == "video":
                mode=_MODE_PLEXPLUGINS
                channel_window="VideoLibrary"

            elif suffix == "music":
                mode=_MODE_MUSIC
                channel_window="MusicFiles"

            else:
                mode=_MODE_GETCONTENT
                channel_window="VideoLibrary"

            c_url="ActivateWindow(%s, plugin://plugin.video.plexbmc?url=%s&mode=%s)" % ( channel_window, getLinkURL(server_details.get_url_location(),media,server_details), mode)
            pms_thumb = str(media.get('thumb', ''))

            if pms_thumb.startswith('/'):
                c_thumb = server_details.get_formatted_url(pms_thumb)

            else:
                c_thumb = pms_thumb

            WINDOW.setProperty("Plexbmc.LatestChannel.%s.Path" % channelCount, c_url)
            WINDOW.setProperty("Plexbmc.LatestChannel.%s.Title" % channelCount, media.get('title', 'Unknown'))
            WINDOW.setProperty("Plexbmc.LatestChannel.%s.Thumb" % channelCount, c_thumb)

            channelCount += 1

            printDebug.debug("Building Recent window title: %s\n      Building Recent window url: %s\n      Building Recent window thumb: %s" % (media.get('title', 'Unknown'),c_url,c_thumb))

    clearChannelShelf(channelCount)        
    return
    
def clearChannelShelf (channelCount=0):
            
    WINDOW = xbmcgui.Window( 10000 )
        
    try:
        for i in range(channelCount, 30+1):
            WINDOW.clearProperty("Plexbmc.LatestChannel.%s.Path"   % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestChannel.%s.Title"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.LatestChannel.%s.Thumb"  % ( i ) )
        printDebug.debug("Done clearing channels")
    except: pass

    return

def clearQueueShelf (queueCount=0):

    WINDOW = xbmcgui.Window( 10000 )

    try:
        for i in range(queueCount, 15+1):
            WINDOW.clearProperty("Plexbmc.Queue.%s.Path"   % ( i ) )
            WINDOW.clearProperty("Plexbmc.Queue.%s.Title"  % ( i ) )
            WINDOW.clearProperty("Plexbmc.Queue.%s.Thumb"  % ( i ) )
        printDebug.debug("Done clearing Queue shelf")
    except: pass

    return

def myPlexQueue():
    printDebug.debug("== ENTER ==")

    if __settings__.getSetting('myplex_user') == '':
        xbmc.executebuiltin("XBMC.Notification(myplex not configured,)")
        return

    tree=plex_network.get_myplex_queue()

    PlexPlugins('http://my.plexapp.com/playlists/queue/all', tree)
    return

def libraryRefresh( server_uuid , section_id):
    printDebug.debug("== ENTER ==")
    
    server=plex_network.get_server_from_uuid(server_uuid)
    server.refresh_section(section_id)
    
    printDebug.info("Library refresh requested")
    xbmc.executebuiltin("XBMC.Notification(\"PleXBMC\",Library Refresh started,100)")
    return

def watched( server_uuid, metadata_id, watched='watch' ):
    printDebug.debug("== ENTER ==")

    server=plex_network.get_server_from_uuid(server_uuid)

    if watched == 'watch':
        printDebug.info("Marking %s as watched" % metadata_id)
        server.mark_item_watched(metadata_id)
    else:
        printDebug.info("Marking %s as unwatched" % metadata_id)
        server.mark_item_unwatched(metadata_id)

    xbmc.executebuiltin("Container.Refresh")

    return

def deleteMedia( server_uuid, metadata_id ):
    printDebug.debug("== ENTER ==")
    printDebug.info("Deleting media at: %s" % metadata_id)

    return_value = xbmcgui.Dialog().yesno("Confirm file delete?","Delete this item? This action will delete media and associated data files.")

    if return_value:
        printDebug.debug("Deleting....")
        server=plex_network.get_server_from_uuid(server_uuid)
        server.delete_metadata(metadata_id)
        xbmc.executebuiltin("Container.Refresh")

    return True
        
def alterSubs ( server_uuid, metadata_id ):
    '''
        Display a list of available Subtitle streams and allow a user to select one.
        The currently selected stream will be annotated with a *
    '''
    printDebug.debug("== ENTER ==")

    server = plex_network.get_server_from_uuid(server_uuid)
    tree = server.get_metadata(metadata_id)
    
    sub_list=['']
    display_list=["None"]
    fl_select=False
    for parts in tree.getiterator('Part'):

        part_id=parts.get('id')

        for streams in parts:

            if streams.get('streamType','') == "3":

                stream_id=streams.get('id')
                lang=streams.get('languageCode',"Unknown").encode('utf-8')
                printDebug.debug("Detected Subtitle stream [%s] [%s]" % ( stream_id, lang ) )

                if streams.get('format',streams.get('codec')) == "idx":
                    printDebug.debug("Stream: %s - Ignoring idx file for now" % stream_id)
                    continue
                else:
                    sub_list.append(stream_id)

                    if streams.get('selected',None) == '1':
                        fl_select=True
                        language=streams.get('language','Unknown')+"*"
                    else:
                        language=streams.get('language','Unknown')

                    display_list.append(language)
        break

    if not fl_select:
        display_list[0]=display_list[0]+"*"

    subScreen = xbmcgui.Dialog()
    result = subScreen.select('Select subtitle',display_list)
    if result == -1:
        return False

    printDebug.debug("User has selected stream %s" % sub_list[result])
    server.set_subtitle_stream(part_id,  sub_list[result])

    return True

def alterAudio ( server_uuid, metadata_id ):
    '''
        Display a list of available audio streams and allow a user to select one.
        The currently selected stream will be annotated with a *
    '''
    printDebug.debug("== ENTER ==")

    server = plex_network.get_server_from_uuid(server_uuid)
    tree = server.get_metadata(metadata_id)
    
    audio_list=[]
    display_list=[]
    for parts in tree.getiterator('Part'):

        part_id=parts.get('id')

        for streams in parts:

            if streams.get('streamType','') == "2":

                stream_id=streams.get('id')
                audio_list.append(stream_id)
                lang=streams.get('languageCode', "Unknown")

                printDebug.debug("Detected Audio stream [%s] [%s] " % ( stream_id, lang))

                if streams.get('channels','Unknown') == '6':
                    channels="5.1"
                elif streams.get('channels','Unknown') == '7':
                    channels="6.1"
                elif streams.get('channels','Unknown') == '2':
                    channels="Stereo"
                else:
                    channels=streams.get('channels','Unknown')

                if streams.get('codec','Unknown') == "ac3":
                    codec="AC3"
                elif streams.get('codec','Unknown') == "dca":
                    codec="DTS"
                else:
                    codec=streams.get('codec','Unknown')

                language="%s (%s %s)" % ( streams.get('language','Unknown').encode('utf-8') , codec, channels )

                if streams.get('selected') == '1':
                    language=language+"*"

                display_list.append(language)
        break

    audioScreen = xbmcgui.Dialog()
    result = audioScreen.select('Select audio',display_list)
    if result == -1:
        return False

    printDebug.debug("User has selected stream %s" % audio_list[result])

    server.set_audio_stream(part_id, audio_list[result])

    return True

def setWindowHeading(tree) :
    WINDOW = xbmcgui.Window( xbmcgui.getCurrentWindowId() )
    try:
        WINDOW.setProperty("heading", tree.get('title1'))
    except:
        WINDOW.clearProperty("heading")
    try:
        WINDOW.setProperty("heading2", tree.get('title2'))
    except:
        WINDOW.clearProperty("heading2")

def setMasterServer () :
    printDebug.debug("== ENTER ==")

    servers=getMasterServer(True)
    printDebug.debug(str(servers))
    
    current_master=settings.get_setting('masterserver')
    
    displayList=[]
    for address in servers:
        found_server = address.get_name()
        if found_server == current_master:
            found_server = found_server+"*"
        displayList.append(found_server)
    
    audioScreen = xbmcgui.Dialog()
    result = audioScreen.select('Select master server', displayList)
    if result == -1:
        return False

    printDebug.debug("Setting master server to: %s" % servers[result].get_name() )
    settings.update_master_server(servers[result].get_name() )
    return

def displayServers( url ):
    printDebug.debug("== ENTER ==")
    type=url.split('/')[2]
    printDebug.debug("Displaying entries for %s" % type)
    Servers = plex_network.get_server_list()
    Servers_list=len(Servers)

    #For each of the servers we have identified
    for mediaserver in Servers:

        if mediaserver.is_secondary():
            continue
    
        details={'title' : mediaserver.get_name() }

        if mediaserver.get_token():
            extraData={'token' : mediaserver.get_token() }
        else:
            extraData={}

        if type == "video":
            extraData['mode']=_MODE_PLEXPLUGINS
            s_url='%s%s' % ( mediaserver.get_url_location(), '/video' )
            if Servers_list == 1:
                PlexPlugins(s_url+getAuthDetails(extraData,prefix="?"))
                return

        elif type == "online":
            extraData['mode']=_MODE_PLEXONLINE
            s_url='%s%s' % ( mediaserver.get_url_location() , '/system/plexonline')
            if Servers_list == 1:
                plexOnline(s_url+getAuthDetails(extraData,prefix="?"))
                return

        elif type == "music":
            extraData['mode']=_MODE_MUSIC
            s_url='%s%s' % ( mediaserver.get_url_location(), '/music' )
            if Servers_list == 1:
                music(s_url+getAuthDetails(extraData,prefix="?"))
                return

        elif type == "photo":
            extraData['mode']=_MODE_PHOTOS
            s_url='%s%s' % ( mediaserver.get_url_location(), '/photos' )
            if Servers_list == 1:
                photo(s_url+getAuthDetails(extraData,prefix="?"))
                return

        addGUIItem(s_url, details, extraData )

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=True)
    
##So this is where we really start the plugin.

__settings__ = GLOBAL_SETUP['__settings__']

printDebug=printDebug("PleXBMC")

print "PleXBMC -> Running PleXBMC: %s " % GLOBAL_SETUP['__version__']

wake_servers()

if settings.get_debug() >= printDebug.DEBUG_INFO:
    print "PleXBMC -> Script argument is %s" % sys.argv
    print "PleXBMC -> Running Python: %s" % str(sys.version_info)
    print "PleXBMC -> CWD is set to: %s" % GLOBAL_SETUP['__cwd__']
    print "PleXBMC -> Platform: %s" % GLOBAL_SETUP['platform']
    print "PleXBMC -> Setting debug: %s" % printDebug.get_name(settings.get_debug())
    print "PleXBMC -> FullRes Thumbs are set to: %s" % settings.get_setting('fullres_thumbnails')
    print "PleXBMC -> Settings streaming: %s" % settings.get_stream()
    print "PleXBMC -> Setting filter menus: %s" % settings.get_setting('secondary')
    print "PleXBMC -> Flatten is: %s" % settings.get_setting('flatten')
    if settings.get_setting('streamControl') == _SUB_AUDIO_XBMC_CONTROL:
        print "PleXBMC -> Setting stream Control to : XBMC CONTROL"
    elif settings.get_setting('streamControl') == _SUB_AUDIO_PLEX_CONTROL:
        print "PleXBMC -> Setting stream Control to : PLEX CONTROL"
    elif settings.get_setting('streamControl') == _SUB_AUDIO_NEVER_SHOW:
        print "PleXBMC -> Setting stream Control to : NEVER SHOW"

    print "PleXBMC -> Force DVD playback: %s" % settings.get_setting('forcedvd')
    print "PleXBMC -> SMB IP Override: %s" % settings.get_setting('nasoverride')
    if settings.get_setting('nasoverride') and not settings.get_setting('nasoverrideip'):
        print "PleXBMC -> No NAS IP Specified.  Ignoring setting"
    else:
        print "PleXBMC -> NAS IP: " + settings.get_setting('nasoverrideip')
else:
    print "PleXBMC -> Debug is turned off.  Running silent"

g_thumb = "special://home/addons/plugin.video.plexbmc/resources/thumb.png"

#Set up holding variable for session ID
global g_sessionID
g_sessionID=None

pluginhandle=0
plex_network=plex.Plex(load=True)

def start_plexbmc():
    try:
        params=get_params(sys.argv[2])
    except:
        params={}

    #Now try and assign some data to them
    param_url=params.get('url',None)

    if param_url and ( param_url.startswith('http') or param_url.startswith('file') ):
            param_url = urllib.unquote(param_url)

    param_name=urllib.unquote_plus(params.get('name',""))
    mode=int(params.get('mode',-1))
    play_transcode=True if int(params.get('transcode',0)) == 1 else False
    param_identifier=params.get('identifier',None)
    param_indirect=params.get('indirect',None)
    force=params.get('force')


    #Populate Skin variables
    if str(sys.argv[1]) == "skin":
        try:
            type=sys.argv[2]
        except:
            type=None
        skin(type=type)

    elif str(sys.argv[1]) == "amberskin":
        amberskin()
     
    #Populate recently/on deck shelf items 
    elif str(sys.argv[1]) == "shelf":
        shelf()

    #Populate channel recently viewed items    
    elif str(sys.argv[1]) == "channelShelf":
        shelfChannel()
        
    #Send a library update to Plex    
    elif sys.argv[1] == "update":
        server_uuid=sys.argv[2]
        section_id=sys.argv[3]
        libraryRefresh(server_uuid, section_id)
        
    #Mark an item as watched/unwatched in plex    
    elif sys.argv[1] == "watch":
        server_uuid=sys.argv[2]
        metadata_id=sys.argv[3]
        watch_status=sys.argv[4]
        watched(server_uuid, metadata_id, watch_status )
        
    #Open the add-on settings page, then refresh plugin
    elif sys.argv[1] == "setting":
        settings.openSettings()
        WINDOW = xbmcgui.getCurrentWindowId()
        if WINDOW == 10000:
            printDebug.debug("Currently in home - refreshing to allow new settings to be taken")
            xbmc.executebuiltin("XBMC.ActivateWindow(Home)")
                  
    #nt currently used              
    elif sys.argv[1] == "refreshplexbmc":
        plex_network.discover()
        server_list = plex_network.get_server_list()
        skin(server_list)
        shelf(server_list)
        shelfChannel(server_list)

    #delete media from PMS    
    elif sys.argv[1] == "delete":
        server_uuid=sys.argv[2]
        metadata_id=sys.argv[3]
        deleteMedia(server_uuid, metadata_id)

    #Refresh the current XBMC listing    
    elif sys.argv[1] == "refresh":
        xbmc.executebuiltin("Container.Refresh")
        
    #Display subtitle selection screen    
    elif sys.argv[1] == "subs":
        server_uuid=sys.argv[2]
        metadata_id=sys.argv[3]
        alterSubs(server_uuid, metadata_id)
        
    #Display audio streanm selection screen    
    elif sys.argv[1] == "audio":
        server_uuid=sys.argv[2]
        metadata_id=sys.argv[3]
        alterAudio(server_uuid, metadata_id)
        
    #Allow a mastre server to be selected (for myplex queue)    
    elif sys.argv[1] == "master":
        setMasterServer()

    #Delete cache and refresh it    
    elif str(sys.argv[1]) == "cacherefresh":
        plex_network.delete_cache()
        xbmc.executebuiltin("ReloadSkin()")

    #else move to the main code    
    else:

        global pluginhandle
        pluginhandle = int(sys.argv[1])

        WINDOW = xbmcgui.Window( xbmcgui.getCurrentWindowId() )
        WINDOW.clearProperty("heading")
        WINDOW.clearProperty("heading2")

        if settings.get_debug() >= printDebug.DEBUG_INFO:
            print "PleXBMC -> Mode: %s " % mode
            print "PleXBMC -> URL: %s" % param_url
            print "PleXBMC -> Name: %s" % param_name
            print "PleXBMC -> identifier: %s" % param_identifier

        #Run a function based on the mode variable that was passed in the URL
        if ( mode == None ) or ( param_url == None ) or ( len(param_url)<1 ):
            displaySections()

        elif mode == _MODE_GETCONTENT:
            getContent(param_url)

        elif mode == _MODE_TVSHOWS:
            TVShows(param_url)

        elif mode == _MODE_MOVIES:
            Movies(param_url)

        elif mode == _MODE_ARTISTS:
            artist(param_url)

        elif mode == _MODE_TVSEASONS:
            TVSeasons(param_url)

        elif mode == _MODE_PLAYLIBRARY:
            playLibraryMedia(param_url,force=force, override=play_transcode)

        elif mode == _MODE_PLAYSHELF:
            playLibraryMedia(param_url,full_data=True, shelf=True)

        elif mode == _MODE_TVEPISODES:
            TVEpisodes(param_url)

        elif mode == _MODE_PLEXPLUGINS:
            PlexPlugins(param_url)

        elif mode == _MODE_PROCESSXML:
            processXML(param_url)

        elif mode == _MODE_BASICPLAY:
            PLAY(param_url)

        elif mode == _MODE_ALBUMS:
            albums(param_url)

        elif mode == _MODE_TRACKS:
            tracks(param_url)

        elif mode == _MODE_PHOTOS:
            photo(param_url)

        elif mode == _MODE_MUSIC:
            music(param_url)

        elif mode == _MODE_VIDEOPLUGINPLAY:
            videoPluginPlay(param_url,param_identifier,param_indirect)

        elif mode == _MODE_PLEXONLINE:
            plexOnline(param_url)

        elif mode == _MODE_CHANNELINSTALL:
            install(param_url,param_name)

        elif mode == _MODE_CHANNELVIEW:
            channelView(param_url)

        elif mode == _MODE_PLAYLIBRARY_TRANSCODE:
            playLibraryMedia(param_url,override=True)

        elif mode == _MODE_MYPLEXQUEUE:
            myPlexQueue()

        elif mode == _MODE_CHANNELSEARCH:
            channelSearch( param_url, params.get('prompt') )

        elif mode == _MODE_CHANNELPREFS:
            channelSettings ( param_url, params.get('id') )

        elif mode == _MODE_SHARED_MOVIES:
            displaySections(filter="movies", display_shared=True)

        elif mode == _MODE_SHARED_SHOWS:
            displaySections(filter="tvshows", display_shared=True)
            
        elif mode == _MODE_SHARED_PHOTOS:
            displaySections(filter="photos", display_shared=True)
            
        elif mode == _MODE_SHARED_MUSIC:
            displaySections(filter="music", display_shared=True)

        elif mode == _MODE_SHARED_ALL:
            displaySections(display_shared=True)
            
        elif mode == _MODE_DELETE_REFRESH:
            plex_network.delete_cache()
            xbmc.executebuiltin("Container.Refresh")

        elif mode == _MODE_PLAYLISTS:
            processXML(param_url)
        
        elif mode == _MODE_DISPLAYSERVERS:
            displayServers(param_url)


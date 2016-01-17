"""
    @document   : plexbmc.py
    @package    : PleXBMC add-on
    @author     : Hippojay (aka Dave Hawes-Johnson)
    @copyright  : 2011-2015, Hippojay
    @version    : 4.0 (Helix)

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
"""

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
from resources.lib.common import *  # Needed first to setup import locations
from resources.lib.plex import plex


def select_media_type(part_data, server, dvdplayback=False):
    stream = part_data['key']
    file = part_data['file']

    if (file is None) or (settings.get_stream() == "1"):
        log_print.debug("Selecting stream")
        return server.get_formatted_url(stream)

    # First determine what sort of 'file' file is

    if file[0:2] == "\\\\":
        log_print.debug("Detected UNC source file")
        type = "UNC"
    elif file[0:1] == "/" or file[0:1] == "\\":
        log_print.debug("Detected unix source file")
        type = "nixfile"
    elif file[1:3] == ":\\" or file[1:2] == ":/":
        log_print.debug("Detected windows source file")
        type = "winfile"
    else:
        log_print.debug("Unknown file type source: %s" % file)
        type = None

    # 0 is auto select.  basically check for local file first, then stream if not found
    if settings.get_stream() == "0":
        # check if the file can be found locally
        if type == "nixfile" or type == "winfile":
            log_print.debug("Checking for local file")
            try:
                exists = open(file, 'r')
                log_print.debug("Local file found, will use this")
                exists.close()
                return "file:%s" % file
            except:
                pass

        log_print.debug("No local file")
        if dvdplayback:
            log_print.debug("Forcing SMB for DVD playback")
            settings.set_stream("2")
        else:
            return server.get_formatted_url(stream)

    # 2 is use SMB
    elif settings.get_stream() == "2" or settings.get_stream() == "3":

        file = urllib.unquote(file)
        if settings.get_stream() == "2":
            protocol = "smb"
        else:
            protocol = "afp"

        log_print.debug("Selecting smb/unc")
        if type == "UNC":
            filelocation = "%s:%s" % (protocol, file.replace("\\", "/"))
        else:
            # Might be OSX type, in which case, remove Volumes and replace with server
            server = server.get_location().split(':')[0]
            loginstring = ""

            if settings.get_setting('nasoverride'):
                if settings.get_setting('nasoverrideip'):
                    server = settings.get_setting('nasoverrideip')
                    log_print.debug("Overriding server with: %s" % server)

                if settings.get_setting('nasuserid'):
                    loginstring = "%s:%s@" % (settings.get_setting('nasuserid'), settings.get_setting('naspass'))
                    log_print.debug("Adding AFP/SMB login info for user: %s" % settings.get_setting('nasuserid'))

            if file.find('Volumes') > 0:
                filelocation = "%s:/%s" % (protocol, file.replace("Volumes", loginstring+server))
            else:
                if type == "winfile":
                    filelocation = ("%s://%s%s/%s" % (protocol, loginstring, server, file[3:].replace("\\", "/")))
                else:
                    # else assume its a file local to server available over smb/samba.  Add server name to file path.
                    filelocation = "%s://%s%s%s" % (protocol, loginstring, server, file)

        if settings.get_setting('nasoverride') and settings.get_setting('nasroot'):
            # Re-root the file path
            log_print.debug("Altering path %s so root is: %s" % (filelocation, settings.get_setting('nasroot')))
            if '/'+settings.get_setting('nasroot')+'/' in filelocation:
                components = filelocation.split('/')
                index = components.index(settings.get_setting('nasroot'))
                for i in range(3, index):
                    components.pop(3)
                filelocation = '/'.join(components)
    else:
        log_print.debug("No option detected, streaming is safest to choose")
        filelocation = server.get_formatted_url(stream)

    log_print.debug("Returning URL: %s " % filelocation)
    return filelocation


def add_item_to_gui(url, details, extra_data, context=None, folder=True):

    log_print.debug("Adding Dir for [%s]\n"
                    "      Passed details: %s\n"
                    "      Passed extraData: %s" % (details.get('title', 'Unknown'), details, extra_data))

    # Create the URL to pass to the item
    if not folder and extra_data['type'] == "image":
        link_url = url
    elif url.startswith('http') or url.startswith('file'):
        link_url = "%s?url=%s&mode=%s" % (sys.argv[0], urllib.quote(url), extra_data.get('mode', 0))
    else:
        link_url = "%s?url=%s&mode=%s" % (sys.argv[0], url, extra_data.get('mode', 0))

    if extra_data.get('parameters'):
        for argument, value in extra_data.get('parameters').items():
            link_url = "%s&%s=%s" % (link_url, argument, urllib.quote(value))

    log_print.debug("URL to use for listing: %s" % link_url)

    liz = xbmcgui.ListItem(details.get('title', 'Unknown'), thumbnailImage=extra_data.get('thumb', GENERIC_THUMBNAIL))

    log_print.debug("Setting thumbnail as %s" % extra_data.get('thumb', GENERIC_THUMBNAIL))

    # Set the properties of the item, such as summary, name, season, etc
    liz.setInfo(type=extra_data.get('type', 'Video'), infoLabels=details)

    # Music related tags
    if extra_data.get('type', '').lower() == "music":
        liz.setProperty('Artist_Genre', details.get('genre', ''))
        liz.setProperty('Artist_Description', extra_data.get('plot', ''))
        liz.setProperty('Album_Description', extra_data.get('plot', ''))

    # For all end items    
    if not folder:
        liz.setProperty('IsPlayable', 'true')

        if extra_data.get('type', 'video').lower() == "video":
            liz.setProperty('TotalTime', str(extra_data.get('duration')))
            liz.setProperty('ResumeTime', str(extra_data.get('resume')))

            if not settings.get_setting('skipflags'):
                log_print.debug("Setting VrR as : %s" % extra_data.get('VideoResolution', ''))
                liz.setProperty('VideoResolution', extra_data.get('VideoResolution', ''))
                liz.setProperty('VideoCodec', extra_data.get('VideoCodec', ''))
                liz.setProperty('AudioCodec', extra_data.get('AudioCodec', ''))
                liz.setProperty('AudioChannels', extra_data.get('AudioChannels', ''))
                liz.setProperty('VideoAspect', extra_data.get('VideoAspect', ''))

                video_codec = {}
                if extra_data.get('xbmc_VideoCodec'): video_codec['codec'] = extra_data.get('xbmc_VideoCodec')
                if extra_data.get('xbmc_VideoAspect'): video_codec['aspect'] = float(extra_data.get('xbmc_VideoAspect'))
                if extra_data.get('xbmc_height'): video_codec['height'] = int(extra_data.get('xbmc_height'))
                if extra_data.get('xbmc_width'): video_codec['width'] = int(extra_data.get('xbmc_width'))
                if extra_data.get('duration'): video_codec['duration'] = int(extra_data.get('duration'))

                audio_codec = {}
                if extra_data.get('xbmc_AudioCodec'): audio_codec['codec'] = extra_data.get('xbmc_AudioCodec')
                if extra_data.get('xbmc_AudioChannels'): audio_codec['channels'] = int(extra_data.get('xbmc_AudioChannels'))

                liz.addStreamInfo('video', video_codec)
                liz.addStreamInfo('audio', audio_codec)

    if extra_data.get('source') == 'tvshows' or extra_data.get('source') == 'tvseasons':
        # Then set the number of watched and unwatched, which will be displayed per season
        liz.setProperty('TotalEpisodes', str(extra_data['TotalEpisodes']))
        liz.setProperty('WatchedEpisodes', str(extra_data['WatchedEpisodes']))
        liz.setProperty('UnWatchedEpisodes', str(extra_data['UnWatchedEpisodes']))

        # Hack to show partial flag for TV shows and seasons
        if extra_data.get('partialTV') == 1:
            liz.setProperty('TotalTime', '100')
            liz.setProperty('ResumeTime', '50')

    # assign artwork
    fanart = extra_data.get('fanart_image', '')
    thumb = extra_data.get('thumb', '')
    banner = extra_data.get('banner', '')
    
    # tvshow poster
    season_thumb = extra_data.get('season_thumb', '')
    
    if season_thumb:
        poster = season_thumb
    else:
        poster = thumb
    
    if fanart:
        log_print.debug("Setting fan art as %s" % fanart)
        liz.setProperty('fanart_image', fanart)
    if banner:
        log_print.debug("Setting banner as %s" % banner)
        liz.setProperty('banner', '%s' % banner)
    if season_thumb:
        log_print.debug("Setting season Thumb as %s" % season_thumb)
        liz.setProperty('seasonThumb', '%s' % season_thumb)
        
    liz.setArt({"fanart": fanart, "poster": poster, "banner": banner, "thumb": thumb})
    
    if context is not None:
        if not folder and extra_data.get('type', 'video').lower() == "video":
            # Play Transcoded
            context.insert(0, ('Play Transcoded', "XBMC.PlayMedia(%s&transcode=1)" % link_url, ))
            log_print.debug("Setting transcode options to [%s&transcode=1]" % link_url)
        log_print.debug("Building Context Menus")
        liz.addContextMenuItems(context, settings.get_setting('contextreplace'))

    return xbmcplugin.addDirectoryItem(handle=pluginhandle, url=link_url, listitem=liz, isFolder=folder)


def display_sections(filter=None, display_shared=False):
    log_print.debug("== ENTER ==")
    xbmcplugin.setContent(pluginhandle, 'files')

    server_list = plex_network.get_server_list()
    log_print.debug("Using list of %s servers: %s" % (len(server_list), server_list))

    for server in server_list:

        server.discover_sections()

        for section in server.get_sections():

            if display_shared and server.is_owned():
                continue

            details = {'title': section.get_title()}

            if len(server_list) > 1:
                details['title'] = "%s: %s" % (server.get_name(), details['title'])

            extra_data = {'fanart_image': server.get_fanart(section),
                          'type'        : "Video"}

            # Determine what we are going to do process after a link selected by the user, based on the content we find

            path = section.get_path()

            if section.is_show():
                mode = MODE_TVSHOWS
                if (filter is not None) and (filter != "tvshows"):
                    continue

            elif section.is_movie():
                mode = MODE_MOVIES
                if (filter is not None) and (filter != "movies"):
                    continue

            elif section.is_artist():
                mode = MODE_ARTISTS
                if (filter is not None) and (filter != "music"):
                    continue

            elif section.is_photo():
                mode = MODE_PHOTOS
                if (filter is not None) and (filter != "photos"):
                    continue
            else:
                log_print.debug("Ignoring section %s of type %s as unable to process"
                                % (details['title'], section.get_type()))
                continue

            if settings.get_setting('secondary'):
                mode = MODE_GETCONTENT
            else:
                path = path+'/all'

            extra_data['mode'] = mode
            section_url = '%s%s' % (server.get_url_location(), path)

            if not settings.get_setting('skipcontextmenus'):
                context = [('Refresh library section', 'RunScript(plugin.video.plexbmc, update, %s, %s)'
                            % (server.get_uuid(), section.get_key()))]
            else:
                context = None

            # Build that listing..
            add_item_to_gui(section_url, details, extra_data, context)

    if display_shared:
        xbmcplugin.endOfDirectory(pluginhandle, cacheToDisc=settings.get_setting('kodicache'))
        return

    # For each of the servers we have identified            
    if plex_network.is_myplex_signedin():
        add_item_to_gui('http://myplexqueue', {'title': 'myplex Queue'}, {'type': 'Video', 'mode': MODE_MYPLEXQUEUE})

    for server in server_list:

        if server.is_offline() or server.is_secondary():
            continue

        # Plex plugin handling
        if (filter is not None) and (filter != "plugins"):
            continue

        if len(server_list) > 1:
            prefix = server.get_name()+": "
        else:
            prefix = ""

        details = {'title': prefix+"Channels"}
        extra_data = {'type': "Video"}

        extra_data['mode'] = MODE_CHANNELVIEW
        u = "%s/channels/all" % server.get_url_location()
        add_item_to_gui(u, details, extra_data)

        # Create plexonline link
        details['title'] = prefix+"Plex Online"
        extra_data['type'] = "file"
        extra_data['mode'] = MODE_PLEXONLINE

        u = "%s/system/plexonline" % server.get_url_location()
        add_item_to_gui(u, details, extra_data)

        # create playlist link
        details['title'] = prefix+"Playlists"
        extra_data['type'] = "file"
        extra_data['mode'] = MODE_PLAYLISTS

        u = "%s/playlists" % server.get_url_location()
        add_item_to_gui(u, details, extra_data)

    if plex_network.is_myplex_signedin():

        if plex_network.is_plexhome_enabled():
            details = {'title': "Switch User"}
            extra_data = {'type': 'file'}

            u = "cmd:switchuser"
            add_item_to_gui(u, details, extra_data)

        details = {'title': "Sign Out"}
        extra_data = {'type': 'file'}

        u = "cmd:signout"
        add_item_to_gui(u, details, extra_data)
    else:
        details = {'title': "Sign In"}
        extra_data = {'type': 'file'}

        u = "cmd:signintemp"
        add_item_to_gui(u, details, extra_data)

    details = {'title': "Display servers"}
    extra_data = {'type': 'file'}
    data_url = "cmd:displayservers"
    add_item_to_gui(data_url, details, extra_data)

    if settings.get_setting('cache'):
        details = {'title': "Refresh Data"}
        extra_data = {'type': "file",
                      'mode': MODE_DELETE_REFRESH}

        u = "http://nothing"
        add_item_to_gui(u, details, extra_data)

    # All XML entries have been parsed and we are ready to allow the user to browse around.  So end the screen listing.
    xbmcplugin.endOfDirectory(pluginhandle, cacheToDisc=settings.get_setting('kodicache'))


def enforce_skin_view(mode):

    '''
    Ensure that the views are consistance across plugin usage, depending
    upon view selected by user
    @input: User view selection
    @return: view id for skin
    '''

    log_print.debug("== ENTER ==")

    if not settings.get_setting('skinoverride'):
        return None

    skinname = settings.get_setting('skinname')

    current_skin_name = xbmc.getSkinDir()

    skin_map = {'2': 'skin.confluence',
                '0': 'skin.quartz',
                '1': 'skin.quartz3',
                '3': 'skin.amber',
                '4': 'skin.aeon.nox.5'}

    if skin_map[skinname] not in current_skin_name:
        log_print.debug("Do not have the correct skin [%s] selected in settings [%s] - ignoring" % (current_skin_name, skin_map[skinname]))
        return None

    if mode == "movie":
        log_print.debug("Looking for movie skin settings")
        viewname = settings.get_setting('mo_view_%s' % skinname)

    elif mode == "tv":
        log_print.debug("Looking for tv skin settings")
        viewname = settings.get_setting('tv_view_%s' % skinname)

    elif mode == "music":
        log_print.debug("Looking for music skin settings")
        viewname = settings.get_setting('mu_view_%s' % skinname)

    elif mode == "episode":
        log_print.debug("Looking for music skin settings")
        viewname = settings.get_setting('ep_view_%s' % skinname)

    elif mode == "season":
        log_print.debug("Looking for music skin settings")
        viewname = settings.get_setting('se_view_%s' % skinname)

    else:
        viewname = "None"

    log_print.debug("view name is %s" % viewname)

    if viewname == "None":
        return None

    QuartzV3_views={'List': 50,
                    'Big List': 51,
                    'MediaInfo': 52,
                    'MediaInfo 2': 54,
                    'Big Icons': 501,
                    'Icons': 53,
                    'Panel': 502,
                    'Wide': 55,
                    'Fanart 1': 57,
                    'Fanart 2': 59,
                    'Fanart 3': 500}

    Quartz_views={'List': 50,
                  'MediaInfo': 51,
                  'MediaInfo 2': 52,
                  'Icons': 53,
                  'Wide': 54,
                  'Big Icons': 55,
                  'Icons 2': 56,
                  'Panel': 57,
                  'Fanart': 58,
                  'Fanart 2': 59}

    Confluence_views={'List': 50,
                      'Big List': 51,
                      'Thumbnail': 500,
                      'Poster Wrap': 501,
                      'Fanart': 508,
                      'Media Info': 504,
                      'Media Info 2': 503,
                      'Media Info 3': 515,
                      'Wide Icons': 505}

    Amber_views = {'List': 50,
                   'Big List': 52,
                   'Panel': 51,
                   'Low List': 54,
                   'Icons': 53,
                   'Big Panel': 55,
                   'Fanart': 59}

    aeon_nox_views = {'List'      : 50,
                      'InfoWall'  : 51,
                      'Landscape' : 52,
                      'ShowCase1' : 53,
                      'ShowCase2' : 54,
                      'TriPanel'  : 55,
                      'Posters'   : 56,
                      'Shift'     : 57,
                      'BannerWall': 58,
                      'Logo'      : 59,
                      'Wall'      : 500,
                      'LowList'   : 501,
                      'Episode'   : 502,
                      'Wall'      : 503,
                      'BigList'   : 510}

    skin_list = {"0": Quartz_views,
                 "1": QuartzV3_views,
                 "2": Confluence_views,
                 "3": Amber_views,
                 "4": aeon_nox_views}

    log_print.debug("Using skin view: %s" % skin_list[skinname][viewname])

    try:
        return skin_list[skinname][viewname]
    except:
        print "PleXBMC -> skin name or view name error"
        return None


def process_movies(url, tree=None):
    log_print.debug("== ENTER ==")
    xbmcplugin.setContent(pluginhandle, 'movies')

    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE_IGNORE_THE)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_DATEADDED)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_DATE)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_VIDEO_RATING)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_VIDEO_RUNTIME)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_MPAA_RATING)

    # get the server name from the URL, which was passed via the on screen listing..

    server = plex_network.get_server_from_url(url)

    tree = get_xml(url,tree)
    if tree is None:
        return

    set_window_heading(tree)
    random_number = str(random.randint(1000000000, 9999999999))

    # Find all the video tags, as they contain the data we need to link to a file.
    start_time = time.time()
    count = 0
    for movie in tree:

        if movie.tag == "Video":
            movie_tag(url, server, tree, movie, random_number)
            count += 1

    log_print.info("PROCESS: It took %s seconds to process %s items" % (time.time()-start_time, count))
    log_print.debug("Skin override is: %s" % settings.get_setting('skinoverride'))
    view_id = enforce_skin_view('movie')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle, cacheToDisc=settings.get_setting('kodicache'))


def build_context_menu(url, item_data, server):
    context = []
    url_parts = urlparse.urlparse(url)
    section = url_parts.path.split('/')[3]
    item_id = item_data.get('ratingKey', '0')

    # Mark media unwatched
    context.append(('Mark as Unwatched', 'RunScript(plugin.video.plexbmc, watch, %s, %s, %s)' % (server.get_uuid(), item_id, 'unwatch')))
    context.append(('Mark as Watched', 'RunScript(plugin.video.plexbmc, watch, %s, %s, %s)' % (server.get_uuid(), item_id, 'watch')))
    context.append(('Rescan library section', 'RunScript(plugin.video.plexbmc, update, %s, %s)' % (server.get_uuid(), section )))
    context.append(('Delete media', "RunScript(plugin.video.plexbmc, delete, %s, %s)" % (server.get_uuid(), item_id)))
    context.append(('Reload Section', 'RunScript(plugin.video.plexbmc, refresh)'))
    context.append(('Select Audio', "RunScript(plugin.video.plexbmc, audio, %s, %s)" % (server.get_uuid(), item_id)))
    context.append(('Select Subtitle', "RunScript(plugin.video.plexbmc, subs, %s, %s)" % (server.get_uuid(), item_id)))

    log_print.debug("Using context menus: %s" % context)

    return context


def process_tvshows(url, tree=None):
    log_print.debug("== ENTER ==")
    xbmcplugin.setContent(pluginhandle, 'tvshows')
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE_IGNORE_THE)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_DATE)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_VIDEO_RATING)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_MPAA_RATING)

    # Get the URL and server name.  Get the XML and parse
    tree = get_xml(url,tree)
    if tree is None:
        return

    server = plex_network.get_server_from_url(url)

    set_window_heading(tree)
    # For each directory tag we find
    ShowTags = tree.findall('Directory')
    for show in ShowTags:

        tempgenre = []

        for child in show:
            if child.tag == "Genre":
                        tempgenre.append(child.get('tag', ''))

        watched = int(show.get('viewedLeafCount', 0))

        # Create the basic data structures to pass up
        details = {'title'     : show.get('title', 'Unknown').encode('utf-8'),
                   'sorttitle' : show.get('titleSort', show.get('title', 'Unknown')).encode('utf-8'),
                   'tvshowname': show.get('title', 'Unknown').encode('utf-8'),
                   'studio'    : show.get('studio', '').encode('utf-8'),
                   'plot'      : show.get('summary', '').encode('utf-8'),
                   'season'    : 0,
                   'episode'   : int(show.get('leafCount', 0)),
                   'mpaa'      : show.get('contentRating', ''),
                   'aired'     : show.get('originallyAvailableAt', ''),
                   'genre'     : " / ".join(tempgenre)}

        extraData = {'type'             : 'video',
                     'source'           : 'tvshows',
                     'UnWatchedEpisodes': int(details['episode']) - watched,
                     'WatchedEpisodes'  : watched,
                     'TotalEpisodes'    : details['episode'],
                     'thumb'            : get_thumb_image(show, server),
                     'fanart_image'     : get_fanart_image(show, server),
                     'banner'           : get_banner_image(show, server),
                     'key'              : show.get('key', ''),
                     'ratingKey'        : str(show.get('ratingKey', 0))}

        # Set up overlays for watched and unwatched episodes
        if extraData['WatchedEpisodes'] == 0:
            details['playcount'] = 0
        elif extraData['UnWatchedEpisodes'] == 0:
            details['playcount'] = 1
        else:
            extraData['partialTV'] = 1

        # Create URL based on whether we are going to flatten the season view
        if settings.get_setting('flatten') == "2":
            log_print.debug("Flattening all shows")
            extraData['mode'] = MODE_TVEPISODES
            u = '%s%s' % (server.get_url_location(), extraData['key'].replace("children", "allLeaves"))
        else:
            extraData['mode'] = MODE_TVSEASONS
            u = '%s%s' % (server.get_url_location(), extraData['key'])

        if not settings.get_setting('skipcontextmenus'):
            context = build_context_menu(url, extraData, server)
        else:
            context = None

        add_item_to_gui(u, details, extraData, context)

    log_print("Skin override is: %s" % settings.get_setting('skinoverride'))
    view_id = enforce_skin_view('tv')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle, cacheToDisc=settings.get_setting('kodicache'))


def process_tvseasons(url):
    log_print.debug("== ENTER ==")
    xbmcplugin.setContent(pluginhandle, 'seasons')

    # Get URL, XML and parse
    server = plex_network.get_server_from_url(url)
    tree = get_xml(url)
    if tree is None:
        return

    willFlatten=False
    if settings.get_setting('flatten') == "1":
        # check for a single season
        if int(tree.get('size',0)) == 1:
            log_print.debug("Flattening single season show")
            willFlatten=True

    sectionart = get_fanart_image(tree, server)
    banner = get_banner_image(tree, server)
    set_window_heading(tree)
    # For all the directory tags
    SeasonTags = tree.findall('Directory')
    plot = tree.get('summary','').encode('utf-8')
    for season in SeasonTags:

        if willFlatten:
            url = server.get_url_location()+season.get('key')
            process_tvepisodes(url)
            return

        if settings.get_setting('disable_all_season') and season.get('index') is None:
            continue

        watched=int(season.get('viewedLeafCount', 0))

        # Create the basic data structures to pass up
        details = {'title'     : season.get('title', 'Unknown').encode('utf-8'),
                   'tvshowname': season.get('title', 'Unknown').encode('utf-8'),
                   'sorttitle' : season.get('titleSort', season.get('title', 'Unknown')).encode('utf-8'),
                   'studio'    : season.get('studio', '').encode('utf-8'),
                   'plot'      : plot,
                   'season'    : 0,
                   'episode'   : int(season.get('leafCount', 0)),
                   'mpaa'      : season.get('contentRating', ''),
                   'aired'     : season.get('originallyAvailableAt', '')}

        if season.get('sorttitle'): details['sorttitle'] = season.get('sorttitle')

        extraData = {'type'             : 'video',
                     'source'           : 'tvseasons',
                     'TotalEpisodes'    : details['episode'],
                     'WatchedEpisodes'  : watched,
                     'UnWatchedEpisodes': details['episode'] - watched,
                     'thumb'            : get_thumb_image(season, server),
                     'fanart_image'     : get_fanart_image(season, server),
                     'banner'           : banner,
                     'key'              : season.get('key', ''),
                     'ratingKey'        : str(season.get('ratingKey', 0)),
                     'mode'             : MODE_TVEPISODES}

        if extraData['fanart_image'] == "":
            extraData['fanart_image'] = sectionart

        # Set up overlays for watched and unwatched episodes
        if extraData['WatchedEpisodes'] == 0:
            details['playcount'] = 0
        elif extraData['UnWatchedEpisodes'] == 0:
            details['playcount'] = 1
        else:
            extraData['partialTV'] = 1

        url = '%s%s' % ( server.get_url_location() , extraData['key'] )

        if not settings.get_setting('skipcontextmenus'):
            context = build_context_menu(url, season, server)
        else:
            context = None

        # Build the screen directory listing
        add_item_to_gui(url, details, extraData, context)

    log_print.debug("Skin override is: %s" % settings.get_setting('skinoverride'))
    view_id = enforce_skin_view('season')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=settings.get_setting('kodicache'))


def process_tvepisodes(url, tree=None):
    log_print.debug("== ENTER ==")
    xbmcplugin.setContent(pluginhandle, 'episodes')

    tree = get_xml(url,tree)
    if tree is None:
        return

    set_window_heading(tree)


    # get season thumb for SEASON NODE
    season_thumb = tree.get('thumb', '')
    print season_thumb
    if season_thumb == "/:/resources/show.png": 
        season_thumb = ""

    ShowTags = tree.findall('Video')
    server = plex_network.get_server_from_url(url)

    if not settings.get_setting('skipimages'):
        sectionart=get_fanart_image(tree, server)

    banner = get_banner_image(tree, server)

    randomNumber=str(random.randint(1000000000,9999999999))

    if tree.get('mixedParents') == '1':
        log_print.info('Setting plex sort')
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_UNSORTED ) # maintain original plex sorted
    else:
        log_print.info('Setting KODI sort')
        xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_EPISODE )  # episode

    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_DATE)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE_IGNORE_THE)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_DATEADDED)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_VIDEO_RATING)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_VIDEO_RUNTIME)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_MPAA_RATING)

    for episode in ShowTags:

        log_print.debug("---New Item---")
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

        log_print.debug("Media attributes are %s" % mediaarguments)

        # Gather some data
        view_offset=episode.get('viewOffset',0)
        duration=int(mediaarguments.get('duration',episode.get('duration',0)))/1000

        # Required listItem entries for XBMC
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

        if tree.get('mixedParents') == '1':
            if tree.get('parentIndex') == '1':
                details['title'] = "%sx%s %s" % ( details['season'], str(details['episode']).zfill(2), details['title'] )
            else:
                details['title'] = "%s - %sx%s %s" % ( details['tvshowtitle'], details['season'], str(details['episode']).zfill(2), details['title'] )

        # Extra data required to manage other properties
        extraData={'type'         : "Video" ,
                   'source'       : 'tvepisodes',
                   'thumb'        : get_thumb_image(episode, server) ,
                   'fanart_image' : get_fanart_image(episode, server) ,
                   'banner'       : banner,
                   'key'          : episode.get('key',''),
                   'ratingKey'    : str(episode.get('ratingKey',0)),
                   'duration'     : duration,
                   'resume'       : int(int(view_offset)/1000) }

        if extraData['fanart_image'] == "" and not settings.get_setting('skipimages'):
            extraData['fanart_image'] = sectionart

        if season_thumb:
            extraData['season_thumb'] = server.get_url_location() + season_thumb

        # get ALL SEASONS or TVSHOW thumb
        if not season_thumb and episode.get('parentThumb', ""):
            extraData['season_thumb'] = "%s%s" % (server.get_url_location(), episode.get('parentThumb', ""))
        elif not season_thumb and episode.get('grandparentThumb', ""):
            extraData['season_thumb'] = "%s%s" % (server.get_url_location(), episode.get('grandparentThumb', ""))

        # Determine what tupe of watched flag [overlay] to use
        if int(episode.get('viewCount',0)) > 0:
            details['playcount'] = 1
        else: 
            details['playcount'] = 0

        # Extended Metadata
        if not settings.get_setting('skipmetadata'):
            details['cast']     = tempcast
            details['director'] = " / ".join(tempdir)
            details['writer']   = " / ".join(tempwriter)
            details['genre']    = " / ".join(tempgenre)

        # Add extra media flag data
        if not settings.get_setting('skipflags'):
            extraData.update(get_media_data(mediaarguments))

        # Build any specific context menu entries
        if not settings.get_setting('skipcontextmenus'):
            context=build_context_menu(url, extraData,server)
        else:
            context=None

        extraData['mode']=MODE_PLAYLIBRARY
        separator = "?"
        if "?" in extraData['key']:
            separator = "&"
        u="%s%s%st=%s" % (server.get_url_location(), extraData['key'], separator, randomNumber)

        add_item_to_gui(u,details,extraData, context, folder=False)

    log_print.debug("Skin override is: %s" % settings.get_setting('skinoverride'))
    view_id = enforce_skin_view('episode')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=settings.get_setting('kodicache'))


def get_audio_subtitles_from_media(server, tree, full=False):
    '''
        Cycle through the Parts sections to find all "selected" audio and subtitle streams
        If a stream is marked as selected=1 then we will record it in the dict
        Any that are not, are ignored as we do not need to set them
        We also record the media locations for playback decision later on
    '''
    log_print.debug("== ENTER ==")
    log_print.debug("Gather media stream info" )

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
                log_print.debug("No Video data found")
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
                        'thumbnailImage': get_thumb_image(timings,server) }

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
                       'thumbnailImage': get_thumb_image(timings,server) }

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

        # Get the media locations (file and web) for later on
        for stuff in options:

            try:
                bits=stuff.get('key'), stuff.get('file')
                parts.append(bits)
                media_details_list.append(media_details_temp)
                partsCount += 1
            except: pass

    # if we are deciding internally or forcing an external subs file, then collect the data
    if media_type == "video" and settings.get_setting('streamControl') == SUB_AUDIO_PLEX_CONTROL:

        contents="all"
        tags=tree.getiterator('Stream')

        for bits in tags:
            stream=dict(bits.items())

            # Audio Streams
            if stream['streamType'] == '2':
                audioCount += 1
                audioOffset += 1
                if stream.get('selected') == "1":
                    log_print.debug("Found preferred audio id: %s " % stream['id'] )
                    audio=stream
                    selectedAudioOffset=audioOffset

            # Subtitle Streams
            elif stream['streamType'] == '3':

                if subOffset == -1:
                    subOffset = int(stream.get('index',-1))
                elif stream.get('index',-1) > 0 and stream.get('index',-1) < subOffset:
                    subOffset = int(stream.get('index',-1))

                if stream.get('selected') == "1":
                    log_print.debug( "Found preferred subtitles id : %s " % stream['id'])
                    subCount += 1
                    subtitle=stream
                    if stream.get('key'):
                        subtitle['key'] = server.get_formatted_url(stream['key'])
                    else:
                        selectedSubOffset=int( stream.get('index') ) - subOffset

    else:
            log_print.debug( "Stream selection is set OFF")

    streamData={'contents'   : contents ,                # What type of data we are holding
                'audio'      : audio ,                   # Audio data held in a dict
                'audioCount' : audioCount ,              # Number of audio streams
                'subtitle'   : subtitle ,                # Subtitle data (embedded) held as a dict
                'subCount'   : subCount ,                # Number of subtitle streams
                'parts'      : parts ,                   # The differet media locations
                'partsCount' : partsCount ,              # Number of media locations
                'media'      : media ,                   # Resume/duration data for media
                'details'    : media_details_list ,      # Bitrate, resolution and container for each part
                'subOffset'  : selectedSubOffset ,       # Stream index for selected subs
                'audioOffset': selectedAudioOffset ,     # STream index for select audio
                'full_data'  : full_data ,               # Full metadata extract if requested
                'type'       : media_type ,              # Type of metadata
                'extra'      : extra }                   # Extra data

    log_print.debug( streamData )
    return streamData


def play_playlist(server, data):
    log_print.debug("== ENTER ==")
    log_print.debug("Creating new playlist")
    playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
    playlist.clear()

    tree = get_xml(server.get_url_location()+data['extra'].get('album')+"/children")

    if tree is None:
        return

    TrackTags=tree.findall('Track')
    for track in TrackTags:

        log_print.debug("Adding playlist item")

        url, item = track_tag(server, tree, track, listing = False)

        liz=xbmcgui.ListItem(item.get('title','Unknown'), iconImage=data['full_data'].get('thumbnailImage','') , thumbnailImage=data['full_data'].get('thumbnailImage',''))

        liz.setInfo( type='music', infoLabels=item )        
        playlist.add(url, liz)

    index = int(data['extra'].get('index',0)) - 1
    log_print.debug("Playlist complete.  Starting playback from track %s [playlist index %s] " % (data['extra'].get('index',0), index ))
    xbmc.Player().playselected( index )   

    
    
    return


def play_library_media(vids, override=False, force=None, full_data=False, shelf=False):
    
    # assume widget if playback initiated from home
    if xbmc.getCondVisibility("Window.IsActive(home)"): 
        shelf = True
        full_data = True
    
    session=None
    if settings.get_setting('transcode'):
        override=True

    if override:
        full_data = True

    server=plex_network.get_server_from_url(vids)

    id=vids.split('?')[0].split('&')[0].split('/')[-1]

    tree=get_xml(vids)
    if tree is None:
        return

    if force:
        full_data = True

    streams=get_audio_subtitles_from_media(server,tree, full_data)

    if force and streams['type'] == "music":
        play_playlist(server, streams)
        return

    url=select_media_to_play(streams, server)

    if url is None:
        return

    protocol=url.split(':',1)[0]

    if protocol == "file":
        log_print.debug( "We are playing a local file")
        playurl=url.split(':',1)[1]
    elif protocol.startswith("http"):
        log_print.debug( "We are playing a stream")
        if override:
            log_print.debug( "We will be transcoding the stream")
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
        log_print.debug("Shelf playback: display resume dialog")
        displayTime = str(datetime.timedelta(seconds=resume))
        display_list = [ "Resume from %s" % displayTime , "Start from beginning"]
        resumeScreen = xbmcgui.Dialog()
        result = resumeScreen.select('Resume',display_list)
        if result == -1:
            return False

        if result == 1:
           resume=0

    log_print.debug("Resume has been set to %s " % resume)

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

    if force or shelf or session is not None:
        if resume:
            item.setProperty('ResumeTime', str(resume) )
            item.setProperty('TotalTime', str(duration) )
            item.setProperty('StartOffset', str(resume))
            log_print.info("Playback from resume point: %s" % resume)

    if streams['type'] == "picture":
        import json
        request=json.dumps({ "id"      : 1,
                             "jsonrpc" : "2.0",
                             "method"  : "Player.Open",
                             "params"  : { "item"  :  {"file": playurl } } } )
        html=xbmc.executeJSONRPC(request)
        return
    else:
        if shelf:
            # if launched from widget, use player.play for playback so artwork and resume works correctly
            xbmcplugin.setResolvedUrl(pluginhandle, False, item)
            start = xbmc.Player().play(playurl,item)
        else:
            start = xbmcplugin.setResolvedUrl(pluginhandle, True, item)

    # record the playing file and server in the home window
    # so that plexbmc helper can find out what is playing
    WINDOW = xbmcgui.Window( 10000 )
    WINDOW.setProperty('plexbmc.nowplaying.server', server.get_location())
    WINDOW.setProperty('plexbmc.nowplaying.id', id)

    # Set a loop to wait for positive confirmation of playback
    count = 0
    while not xbmc.Player().isPlaying():
        log_print.debug( "Not playing yet...sleep for 2")
        count = count + 2
        if count >= 20:
            return
        else:
            time.sleep(2)

    if not override:
        set_audio_subtitles(streams)

    if streams['type'] == "video" or streams['type'] == "music":
        monitor_playback(id,server, playurl, session)

    return


def set_audio_subtitles(stream):
    '''
        Take the collected audio/sub stream data and apply to the media
        If we do not have any subs then we switch them off
    '''

    log_print.debug("== ENTER ==")

    # If we have decided not to collect any sub data then do not set subs
    if stream['contents'] == "type":
        log_print.info("No audio or subtitle streams to process.")

        # If we have decided to force off all subs, then turn them off now and return
        if settings.get_setting('streamControl') == SUB_AUDIO_NEVER_SHOW :
            xbmc.Player().showSubtitles(False)
            log_print ("All subs disabled")

        return True

    # Set the AUDIO component
    if settings.get_setting('streamControl') == SUB_AUDIO_PLEX_CONTROL:
        log_print.debug("Attempting to set Audio Stream")

        audio = stream['audio']

        if stream['audioCount'] == 1:
            log_print.info("Only one audio stream present - will leave as default")

        elif audio:
            log_print.debug("Attempting to use selected language setting: %s" % audio.get('language',audio.get('languageCode','Unknown')).encode('utf8'))
            log_print.info("Found preferred language at index %s" % stream['audioOffset'])
            try:
                xbmc.Player().setAudioStream(stream['audioOffset'])
                log_print.debug("Audio set")
            except:
                log_print.info("Error setting audio, will use embedded default stream")

    # Set the SUBTITLE component
    if settings.get_setting('streamControl') == SUB_AUDIO_PLEX_CONTROL:
        log_print.debug("Attempting to set preferred subtitle Stream")
        subtitle=stream['subtitle']
        if subtitle:
            log_print.debug("Found preferred subtitle stream" )
            try:
                xbmc.Player().showSubtitles(False)
                if subtitle.get('key'):
                    xbmc.Player().setSubtitles(subtitle['key'])                
                else:
                    log_print.info("Enabling embedded subtitles at index %s" % stream['subOffset'])
                    xbmc.Player().setSubtitleStream(int(stream['subOffset']))

                xbmc.Player().showSubtitles(True)      
                return True
            except:
                log_print.info("Error setting subtitle")

        else:
            log_print.info("No preferred subtitles to set")
            xbmc.Player().showSubtitles(False)

    return False


def select_media_to_play(data, server):
    log_print.debug("== ENTER ==")
    # if we have two or more files for the same movie, then present a screen
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
                # name="%s %s %sMbps" % (items[1].split('/')[-1], details[indexCount]['videoResolution'], details[indexCount]['bitrate'])
            else:
                name="%s %s %sMbps" % (items[0].split('.')[-1], details[indexCount]['videoResolution'], details[indexCount]['bitrate'])

            if settings.get_setting('forcedvd'):
                if '.ifo' in name.lower():
                    log_print.debug( "Found IFO DVD file in " + name )
                    name="DVD Image"
                    dvdIndex.append(indexCount)

            dialogOptions.append(name)
            indexCount+=1

        log_print.debug("Create selection dialog box - we have a decision to make!")
        startTime = xbmcgui.Dialog()
        result = startTime.select('Select media to play',dialogOptions)
        if result == -1:
            return None

        if result in dvdIndex:
            log_print.debug( "DVD Media selected")
            dvdplayback=True

    else:
        if settings.get_setting('forcedvd'):
            if '.ifo' in options[result]:
                dvdplayback=True

    newurl=select_media_type({'key': options[result][0] , 'file' : options[result][1]},server,dvdplayback)

    log_print.debug("We have selected media at %s" % newurl)
    return newurl


def monitor_playback(id, server, playurl, session=None):
    log_print.debug("== ENTER ==")

    if session:
        log_print.debug("We are monitoring a transcode session")

    if settings.get_setting('monitoroff'):
        return

    playedTime = 0
    totalTime = 0
    currentTime = 0
    # Whilst the file is playing back
    while xbmc.Player().isPlaying():

        try:
            if not ( playurl == xbmc.Player().getPlayingFile() ):
                log_print.info("File stopped being played")
                break
        except: pass

        currentTime = int(xbmc.Player().getTime())
        totalTime = int(xbmc.Player().getTotalTime())

        try:
            progress = int(( float(currentTime) / float(totalTime) ) * 100)
        except:
            progress = 0

        if playedTime == currentTime:
            log_print.debug( "Movies paused at: %s secs of %s @ %s%%" % ( currentTime, totalTime, progress) )
            server.report_playback_progress(id,currentTime*1000, state="paused", duration=totalTime*1000)
        else:

            log_print.debug( "Movies played time: %s secs of %s @ %s%%" % ( currentTime, totalTime, progress) )
            server.report_playback_progress(id,currentTime*1000, state="playing", duration=totalTime*1000)
            playedTime = currentTime

        xbmc.sleep(2000)

    # If we get this far, playback has stopped
    log_print.debug("Playback Stopped")
    server.report_playback_progress(id,playedTime*1000, state='stopped', duration=totalTime*1000)

    if session is not None:
        log_print.debug("Stopping PMS transcode job with session %s" % session)
        server.stop_transcode_session(session)

    return


def play_media_stream(url):
    log_print.debug("== ENTER ==")

    if url.startswith('file'):
        log_print.debug( "We are playing a local file")
        # Split out the path from the URL
        playurl=url.split(':',1)[1]
    elif url.startswith('http'):
        log_print.debug( "We are playing a stream")
        if '?' in url:
            server=plex_network.get_server_from_url(url)
            playurl=server.get_formatted_url(url)
    else:
        playurl=url

    item = xbmcgui.ListItem(path=playurl)
    return xbmcplugin.setResolvedUrl(pluginhandle, True, item)


def play_video_channel(vids, prefix=None, indirect=None, transcode=False):
    server=plex_network.get_server_from_url(vids)
    if "node.plexapp.com" in vids:
        server=get_master_server()

    if indirect:
        # Probably should transcode this
        if vids.startswith('http'):
            vids='/'+vids.split('/',3)[3]
            transcode=True

        session, vids=server.get_universal_transcode(vids)

    '''# If we find the url lookup service, then we probably have a standard plugin, but possibly with resolution choices
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

        # If we have options, create a dialog menu
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

    # Check if there is a further level of XML required
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
    # if we have a plex URL, then this is a transcoding URL
    if 'plex://' in vids:
        log_print.debug("found webkit video, pass to transcoder")
        if not (prefix):
            prefix="system"
            if settings.get_setting('transcode_type') == "universal":
                session, vids=server.get_universal_transcode(vids)
            elif settings.get_setting('transcode_type') == "legacy":
                session, vids=server.get_legacy_transcode(0,vids,prefix)

        # Workaround for XBMC HLS request limit of 1024 byts
        if len(vids) > 1000:
            log_print.debug("XBMC HSL limit detected, will pre-fetch m3u8 playlist")

            playlist = get_xml(vids)

            if not playlist or not "# EXTM3U" in playlist:

                log_print.debug("Unable to get valid m3u8 playlist from transcoder")
                return

            server=plex_network.get_server_from_url(vids)
            session=playlist.split()[-1]
            vids="%s/video/:/transcode/segmented/%s?t=1" % (server.get_url_location(), session)

    log_print.debug("URL to Play: %s " % vids)
    log_print.debug("Prefix is: %s" % prefix)

    # If this is an Apple movie trailer, add User Agent to allow access
    if 'trailers.apple.com' in vids:
        url=vids+"|User-Agent=QuickTime/7.6.9 (qtver=7.6.9;os=Windows NT 6.1Service Pack 1)"
    else:
        url=vids

    log_print.debug("Final URL is: %s" % url)

    item = xbmcgui.ListItem(path=url)
    start = xbmcplugin.setResolvedUrl(pluginhandle, True, item)

    if transcode:
        try:
            monitor_channel_transcode_playback(session,server)
        except:
            log_print.debug("Unable to start transcode monitor")
    else:
        log_print.debug("Not starting monitor")

    return


def monitor_channel_transcode_playback(sessionID, server):
    log_print.debug("== ENTER ==")

    # Logic may appear backward, but this does allow for a failed start to be detected
    # First while loop waiting for start

    if settings.get_setting('monitoroff'):
        return

    count=0
    while not xbmc.Player().isPlaying():
        log_print.debug( "Not playing yet...sleep for 2")
        count = count + 2
        if count >= 40:
            # Waited 20 seconds and still no movie playing - assume it isn't going to..
            return
        else:
            xbmc.sleep(2000)

    while xbmc.Player().isPlaying():
        log_print.debug("Waiting for playback to finish")
        xbmc.sleep(4000)

    log_print.debug("Playback Stopped")
    log_print.debug("Stopping PMS transcode job with session: %s" % sessionID)
    server.stop_transcode_session(sessionID)

    return


def get_params(paramstring):
    log_print.debug("== ENTER ==")
    log_print.debug("Parameter string: %s" % paramstring)
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


def channel_search(url, prompt):
    '''
        When we encounter a search request, branch off to this function to generate the keyboard
        and accept the terms.  This URL is then fed back into the correct function for
        onward processing.
    '''
    log_print.debug("== ENTER ==")

    if prompt:
        prompt=urllib.unquote(prompt)
    else:
        prompt="Enter Search Term..."

    kb = xbmc.Keyboard('', 'heading')
    kb.setHeading(prompt)
    kb.doModal()
    if (kb.isConfirmed()):
        text = kb.getText()
        log_print.debug("Search term input: %s" % text)
        url=url+'&query='+urllib.quote(text)
        plex_plugins( url )
    return


def get_content(url):
    '''
        This function takes teh URL, gets the XML and determines what the content is
        This XML is then redirected to the best processing function.
        If a search term is detected, then show keyboard and run search query
        @input: URL of XML page
        @return: nothing, redirects to another function
    '''
    log_print.debug("== ENTER ==")

    server=plex_network.get_server_from_url(url)
    lastbit=url.split('/')[-1]
    log_print.debug("URL suffix: %s" % lastbit)

    # Catch search requests, as we need to process input before getting results.
    if lastbit.startswith('search'):
        log_print.debug("This is a search URL.  Bringing up keyboard")
        kb = xbmc.Keyboard('', 'heading')
        kb.setHeading('Enter search term')
        kb.doModal()
        if (kb.isConfirmed()):
            text = kb.getText()
            log_print.debug("Search term input: %s" % text)
            url=url+'&query='+urllib.quote(text)
        else:
            return

    tree = server.processed_xml(url)

    set_window_heading(tree)

    if lastbit == "folder" or lastbit == "playlists":
        process_xml(url,tree)
        return

    view_group=tree.get('viewGroup')

    if view_group == "movie":
        log_print.debug( "This is movie XML, passing to Movies")
        process_movies(url, tree)
    elif view_group == "show":
        log_print.debug( "This is tv show XML")
        process_tvshows(url,tree)
    elif view_group == "episode":
        log_print.debug("This is TV episode XML")
        process_tvepisodes(url,tree)
    elif view_group == 'artist':
        log_print.debug( "This is music XML")
        artist(url, tree)
    elif view_group== 'album' or view_group == 'albums':
        albums(url,tree)
    elif view_group == 'track':
        log_print.debug("This is track XML")
        tracks(url, tree) # sorthing is handled here
    elif view_group =="photo":
        log_print.debug("This is a photo XML")
        photo(url,tree)
    else:
        process_directory(url,tree)

    return


def process_directory(url, tree=None):
    log_print.debug("== ENTER ==")
    log_print.debug("Processing secondary menus")
    xbmcplugin.setContent(pluginhandle, "")

    server = plex_network.get_server_from_url(url)
    set_window_heading(tree)
    for directory in tree:
        details={'title' : directory.get('title','Unknown').encode('utf-8') }
        extraData={'thumb'        : get_thumb_image(tree, server) ,
                   'fanart_image' : get_fanart_image(tree, server) }

        extraData['mode'] = MODE_GETCONTENT
        u='%s' % (get_link_url(url, directory, server))

        add_item_to_gui(u, details, extraData)

    xbmcplugin.endOfDirectory(pluginhandle, cacheToDisc=settings.get_setting('kodicache'))


def artist(url, tree=None):
    '''
        Process artist XML and display data
        @input: url of XML page, or existing tree of XML page
        @return: nothing
    '''
    log_print.debug("== ENTER ==")
    xbmcplugin.setContent(pluginhandle, 'artists')
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_ARTIST_IGNORE_THE)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LASTPLAYED)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)

    # Get the URL and server name.  Get the XML and parse
    tree=get_xml(url,tree)
    if tree is None:
        return

    server=plex_network.get_server_from_url(url)
    set_window_heading(tree)
    ArtistTag=tree.findall('Directory')
    for artist in ArtistTag:

        details={'artist'  : artist.get('title','').encode('utf-8') }

        details['title']=details['artist']

        extraData={'type'         : "Music" ,
                   'thumb'        : get_thumb_image(artist, server) ,
                   'fanart_image' : get_fanart_image(artist, server) ,
                   'ratingKey'    : artist.get('title','') ,
                   'key'          : artist.get('key','') ,
                   'mode'         : MODE_ALBUMS ,
                   'plot'         : artist.get('summary','') }

        url='%s%s' % (server.get_url_location(), extraData['key'] )

        add_item_to_gui(url,details,extraData)

    log_print.debug("Skin override is: %s" % settings.get_setting('skinoverride'))
    view_id = enforce_skin_view('music')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=settings.get_setting('kodicache'))


def albums(url, tree=None):
    log_print.debug("== ENTER ==")
    xbmcplugin.setContent(pluginhandle, 'albums')
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_ALBUM_IGNORE_THE)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_ARTIST_IGNORE_THE)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LASTPLAYED)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)

    # Get the URL and server name.  Get the XML and parse
    tree=get_xml(url,tree)
    if tree is None:
        return

    server=plex_network.get_server_from_url(url)
    sectionart=get_fanart_image(tree, server)
    set_window_heading(tree)
    AlbumTags=tree.findall('Directory')
    recent = True if 'recentlyAdded' in url else False
    for album in AlbumTags:

        details={'album'   : album.get('title','').encode('utf-8') ,
                 'year'    : int(album.get('year',0)) ,
                 'artist'  : tree.get('parentTitle', album.get('parentTitle','')).encode('utf-8') }

        if recent:
            details['title']="%s - %s" % ( details['artist'], details['album'])
        else:
            details['title']=details['album']         
            
        extraData={'type'         : "Music" ,
                   'thumb'        : get_thumb_image(album, server) ,
                   'fanart_image' : get_fanart_image(album, server) ,
                   'key'          : album.get('key',''),
                   'mode'         : MODE_TRACKS ,
                   'plot'         : album.get('summary','')}

        if extraData['fanart_image'] == "":
            extraData['fanart_image']=sectionart

        url='%s%s' % (server.get_url_location(), extraData['key'] )

        add_item_to_gui(url,details,extraData)

    log_print.debug("Skin override is: %s" % settings.get_setting('skinoverride'))
    view_id = enforce_skin_view('music')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=settings.get_setting('kodicache'))


def tracks(url, tree=None):
    log_print.debug("== ENTER ==")
    xbmcplugin.setContent(pluginhandle, 'songs')
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_TITLE_IGNORE_THE)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_DURATION)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_SONG_RATING)
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_TRACKNUM)

    tree=get_xml(url,tree)
    if tree is None:
        return

    playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
    playlist.clear()

    server=plex_network.get_server_from_url(url)
    sectionart=get_fanart_image(tree, server)
    sectionthumb=get_thumb_image(tree, server)
    set_window_heading(tree)
    TrackTags=tree.findall('Track')
    for track in TrackTags:
        if track.get('thumb'):
            sectionthumb=get_thumb_image(track, server)

        track_tag(server, tree, track, sectionart, sectionthumb)

    log_print.debug("Skin override is: %s" % settings.get_setting('skinoverride'))
    view_id = enforce_skin_view('music')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=settings.get_setting('kodicache'))


def get_xml(url, tree=None):
    log_print.debug("== ENTER ==")

    if tree is None:
        tree=plex_network.get_processed_xml(url)

    if tree.get('message'):
        xbmcgui.Dialog().ok(tree.get('header','Message'),tree.get('message',''))
        return None

    return tree


def plex_plugins(url, tree=None):
    '''
        Main function to parse plugin XML from PMS
        Will create dir or item links depending on what the
        main tag is.
        @input: plugin page URL
        @return: nothing, creates XBMC GUI listing
    '''
    log_print.debug("== ENTER ==")
    xbmcplugin.setContent(pluginhandle, 'addons')
    server=plex_network.get_server_from_url(url)
    tree = get_xml(url,tree)
    if tree is None:
        return

    myplex_url=False
    if (tree.get('identifier') != "com.plexapp.plugins.myplex") and ( "node.plexapp.com" in url ) :
        myplex_url=True
        log_print.debug("This is a myplex URL, attempting to locate master server")
        server=get_master_server()

    for plugin in tree:

        details={'title'   : plugin.get('title','Unknown').encode('utf-8') }

        if details['title'] == "Unknown":
            details['title']=plugin.get('name',"Unknown").encode('utf-8')

        if plugin.get('summary'):
            details['plot']=plugin.get('summary')

        extraData={'thumb'        : get_thumb_image(plugin, server) ,
                   'fanart_image' : get_fanart_image(plugin, server) ,
                   'identifier'   : tree.get('identifier','') ,
                   'type'         : "Video" ,
                   'key'          : plugin.get('key','') }

        if myplex_url:
            extraData['key']=extraData['key'].replace('node.plexapp.com:32400',server.get_location())

        if extraData['fanart_image'] == "":
            extraData['fanart_image']=get_fanart_image(tree, server)

        p_url=get_link_url(url, extraData, server)

        if plugin.tag == "Directory" or plugin.tag == "Podcast":

            if plugin.get('search') == '1':
                extraData['mode']=MODE_CHANNELSEARCH
                extraData['parameters']={'prompt' : plugin.get('prompt',"Enter Search Term").encode('utf-8') }
            else:
                extraData['mode']=MODE_PLEXPLUGINS

            add_item_to_gui(p_url, details, extraData)

        elif plugin.tag == "Video":
            extraData['mode']=MODE_VIDEOPLUGINPLAY

            for child in plugin:
                if child.tag == "Media":
                    extraData['parameters'] = {'indirect' : child.get('indirect','0')}            

            add_item_to_gui(p_url, details, extraData, folder=False)

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
            extraData['mode']=MODE_CHANNELPREFS
            extraData['parameters']={'id' : plugin.get('id') }
            add_item_to_gui(url, details, extraData)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=settings.get_setting('kodicache'))


def channel_settings(url, settingID):
    '''
        Take the setting XML and parse it to create an updated
        string with the new settings.  For the selected value, create
        a user input screen (text or list) to update the setting.
        @ input: url
        @ return: nothing
    '''
    log_print.debug("== ENTER ==")
    log_print.debug("Setting preference for ID: %s" % settingID )

    if not settingID:
        log_print.debug("ID not set")
        return

    tree=get_xml(url)
    if tree is None:
        return

    set_window_heading(tree)
    setString=None
    for plugin in tree:

        if plugin.get('id') == settingID:
            log_print.debug("Found correct id entry for: %s" % settingID)
            id=settingID

            label=plugin.get('label',"Enter value")
            option=plugin.get('option')
            value=plugin.get('value')

            if plugin.get('type') == "text":
                log_print.debug("Setting up a text entry screen")
                kb = xbmc.Keyboard(value, 'heading')
                kb.setHeading(label)

                if option == "hidden":
                    kb.setHiddenInput(True)
                else:
                    kb.setHiddenInput(False)

                kb.doModal()
                if (kb.isConfirmed()):
                    value = kb.getText()
                    log_print.debug("Value input: %s " % value)
                else:
                    log_print.debug("User cancelled dialog")
                    return False

            elif plugin.get('type') == "enum":
                log_print.debug("Setting up an enum entry screen")

                values=plugin.get('values').split('|')

                settingScreen = xbmcgui.Dialog()
                value = settingScreen.select(label,values)
                if value == -1:
                    log_print.debug("User cancelled dialog")
                    return False
            else:
                log_print.debug('Unknown option type: %s' % plugin.get('id') )

        else:
            value=plugin.get('value')
            id=plugin.get('id')

        if setString is None:
            setString='%s/set?%s=%s' % (url, id, value)
        else:
            setString='%s&%s=%s' % (setString, id, value)

    log_print.debug("Settings URL: %s" % setString )
    plex_network.talk_to_server(setString)
    xbmc.executebuiltin("Container.Refresh")

    return False


def process_xml(url, tree=None):
    '''
        Main function to parse plugin XML from PMS
        Will create dir or item links depending on what the
        main tag is.
        @input: plugin page URL
        @return: nothing, creates XBMC GUI listing
    '''
    log_print.debug("== ENTER ==")
    xbmcplugin.setContent(pluginhandle, 'movies')
    server=plex_network.get_server_from_url(url)
    tree=get_xml(url,tree)
    if tree is None:
        return
    set_window_heading(tree)
    for plugin in tree:

        details={'title'   : plugin.get('title','Unknown').encode('utf-8') }

        if details['title'] == "Unknown":
            details['title']=plugin.get('name',"Unknown").encode('utf-8')

        extraData={'thumb'        : get_thumb_image(plugin, server) ,
                   'fanart_image' : get_fanart_image(plugin, server) ,
                   'identifier'   : tree.get('identifier','') ,
                   'type'         : "Video" }

        if extraData['fanart_image'] == "":
            extraData['fanart_image']=get_fanart_image(tree, server)

        p_url=get_link_url(url, plugin, server)

        if plugin.tag == "Directory" or plugin.tag == "Podcast":
            extraData['mode']=MODE_PROCESSXML
            add_item_to_gui(p_url, details, extraData)

        elif plugin.tag == "Track":
            track_tag(server, tree, plugin)

        elif plugin.tag == "Playlist":
            playlist_tag(url, server, tree, plugin)

        elif tree.get('viewGroup') == "movie":
            process_movies(url, tree)
            return

        elif tree.get('viewGroup') == "episode":
            process_tvepisodes(url, tree)
            return

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=settings.get_setting('kodicache'))


def movie_tag(url, server, tree, movie, random_number):

    log_print.debug("---New Item---")
    tempgenre = []
    tempcast = []
    tempdir = []
    tempwriter = []

    # Lets grab all the info we can quickly through either a dictionary, or assignment to a list
    # We'll process it later
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

    log_print.debug("Media attributes are %s" % mediaarguments)

    # Gather some data
    view_offset = movie.get('viewOffset', 0)
    duration = int(mediaarguments.get('duration', movie.get('duration', 0)))/1000

    # Required listItem entries for XBMC
    details = {'plot'     : movie.get('summary', '').encode('utf-8'),
               'title'    : movie.get('title', 'Unknown').encode('utf-8'),
               'sorttitle': movie.get('titleSort', movie.get('title', 'Unknown')).encode('utf-8'),
               'rating'   : float(movie.get('rating', 0)),
               'studio'   : movie.get('studio', '').encode('utf-8'),
               'mpaa'     : movie.get('contentRating', '').encode('utf-8'),
               'year'     : int(movie.get('year', 0)),
               'date'     : movie.get('originallyAvailableAt', '1970-01-01'),
               'premiered': movie.get('originallyAvailableAt', '1970-01-01'),
               'tagline'  : movie.get('tagline', ''),
               'dateAdded': str(datetime.datetime.fromtimestamp(int(movie.get('addedAt', 0))))}

    # Extra data required to manage other properties
    extraData={'type'        : "Video",
               'source'      : 'movies',
               'thumb'       : get_thumb_image(movie, server),
               'fanart_image': get_fanart_image(movie, server),
               'key'         : movie.get('key', ''),
               'ratingKey'   : str(movie.get('ratingKey', 0)),
               'duration'    : duration,
               'resume'      : int(int(view_offset)/1000)}

    # Determine what type of watched flag [overlay] to use
    if int(movie.get('viewCount', 0)) > 0:
        details['playcount'] = 1
    elif int(movie.get('viewCount', 0)) == 0:
        details['playcount'] = 0

    # Extended Metadata
    if not settings.get_setting('skipmetadata'):
        details['cast']     = tempcast
        details['director'] = " / ".join(tempdir)
        details['writer']   = " / ".join(tempwriter)
        details['genre']    = " / ".join(tempgenre)

    if movie.get('primaryExtraKey') is not None:
        details['trailer'] = "plugin://plugin.video.plexbmc/?url=%s%s?t=%s&mode=%s" % (server.get_url_location(), movie.get('primaryExtraKey', ''), random_number, MODE_PLAYLIBRARY)
        log_print.debug('Trailer plugin url added: %s' % details['trailer'])

    # Add extra media flag data
    if not settings.get_setting('skipflags'):
        extraData.update(get_media_data(mediaarguments))

    # Build any specific context menu entries
    if not settings.get_setting('skipcontextmenus'):
        context = build_context_menu(url, extraData, server)
    else:
        context = None
    # http:// <server> <path> &mode=<mode> &t=<rnd>
    extraData['mode'] = MODE_PLAYLIBRARY
    separator = "?"
    if "?" in extraData['key']:
        separator = "&"
    final_url = "%s%s%st=%s" % (server.get_url_location(), extraData['key'], separator, random_number)

    add_item_to_gui(final_url, details, extraData, context, folder=False)
    return


def get_media_data(tag_dict):
    '''
        Extra the media details from the XML
        @input: dict of <media /> tag attributes
        @output: dict of required values
    '''
    log_print.debug("== ENTER ==")

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


def track_tag(server, tree, track, sectionart="", sectionthumb="", listing=True):
    log_print.debug("== ENTER ==")
    xbmcplugin.setContent(pluginhandle, 'songs')

    for child in track:
        for babies in child:
            if babies.tag == "Part":
                partDetails=(dict(babies.items()))

    log_print.debug( "Part is %s" % partDetails)

    details={'TrackNumber' : int(track.get('index',0)) ,
             'title'       : str(track.get('index',0)).zfill(2)+". "+track.get('title','Unknown').encode('utf-8') ,
             'rating'      : float(track.get('rating',0)) ,
             'album'       : track.get('parentTitle', tree.get('parentTitle','')).encode('utf-8') ,
             'artist'      : track.get('grandparentTitle', tree.get('grandparentTitle','')).encode('utf-8') ,
             'duration'    : int(track.get('duration',0))/1000 }

    extraData={'type'          : "music" ,
               'fanart_image'  : sectionart ,
               'thumb'         : sectionthumb ,
               'key'           : track.get('key','') }

    # If we are streaming, then get the virtual location
    extraData['mode']=MODE_PLAYLIBRARY
    u="%s%s" % (server.get_url_location(), extraData['key'])

    if listing:
        add_item_to_gui(u,details,extraData,folder=False)
    else:
        return ( url, details )


def playlist_tag(url, server, tree, track, sectionart="", sectionthumb="", listing=True):
    log_print.debug("== ENTER ==")

    details={'title'       : track.get('title','Unknown').encode('utf-8') ,
             'duration'    : int(track.get('duration',0))/1000 
             }

    extraData={'type'         : track.get('playlistType', ''),
               'thumb'      : get_thumb_image({'thumb' : track.get('composite', '')},server)}

    if extraData['type'] == "video":
        extraData['mode'] = MODE_MOVIES
    elif extraData['type'] == "audio":
        extraData['mode'] = MODE_TRACKS
    else:
        extraData['mode']=MODE_GETCONTENT

    u=get_link_url(url, track, server)

    if listing:
        add_item_to_gui(u,details,extraData,folder=True)
    else:
        return ( url, details )


def photo(url, tree=None):
    log_print.debug("== ENTER ==")
    server=plex_network.get_server_from_url(url)

    xbmcplugin.setContent(pluginhandle, 'photo')

    tree=get_xml(url,tree)
    if tree is None:
        return

    sectionArt=get_fanart_image(tree,server)
    set_window_heading(tree)
    for picture in tree:

        details={'title' : picture.get('title',picture.get('name','Unknown')).encode('utf-8') }

        if not details['title']:
            details['title'] = "Unknown"

        extraData={'thumb'        : get_thumb_image(picture, server) ,
                   'fanart_image' : get_fanart_image(picture, server) ,
                   'type'         : "image" }

        if extraData['fanart_image'] == "":
            extraData['fanart_image']=sectionArt

        u=get_link_url(url, picture, server)

        if picture.tag == "Directory":
            extraData['mode']=MODE_PHOTOS
            add_item_to_gui(u,details,extraData)

        elif picture.tag == "Photo":

            if tree.get('viewGroup','') == "photo":
                for photo in picture:
                    if photo.tag == "Media":
                        for images in photo:
                            if images.tag == "Part":
                                extraData['key']=server.get_url_location()+images.get('key','')
                                details['size']=int(images.get('size',0))
                                u=extraData['key']

            add_item_to_gui(u,details,extraData,folder=False)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=settings.get_setting('kodicache'))


def music(url, tree=None):
    log_print.debug("== ENTER ==")
    xbmcplugin.setContent(pluginhandle, 'artists')

    server=plex_network.get_server_from_url(url) 

    tree=get_xml(url,tree)
    if tree is None:
        return

    set_window_heading(tree)
    for grapes in tree:

        if grapes.get('key') is None:
            continue

        details={'genre'       : grapes.get('genre','').encode('utf-8') ,
                 'artist'      : grapes.get('artist','').encode('utf-8') ,
                 'year'        : int(grapes.get('year',0)) ,
                 'album'       : grapes.get('album','').encode('utf-8') ,
                 'tracknumber' : int(grapes.get('index',0)) ,
                 'title'       : "Unknown" }

        extraData={'type'        : "Music" ,
                   'thumb'       : get_thumb_image(grapes, server) ,
                   'fanart_image': get_fanart_image(grapes, server) }

        if extraData['fanart_image'] == "":
            extraData['fanart_image']=get_fanart_image(tree, server)

        u=get_link_url(url, grapes, server)

        if grapes.tag == "Track":
            log_print.debug("Track Tag")
            xbmcplugin.setContent(pluginhandle, 'songs')

            details['title']=grapes.get('track',grapes.get('title','Unknown')).encode('utf-8')
            details['duration']=int(int(grapes.get('totalTime',0))/1000)

            extraData['mode']=MODE_BASICPLAY
            add_item_to_gui(u,details,extraData,folder=False)

        else:

            if grapes.tag == "Artist":
                log_print.debug("Artist Tag")
                xbmcplugin.setContent(pluginhandle, 'artists')
                details['title']=grapes.get('artist','Unknown').encode('utf-8')

            elif grapes.tag == "Album":
                log_print.debug("Album Tag")
                xbmcplugin.setContent(pluginhandle, 'albums')
                details['title']=grapes.get('album','Unknown').encode('utf-8')

            elif grapes.tag == "Genre":
                details['title']=grapes.get('genre','Unknown').encode('utf-8')

            else:
                log_print.debug("Generic Tag: %s" % grapes.tag)
                details['title']=grapes.get('title','Unknown').encode('utf-8')

            extraData['mode']=MODE_MUSIC
            add_item_to_gui(u,details,extraData)

    log_print.debug("Skin override is: %s" % settings.get_setting('skinoverride'))
    view_id = enforce_skin_view('music')
    if view_id:
        xbmc.executebuiltin("Container.SetViewMode(%s)" % view_id)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=settings.get_setting('kodicache'))


def get_thumb_image(data, server, width=720, height=720):
    '''
        Simply take a URL or path and determine how to format for images
        @ input: elementTree element, server name
        @ return formatted URL
    '''

    if settings.get_setting('skipimages'):
        return ''

    thumbnail = data.get('thumb', '').split('?t')[0].encode('utf-8')

    if thumbnail.startswith("http"):
        return thumbnail

    elif thumbnail.startswith('/'):
        if settings.get_setting('fullres_thumbs'):
            return server.get_kodi_header_formatted_url(thumbnail)
        else:
            return server.get_kodi_header_formatted_url('/photo/:/transcode?url=%s&width=%s&height=%s'
                                                        % (urllib.quote_plus('http://localhost:32400' + thumbnail),
                                                           width, height))

    return GENERIC_THUMBNAIL


def get_banner_image(data, server, width=720, height=720):
    """
        Simply take a URL or path and determine how to format for images
        @ input: elementTree element, server name
        @ return formatted URL
    """

    if settings.get_setting('skipimages'):
        return ''

    thumbnail = data.get('banner', '').split('?t')[0].encode('utf-8')

    if thumbnail.startswith("http"):
        return thumbnail

    elif thumbnail.startswith('/'):
        if settings.get_setting('fullres_thumbs'):
            return server.get_kodi_header_formatted_url(thumbnail)
        else:
            return server.get_kodi_header_formatted_url('/photo/:/transcode?url=%s&width=%s&height=%s'
                                                        % (urllib.quote_plus('http://localhost:32400' + thumbnail),
                                                           width, height))

    return GENERIC_THUMBNAIL


def get_shelfthumb_image(data, server, season_thumb=False, prefer_season=False, width=400, height=400):
    '''
        Simply take a URL or path and determine how to format for images
        @ input: elementTree element, server name
        @ return formatted URL
    '''

    if season_thumb:
        if prefer_season:
            thumbnail = data.get('parentThumb', data.get('grandparentThumb', '')).split('?t')[0].encode('utf-8')
        else:
            thumbnail = data.get('grandparentThumb', '').split('?t')[0].encode('utf-8')
    else:
        thumbnail = data.get('thumb', '').split('?t')[0].encode('utf-8')

    if thumbnail.startswith("http"):
        return thumbnail

    elif thumbnail.startswith('/'):
        if settings.get_setting('fullres_thumbs'):
            return server.get_kodi_header_formatted_url(thumbnail)
        else:
            return server.get_kodi_header_formatted_url('/photo/:/transcode?url=%s&width=%s&height=%s'
                                                        % (urllib.quote_plus('http://localhost:32400' + thumbnail),
                                                           width, height))

    return GENERIC_THUMBNAIL


def get_fanart_image(data, server, width=1280, height=720):
    '''
        Simply take a URL or path and determine how to format for fanart
        @ input: elementTree element, server name
        @ return formatted URL for photo resizing
    '''
    if settings.get_setting('skipimages'):
        return ''

    fanart = data.get('art', '').encode('utf-8')

    if fanart.startswith('http'):
        return fanart

    elif fanart.startswith('/'):
        if settings.get_setting('fullres_fanart'):
            return server.get_kodi_header_formatted_url(fanart)
        else:
            return server.get_kodi_header_formatted_url('/photo/:/transcode?url=%s&width=%s&height=%s' % (urllib.quote_plus('http://localhost:32400' + fanart), width, height))

    return ''


def get_link_url(url, pathData, server, season_shelf=False):
    if not season_shelf:
        path = pathData.get('key', '')
    else:
        path = pathData.get('parentKey', '') + "/children"

    log_print.debug("Path is %s" % path)

    if path == '':
        log_print.debug("Empty Path")
        return

    # If key starts with http, then return it
    if path.startswith('http'):
        log_print.debug("Detected http(s) link")
        return path

    # If key starts with a / then prefix with server address
    elif path.startswith('/'):
        log_print.debug("Detected base path link")
        return '%s%s' % (server.get_url_location(), path)

    # If key starts with plex:// then it requires transcoding
    elif path.startswith("plex:") :
        log_print.debug("Detected plex link")
        components = path.split('&')
        for i in components:
            if 'prefix=' in i:
                del components[components.index(i)]
                break
        if pathData.get('identifier') is not None:
            components.append('identifier='+pathData['identifier'])

        path='&'.join(components)
        return 'plex://'+server.get_location()+'/'+'/'.join(path.split('/')[3:])

    elif path.startswith("rtmp"):
        log_print.debug("Detected RTMP link")
        return path

    # Any thing else is assumed to be a relative path and is built on existing url
    else:
        log_print.debug("Detected relative link")
        return "%s/%s" % (url, path)

    return url


def plex_online(url):
    log_print.debug("== ENTER ==")
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
                   'thumb'     : get_thumb_image(plugin,server)}

        extraData['mode']=MODE_CHANNELINSTALL

        if extraData['installed'] == 1:
            details['title']=details['title']+" (installed)"

        elif extraData['installed'] == 2:
            extraData['mode']=MODE_PLEXONLINE

        u=get_link_url(url, plugin, server)

        extraData['parameters']={'name' : details['title'] }

        add_item_to_gui(u, details, extraData)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=settings.get_setting('kodicache'))


def install(url, name):
    log_print.debug("== ENTER ==")
    server=plex_network.get_server_from_url(url)
    tree=server.processed_xml(url)
    if tree is None:
        return

    operations={}
    i=0
    for plums in tree.findall('Directory'):
        operations[i]=plums.get('title')

        # If we find an install option, switch to a yes/no dialog box
        if operations[i].lower() == "install":
            log_print.debug("Not installed.  Print dialog")
            ret = xbmcgui.Dialog().yesno("Plex Online","About to install " + name)

            if ret:
                log_print.debug("Installing....")
                tree = server.processed_xml(url+"/install")

                msg=tree.get('message','(blank)')
                log_print.debug(msg)
                xbmcgui.Dialog().ok("Plex Online",msg)
            return

        i+=1

    # Else continue to a selection dialog box
    ret = xbmcgui.Dialog().select("This plugin is already installed..",operations.values())

    if ret == -1:
        log_print.debug("No option selected, cancelling")
        return

    log_print.debug("Option %s selected.  Operation is %s" % (ret, operations[ret]))
    u=url+"/"+operations[ret].lower()
    tree = server.processed_xml(u)

    msg=tree.get('message')
    log_print.debug(msg)
    xbmcgui.Dialog().ok("Plex Online",msg)
    xbmc.executebuiltin("Container.Refresh")

    return


def channel_view(url):
    log_print.debug("== ENTER ==")
    server=plex_network.get_server_from_url(url)
    tree=server.processed_xml(url)

    if tree is None:
        return

    set_window_heading(tree)
    for channels in tree.getiterator('Directory'):

        if channels.get('local','') == "0":
            continue

        arguments=dict(channels.items())

        extraData={'fanart_image' : get_fanart_image(channels, server) ,
                   'thumb'        : get_thumb_image(channels, server) }

        details={'title' : channels.get('title','Unknown') }

        suffix=channels.get('key').split('/')[1]

        if channels.get('unique','')=='0':
            details['title']="%s (%s)" % ( details['title'], suffix )

        # Alter data sent into getlinkurl, as channels use path rather than key
        p_url=get_link_url(url, {'key': channels.get('key'), 'identifier' : channels.get('key')} , server)

        if suffix == "photos":
            extraData['mode']=MODE_PHOTOS
        elif suffix == "video":
            extraData['mode']=MODE_PLEXPLUGINS
        elif suffix == "music":
            extraData['mode']=MODE_MUSIC
        else:
            extraData['mode']=MODE_GETCONTENT

        add_item_to_gui(p_url,details,extraData)

    xbmcplugin.endOfDirectory(pluginhandle,cacheToDisc=settings.get_setting('kodicache'))


def skin(server_list=None, type=None):
    # Gather some data and set the window properties
    log_print.debug("== ENTER ==")
    # Get the global host variable set in settings
    WINDOW = xbmcgui.Window( 10000 )

    sectionCount=0
    serverCount=0
    sharedCount=0
    shared_flag={}
    hide_shared = settings.get_setting('hide_shared')
    
    WINDOW.setProperty("plexbmc.myplex_signedin" , str(plex_network.is_myplex_signedin()))
    WINDOW.setProperty("plexbmc.plexhome_enabled" , str(plex_network.is_plexhome_enabled()))
    if server_list is None:
        server_list=plex_network.get_server_list()

    for server in server_list:

        server.discover_sections()

        for section in server.get_sections():

            extraData={ 'fanart_image' : server.get_fanart(section) ,
                        'thumb'        : server.get_fanart(section) }

            # Determine what we are going to do process after a link is selected by the user, based on the content we find

            path=section.get_path()

            if section.is_show():
                if hide_shared == "true" and not server.is_owned():
                    shared_flag['show']=True
                    continue
                window="VideoLibrary"
                mode=MODE_TVSHOWS
                WINDOW.setProperty("plexbmc.%d.search" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/search?type=4", mode) )
            if  section.is_movie():
                if hide_shared == "true" and not server.is_owned():
                    shared_flag['movie']=True
                    continue
                window="VideoLibrary"
                mode=MODE_MOVIES
                WINDOW.setProperty("plexbmc.%d.search" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/search?type=1", mode) )
            if  section.is_artist():
                if hide_shared == "true" and not server.is_owned():
                    shared_flag['artist']=True
                    continue
                window="MusicFiles"
                mode=MODE_ARTISTS
                WINDOW.setProperty("plexbmc.%d.album" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/albums", mode) )
                WINDOW.setProperty("plexbmc.%d.search" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/search?type=10", mode) )
            if  section.is_photo():
                if hide_shared == "true" and not server.is_owned():
                    shared_flag['photo']=True
                    continue
                window="Pictures"
                WINDOW.setProperty("plexbmc.%d.year" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/year", mode) )
                mode=MODE_PHOTOS

            if settings.get_setting('secondary'):
                mode=MODE_GETCONTENT
            else:
                path=path+'/all'

            s_url='%s%s&mode=%s' % ( server.get_url_location(), path, mode)

            # Build that listing..
            WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , section.get_title())
            WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , server.get_name())
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s,return)" % (window, s_url))
            WINDOW.setProperty("plexbmc.%d.art"      % (sectionCount) , extraData['fanart_image'])
            WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , section.get_type())
            WINDOW.setProperty("plexbmc.%d.icon"     % (sectionCount) , extraData.get('thumb',GENERIC_THUMBNAIL))
            WINDOW.setProperty("plexbmc.%d.thumb"    % (sectionCount) , extraData.get('thumb',GENERIC_THUMBNAIL))
            WINDOW.setProperty("plexbmc.%d.partialpath" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s" % (window, server.get_url_location(), section.get_path()))
            WINDOW.setProperty("plexbmc.%d.search" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/search?type=1", mode) )
            WINDOW.setProperty("plexbmc.%d.recent" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/recentlyAdded", mode) )
            WINDOW.setProperty("plexbmc.%d.all" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/all", mode, ) )
            WINDOW.setProperty("plexbmc.%d.viewed" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/recentlyViewed", mode) )
            WINDOW.setProperty("plexbmc.%d.ondeck" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/onDeck", mode) )
            WINDOW.setProperty("plexbmc.%d.released" % (sectionCount) , "ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s%s%s&mode=%s,return)" % (window, server.get_url_location(), section.get_path(), "/newest", mode) )
            WINDOW.setProperty("plexbmc.%d.shared"     % (sectionCount) , "false")

            log_print.debug("Building window properties index [%s] which is [%s]" % (sectionCount, section.get_title()))
            log_print.debug("PATH in use is: ActivateWindow(%s,plugin://plugin.video.plexbmc/?url=%s,return)" % (window, s_url))
            sectionCount += 1

    if type == "nocat":
        WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared...")
        WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
        WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=/&mode=%s,return)" % MODE_SHARED_ALL )
        WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "movie")
        WINDOW.setProperty("plexbmc.%d.shared"   % (sectionCount) , "true")
        sectionCount += 1

    else:

        if shared_flag.get('movie'):
            WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared...")
            WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=/&mode=%s,return)" % MODE_SHARED_MOVIES )
            WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "movie")
            WINDOW.setProperty("plexbmc.%d.shared"   % (sectionCount) , "true")
            sectionCount += 1

        if shared_flag.get('show'):
            WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared...")
            WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=/&mode=%s,return)" % MODE_SHARED_SHOWS)
            WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "show")
            WINDOW.setProperty("plexbmc.%d.shared"   % (sectionCount) , "true")
            sectionCount += 1

        if shared_flag.get('artist'):
            WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared...")
            WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(MusicFiles,plugin://plugin.video.plexbmc/?url=/&mode=%s,return)" % MODE_SHARED_MUSIC)
            WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "artist")
            WINDOW.setProperty("plexbmc.%d.shared"     % (sectionCount) , "true")
            sectionCount += 1

        if shared_flag.get('photo'):
            WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared...")
            WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(Pictures,plugin://plugin.video.plexbmc/?url=/&mode=%s,return)" % MODE_SHARED_PHOTOS)
            WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "photo")
            WINDOW.setProperty("plexbmc.%d.shared"     % (sectionCount) , "true")
            sectionCount += 1

    # For each of the servers we have identified
    numOfServers=len(server_list)

    for server in server_list:

        if server.is_secondary():
            continue

        if settings.get_setting('channelview'):
            WINDOW.setProperty("plexbmc.channel", "1")
            WINDOW.setProperty("plexbmc.%d.server.channel" % (serverCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=%s/channels/all&mode=21,return)" % server.get_url_location())
        else:
            WINDOW.clearProperty("plexbmc.channel")
            WINDOW.setProperty("plexbmc.%d.server.video" % (serverCount) , "%s/video&mode=7" % server.get_url_location() )
            WINDOW.setProperty("plexbmc.%d.server.music" % (serverCount) , "%s/music&mode=17" % server.get_url_location() )
            WINDOW.setProperty("plexbmc.%d.server.photo" % (serverCount) , "%s/photos&mode=16" % server.get_url_location() )

        WINDOW.setProperty("plexbmc.%d.server.online" % (serverCount) , "%s/system/plexonline&mode=19" % server.get_url_location() )

        WINDOW.setProperty("plexbmc.%d.server" % (serverCount) , server.get_name())

        serverCount+=1

    # Clear out old data
    clear_skin_sections(WINDOW, sectionCount, int(WINDOW.getProperty("plexbmc.sectionCount") if '' else 50))

    log_print.debug("Total number of skin sections is [%s]" % sectionCount )
    log_print.debug("Total number of servers is [%s]" % numOfServers)
    WINDOW.setProperty("plexbmc.sectionCount", str(sectionCount))
    WINDOW.setProperty("plexbmc.numServers", str(numOfServers))
    if plex_network.is_myplex_signedin():
        WINDOW.setProperty("plexbmc.queue" , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=http://myplexqueue&mode=24,return)")
        WINDOW.setProperty("plexbmc.myplex",  "1" )
    else:
        WINDOW.clearProperty("plexbmc.myplex")

    return


def amberskin():
    # Gather some data and set the window properties
    log_print.debug("== ENTER ==")
    # Get the global host variable set in settings
    WINDOW = xbmcgui.Window( 10000 )

    sectionCount=0
    serverCount=0
    sharedCount=0
    shared_flag={}
    hide_shared = settings.get_setting('hide_shared')

    server_list=plex_network.get_server_list()

    WINDOW.setProperty("plexbmc.myplex_signedin" , str(plex_network.is_myplex_signedin()))
    WINDOW.setProperty("plexbmc.plexhome_enabled" , str(plex_network.is_plexhome_enabled()))

    if plex_network.is_plexhome_enabled():
        WINDOW.setProperty("plexbmc.plexhome_user" , str(plex_network.get_myplex_user()))
        WINDOW.setProperty("plexbmc.plexhome_avatar" , str(plex_network.get_myplex_avatar()))

    log_print.debug("Using list of %s servers: %s " % (len(server_list), server_list))

    for server in server_list:

        server.discover_sections()

        for section in server.get_sections():

            log_print.debug("=Enter amberskin section=")
            log_print.debug(str(section.__dict__))
            log_print.debug("=/section=")

            extraData = {'fanart_image': server.get_fanart(section)}

            # Determine what we are going to do process after a link is selected by the user, based on the content we find
            path = section.get_path()
            base_url="plugin://plugin.video.plexbmc/?url=%s" % server.get_url_location()

            if section.is_show():
                if hide_shared and not server.is_owned():
                    shared_flag['show']=True
                    sharedCount += 1
                    continue
                window="VideoLibrary"
                mode=MODE_TVSHOWS
                WINDOW.setProperty("plexbmc.%d.search" % (sectionCount) , "ActivateWindow(%s,%s%s%s&mode=%s,return)" % (window, base_url, path, "/search?type=4", mode) )

            elif section.is_movie():
                if hide_shared and not server.is_owned():
                    shared_flag['movie']=True
                    sharedCount += 1
                    continue
                window="VideoLibrary"
                mode=MODE_MOVIES
                WINDOW.setProperty("plexbmc.%d.search" % (sectionCount) , "ActivateWindow(%s,%s%s%s&mode=%s,return)" % (window, base_url, path, "/search?type=1", mode) )  
                
            elif section.is_artist():
                if hide_shared and not server.is_owned():
                    shared_flag['artist']=True
                    sharedCount += 1
                    continue
                window="MusicFiles"
                mode=MODE_ARTISTS
                WINDOW.setProperty("plexbmc.%d.album" % (sectionCount) , "ActivateWindow(%s,%s%s%s&mode=%s,return)" % (window, base_url, path, "/albums", mode) )
                WINDOW.setProperty("plexbmc.%d.search" % (sectionCount) , "ActivateWindow(%s,%s%s%s&mode=%s,return)" % (window, base_url, path, "/search?type=10", mode) )
            elif  section.is_photo():
                if hide_shared and not server.is_owned():
                    shared_flag['photo']=True
                    sharedCount += 1
                    continue
                window="Pictures"
                WINDOW.setProperty("plexbmc.%d.year" % (sectionCount) , "ActivateWindow(%s,%s%s%s&mode=%s,return)" % (window, base_url, path, "/year", mode) )
                
            else:
                if hide_shared and not server.is_owned():
                    shared_flag['movie']=True
                    sharedCount += 1
                    continue
                window="Videos"
                mode=MODE_PHOTOS

            if settings.get_setting('secondary'):
                mode=MODE_GETCONTENT
                suffix=''
            else:
                suffix='/all'

                
            # Build that listing..
            WINDOW.setProperty("plexbmc.%d.uuid" % (sectionCount) , section.get_uuid())
            WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , section.get_title())
            WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , server.get_name())
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(%s,%s%s&mode=%s,return)" % ( window, base_url, path+suffix, mode))
            WINDOW.setProperty("plexbmc.%d.art"      % (sectionCount) , extraData['fanart_image'])
            WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , section.get_type())
            WINDOW.setProperty("plexbmc.%d.icon"     % (sectionCount) , extraData.get('thumb',GENERIC_THUMBNAIL))
            WINDOW.setProperty("plexbmc.%d.thumb"    % (sectionCount) , extraData.get('thumb',GENERIC_THUMBNAIL))
            WINDOW.setProperty("plexbmc.%d.partialpath" % (sectionCount) , "ActivateWindow(%s,%s%s" % (window, base_url, path))
            WINDOW.setProperty("plexbmc.%d.search" % (sectionCount) , "ActivateWindow(%s,%s%s%s&mode=%s,return)" % (window, base_url, path, "/search?type=1", mode) )
            WINDOW.setProperty("plexbmc.%d.recent" % (sectionCount) , "ActivateWindow(%s,%s%s%s&mode=%s,return)" % (window, base_url, path, "/recentlyAdded", mode) )
            WINDOW.setProperty("plexbmc.%d.all" % (sectionCount) , "ActivateWindow(%s,%s%s%s&mode=%s,return)" % (window, base_url, path, "/all", mode) )
            WINDOW.setProperty("plexbmc.%d.viewed" % (sectionCount) , "ActivateWindow(%s,%s%s%s&mode=%s,return)" % (window, base_url, path, "/recentlyViewed", mode) )
            WINDOW.setProperty("plexbmc.%d.ondeck" % (sectionCount) , "ActivateWindow(%s,%s%s%s&mode=%s,return)" % (window, base_url, path, "/onDeck", mode) )
            WINDOW.setProperty("plexbmc.%d.released" % (sectionCount) , "ActivateWindow(%s,%s%s%s&mode=%s,return)" % (window, base_url, path, "/newest", mode) )
            WINDOW.setProperty("plexbmc.%d.shared"     % (sectionCount) , "false")
            WINDOW.setProperty("plexbmc.%d.ondeck.content" % (sectionCount) , "%s%s%s&mode=%s" % (base_url, path, "/onDeck", mode) )
            WINDOW.setProperty("plexbmc.%d.recent.content" % (sectionCount) , "%s%s%s&mode=%s" % (base_url, path, "/recentlyAdded", mode) )

            log_print.debug("Building window properties index [%s] which is [%s]" % (sectionCount, section.get_title()))
            log_print.debug("PATH in use is: ActivateWindow(%s,%s%s&mode=%s,return)" % ( window, base_url, path, mode))
            sectionCount += 1

    if plex_network.is_myplex_signedin() and hide_shared and sharedCount != 0:
        WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared Content")
        WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
        WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=/&mode=%s,return)" % MODE_SHARED_ALL)
        WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "shared")
        WINDOW.setProperty("plexbmc.%d.shared"   % (sectionCount) , "true")
        sectionCount += 1

    elif sharedCount != 0:

        WINDOW.setProperty("plexbmc.%d.title"    % (sectionCount) , "Shared...")
        WINDOW.setProperty("plexbmc.%d.subtitle" % (sectionCount) , "Shared")
        WINDOW.setProperty("plexbmc.%d.type"     % (sectionCount) , "shared")
        WINDOW.setProperty("plexbmc.%d.shared"   % (sectionCount) , "true")

        if shared_flag.get('movie'):
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=/&mode=%s,return)" % MODE_SHARED_MOVIES)

        if shared_flag.get('show'):
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=/&mode=%s,return)" % MODE_SHARED_SHOWS)

        if shared_flag.get('artist'):
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(MusicFiles,plugin://plugin.video.plexbmc/?url=/&mode=%s,return)"% MODE_SHARED_MUSIC)

        if shared_flag.get('photo'):
            WINDOW.setProperty("plexbmc.%d.path"     % (sectionCount) , "ActivateWindow(Pictures,plugin://plugin.video.plexbmc/?url=/&mode=%s,return)" % MODE_SHARED_PHOTOS)

        sectionCount += 1

    # For each of the servers we have identified
    numOfServers=len(server_list)
    # shelfChannel (server_list)

    for server in server_list:

        log_print.debug(server.get_details())

        if server.is_secondary():
            continue

        if settings.get_setting('channelview'):
            WINDOW.setProperty("plexbmc.channel", "1")
            WINDOW.setProperty("plexbmc.%d.server.channel" % (serverCount) , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=%s%s&mode=%s, return" % (server.get_url_location(), "/channels/all", MODE_CHANNELVIEW ))
        else:
            WINDOW.clearProperty("plexbmc.channel")
            WINDOW.setProperty("plexbmc.%d.server.video" % (serverCount) , "%s%s&mode=%s" % (server.get_url_location(), "/video", MODE_PLEXPLUGINS ))
            WINDOW.setProperty("plexbmc.%d.server.music" % (serverCount) , "%s%s&mode=%s" % (server.get_url_location(), "/music", MODE_MUSIC ))
            WINDOW.setProperty("plexbmc.%d.server.photo" % (serverCount) , "%s%s&mode=%s" % (server.get_url_location(), "/photos", MODE_PHOTOS ))

        WINDOW.setProperty("plexbmc.%d.server.online" % (serverCount) , "%s%s&mode=%s" % (server.get_url_location(), "/system/plexonline", MODE_PLEXONLINE ))

        WINDOW.setProperty("plexbmc.%d.server" % (serverCount) , server.get_name())

        serverCount+=1

    # Clear out old data
    clear_skin_sections(WINDOW, sectionCount, int(WINDOW.getProperty("plexbmc.sectionCount") if '' else 50))

    log_print.debug("Total number of skin sections is [%s]" % sectionCount )
    log_print.debug("Total number of servers is [%s]" % numOfServers)
    WINDOW.setProperty("plexbmc.sectionCount", str(sectionCount))
    WINDOW.setProperty("plexbmc.numServers", str(numOfServers))

    if plex_network.is_myplex_signedin():
        WINDOW.setProperty("plexbmc.queue" , "ActivateWindow(VideoLibrary,plugin://plugin.video.plexbmc/?url=http://myplexqueue&mode=24,return)")
        WINDOW.setProperty("plexbmc.myplex",  "1" )

        # Now let's populate queue shelf items since we have MyPlex login
        if settings.get_setting('homeshelf') != '3':
            log_print.debug("== ENTER ==")

            root = plex_network.get_myplex_queue()
            server_address = get_master_server()
            queue_count = 1

            for media in root:
                log_print.debug("Found a queue item entry: [%s]" % (media.get('title', '').encode('UTF-8') , ))
                m_url = "plugin://plugin.video.plexbmc?url=%s&mode=%s&indirect=%s" % (get_link_url(server_address.get_url_location(), media, server_address), 18, 1)
                m_thumb = get_shelfthumb_image(media, server_address)

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

                log_print.debug("Building Queue item: %s" % media.get('title', 'Unknown').encode('UTF-8'))
                log_print.debug("Building Queue item url: %s" % m_url)
                log_print.debug("Building Queue item thumb: %s" % m_thumb)

            clear_shelf_queue(queue_count)

    else:
        WINDOW.clearProperty("plexbmc.myplex")

    full_shelf (server_list)


def clear_skin_sections(WINDOW=None, start=0, finish=50):
    log_print.debug("Clearing properties from [%s] to [%s]" % (start, finish))

    if WINDOW is None:
        WINDOW = xbmcgui.Window( 10000 )
    
    try:
        for i in range(start, finish+1):

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
            WINDOW.clearProperty("plexbmc.%d.recent.content"    % ( i ) )
            WINDOW.clearProperty("plexbmc.%d.ondeck.content"    % ( i ) )    
    except: 
        log_print.debug("Clearing stopped")
    log_print.debug("Finished clearing properties")


def full_shelf(server_list={}):
    # Gather some data and set the window properties
    log_print.debug("== ENTER ==")

    if settings.get_setting('homeshelf') == '3' or ( not settings.get_setting('movieShelf') and not settings.get_setting('tvShelf') and not settings.get_setting('musicShelf')):
        log_print.debug("Disabling all shelf items")
        clear_shelf()
        clear_ondeck_shelf()
        return

    # Get the global host variable set in settings
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
        clear_shelf(0, 0, 0, 0)
        return

    randomNumber = str(random.randint(1000000000,9999999999))

    for server_details in server_list:

        if not server_details.is_owned():
            continue

        for section in server_details.get_sections():

            if settings.get_setting('homeshelf') == '0' or settings.get_setting('homeshelf') == '2':

                tree = server_details.get_recently_added(section=section.get_key(), size=15, hide_watched=settings.get_setting('hide_watched_recent_items'))

                if tree is None:
                    log_print.debug("PLEXBMC -> RecentlyAdded items not found on: %s" % server_details.get_url_location())
                    continue

                libraryuuid = tree.get("librarySectionUUID",'').encode('utf-8')

                ep_helper = {}  # helper season counter
                for eachitem in tree:

                    if eachitem.get("type", "") == "episode":
                        key = int(eachitem.get("parentRatingKey"))  # season identifier

                        if key in ep_helper:
                            continue

                        ep_helper[key] = key  # use seasons as dict key so we can check

                    recent_list.append((eachitem, server_details, libraryuuid))

            if settings.get_setting('homeshelf') == '1' or settings.get_setting('homeshelf') == '2':

                tree = server_details.get_ondeck(section=section.get_key(),size=15)
                if tree is None:
                    print ("PLEXBMC -> OnDeck items not found on: " + server_details.get_url_location(), False)
                    continue

                libraryuuid = tree.get("librarySectionUUID",'').encode('utf-8')
                for eachitem in tree:
                    ondeck_list.append((eachitem, server_details, libraryuuid))

    log_print.debugplus("Recent object is: %s" % recent_list)
    log_print.debugplus("ondeck object is: %s" % ondeck_list)
    prefer_season=settings.get_setting('prefer_season_thumbs')
    
    # For each of the servers we have identified
    for media, source_server, libuuid in recent_list:

        if media.get('type') == "movie":

            if not settings.get_setting('movieShelf'):
                WINDOW.clearProperty("Plexbmc.LatestMovie.1.Path" )
                continue

            title_name=media.get('title','Unknown').encode('UTF-8')
            log_print.debug("Found a recent movie entry: [%s]" % title_name)

            title_url="plugin://plugin.video.plexbmc?url=%s&mode=%s&t=%s" % ( get_link_url(source_server.get_url_location(),media,source_server), MODE_PLAYSHELF, randomNumber)
            title_thumb = get_shelfthumb_image(media,source_server)

            if media.get('duration') > 0:
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


        elif media.get('type') == "season":

            title_name=media.get('parentTitle','Unknown').encode('UTF-8')
            log_print.debug("Found a recent season entry [%s]" % title_name)

            if not settings.get_setting('tvShelf'):
                WINDOW.clearProperty("Plexbmc.LatestEpisode.1.Path" )
                continue

            title_url="ActivateWindow(VideoLibrary, plugin://plugin.video.plexbmc?url=%s&mode=%s, return)" % ( get_link_url(source_server.get_url_location(),media,source_server), MODE_TVEPISODES)
            title_thumb=get_shelfthumb_image(media,source_server)

            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.Path" % recentSeasonCount, title_url )
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeTitle" % recentSeasonCount, '')
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeSeason" % recentSeasonCount, media.get('title','').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.ShowTitle" % recentSeasonCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.Thumb" % recentSeasonCount, title_thumb)
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.uuid" % recentSeasonCount, media.get('librarySectionUUID','').encode('UTF-8'))

            recentSeasonCount += 1

        elif media.get('type') == "album":

            if not settings.get_setting('musicShelf'):
                WINDOW.clearProperty("Plexbmc.LatestAlbum.1.Path" )
                continue

            title_name=media.get('parentTitle','Unknown').encode('UTF-8')
            title_url="ActivateWindow(MusicFiles, plugin://plugin.video.plexbmc?url=%s&mode=%s, return)" % ( get_link_url(source_server.get_url_location(),media,source_server), MODE_TRACKS)
            title_thumb=get_shelfthumb_image(media,source_server)

            log_print.debug("Found a recent album entry: [%s]" % title_name)

            WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Path" % recentMusicCount, title_url )
            WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Title" % recentMusicCount, media.get('title','Unknown').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Artist" % recentMusicCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Thumb" % recentMusicCount, title_thumb)

            recentMusicCount += 1

        elif media.get('type') == "photo":

            title_name=media.get('title','Unknown').encode('UTF-8')
            title_url="ActivateWindow(Pictures, plugin://plugin.video.plexbmc/?url=%s%s&mode=%s,return" % ( source_server.get_url_location(), "/recentlyAdded", MODE_PHOTOS)
            title_thumb = get_shelfthumb_image(media, source_server)

            log_print.debug("Found a recent photo entry: [%s]" % title_name)

            WINDOW.setProperty("Plexbmc.LatestPhoto.%s.Path" % recentPhotoCount, title_url)
            WINDOW.setProperty("Plexbmc.LatestPhoto.%s.Title" % recentPhotoCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestPhoto.%s.Thumb" % recentPhotoCount, title_thumb)

            recentPhotoCount += 1

        elif media.get('type') == "episode":

            title_name=media.get('title','Unknown').encode('UTF-8')
            log_print.debug("Found an Recent episode entry [%s]" % title_name)

            if not settings.get_setting('tvShelf'):
                WINDOW.clearProperty("Plexbmc.LatestEpisode.1.Path" )
                continue

            title_url="ActivateWindow(Videos, plugin://plugin.video.plexbmc?url=%s&mode=%s, return)" % ( get_link_url(source_server.get_url_location(), media, source_server, season_shelf=True), MODE_TVEPISODES)
            title_thumb = get_shelfthumb_image(media, source_server, season_thumb=True, prefer_season=prefer_season)

            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.Path" % recentSeasonCount, title_url)
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeTitle" % recentSeasonCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeNumber" % recentSeasonCount, media.get('index','').encode('utf-8'))
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeSeason" % recentSeasonCount, media.get('parentIndex','').encode('UTF-8')+'.'+media.get('index','Unknown').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeSeasonNumber" % recentSeasonCount, media.get('parentIndex','').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.ShowTitle" % recentSeasonCount, media.get('grandparentTitle','').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.Thumb" % recentSeasonCount, title_thumb)
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.uuid" % recentSeasonCount, libuuid)

            recentSeasonCount += 1

        log_print.debug(" Building Recent window title: %s\n    Building Recent window url: %s\n    Building Recent window thumb: %s" % (title_name, title_url, title_thumb))

    clear_shelf(recentMovieCount, recentSeasonCount, recentMusicCount, recentPhotoCount)

    # For each of the servers we have identified
    for media, source_server, libuuid in ondeck_list:

        if media.get('type') == "movie":

            title_name=media.get('title','Unknown').encode('UTF-8')
            log_print.debug("Found a OnDeck movie entry: [%s]" % title_name)

            if not settings.get_setting('movieShelf'):
                WINDOW.clearProperty("Plexbmc.OnDeckMovie.1.Path" )
                continue

            title_url = "plugin://plugin.video.plexbmc?url=%s&mode=%s&t=%s" % ( get_link_url(source_server.get_url_location(),media,source_server), MODE_PLAYSHELF, randomNumber)
            title_thumb = get_shelfthumb_image(media,source_server)

            if media.get('duration') > 0:
                # movie_runtime = media.get('duration', '0')
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

        elif media.get('type') == "season":

            title_name=media.get('parentTitle','Unknown').encode('UTF-8')
            log_print.debug("Found a OnDeck season entry [%s]" % title_name)

            if not settings.get_setting('tvShelf'):
                WINDOW.clearProperty("Plexbmc.OnDeckEpisode.1.Path" )
                continue

            title_url="ActivateWindow(VideoLibrary, plugin://plugin.video.plexbmc?url=%s&mode=%s, return)" % ( get_link_url(source_server.get_url_location(),media,source_server), MODE_TVEPISODES)
            title_thumb=get_shelfthumb_image(media,source_server)

            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.Path" % ondeckSeasonCount, title_url )
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.EpisodeTitle" % ondeckSeasonCount, '')
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.EpisodeSeason" % ondeckSeasonCount, media.get('title','').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.ShowTitle" % ondeckSeasonCount, title_name)
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.Thumb" % ondeckSeasonCount, title_thumb)

            ondeckSeasonCount += 1

        elif media.get('type') == "episode":

            title_name=media.get('title','Unknown').encode('UTF-8')
            log_print.debug("Found an onDeck episode entry [%s]" % title_name)

            if not settings.get_setting('tvShelf'):
                WINDOW.clearProperty("Plexbmc.OnDeckEpisode.1.Path" )
                continue

            title_url="PlayMedia(plugin://plugin.video.plexbmc?url=%s&mode=%s&t=%s)" % (get_link_url(source_server.get_url_location(), media, source_server), MODE_PLAYSHELF, randomNumber)
            title_thumb=get_shelfthumb_image(media, source_server, season_thumb=True, prefer_season=prefer_season)

            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.Path" % ondeckSeasonCount, title_url)
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.EpisodeTitle" % ondeckSeasonCount, title_name)
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.EpisodeNumber" % ondeckSeasonCount, media.get('index','').encode('utf-8'))
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.EpisodeSeason" % ondeckSeasonCount, media.get('grandparentTitle','Unknown').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.EpisodeSeasonNumber" % ondeckSeasonCount, media.get('parentIndex','').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.ShowTitle" % ondeckSeasonCount, title_name)
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.Thumb" % ondeckSeasonCount, title_thumb)
            WINDOW.setProperty("Plexbmc.OnDeckEpisode.%s.uuid" % ondeckSeasonCount, libuuid)

            ondeckSeasonCount += 1

        log_print.debug(" Building onDeck window title: %s\n    Building onDeck window url: %s\n    Building onDeck window thumb: %s" % (title_name, title_url, title_thumb))

    clear_ondeck_shelf(ondeckMovieCount, ondeckSeasonCount)


def display_content(acceptable_level, content_level):

    '''
        Takes a content Rating and decides whether it is an allowable
        level, as defined by the content filter
        @input: content rating
        @output: boolean
    '''

    log_print.info("Checking rating flag [%s] against [%s]" % (content_level, acceptable_level))

    if acceptable_level == "Adults":
        log_print.debug("OK to display")
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

                  'E' : 0 ,       # ACB Kids (hopefully)
                  'G' : 0 ,       # ACB Kids
                  'PG' : 0 ,      # ACB Kids
                  'M' : 1 ,       # ACB Teens
                  'MA15+' : 2 ,   # ADC Adults
                  'R18+' : 2 ,    # ACB Adults
                  'X18+' : 2 ,    # ACB Adults

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
        log_print.debug("Setting [None] rating as %s" % settings.get_setting('contentNone') )
        if content_map[settings.get_setting('contentNone')] <= content_map[acceptable_level]:
            log_print.debug("OK to display")
            return True
    else:
        try:
            if rating_map[content_level] <= content_map[acceptable_level]:
                log_print.debug("OK to display")
                return True
        except:
            print "Unknown rating flag [%s] whilst lookuing for [%s] - will filter for now, but needs to be added" % (content_level, acceptable_level)

    log_print.debug("NOT OK to display")
    return False


def shelf(server_list=None):
    # Gather some data and set the window properties
    log_print.debug("== ENTER ==")

    if not (settings.get_setting('movieShelf') and settings.get_setting('tvShelf') and settings.get_setting('musicShelf')) or settings.get_setting('homeshelf') == '3':
        log_print.debug("Disabling all shelf items")
        clear_shelf()
        return

    # Get the global host variable set in settings
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
        clear_shelf(0,0,0)
        return

    randomNumber=str(random.randint(1000000000,9999999999))

    for server_details in server_list():

        if server_details.is_secondary() or not server_details.is_owned():
            continue

        if settings.get_setting('homeshelf') == '0' or settings.get_setting('homeshelf') == '2':
            tree=server_details.get_server_recentlyadded()
        else:
            direction=False
            tree=server_details.get_server_ondeck()

        if tree is None:
            xbmc.executebuiltin("XBMC.Notification(Unable to contact server: %s,)" % server_details.get_name() )
            clear_shelf()
            return

        for eachitem in tree:

            if direction:
                added_list[int(eachitem.get('addedAt',0))] = (eachitem, server_details )
            else:
                added_list[full_count] = (eachitem, server_details)
                full_count += 1

    library_filter = settings.get_setting('libraryfilter')
    acceptable_level = settings.get_setting('contentFilter')

    # For each of the servers we have identified
    for media, server in sorted(added_list, reverse=direction):

        if media.get('type') == "movie":

            title_name=media.get('title','Unknown').encode('UTF-8')

            log_print.debug("Found a recent movie entry: [%s]" % title_name )

            if not settings.get_setting('movieShelf'):
                WINDOW.clearProperty("Plexbmc.LatestMovie.1.Path" )
                continue

            if not display_content( acceptable_level , media.get('contentRating') ):
                continue

            if media.get('librarySectionID') == library_filter:
                log_print.debug("SKIPPING: Library Filter match: %s = %s " % (library_filter, media.get('librarySectionID')))
                continue

            title_url="plugin://plugin.video.plexbmc?url=%s&mode=%s&t=%s" % ( get_link_url(server.get_url_location(),media,server), MODE_PLAYSHELF, randomNumber)
            title_thumb=get_thumb_image(media,server)

            WINDOW.setProperty("Plexbmc.LatestMovie.%s.Path" % movieCount, title_url)
            WINDOW.setProperty("Plexbmc.LatestMovie.%s.Title" % movieCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestMovie.%s.Thumb" % movieCount, title_thumb)

            movieCount += 1

        elif media.get('type') == "season":

            log_print.debug("Found a recent season entry [%s]" % ( media.get('parentTitle','Unknown').encode('UTF-8') , ))

            if not settings.get_setting('tvShelf'):
                WINDOW.clearProperty("Plexbmc.LatestEpisode.1.Path" )
                continue

            title_name=media.get('parentTitle','Unknown').encode('UTF-8')
            title_url="ActivateWindow(VideoLibrary, plugin://plugin.video.plexbmc?url=%s&mode=%s, return)" % ( get_link_url(server.get_url_location(),media,server), MODE_TVEPISODES)
            title_thumb=get_thumb_image(media,server)

            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.Path" % seasonCount, title_url )
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeTitle" % seasonCount, '')
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeSeason" % seasonCount, media.get('title','').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.ShowTitle" % seasonCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.Thumb" % seasonCount, title_thumb)
            seasonCount += 1

        elif media.get('type') == "album":

            if not settings.get_setting('musicShelf'):
                WINDOW.clearProperty("Plexbmc.LatestAlbum.1.Path" )
                continue

            log_print.debug("Found a recent album entry")

            title_name=media.get('parentTitle','Unknown').encode('UTF-8')
            title_url="ActivateWindow(MusicFiles, plugin://plugin.video.plexbmc?url=%s&mode=%s, return)" % ( get_link_url(server.get_url_location(),media,server), MODE_TRACKS)
            title_thumb=get_thumb_image(media,server)

            WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Path" % musicCount, title_url )
            WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Title" % musicCount, media.get('title','Unknown').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Artist" % musicCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestAlbum.%s.Thumb" % musicCount, title_thumb)
            musicCount += 1

        elif media.get('type') == "episode":

            title_name=media.get('title','Unknown').encode('UTF-8')
            log_print.debug("Found an onDeck episode entry [%s]" % title_name)

            if not settings.get_setting('tvShelf'):
                WINDOW.clearProperty("Plexbmc.LatestEpisode.1.Path" )
                continue

            title_url="PlayMedia(plugin://plugin.video.plexbmc?url=%s&mode=%s%s)" % ( get_link_url(server.get_url_location(),media,server), MODE_PLAYSHELF)
            title_thumb=server.get_kodi_header_formatted_url(media.get('grandparentThumb',''))

            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.Path" % seasonCount, title_url )
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeTitle" % seasonCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.EpisodeSeason" % seasonCount, media.get('grandparentTitle','Unknown').encode('UTF-8'))
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.ShowTitle" % seasonCount, title_name)
            WINDOW.setProperty("Plexbmc.LatestEpisode.%s.Thumb" % seasonCount, title_thumb)
            seasonCount += 1

        log_print.debug(" Building Recent window title: %s\n        Building Recent window url: %s\n        Building Recent window thumb: %s" % (title_name, title_url, title_thumb))

    clear_shelf( movieCount, seasonCount, musicCount)


def clear_shelf(movie_count=0, season_count=0, music_count=0, photo_count=0):
    # Clear out old data
    WINDOW = xbmcgui.Window(10000)
    log_print.debug("Clearing unused properties")

    try:
        for i in range(movie_count, 50+1):
            WINDOW.clearProperty("Plexbmc.LatestMovie.%s.Path" % i)
            WINDOW.clearProperty("Plexbmc.LatestMovie.%s.Title" % i)
            WINDOW.clearProperty("Plexbmc.LatestMovie.%s.Year" % i)
            WINDOW.clearProperty("Plexbmc.LatestMovie.%s.Rating" % i)
            WINDOW.clearProperty("Plexbmc.LatestMovie.%s.Duration" % i)
            WINDOW.clearProperty("Plexbmc.LatestMovie.%s.Thumb" % i)
            WINDOW.clearProperty("Plexbmc.LatestMovie.%s.uuid" % i)
        log_print.debug("Done clearing movies")
    except:
        pass

    try:
        for i in range(season_count, 50+1):
            WINDOW.clearProperty("Plexbmc.LatestEpisode.%s.Path" % i)
            WINDOW.clearProperty("Plexbmc.LatestEpisode.%s.EpisodeTitle" % i)
            WINDOW.clearProperty("Plexbmc.LatestEpisode.%s.EpisodeSeason" % i)
            WINDOW.clearProperty("Plexbmc.LatestEpisode.%s.ShowTitle" % i)
            WINDOW.clearProperty("Plexbmc.LatestEpisode.%s.Thumb" % i)
            WINDOW.clearProperty("Plexbmc.LatestEpisode.%s.uuid" % i)
        log_print.debug("Done clearing tv")
    except:
        pass

    try:
        for i in range(music_count, 25+1):
            WINDOW.clearProperty("Plexbmc.LatestAlbum.%s.Path" % i)
            WINDOW.clearProperty("Plexbmc.LatestAlbum.%s.Title" % i)
            WINDOW.clearProperty("Plexbmc.LatestAlbum.%s.Artist" % i)
            WINDOW.clearProperty("Plexbmc.LatestAlbum.%s.Thumb" % i)
        log_print.debug("Done clearing music")
    except:
        pass

    try:
        for i in range(photo_count, 25+1):
            WINDOW.clearProperty("Plexbmc.LatestPhoto.%s.Path" % i)
            WINDOW.clearProperty("Plexbmc.LatestPhoto.%s.Title" % i)
            WINDOW.clearProperty("Plexbmc.LatestPhoto.%s.Thumb" % i)
        log_print.debug("Done clearing photos")
    except:
        pass

    return


def clear_ondeck_shelf(movie_count=0, season_count=0):
    # Clear out old data
    gui_window = xbmcgui.Window(10000)
    log_print.debug("Clearing unused On Deck properties")

    try:
        for i in range(movie_count, 60+1):
            gui_window.clearProperty("Plexbmc.OnDeckMovie.%s.Path" % i)
            gui_window.clearProperty("Plexbmc.OnDeckMovie.%s.Title" % i)
            gui_window.clearProperty("Plexbmc.OnDeckMovie.%s.Thumb" % i)
            gui_window.clearProperty("Plexbmc.OnDeckMovie.%s.Rating" % i)
            gui_window.clearProperty("Plexbmc.OnDeckMovie.%s.Duration" % i)
            gui_window.clearProperty("Plexbmc.OnDeckMovie.%s.Year" % i)
            gui_window.clearProperty("Plexbmc.OnDeckMovie.%s.uuid" % i)
        log_print.debug("Done clearing On Deck movies")
    except:
        pass

    try:
        for i in range(season_count, 60+1):
            gui_window.clearProperty("Plexbmc.OnDeckEpisode.%s.Path" % i)
            gui_window.clearProperty("Plexbmc.OnDeckEpisode.%s.EpisodeTitle" % i)
            gui_window.clearProperty("Plexbmc.OnDeckEpisode.%s.EpisodeSeason" % i)
            gui_window.clearProperty("Plexbmc.OnDeckEpisode.%s.ShowTitle" % i)
            gui_window.clearProperty("Plexbmc.OnDeckEpisode.%s.Thumb" % i)
            gui_window.clearProperty("Plexbmc.OnDeckEpisode.%s.uuid" % i)
        log_print.debug("Done clearing On Deck tv")
    except:
        pass

    return


def set_shelf_channel(server_list=None):
    # Gather some data and set the window properties
    log_print.debug("== ENTER ==")

    if not settings.get_setting('channelShelf') or settings.get_setting('homeshelf') == '3':
        log_print.debug("Disabling channel shelf")
        clear_shelf_channel()
        return

    # Get the global host variable set in settings
    gui_window = xbmcgui.Window(10000)

    channel_count = 1

    if server_list is None:
        server_list = plex_network.get_server_list()

    if not server_list:
        xbmc.executebuiltin("XBMC.Notification(Unable to see any media servers,)")
        clear_shelf_channel()
        return

    for server_details in server_list:

        if server_details.is_secondary() or not server_details.is_owned():
            continue

        if not settings.get_setting('channelShelf') or settings.get_setting('homeshelf') == '3':
            gui_window.clearProperty("Plexbmc.LatestChannel.1.Path")
            return

        tree = server_details.get_channel_recentlyviewed()
        if tree is None:
            xbmc.executebuiltin("XBMC.Notification(Unable to contact server: %s, )" % server_details.get_name())
            clear_shelf_channel(0)
            return

        # For each of the servers we have identified
        for media in tree:

            log_print.debug("Found a recent channel entry")
            suffix = media.get('key').split('/')[1]

            if suffix == "photos":
                mode = MODE_PHOTOS
                channel_window = "Pictures"

            elif suffix == "video":
                mode = MODE_PLEXPLUGINS
                channel_window = "VideoLibrary"

            elif suffix == "music":
                mode = MODE_MUSIC
                channel_window = "MusicFiles"

            else:
                mode = MODE_GETCONTENT
                channel_window = "VideoLibrary"

            c_url = "ActivateWindow(%s, plugin://plugin.video.plexbmc?url=%s&mode=%s)" % (channel_window, get_link_url(server_details.get_url_location(), media, server_details), mode)
            pms_thumb = str(media.get('thumb', ''))

            if pms_thumb.startswith('/'):
                c_thumb = server_details.get_kodi_header_formatted_url(pms_thumb)

            else:
                c_thumb = pms_thumb

            gui_window.setProperty("Plexbmc.LatestChannel.%s.Path" % channel_count, c_url)
            gui_window.setProperty("Plexbmc.LatestChannel.%s.Title" % channel_count, media.get('title', 'Unknown'))
            gui_window.setProperty("Plexbmc.LatestChannel.%s.Thumb" % channel_count, c_thumb)

            channel_count += 1

            log_print.debug("Building Recent window title: %s\n      Building Recent window url: %s\n      Building Recent window thumb: %s" % (media.get('title', 'Unknown'), c_url, c_thumb))

    clear_shelf_channel(channel_count)
    return


def clear_shelf_channel(channel_count=0):

    gui_window = xbmcgui.Window(10000)

    try:
        for i in range(channel_count, 30+1):
            gui_window.clearProperty("Plexbmc.LatestChannel.%s.Path" % i)
            gui_window.clearProperty("Plexbmc.LatestChannel.%s.Title" % i)
            gui_window.clearProperty("Plexbmc.LatestChannel.%s.Thumb" % i)
        log_print.debug("Done clearing channels")
    except:
        pass

    return


def clear_shelf_queue(queue_count=0):

    gui_window = xbmcgui.Window(10000)

    try:
        for queue_number in range(queue_count, 15+1):
            gui_window.clearProperty("Plexbmc.Queue.%s.Path" % queue_number)
            gui_window.clearProperty("Plexbmc.Queue.%s.Title" % queue_number)
            gui_window.clearProperty("Plexbmc.Queue.%s.Thumb" % queue_number)
        log_print.debug("Done clearing Queue shelf")
    except:
        pass

    return


def myplex_queue():
    log_print.debug("== ENTER ==")

    if not plex_network.is_myplex_signedin():
        xbmc.executebuiltin("XBMC.Notification(myplex not configured,)")
        return

    tree = plex_network.get_myplex_queue()

    plex_plugins('https://plex.tv/playlists/queue/all', tree)
    return


def refresh_plex_library(server_uuid, section_id):
    log_print.debug("== ENTER ==")

    server = plex_network.get_server_from_uuid(server_uuid)
    server.refresh_section(section_id)

    log_print.info("Library refresh requested")
    xbmc.executebuiltin("XBMC.Notification(\"PleXBMC\",Library Refresh started,100)")
    return


def watched(server_uuid, metadata_id, watched_status='watch'):
    log_print.debug("== ENTER ==")

    server = plex_network.get_server_from_uuid(server_uuid)

    if watched_status == 'watch':
        log_print.info("Marking %s as watched" % metadata_id)
        server.mark_item_watched(metadata_id)
    else:
        log_print.info("Marking %s as unwatched" % metadata_id)
        server.mark_item_unwatched(metadata_id)

    xbmc.executebuiltin("Container.Refresh")

    return


def delete_library_media(server_uuid, metadata_id):
    log_print.debug("== ENTER ==")
    log_print.info("Deleting media at: %s" % metadata_id)

    return_value = xbmcgui.Dialog().yesno("Confirm file delete?", "Delete this item? This action will delete media and associated data files.")

    if return_value:
        log_print.debug("Deleting....")
        server = plex_network.get_server_from_uuid(server_uuid)
        server.delete_metadata(metadata_id)
        xbmc.executebuiltin("Container.Refresh")

    return True


def set_library_subtitiles(server_uuid, metadata_id):
    """
        Display a list of available Subtitle streams and allow a user to select one.
        The currently selected stream will be annotated with a *
    """
    log_print.debug("== ENTER ==")

    server = plex_network.get_server_from_uuid(server_uuid)
    tree = server.get_metadata(metadata_id)

    sub_list = ['']
    display_list = ["None"]
    fl_select = False
    for parts in tree.getiterator('Part'):

        part_id = parts.get('id')

        for streams in parts:

            if streams.get('streamType', '') == "3":

                stream_id = streams.get('id')
                lang = streams.get('languageCode', "Unknown").encode('utf-8')
                log_print.debug("Detected Subtitle stream [%s] [%s]" % (stream_id, lang))

                if streams.get('format', streams.get('codec')) == "idx":
                    log_print.debug("Stream: %s - Ignoring idx file for now" % stream_id)
                    continue
                else:
                    sub_list.append(stream_id)

                    if streams.get('selected') == '1':
                        fl_select = True
                        language = streams.get('language', 'Unknown')+"*"
                    else:
                        language = streams.get('language', 'Unknown')

                    display_list.append(language)
        break

    if not fl_select:
        display_list[0] = display_list[0]+"*"

    subtitle_screen = xbmcgui.Dialog()
    result = subtitle_screen.select('Select subtitle', display_list)
    if result == -1:
        return False

    log_print.debug("User has selected stream %s" % sub_list[result])
    server.set_subtitle_stream(part_id,  sub_list[result])

    return True


def set_library_audio(server_uuid, metadata_id):
    """
        Display a list of available audio streams and allow a user to select one.
        The currently selected stream will be annotated with a *
    """
    log_print.debug("== ENTER ==")

    server = plex_network.get_server_from_uuid(server_uuid)
    tree = server.get_metadata(metadata_id)

    audio_list = []
    display_list = []
    for parts in tree.getiterator('Part'):

        part_id = parts.get('id')

        for streams in parts:

            if streams.get('streamType', '') == "2":

                stream_id = streams.get('id')
                audio_list.append(stream_id)
                lang = streams.get('languageCode', "Unknown")

                log_print.debug("Detected Audio stream [%s] [%s] " % (stream_id, lang))

                if streams.get('channels', 'Unknown') == '6':
                    channels = "5.1"
                elif streams.get('channels', 'Unknown') == '7':
                    channels = "6.1"
                elif streams.get('channels', 'Unknown') == '2':
                    channels = "Stereo"
                else:
                    channels = streams.get('channels', 'Unknown')

                if streams.get('codec', 'Unknown') == "ac3":
                    codec = "AC3"
                elif streams.get('codec', 'Unknown') == "dca":
                    codec = "DTS"
                else:
                    codec = streams.get('codec', 'Unknown')

                language = "%s (%s %s)" % (streams.get('language', 'Unknown').encode('utf-8'), codec, channels)

                if streams.get('selected') == '1':
                    language = language+"*"

                display_list.append(language)
        break

    audio_screen = xbmcgui.Dialog()
    result = audio_screen.select('Select audio', display_list)
    if result == -1:
        return False

    log_print.debug("User has selected stream %s" % audio_list[result])

    server.set_audio_stream(part_id, audio_list[result])

    return True


def set_window_heading(tree):
    gui_window = xbmcgui.Window(xbmcgui.getCurrentWindowId())
    try:
        gui_window.setProperty("heading", tree.get('title1'))
    except:
        gui_window.clearProperty("heading")
    try:
        gui_window.setProperty("heading2", tree.get('title2'))
    except:
        gui_window.clearProperty("heading2")


def get_master_server(all=False):
    log_print.debug("== ENTER ==")

    possible_servers = []
    current_master = settings.get_setting('masterServer')
    for serverData in plex_network.get_server_list():
        log_print.debug(str(serverData))
        if serverData.get_master() == 1:
            possible_servers.append(serverData)
    log_print.debug("Possible master servers are: %s" % possible_servers)

    if all:
        return possible_servers

    if len(possible_servers) > 1:
        preferred = "local"
        for serverData in possible_servers:
            if serverData.get_name == current_master:
                log_print.debug("Returning current master")
                return serverData
            if preferred == "any":
                log_print.debug("Returning 'any'")
                return serverData
            else:
                if serverData.get_discovery() == preferred:
                    log_print.debug("Returning local")
                    return serverData
    elif len(possible_servers) == 0:
        return

    return possible_servers[0]


def set_master_server():
    log_print.debug("== ENTER ==")

    servers = get_master_server(True)
    log_print.debug(str(servers))

    current_master = settings.get_setting('masterServer')

    display_option_list = []
    for address in servers:
        found_server = address.get_name()
        if found_server == current_master:
            found_server = found_server+"*"
        display_option_list.append(found_server)

    audio_select_screen = xbmcgui.Dialog()
    result = audio_select_screen.select('Select master server', display_option_list)
    if result == -1:
        return False

    log_print.debug("Setting master server to: %s" % servers[result].get_name())
    settings.update_master_server(servers[result].get_name())
    return


def display_known_servers():
    known_servers = plex_network.get_server_list()
    display_list = []

    for device in known_servers:
        name = device.get_name()
        status = device.get_status()
        if device.is_secure():
            secure = "SSL"
        else:
            secure = "Not Secure"

        log_print.debug("Device: %s [%s] [%s]" % (name, status, secure))
        log_print.debugplus("Full device dump [%s]" % device.__dict__)
        display_list.append("%s [%s] [%s]" % (name, status, secure))

    server_display_screen = xbmcgui.Dialog()
    server_display_screen.select('Known server list', display_list)
    return


def display_plex_servers(url):
    log_print.debug("== ENTER ==")
    type = url.split('/')[2]
    log_print.debug("Displaying entries for %s" % type)
    servers = plex_network.get_server_list()
    servers_list = len(servers)

    # For each of the servers we have identified
    for mediaserver in servers:

        if mediaserver.is_secondary():
            continue

        details = {'title': mediaserver.get_name()}

        extra_data = {}

        if type == "video":
            extra_data['mode'] = MODE_PLEXPLUGINS
            s_url = '%s%s' % (mediaserver.get_url_location(), '/video')
            if servers_list == 1:
                plex_plugins(s_url)
                return

        elif type == "online":
            extra_data['mode'] = MODE_PLEXONLINE
            s_url = '%s%s' % (mediaserver.get_url_location(), '/system/plexonline')
            if servers_list == 1:
                plex_online(s_url)
                return

        elif type == "music":
            extra_data['mode'] = MODE_MUSIC
            s_url = '%s%s' % (mediaserver.get_url_location(), '/music')
            if servers_list == 1:
                music(s_url)
                return

        elif type == "photo":
            extra_data['mode'] = MODE_PHOTOS
            s_url = '%s%s' % (mediaserver.get_url_location(), '/photos')
            if servers_list == 1:
                photo(s_url)
                return
        else:
            s_url = None

        add_item_to_gui(s_url, details, extra_data)

    xbmcplugin.endOfDirectory(pluginhandle, cacheToDisc=settings.get_setting('kodicache'))


def switch_user():
    # Get listof users
    user_list = plex_network.get_plex_home_users()
    # zero means we are not plexHome'd up
    if user_list is None or len(user_list) == 1:
        log_print("No users listed or only one user, plexHome not enabled")
        return False

    log_print("found %s users: %s" % (len(user_list), user_list.keys()))

    # Get rid of currently logged in user.
    user_list.pop(plex_network.get_myplex_user(), None)
    
    select_screen = xbmcgui.Dialog()
    result = select_screen.select('Switch User', user_list.keys())
    if result == -1:
        log_print("Dialog cancelled")
        return False

    log_print("user [%s] selected" % user_list.keys()[result])
    user = user_list[user_list.keys()[result]]

    pin = None
    if user['protected'] == '1':
        log_print("Protected user [%s], requesting password" % user['title'])
        pin = select_screen.input("Enter PIN", type=xbmcgui.INPUT_NUMERIC, option=xbmcgui.ALPHANUM_HIDE_INPUT)

    success, msg = plex_network.switch_plex_home_user(user['id'], pin)

    if not success:
        xbmcgui.Dialog().ok("Switch Failed", msg)
        return False

    return True 

# #So this is where we really start the addon 
log_print = PrintDebug("PleXBMC")

print "PleXBMC -> Running PleXBMC: %s " % GLOBAL_SETUP['__version__']

wake_servers()

if settings.get_debug() >= log_print.DEBUG_INFO:
    print "PleXBMC -> Script argument is %s" % sys.argv
    print "PleXBMC -> Running Python: %s" % str(sys.version_info)
    print "PleXBMC -> CWD is set to: %s" % GLOBAL_SETUP['__cwd__']
    print "PleXBMC -> Platform: %s" % GLOBAL_SETUP['platform']
    print "PleXBMC -> Setting debug: %s" % log_print.get_name(settings.get_debug())
    print "PleXBMC -> FullRes Thumbs are set to: %s" % settings.get_setting('fullres_thumbs')
    print "PleXBMC -> Settings streaming: %s" % settings.get_stream()
    print "PleXBMC -> Setting filter menus: %s" % settings.get_setting('secondary')
    print "PleXBMC -> Flatten is: %s" % settings.get_setting('flatten')
    if settings.get_setting('streamControl') == SUB_AUDIO_XBMC_CONTROL:
        print "PleXBMC -> Setting stream Control to : XBMC CONTROL"
    elif settings.get_setting('streamControl') == SUB_AUDIO_PLEX_CONTROL:
        print "PleXBMC -> Setting stream Control to : PLEX CONTROL"
    elif settings.get_setting('streamControl') == SUB_AUDIO_NEVER_SHOW:
        print "PleXBMC -> Setting stream Control to : NEVER SHOW"

    print "PleXBMC -> Force DVD playback: %s" % settings.get_setting('forcedvd')
    print "PleXBMC -> SMB IP Override: %s" % settings.get_setting('nasoverride')
    if settings.get_setting('nasoverride') and not settings.get_setting('nasoverrideip'):
        print "PleXBMC -> No NAS IP Specified.  Ignoring setting"
    else:
        print "PleXBMC -> NAS IP: " + settings.get_setting('nasoverrideip')
else:
    print "PleXBMC -> Debug is turned off.  Running silent"

pluginhandle = 0
plex_network = plex.Plex(load=False)


def start_plexbmc():
    try:
        params = get_params(sys.argv[2])
    except:
        params = {}

    # Now try and assign some data to them
    param_url = params.get('url')
    command = None

    if param_url:
        if param_url.startswith('http') or param_url.startswith('file'):
            param_url = urllib.unquote(param_url)
        elif param_url.startswith('cmd'):
            command = urllib.unquote(param_url).split(':')[1]

    param_name = urllib.unquote_plus(params.get('name', ""))
    mode = int(params.get('mode', -1))
    play_transcode = True if int(params.get('transcode', 0)) == 1 else False
    param_identifier = params.get('identifier')
    param_indirect = params.get('indirect')
    force = params.get('force')

    if command is None:
        try:
            command = sys.argv[1]
        except:
            pass

    if command == "cacherefresh":
        plex_network.delete_cache()
        xbmc.executebuiltin("ReloadSkin()")
    # Open the add-on settings page, then refresh plugin
    elif command == "setting":
        settings.open_settings()
        if xbmcgui.getCurrentWindowId() == 10000:
            log_print.debug("Currently in home - refreshing to allow new settings to be taken")
            xbmc.executebuiltin("ReloadSkin()")
    # Refresh the current XBMC listing    
    elif command == "refresh":
        xbmc.executebuiltin("Container.Refresh")
    elif command == "switchuser":
        if switch_user():
            clear_skin_sections()
            clear_ondeck_shelf()
            clear_shelf()
            gui_window = xbmcgui.Window(10000)
            gui_window.setProperty("plexbmc.plexhome_user", str(plex_network.get_myplex_user()))
            gui_window.setProperty("plexbmc.plexhome_avatar", str(plex_network.get_myplex_avatar()))
            if xbmcgui.getCurrentWindowId() == 10000:
                log_print.debug("Currently in home - refreshing to allow new settings to be taken")
                xbmc.executebuiltin("ReloadSkin()")
            else:
                xbmc.executebuiltin("Container.Refresh")
        else:
            log_print.info("Switch User Failed")

    elif command == "signout":
        if not plex_network.is_admin():
            return xbmcgui.Dialog().ok("Sign Out", "To sign out you must be logged in as an admin user. Please switch user and try again")

        ret = xbmcgui.Dialog().yesno("myplex", "You are currently signed into myPlex. Are you sure you want to sign out?")
        if ret:
            plex_network.signout()
            gui_window = xbmcgui.Window(10000)
            gui_window.clearProperty("plexbmc.plexhome_user")
            gui_window.clearProperty("plexbmc.plexhome_avatar")
            clear_skin_sections()
            clear_ondeck_shelf()
            clear_shelf()
            xbmc.executebuiltin("ReloadSkin()")

    elif command == "signin":
        from resources.lib.plex import plexsignin
        signin_window = plexsignin.PlexSignin('Myplex Login')
        signin_window.set_authentication_target(plex_network)
        signin_window.start()
        del signin_window

    elif command == "signintemp":
        # Awful hack to get around running a script from a listitem..
        xbmc.executebuiltin('XBMC.RunScript(plugin.video.plexbmc, signin)')       

    elif command == "managemyplex":

        if not plex_network.is_myplex_signedin():
            ret = xbmcgui.Dialog().yesno("Manage myplex", "You are not currently logged into myplex.  Please continue to sign in, or cancel to return")
            if ret:
                xbmc.executebuiltin('XBMC.RunScript(plugin.video.plexbmc, signin)')       
            else:
                return

        elif not plex_network.is_admin():
            return xbmcgui.Dialog().ok("Manage myplex", "To access these screens you must be logged in as an admin user.  Please switch user and try again")

        from resources.lib.plex import plexsignin
        manage_window = plexsignin.PlexManage('Manage myplex')
        manage_window.set_authentication_target(plex_network)
        manage_window.start()
        del manage_window
    elif command == "displayservers":
        plex_network.load()
        display_known_servers()

    else:
        plex_network.load()

        # Populate Skin variables
        if command == "skin":
            try:
                type = sys.argv[2]
            except:
                type = None
            skin(type=type)

        elif command == "amberskin":
            amberskin()

        # Populate recently/on deck shelf items 
        elif command == "shelf":
            shelf()

        # Populate channel recently viewed items    
        elif command == "channelShelf":
            set_shelf_channel()
            pass
            
        # Send a library update to Plex    
        elif command == "update":
            server_uuid = sys.argv[2]
            section_id = sys.argv[3]
            refresh_plex_library(server_uuid, section_id)

        # Mark an item as watched/unwatched in plex    
        elif command == "watch":
            server_uuid = sys.argv[2]
            metadata_id = sys.argv[3]
            watch_status = sys.argv[4]
            watched(server_uuid, metadata_id, watch_status)

        # nt currently used              
        elif command == "refreshplexbmc":
            plex_network.discover()
            server_list = plex_network.get_server_list()
            skin(server_list)
            shelf(server_list)
            set_shelf_channel(server_list)

        # delete media from PMS    
        elif command == "delete":
            server_uuid = sys.argv[2]
            metadata_id = sys.argv[3]
            delete_library_media(server_uuid, metadata_id)

        # Display subtitle selection screen    
        elif command == "subs":
            server_uuid = sys.argv[2]
            metadata_id = sys.argv[3]
            set_library_subtitiles(server_uuid, metadata_id)

        # Display audio streanm selection screen    
        elif command == "audio":
            server_uuid = sys.argv[2]
            metadata_id = sys.argv[3]
            set_library_audio(server_uuid, metadata_id)

        # Allow a mastre server to be selected (for myplex queue)    
        elif command == "master":
            set_master_server()

        # else move to the main code    
        else:

            global pluginhandle
            try:
                pluginhandle = int(command)
            except:
                pass

            gui_window = xbmcgui.Window(xbmcgui.getCurrentWindowId())
            gui_window.clearProperty("heading")
            gui_window.clearProperty("heading2")

            if settings.get_debug() >= log_print.DEBUG_INFO:
                print "PleXBMC -> Mode: %s " % mode
                print "PleXBMC -> URL: %s" % param_url
                print "PleXBMC -> Name: %s" % param_name
                print "PleXBMC -> identifier: %s" % param_identifier

            # Run a function based on the mode variable that was passed in the URL
            if (mode is None) or (param_url is None) or (len(param_url) < 1):
                display_sections()

            elif mode == MODE_GETCONTENT:
                get_content(param_url)

            elif mode == MODE_TVSHOWS:
                process_tvshows(param_url)

            elif mode == MODE_MOVIES:
                process_movies(param_url)

            elif mode == MODE_ARTISTS:
                artist(param_url)

            elif mode == MODE_TVSEASONS:
                process_tvseasons(param_url)

            elif mode == MODE_PLAYLIBRARY:
                play_library_media(param_url, force=force, override=play_transcode)

            elif mode == MODE_PLAYSHELF:
                play_library_media(param_url, full_data=True, shelf=True)

            elif mode == MODE_TVEPISODES:
                process_tvepisodes(param_url)

            elif mode == MODE_PLEXPLUGINS:
                plex_plugins(param_url)

            elif mode == MODE_PROCESSXML:
                process_xml(param_url)

            elif mode == MODE_BASICPLAY:
                play_media_stream(param_url)

            elif mode == MODE_ALBUMS:
                albums(param_url)

            elif mode == MODE_TRACKS:
                tracks(param_url)

            elif mode == MODE_PHOTOS:
                photo(param_url)

            elif mode == MODE_MUSIC:
                music(param_url)

            elif mode == MODE_VIDEOPLUGINPLAY:
                play_video_channel(param_url, param_identifier, param_indirect)

            elif mode == MODE_PLEXONLINE:
                plex_online(param_url)

            elif mode == MODE_CHANNELINSTALL:
                install(param_url, param_name)

            elif mode == MODE_CHANNELVIEW:
                channel_view(param_url)

            elif mode == MODE_PLAYLIBRARY_TRANSCODE:
                play_library_media(param_url, override=True)

            elif mode == MODE_MYPLEXQUEUE:
                myplex_queue()

            elif mode == MODE_CHANNELSEARCH:
                channel_search(param_url, params.get('prompt'))

            elif mode == MODE_CHANNELPREFS:
                channel_settings(param_url, params.get('id'))

            elif mode == MODE_SHARED_MOVIES:
                display_sections(filter="movies", display_shared=True)

            elif mode == MODE_SHARED_SHOWS:
                display_sections(filter="tvshows", display_shared=True)

            elif mode == MODE_SHARED_PHOTOS:
                display_sections(filter="photos", display_shared=True)

            elif mode == MODE_SHARED_MUSIC:
                display_sections(filter="music", display_shared=True)

            elif mode == MODE_SHARED_ALL:
                display_sections(display_shared=True)

            elif mode == MODE_DELETE_REFRESH:
                plex_network.delete_cache()
                xbmc.executebuiltin("Container.Refresh")

            elif mode == MODE_PLAYLISTS:
                process_xml(param_url)

            elif mode == MODE_DISPLAYSERVERS:
                display_plex_servers(param_url)

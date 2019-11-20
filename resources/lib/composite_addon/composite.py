"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

import copy
import sys
import time
import random
import datetime

import xbmc
import xbmcplugin
import xbmcgui

from six.moves.urllib_parse import urlparse
from six.moves.urllib_parse import quote
from six.moves.urllib_parse import unquote
from six.moves.urllib_parse import quote_plus
from six.moves.urllib_parse import unquote_plus
from six.moves import range

from .common import CONFIG
from .common import MODES
from .common import STREAM_CONTROL
from .common import PrintDebug
from .common import get_argv
from .common import get_handle
from .common import encode_utf8
from .common import i18n
from .common import settings
from .common import wake_servers
from .common import write_pickled

from .plex import plex


def select_media_type(part_data, server, dvdplayback=False):
    stream = part_data['key']
    f = part_data['file']
    filelocation = ''

    if (f is None) or (settings.get_stream() == '1'):
        log_print.debug('Selecting stream')
        return server.get_formatted_url(stream)

    # First determine what sort of 'file' file is

    if f[0:2] == '\\\\':
        log_print.debug('Detected UNC source file')
        ftype = 'UNC'
    elif f[0:1] == '/' or f[0:1] == '\\':
        log_print.debug('Detected unix source file')
        ftype = 'nixfile'
    elif f[1:3] == ':\\' or f[1:2] == ':/':
        log_print.debug('Detected windows source file')
        ftype = 'winfile'
    else:
        log_print.debug('Unknown file type source: %s' % f)
        ftype = None

    # 0 is auto select.  basically check for local file first, then stream if not found
    if settings.get_stream() == '0':
        # check if the file can be found locally
        if ftype == 'nixfile' or ftype == 'winfile':
            log_print.debug('Checking for local file')
            try:
                exists = open(f, 'r')
                log_print.debug('Local f found, will use this')
                exists.close()
                return 'file:%s' % f
            except:
                pass

        log_print.debug('No local file')
        if dvdplayback:
            log_print.debug('Forcing SMB for DVD playback')
            settings.set_stream('2')
        else:
            return server.get_formatted_url(stream)

    # 2 is use SMB
    elif settings.get_stream() == '2' or settings.get_stream() == '3':

        f = unquote(f)
        if settings.get_stream() == '2':
            protocol = 'smb'
        else:
            protocol = 'afp'

        log_print.debug('Selecting smb/unc')
        if ftype == 'UNC':
            filelocation = '%s:%s' % (protocol, f.replace('\\', '/'))
        else:
            # Might be OSX type, in which case, remove Volumes and replace with server
            server = server.get_location().split(':')[0]
            loginstring = ''

            if settings.get_setting('nasoverride'):
                if settings.get_setting('nasoverrideip'):
                    server = settings.get_setting('nasoverrideip')
                    log_print.debug('Overriding server with: %s' % server)

                if settings.get_setting('nasuserid'):
                    loginstring = '%s:%s@' % (settings.get_setting('nasuserid'), settings.get_setting('naspass'))
                    log_print.debug('Adding AFP/SMB login info for user: %s' % settings.get_setting('nasuserid'))

            if f.find('Volumes') > 0:
                filelocation = '%s:/%s' % (protocol, f.replace('Volumes', loginstring + server))
            else:
                if ftype == 'winfile':
                    filelocation = ('%s://%s%s/%s' % (protocol, loginstring, server, f[3:].replace('\\', '/')))
                else:
                    # else assume its a file local to server available over smb/samba.  Add server name to file path.
                    filelocation = '%s://%s%s%s' % (protocol, loginstring, server, f)

        if settings.get_setting('nasoverride') and settings.get_setting('nasroot'):
            # Re-root the file path
            log_print.debug('Altering path %s so root is: %s' % (filelocation, settings.get_setting('nasroot')))
            if '/' + settings.get_setting('nasroot') + '/' in filelocation:
                components = filelocation.split('/')
                index = components.index(settings.get_setting('nasroot'))
                for _ in list(range(3, index)):
                    components.pop(3)
                filelocation = '/'.join(components)
    else:
        log_print.debug('No option detected, streaming is safest to choose')
        filelocation = server.get_formatted_url(stream)

    log_print.debug('Returning URL: %s ' % filelocation)
    return filelocation


def add_item_to_gui(url, details, extra_data, context=None, folder=True):
    log_print.debug('Adding [%s]\n'
                    'Passed details: %s\n'
                    'Passed extra_data: %s' % (details.get('title', i18n('Unknown')), details, extra_data))

    is_file = url.startswith('cmd:')

    # Create the URL to pass to the item
    if not folder and extra_data['type'] == 'image':
        link_url = url
    elif url.startswith('http') or url.startswith('file'):
        link_url = '%s?url=%s&mode=%s' % (get_argv()[0], quote(url), extra_data.get('mode', 0))
    else:
        link_url = '%s?url=%s&mode=%s' % (get_argv()[0], url, extra_data.get('mode', 0))

    if extra_data.get('parameters'):
        for argument, value in extra_data.get('parameters').items():
            link_url = '%s&%s=%s' % (link_url, argument, quote(value))

    title = item_translate(details.get('title', i18n('Unknown')), extra_data.get('source'), folder)

    log_print.debug('URL to use for listing: %s' % link_url)
    if CONFIG['kodi_version'] >= 18:
        liz = xbmcgui.ListItem(title, offscreen=True)
    else:
        liz = xbmcgui.ListItem(title)

    set_info_type = extra_data.get('type', 'Video')
    info_labels = copy.deepcopy(details)
    if set_info_type.lower() == 'folder' or set_info_type.lower() == 'file':
        set_info_type = 'Video'

    # Set the properties of the item, such as summary, name, season, etc
    liz.setInfo(type=set_info_type, infoLabels=info_labels)

    # Music related tags
    if extra_data.get('type', '').lower() == 'music':
        liz.setProperty('Artist_Genre', details.get('genre', ''))
        liz.setProperty('Artist_Description', extra_data.get('plot', ''))
        liz.setProperty('Album_Description', extra_data.get('plot', ''))

    # For all end items    
    if not folder:
        liz.setProperty('IsPlayable', 'true')

        if extra_data.get('type', 'video').lower() == 'video':
            liz.setProperty('TotalTime', str(extra_data.get('duration')))
            liz.setProperty('ResumeTime', str(extra_data.get('resume')))

            if not settings.get_setting('skipflags'):
                log_print.debug('Setting VrR as : %s' % extra_data.get('VideoResolution', ''))
                liz.setProperty('VideoResolution', extra_data.get('VideoResolution', ''))
                liz.setProperty('VideoCodec', extra_data.get('VideoCodec', ''))
                liz.setProperty('AudioCodec', extra_data.get('AudioCodec', ''))
                liz.setProperty('AudioChannels', extra_data.get('AudioChannels', ''))
                liz.setProperty('VideoAspect', extra_data.get('VideoAspect', ''))

                video_codec = {}
                if extra_data.get('xbmc_VideoCodec'):
                    video_codec['codec'] = extra_data.get('xbmc_VideoCodec')
                if extra_data.get('xbmc_VideoAspect'):
                    video_codec['aspect'] = float(extra_data.get('xbmc_VideoAspect'))
                if extra_data.get('xbmc_height'):
                    video_codec['height'] = int(extra_data.get('xbmc_height'))
                if extra_data.get('xbmc_width'):
                    video_codec['width'] = int(extra_data.get('xbmc_width'))
                if extra_data.get('duration'):
                    video_codec['duration'] = int(extra_data.get('duration'))

                audio_codec = {}
                if extra_data.get('xbmc_AudioCodec'):
                    audio_codec['codec'] = extra_data.get('xbmc_AudioCodec')
                if extra_data.get('xbmc_AudioChannels'):
                    audio_codec['channels'] = int(extra_data.get('xbmc_AudioChannels'))

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
    thumb = extra_data.get('thumb', CONFIG['icon'])
    banner = extra_data.get('banner', '')

    # tvshow poster
    season_thumb = extra_data.get('season_thumb', '')

    if season_thumb:
        poster = season_thumb
    else:
        if not folder:
            poster = extra_data.get('thumb', 'DefaultPoster.png')
        else:
            poster = thumb

    if season_thumb:
        log_print.debug('Setting season Thumb as %s' % season_thumb)
        liz.setProperty('seasonThumb', '%s' % season_thumb)

    liz.setArt({'fanart': fanart, 'poster': poster, 'banner': banner, 'thumb': thumb, 'icon': thumb})

    if context is not None:
        if not folder and extra_data.get('type', 'video').lower() == 'video':
            # Play Transcoded
            context.insert(0, (i18n('Play Transcoded'), 'PlayMedia(%s&transcode=1)' % link_url,))
            log_print.debug('Setting transcode options to [%s&transcode=1]' % link_url)
        log_print.debug('Building Context Menus')
        liz.addContextMenuItems(context, settings.get_setting('contextreplace'))

    if is_file:
        folder = False
        liz.setProperty('IsPlayable', 'false')

    return xbmcplugin.addDirectoryItem(handle=get_handle(), url=link_url, listitem=liz, isFolder=folder)


def display_sections(cfilter=None, display_shared=False):
    xbmcplugin.setContent(get_handle(), 'files')

    server_list = plex_network.get_server_list()
    log_print.debug('Using list of %s servers: %s' % (len(server_list), server_list))

    for server in server_list:

        server.discover_sections()

        for section in server.get_sections():

            if display_shared and server.is_owned():
                continue

            if settings.get_setting('prefix_server') == '0' or \
                    (settings.get_setting('prefix_server') == '1' and len(server_list) > 1):
                details = {'title': '%s: %s' % (server.get_name(), section.get_title())}
            else:
                details = {'title': section.get_title()}

            extra_data = {'fanart_image': server.get_fanart(section),
                          'type': 'Folder'}

            # Determine what we are going to do process after a link selected by the user, based on the content we find

            path = section.get_path()

            if section.is_show():
                mode = MODES.TVSHOWS
                if (cfilter is not None) and (cfilter != 'tvshows'):
                    continue

            elif section.is_movie():
                mode = MODES.MOVIES
                if (cfilter is not None) and (cfilter != 'movies'):
                    continue

            elif section.is_artist():
                mode = MODES.ARTISTS
                if (cfilter is not None) and (cfilter != 'music'):
                    continue

            elif section.is_photo():
                mode = MODES.PHOTOS
                if (cfilter is not None) and (cfilter != 'photos'):
                    continue
            else:
                log_print.debug('Ignoring section %s of type %s as unable to process'
                                % (details['title'], section.get_type()))
                continue

            if settings.get_setting('secondary'):
                mode = MODES.GETCONTENT
            else:
                path = path + '/all'

            extra_data['mode'] = mode
            section_url = '%s%s' % (server.get_url_location(), path)

            if not settings.get_setting('skipcontextmenus'):
                context = [(i18n('Refresh library section'), 'RunScript(' + CONFIG['id'] + ', update, %s, %s)'
                            % (server.get_uuid(), section.get_key()))]
            else:
                context = None

            # Build that listing..
            add_item_to_gui(section_url, details, extra_data, context)

    if display_shared:
        xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=settings.get_setting('kodicache'))
        return

    # For each of the servers we have identified            
    if plex_network.is_myplex_signedin():
        details = {'title': i18n('myPlex Queue')}
        extra_data = {'type': 'Folder', 'mode': MODES.MYPLEXQUEUE}
        add_item_to_gui('http://myplexqueue', details, extra_data)

    for server in server_list:

        if server.is_offline() or server.is_secondary():
            continue

        # Plex plugin handling
        if (cfilter is not None) and (cfilter != 'plugins'):
            continue

        if settings.get_setting('prefix_server') == '0' or \
                (settings.get_setting('prefix_server') == '1' and len(server_list) > 1):
            prefix = server.get_name() + ': '
        else:
            prefix = ''

        details = {'title': prefix + i18n('Channels')}
        extra_data = {'type': 'Folder', 'mode': MODES.CHANNELVIEW}

        u = '%s/channels/all' % server.get_url_location()
        add_item_to_gui(u, details, extra_data)

        # Create plexonline link
        details = {'title': prefix + i18n('Plex Online')}
        extra_data = {'type': 'Folder', 'mode': MODES.PLEXONLINE}

        u = '%s/system/plexonline' % server.get_url_location()
        add_item_to_gui(u, details, extra_data)

        # create playlist link
        details = {'title': prefix + i18n('Playlists')}
        extra_data = {'type': 'Folder', 'mode': MODES.PLAYLISTS}

        u = '%s/playlists' % server.get_url_location()
        add_item_to_gui(u, details, extra_data)

    if plex_network.is_myplex_signedin():

        if plex_network.is_plexhome_enabled():
            details = {'title': i18n('Switch User')}
            extra_data = {'type': 'file'}

            u = 'cmd:switchuser'
            add_item_to_gui(u, details, extra_data)

        details = {'title': i18n('Sign Out')}
        extra_data = {'type': 'file'}

        u = 'cmd:signout'
        add_item_to_gui(u, details, extra_data)
    else:
        details = {'title': i18n('Sign In')}
        extra_data = {'type': 'file'}

        u = 'cmd:signintemp'
        add_item_to_gui(u, details, extra_data)

    details = {'title': i18n('Display Servers')}
    extra_data = {'type': 'file'}
    data_url = 'cmd:displayservers'
    add_item_to_gui(data_url, details, extra_data)

    if settings.get_setting('cache'):
        details = {'title': i18n('Refresh Data')}
        extra_data = {'type': 'file'}
        u = 'cmd:delete_refresh'
        add_item_to_gui(u, details, extra_data)

    # All XML entries have been parsed and we are ready to allow the user to browse around.  So end the screen listing.
    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=settings.get_setting('kodicache'))


def process_movies(url, tree=None):
    xbmcplugin.setContent(get_handle(), 'movies')

    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE_IGNORE_THE)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_DATEADDED)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_DATE)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_VIDEO_RATING)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_VIDEO_YEAR)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_VIDEO_RUNTIME)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_MPAA_RATING)

    # get the server name from the URL, which was passed via the on screen listing..

    server = plex_network.get_server_from_url(url)

    tree = get_xml(url, tree)
    if tree is None:
        return

    random_number = str(random.randint(1000000000, 9999999999))

    # Find all the video tags, as they contain the data we need to link to a file.
    start_time = time.time()
    count = 0
    for movie in tree:

        if movie.tag == 'Video':
            movie_tag(url, server, tree, movie, random_number)
            count += 1

    log_print.debug('PROCESS: It took %s seconds to process %s items' % (time.time() - start_time, count))
    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=settings.get_setting('kodicache'))


def build_context_menu(url, item_data, server):
    context = []
    url_parts = urlparse(url)
    section = url_parts.path.split('/')[3]

    additional_context_menus = item_data.get('additional_context_menus', {})
    item_id = item_data.get('ratingKey', '0')
    playlist_item_id = item_data.get('playlist_item_id')
    library_section_uuid = item_data.get('library_section_uuid')

    if additional_context_menus.get('go_to'):
        parent_id = item_data.get('parentRatingKey')
        grandparent_id = item_data.get('grandparentRatingKey')
        if parent_id and item_data.get('season') is not None:
            context.append((i18n('Go to') % (i18n('Season') + ' ' + str(item_data.get('season', 0))),
                            'Container.Update(plugin://%s/?mode=6&url=%s&rating_key=%s)' % (CONFIG['id'], server.get_uuid(), parent_id)))
        if grandparent_id and item_data.get('tvshowtitle'):
            context.append((i18n('Go to') % item_data.get('tvshowtitle'),
                            'Container.Update(plugin://%s/?mode=4&url=%s&rating_key=%s)' % (CONFIG['id'], server.get_uuid(), grandparent_id)))

    context.append((i18n('Mark as unwatched'), 'RunScript(' + CONFIG['id'] + ', watch, %s, %s, %s)' % (server.get_uuid(), item_id, 'unwatch')))
    context.append((i18n('Mark as watched'), 'RunScript(' + CONFIG['id'] + ', watch, %s, %s, %s)' % (server.get_uuid(), item_id, 'watch')))

    if playlist_item_id:
        playlist_title = item_data.get('playlist_title')
        context.append((i18n('Delete from playlist'), 'RunScript(' + CONFIG['id'] + ', delete_playlist_item, %s, %s, %s, %s, %s)' % (server.get_uuid(), item_id, playlist_title, playlist_item_id, url_parts.path)))
    elif library_section_uuid:
        context.append((i18n('Add to playlist'), 'RunScript(' + CONFIG['id'] + ', add_playlist_item, %s, %s, %s)' % (server.get_uuid(), item_id, library_section_uuid)))

    if settings.get_setting('showdeletecontextmenu'):
        context.append((i18n('Delete'), 'RunScript(' + CONFIG['id'] + ', delete, %s, %s)' % (server.get_uuid(), item_id)))

    context.append((i18n('Audio'), 'RunScript(' + CONFIG['id'] + ', audio, %s, %s)' % (server.get_uuid(), item_id)))
    context.append((i18n('Subtitles'), 'RunScript(' + CONFIG['id'] + ', subs, %s, %s)' % (server.get_uuid(), item_id)))
    context.append((i18n('Update library'), 'RunScript(' + CONFIG['id'] + ', update, %s, %s)' % (server.get_uuid(), section)))
    context.append((i18n('Refresh'), 'RunScript(' + CONFIG['id'] + ', refresh)'))

    log_print.debug('Using context menus: %s' % context)

    return context


def process_tvshows(url, tree=None):
    xbmcplugin.setContent(get_handle(), 'tvshows')
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE_IGNORE_THE)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_DATE)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_VIDEO_RATING)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_VIDEO_YEAR)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_MPAA_RATING)

    # Get the URL and server name.  Get the XML and parse
    tree = get_xml(url, tree)
    if tree is None:
        return

    server = plex_network.get_server_from_url(url)

    # For each directory tag we find
    show_tags = tree.findall('Directory')
    for show in show_tags:

        tempgenre = []

        for child in show:
            if child.tag == 'Genre':
                tempgenre.append(child.get('tag', ''))

        _watched = int(show.get('viewedLeafCount', 0))

        # Create the basic data structures to pass up
        details = {'title': encode_utf8(show.get('title', i18n('Unknown'))),
                   'sorttitle': encode_utf8(show.get('titleSort', show.get('title', i18n('Unknown')))),
                   'TVShowTitle': encode_utf8(show.get('title', i18n('Unknown'))),
                   'studio': encode_utf8(show.get('studio', '')),
                   'plot': encode_utf8(show.get('summary', '')),
                   'season': 0,
                   'episode': int(show.get('leafCount', 0)),
                   'mpaa': show.get('contentRating', ''),
                   'rating': float(show.get('rating', 0)),
                   'aired': show.get('originallyAvailableAt', ''),
                   'genre': ' / '.join(tempgenre),
                   'mediatype': 'tvshow'}

        extra_data = {'type': 'video',
                      'source': 'tvshows',
                      'UnWatchedEpisodes': int(details['episode']) - _watched,
                      'WatchedEpisodes': _watched,
                      'TotalEpisodes': details['episode'],
                      'thumb': get_thumb_image(show, server),
                      'fanart_image': get_fanart_image(show, server),
                      'banner': get_banner_image(show, server),
                      'key': show.get('key', ''),
                      'ratingKey': str(show.get('ratingKey', 0))}

        # Set up overlays for watched and unwatched episodes
        if extra_data['WatchedEpisodes'] == 0:
            details['playcount'] = 0
        elif extra_data['UnWatchedEpisodes'] == 0:
            details['playcount'] = 1
        else:
            extra_data['partialTV'] = 1

        # Create URL based on whether we are going to flatten the season view
        if settings.get_setting('flatten') == '2':
            log_print.debug('Flattening all shows')
            extra_data['mode'] = MODES.TVEPISODES
            u = '%s%s' % (server.get_url_location(), extra_data['key'].replace('children', 'allLeaves'))
        else:
            extra_data['mode'] = MODES.TVSEASONS
            u = '%s%s' % (server.get_url_location(), extra_data['key'])

        if not settings.get_setting('skipcontextmenus'):
            context = build_context_menu(url, extra_data, server)
        else:
            context = None

        add_item_to_gui(u, details, extra_data, context)

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=settings.get_setting('kodicache'))


def process_tvseasons(url, rating_key=None):
    xbmcplugin.setContent(get_handle(), 'seasons')

    if not url.startswith(('http', 'file')) and rating_key:
        # Get URL, XML and parse
        server = plex_network.get_server_from_uuid(url)
        url = server.get_url_location() + '/library/metadata/%s/children' % str(rating_key)
    else:
        server = plex_network.get_server_from_url(url)

    tree = get_xml(url)
    if tree is None:
        return

    will_flatten = False
    if settings.get_setting('flatten') == '1':
        # check for a single season
        if int(tree.get('size', 0)) == 1:
            log_print.debug('Flattening single season show')
            will_flatten = True

    sectionart = get_fanart_image(tree, server)
    banner = get_banner_image(tree, server)
    # For all the directory tags
    season_tags = tree.findall('Directory')
    plot = encode_utf8(tree.get('summary', ''))
    for season in season_tags:

        if will_flatten:
            url = server.get_url_location() + season.get('key')
            process_tvepisodes(url)
            return

        if settings.get_setting('disable_all_season') and season.get('index') is None:
            continue

        _watched = int(season.get('viewedLeafCount', 0))

        # Create the basic data structures to pass up
        details = {'title': encode_utf8(season.get('title', i18n('Unknown'))),
                   'TVShowTitle': encode_utf8(season.get('parentTitle', i18n('Unknown'))),
                   'sorttitle': encode_utf8(season.get('titleSort', season.get('title', i18n('Unknown')))),
                   'studio': encode_utf8(season.get('studio', '')),
                   'plot': plot,
                   'season': season.get('index', 0),
                   'episode': int(season.get('leafCount', 0)),
                   'mpaa': season.get('contentRating', ''),
                   'aired': season.get('originallyAvailableAt', ''),
                   'mediatype': 'season'
                   }

        if season.get('sorttitle'):
            details['sorttitle'] = season.get('sorttitle')

        extra_data = {'type': 'video',
                      'source': 'tvseasons',
                      'TotalEpisodes': details['episode'],
                      'WatchedEpisodes': _watched,
                      'UnWatchedEpisodes': details['episode'] - _watched,
                      'thumb': get_thumb_image(season, server),
                      'fanart_image': get_fanart_image(season, server),
                      'banner': banner,
                      'key': season.get('key', ''),
                      'ratingKey': str(season.get('ratingKey', 0)),
                      'mode': MODES.TVEPISODES}

        if extra_data['fanart_image'] == '':
            extra_data['fanart_image'] = sectionart

        # Set up overlays for watched and unwatched episodes
        if extra_data['WatchedEpisodes'] == 0:
            details['playcount'] = 0
        elif extra_data['UnWatchedEpisodes'] == 0:
            details['playcount'] = 1
        else:
            extra_data['partialTV'] = 1

        url = '%s%s' % (server.get_url_location(), extra_data['key'])

        if not settings.get_setting('skipcontextmenus'):
            context = build_context_menu(url, season, server)
        else:
            context = None

        # Build the screen directory listing
        add_item_to_gui(url, details, extra_data, context)

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=settings.get_setting('kodicache'))


def process_tvepisodes(url, tree=None, rating_key=None):
    xbmcplugin.setContent(get_handle(), 'episodes')

    if not url.startswith(('http', 'file')) and rating_key:
        # Get URL, XML and parse
        server = plex_network.get_server_from_uuid(url)
        url = server.get_url_location() + '/library/metadata/%s/children' % str(rating_key)

    use_go_to = url.endswith(('onDeck', 'recentlyAdded', 'recentlyViewed', 'newest'))

    tree = get_xml(url, tree)
    if tree is None:
        return

    # get season thumb for SEASON NODE
    season_thumb = tree.get('thumb', '')
    if season_thumb == '/:/resources/show.png':
        season_thumb = ''

    show_tags = tree.findall('Video')
    server = plex_network.get_server_from_url(url)

    sectionart = ''
    if not settings.get_setting('skipimages'):
        sectionart = get_fanart_image(tree, server)

    banner = get_banner_image(tree, server)

    random_number = str(random.randint(1000000000, 9999999999))

    if tree.get('mixedParents') == '1':
        log_print.debug('Setting plex sort')
        xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_UNSORTED)  # maintain original plex sorted
    else:
        log_print.debug('Setting KODI sort')
        xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_EPISODE)  # episode

    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_DATE)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE_IGNORE_THE)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_DATEADDED)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_VIDEO_RATING)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_VIDEO_YEAR)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_VIDEO_RUNTIME)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_MPAA_RATING)

    for episode in show_tags:

        log_print.debug('---New Item---')
        tempgenre = []
        tempcast = []
        tempdir = []
        tempwriter = []
        mediaarguments = {}

        for child in episode:
            if child.tag == 'Media':
                mediaarguments = dict(child.items())
            elif child.tag == 'Genre' and not settings.get_setting('skipmetadata'):
                tempgenre.append(child.get('tag'))
            elif child.tag == 'Writer' and not settings.get_setting('skipmetadata'):
                tempwriter.append(child.get('tag'))
            elif child.tag == 'Director' and not settings.get_setting('skipmetadata'):
                tempdir.append(child.get('tag'))
            elif child.tag == 'Role' and not settings.get_setting('skipmetadata'):
                tempcast.append(child.get('tag'))

        log_print.debug('Media attributes are %s' % mediaarguments)

        # Gather some data
        view_offset = episode.get('viewOffset', 0)
        duration = int(mediaarguments.get('duration', episode.get('duration', 0))) / 1000

        # Required listItem entries for XBMC
        details = {'plot': encode_utf8(episode.get('summary', '')),
                   'title': encode_utf8(episode.get('title', i18n('Unknown'))),
                   'sorttitle': encode_utf8(episode.get('titleSort', episode.get('title', i18n('Unknown')))),
                   'rating': float(episode.get('rating', 0)),
                   'studio': encode_utf8(episode.get('studio', tree.get('studio', ''))),
                   'mpaa': episode.get('contentRating', tree.get('grandparentContentRating', '')),
                   'year': int(episode.get('year', 0)),
                   'tagline': encode_utf8(episode.get('tagline', '')),
                   'episode': int(episode.get('index', 0)),
                   'aired': episode.get('originallyAvailableAt', ''),
                   'tvshowtitle': encode_utf8(episode.get('grandparentTitle', tree.get('grandparentTitle', ''))),
                   'season': int(episode.get('parentIndex', tree.get('parentIndex', 0))),
                   'mediatype': 'episode'}

        if episode.get('sorttitle'):
            details['sorttitle'] = encode_utf8(episode.get('sorttitle'))

        if tree.get('mixedParents') == '1':
            if tree.get('parentIndex') == '1':
                details['title'] = '%sx%s %s' % (details['season'], str(details['episode']).zfill(2), details['title'])
            else:
                details['title'] = '%s - %sx%s %s' % (details['tvshowtitle'], details['season'], str(details['episode']).zfill(2), details['title'])

        # Extra data required to manage other properties
        extra_data = {'type': 'Video',
                      'source': 'tvepisodes',
                      'thumb': get_thumb_image(episode, server),
                      'fanart_image': get_fanart_image(episode, server),
                      'banner': banner,
                      'key': episode.get('key', ''),
                      'ratingKey': str(episode.get('ratingKey', 0)),
                      'parentRatingKey': str(episode.get('parentRatingKey', 0)),
                      'grandparentRatingKey': str(episode.get('grandparentRatingKey', 0)),
                      'duration': duration,
                      'resume': int(int(view_offset) / 1000),
                      'season': details.get('season'),
                      'tvshowtitle': details.get('tvshowtitle'),
                      'additional_context_menus': {'go_to': use_go_to},
                      }

        if extra_data['fanart_image'] == '' and not settings.get_setting('skipimages'):
            extra_data['fanart_image'] = sectionart

        if '-1' in extra_data['fanart_image'] and not settings.get_setting('skipimages'):
            extra_data['fanart_image'] = sectionart

        if season_thumb:
            extra_data['season_thumb'] = server.get_url_location() + season_thumb

        # get ALL SEASONS or TVSHOW thumb
        if not season_thumb and episode.get('parentThumb', ''):
            extra_data['season_thumb'] = '%s%s' % (server.get_url_location(), episode.get('parentThumb', ''))
        elif not season_thumb and episode.get('grandparentThumb', ''):
            extra_data['season_thumb'] = '%s%s' % (server.get_url_location(), episode.get('grandparentThumb', ''))

        # Determine what tupe of watched flag [overlay] to use
        if int(episode.get('viewCount', 0)) > 0:
            details['playcount'] = 1
        else:
            details['playcount'] = 0

        # Extended Metadata
        if not settings.get_setting('skipmetadata'):
            details['cast'] = tempcast
            details['director'] = ' / '.join(tempdir)
            details['writer'] = ' / '.join(tempwriter)
            details['genre'] = ' / '.join(tempgenre)

        # Add extra media flag data
        if not settings.get_setting('skipflags'):
            extra_data.update(get_media_data(mediaarguments))

        # Build any specific context menu entries
        if not settings.get_setting('skipcontextmenus'):
            context = build_context_menu(url, extra_data, server)
        else:
            context = None

        extra_data['mode'] = MODES.PLAYLIBRARY
        separator = '?'
        if '?' in extra_data['key']:
            separator = '&'
        u = '%s%s%st=%s' % (server.get_url_location(), extra_data['key'], separator, random_number)

        add_item_to_gui(u, details, extra_data, context, folder=False)

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=settings.get_setting('kodicache'))


def get_audio_subtitles_from_media(server, tree, full=False):
    """
        Cycle through the Parts sections to find all 'selected' audio and subtitle streams
        If a stream is marked as selected=1 then we will record it in the dict
        Any that are not, are ignored as we do not need to set them
        We also record the media locations for playback decision later on
    """
    log_print.debug('Gather media stream info')

    parts = []
    parts_count = 0
    subtitle = {}
    sub_count = 0
    audio = {}
    audio_count = 0
    media = {}
    sub_offset = -1
    audio_offset = -1
    selected_sub_offset = -1
    selected_audio_offset = -1
    full_data = {}
    contents = 'type'
    extra = {}

    timings = tree.find('Video')
    if timings is not None:
        media_type = 'video'
        extra['path'] = timings.get('key')
    else:
        timings = tree.find('Track')
        if timings:
            media_type = 'music'
            extra['path'] = timings.get('key')
        else:
            timings = tree.find('Photo')
            if timings:
                media_type = 'picture'
                extra['path'] = timings.get('key')
            else:
                log_print.debug('No Video data found')
                return {}

    media['viewOffset'] = timings.get('viewOffset', 0)
    media['duration'] = timings.get('duration', 12 * 60 * 60)

    if full:
        if media_type == 'video':
            full_data = {'plot': encode_utf8(timings.get('summary', '')),
                         'title': encode_utf8(timings.get('title', i18n('Unknown'))),
                         'sorttitle': encode_utf8(timings.get('titleSort', timings.get('title', i18n('Unknown')))),
                         'rating': float(timings.get('rating', 0)),
                         'studio': encode_utf8(timings.get('studio', '')),
                         'mpaa': encode_utf8(timings.get('contentRating', '')),
                         'year': int(timings.get('year', 0)),
                         'tagline': timings.get('tagline', ''),
                         'thumbnailImage': get_thumb_image(timings, server),
                         'mediatype': 'video'}

            if timings.get('type') == 'episode':
                full_data['episode'] = int(timings.get('index', 0))
                full_data['aired'] = timings.get('originallyAvailableAt', '')
                full_data['tvshowtitle'] = encode_utf8(timings.get('grandparentTitle', tree.get('grandparentTitle', '')))
                full_data['season'] = int(timings.get('parentIndex', tree.get('parentIndex', 0)))
                full_data['mediatype'] = 'episode'

        elif media_type == 'music':

            full_data = {'TrackNumber': int(timings.get('index', 0)),
                         'discnumber': int(timings.get('parentIndex', 0)),
                         'title': str(timings.get('index', 0)).zfill(2) + '. ' + encode_utf8(timings.get('title', i18n('Unknown'))),
                         'rating': float(timings.get('rating', 0)),
                         'album': encode_utf8(timings.get('parentTitle', tree.get('parentTitle', ''))),
                         'artist': encode_utf8(timings.get('grandparentTitle', tree.get('grandparentTitle', ''))),
                         'duration': int(timings.get('duration', 0)) / 1000,
                         'thumbnailImage': get_thumb_image(timings, server)}

            extra['album'] = timings.get('parentKey')
            extra['index'] = timings.get('index')

    details = timings.findall('Media')

    media_details_list = []
    for media_details in details:

        resolution = ''
        try:
            if media_details.get('videoResolution') == 'sd':
                resolution = 'SD'
            elif int(media_details.get('videoResolution', 0)) > 1088:
                resolution = '4K'
            elif int(media_details.get('videoResolution', 0)) >= 1080:
                resolution = 'HD 1080'
            elif int(media_details.get('videoResolution', 0)) >= 720:
                resolution = 'HD 720'
            else:  # elif int(media_details.get('videoResolution', 0)) < 720:
                resolution = 'SD'
        except:
            pass

        media_details_temp = {'bitrate': round(float(media_details.get('bitrate', 0)) / 1000, 1),
                              'bitDepth': media_details.get('bitDepth', 8),
                              'videoResolution': resolution,
                              'container': media_details.get('container', 'unknown'),
                              'codec': media_details.get('videoCodec')
                              }

        options = media_details.findall('Part')

        # Get the media locations (file and web) for later on
        for stuff in options:

            try:
                bits = stuff.get('key'), stuff.get('file')
                parts.append(bits)
                media_details_list.append(media_details_temp)
                parts_count += 1
            except:
                pass

    # if we are deciding internally or forcing an external subs file, then collect the data
    if media_type == 'video' and settings.get_setting('streamControl') == STREAM_CONTROL.PLEX:

        contents = 'all'
        tags = tree.getiterator('Stream')

        for bits in tags:
            stream = dict(bits.items())

            # Audio Streams
            if stream['streamType'] == '2':
                audio_count += 1
                audio_offset += 1
                if stream.get('selected') == '1':
                    log_print.debug('Found preferred audio id: %s ' % stream['id'])
                    audio = stream
                    selected_audio_offset = audio_offset

            # Subtitle Streams
            elif stream['streamType'] == '3':

                if sub_offset == -1:
                    sub_offset = int(stream.get('index', -1))
                elif 0 < int(stream.get('index', -1)) < sub_offset:
                    sub_offset = int(stream.get('index', -1))

                if stream.get('selected') == '1':
                    log_print.debug('Found preferred subtitles id : %s ' % stream['id'])
                    sub_count += 1
                    subtitle = stream
                    if stream.get('key'):
                        subtitle['key'] = server.get_formatted_url(stream['key'])
                    else:
                        selected_sub_offset = int(stream.get('index')) - sub_offset

    else:
        log_print.debug('Stream selection is set OFF')

    stream_data = {'contents': contents,  # What type of data we are holding
                   'audio': audio,  # Audio data held in a dict
                   'audio_count': audio_count,  # Number of audio streams
                   'subtitle': subtitle,  # Subtitle data (embedded) held as a dict
                   'sub_count': sub_count,  # Number of subtitle streams
                   'parts': parts,  # The differet media locations
                   'parts_count': parts_count,  # Number of media locations
                   'media': media,  # Resume/duration data for media
                   'details': media_details_list,  # Bitrate, resolution and container for each part
                   'sub_offset': selected_sub_offset,  # Stream index for selected subs
                   'audio_offset': selected_audio_offset,  # STream index for select audio
                   'full_data': full_data,  # Full metadata extract if requested
                   'type': media_type,  # Type of metadata
                   'extra': extra}  # Extra data

    log_print.debug(stream_data)
    return stream_data


def play_playlist(server, data):
    log_print.debug('Creating new playlist')
    playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
    playlist.clear()

    tree = get_xml(server.get_url_location() + data['extra'].get('album') + '/children')

    if tree is None:
        return

    track_tags = tree.findall('Track')
    for track in track_tags:
        log_print.debug('Adding playlist item')

        url, item = track_tag(server, tree, track, listing=False)
        if CONFIG['kodi_version'] >= 18:
            liz = xbmcgui.ListItem(item.get('title', i18n('Unknown')), offscreen=True)
        else:
            liz = xbmcgui.ListItem(item.get('title', i18n('Unknown')))
        thumb = data['full_data'].get('thumbnailImage', CONFIG['icon'])
        liz.setArt({'icon': thumb, 'thumb': thumb})
        liz.setInfo(type='music', infoLabels=item)
        playlist.add(url, liz)

    index = int(data['extra'].get('index', 0)) - 1
    log_print.debug('Playlist complete.  Starting playback from track %s [playlist index %s] ' % (data['extra'].get('index', 0), index))
    xbmc.Player().playselected(index)

    return


def play_library_media(vids, override=False, force=None, full_data=False, transcode_profile=0):
    session = None
    if settings.get_setting('transcode'):
        override = True

    if override:
        full_data = True

    server = plex_network.get_server_from_url(vids)

    media_id = vids.split('?')[0].split('&')[0].split('/')[-1]

    tree = get_xml(vids)
    if tree is None:
        return

    if force:
        full_data = True

    streams = get_audio_subtitles_from_media(server, tree, full_data)

    if force and streams['type'] == 'music':
        play_playlist(server, streams)
        return

    url = select_media_to_play(streams, server)

    codec = streams.get('details', [{}])[0].get('codec')
    resolution = streams.get('details', [{}])[0].get('videoResolution')
    try:
        bit_depth = int(streams.get('details', [{}])[0].get('bitDepth', 8))
    except ValueError:
        bit_depth = None

    if codec and (settings.get_setting('transcode_hevc') and codec.lower() == 'hevc'):
        override = True
    if resolution and (settings.get_setting('transcode_g1080') and resolution.lower() == '4k'):
        override = True
    if bit_depth and (settings.get_setting('transcode_g8bit') and bit_depth > 8):
        override = True

    if url is None:
        return

    protocol = url.split(':', 1)[0]

    if protocol == 'file':
        log_print.debug('We are playing a local file')
        playurl = url.split(':', 1)[1]
    elif protocol.startswith('http'):
        log_print.debug('We are playing a stream')
        if override:
            log_print.debug('We will be transcoding the stream')
            # if settings.get_setting('transcode_type') == '0':  # universal
            session, playurl = server.get_universal_transcode(streams['extra']['path'], transcode_profile=transcode_profile)
            # elif settings.get_setting('transcode_type') == '1':  # legacy
            #     session, playurl = server.get_legacy_transcode(media_id, url)
            # else:
            #     playurl = ''
        else:
            playurl = server.get_formatted_url(url)
    else:
        playurl = url

    resume = int(int(streams['media']['viewOffset']) / 1000)
    duration = int(int(streams['media']['duration']) / 1000)

    log_print.debug('Resume has been set to %s ' % resume)
    if CONFIG['kodi_version'] >= 18:
        item = xbmcgui.ListItem(path=playurl, offscreen=True)
    else:
        item = xbmcgui.ListItem(path=playurl)
    if streams['full_data']:
        item.setInfo(type=streams['type'], infoLabels=streams['full_data'])
        thumb = streams['full_data'].get('thumbnailImage', CONFIG['icon'])
        item.setArt({'icon': thumb, 'thumb': thumb})

    if force:

        if int(force) > 0:
            resume = int(int(force) / 1000)
        else:
            resume = force

    if force or session is not None:
        if resume:
            item.setProperty('ResumeTime', str(resume))
            item.setProperty('TotalTime', str(duration))
            item.setProperty('StartOffset', str(resume))
            log_print.debug('Playback from resume point: %s' % resume)

    if streams['type'] == 'picture':
        import json
        request = json.dumps({'id': 1,
                              'jsonrpc': '2.0',
                              'method': 'Player.Open',
                              'params': {'item': {'file': playurl}}})
        # noinspection PyUnusedLocal
        response = xbmc.executeJSONRPC(request)
        return
    else:
        if streams['type'] == 'video' or streams['type'] == 'music':
            monitor_dict = {
                'media_id': media_id,
                'playing_file': playurl,
                'session': session,
                'server': server,
                'streams': streams if not override else None
            }
            write_pickled('playback_monitor.pickle', monitor_dict)

        xbmcplugin.setResolvedUrl(get_handle(), True, item)


def select_media_to_play(data, server):
    # if we have two or more files for the same movie, then present a screen
    result = 0
    dvdplayback = False

    count = data['parts_count']
    options = data['parts']
    details = data['details']

    if count > 1:

        dialog_options = []
        dvd_index = []
        index_count = 0
        for items in options:

            if items[1]:
                name = items[1].split('/')[-1]
                # name='%s %s %sMbps' % (items[1].split('/')[-1], details[index_count]['videoResolution'], details[index_count]['bitrate'])
            else:
                name = '%s %s %sMbps' % (items[0].split('.')[-1], details[index_count]['videoResolution'], details[index_count]['bitrate'])

            if settings.get_setting('forcedvd'):
                if '.ifo' in name.lower():
                    log_print.debug('Found IFO DVD file in ' + name)
                    name = 'DVD Image'
                    dvd_index.append(index_count)

            dialog_options.append(name)
            index_count += 1

        log_print.debug('Create selection dialog box - we have a decision to make!')
        start_time = xbmcgui.Dialog()
        result = start_time.select(i18n('Select media to play'), dialog_options)
        if result == -1:
            return None

        if result in dvd_index:
            log_print.debug('DVD Media selected')
            dvdplayback = True

    else:
        if settings.get_setting('forcedvd'):
            if '.ifo' in options[result]:
                dvdplayback = True

    newurl = select_media_type({'key': options[result][0], 'file': options[result][1]}, server, dvdplayback)

    log_print.debug('We have selected media at %s' % newurl)
    return newurl


def monitor_playback(media_id, server, session=None):
    if session:
        log_print.debug('We are monitoring a transcode session')

    if settings.get_setting('monitoroff'):
        return

    current_time = 0
    played_time = 0
    progress = 0
    total_time = 0
    wait_time = 0.5
    waited = 0.0

    monitor = xbmc.Monitor()
    player = xbmc.Player()

    # Whilst the file is playing back
    while player.isPlaying() and not monitor.abortRequested():

        try:
            current_time = int(player.getTime())
            total_time = int(player.getTotalTime())
        except RuntimeError:
            pass

        try:
            progress = int((float(current_time) / float(total_time)) * 100)
        except ZeroDivisionError:
            progress = 0

        try:
            report = int((float(waited) / 10.0)) >= 1
        except ZeroDivisionError:
            report = False

        if report:  # only report every ~10 seconds, times are updated at 0.5 seconds
            waited = 0.0
            if played_time == current_time:
                log_print.debug('Video paused at: %s secs of %s @ %s%%' % (current_time, total_time, progress))
                server.report_playback_progress(media_id, current_time * 1000, state='paused', duration=total_time * 1000)
            else:
                log_print.debug('Video played time: %s secs of %s @ %s%%' % (current_time, total_time, progress))
                server.report_playback_progress(media_id, current_time * 1000, state='playing', duration=total_time * 1000)
                played_time = current_time

        if monitor.waitForAbort(wait_time):
            break

        waited += wait_time

    if current_time != 0 and total_time != 0:
        log_print.debug('Playback Stopped: %s secs of %s @ %s%%' % (current_time, total_time, progress))
        # report_playback_progress state=stopped will adjust current time to match duration and mark media as watched if progress >= 98%
        server.report_playback_progress(media_id, current_time * 1000, state='stopped', duration=total_time * 1000)

    if session is not None:
        log_print.debug('Stopping PMS transcode job with session %s' % session)
        server.stop_transcode_session(session)

    return


def play_media_stream(url):
    if url.startswith('file'):
        log_print.debug('We are playing a local file')
        # Split out the path from the URL
        playurl = url.split(':', 1)[1]
    elif url.startswith('http'):
        log_print.debug('We are playing a stream')
        if '?' in url:
            server = plex_network.get_server_from_url(url)
            playurl = server.get_formatted_url(url)
        else:
            playurl = ''
    else:
        playurl = url
    if CONFIG['kodi_version'] >= 18:
        item = xbmcgui.ListItem(path=playurl, offscreen=True)
    else:
        item = xbmcgui.ListItem(path=playurl)
    resolved = playurl != ''
    xbmcplugin.setResolvedUrl(get_handle(), resolved, item)


def play_video_channel(vids, prefix=None, indirect=None, transcode=False):
    server = plex_network.get_server_from_url(vids)
    if 'node.plexapp.com' in vids:
        server = get_master_server()

    session = None

    if indirect:
        # Probably should transcode this
        if vids.startswith('http'):
            vids = '/' + vids.split('/', 3)[3]
            transcode = True

        session, vids = server.get_universal_transcode(vids)

    # if we have a plex URL, then this is a transcoding URL
    if 'plex://' in vids:
        log_print.debug('found webkit video, pass to transcoder')
        if not prefix:
            prefix = 'system'
            # if settings.get_setting('transcode_type') == '0':
            session, vids = server.get_universal_transcode(vids)
            # elif settings.get_setting('transcode_type') == '0':
            #     session, vids = server.get_legacy_transcode(0, vids, prefix)

        # Workaround for Kodi HLS request limit of 1024 byts
        if len(vids) > 1000:
            log_print.debug('Kodi HSL limit detected, will pre-fetch m3u8 playlist')

            playlist = get_xml(vids)

            if not playlist or '# EXTM3U' not in playlist:
                log_print.debug('Unable to get valid m3u8 playlist from transcoder')
                return

            server = plex_network.get_server_from_url(vids)
            session = playlist.split()[-1]
            vids = '%s/video/:/transcode/segmented/%s?t=1' % (server.get_url_location(), session)

    log_print.debug('URL to Play: %s ' % vids)
    log_print.debug('Prefix is: %s' % prefix)

    # If this is an Apple movie trailer, add User Agent to allow access
    if 'trailers.apple.com' in vids:
        url = vids + '|User-Agent=QuickTime/7.6.9 (qtver=7.6.9;os=Windows NT 6.1Service Pack 1)'
    else:
        url = vids

    log_print.debug('Final URL is: %s' % url)
    if CONFIG['kodi_version'] >= 18:
        item = xbmcgui.ListItem(path=url, offscreen=True)
    else:
        item = xbmcgui.ListItem(path=url)
    xbmcplugin.setResolvedUrl(get_handle(), True, item)

    if transcode and session:
        try:
            monitor_channel_transcode_playback(session, server)
        except:
            log_print.debug('Unable to start transcode monitor')
    else:
        log_print.debug('Not starting monitor')

    return


def monitor_channel_transcode_playback(session_id, server):
    # Logic may appear backward, but this does allow for a failed start to be detected
    # First while loop waiting for start

    if settings.get_setting('monitoroff'):
        return

    count = 0
    monitor = xbmc.Monitor()
    player = xbmc.Player()

    log_print.debug('Not playing yet...sleeping for upto 20 seconds at 2 second intervals')
    while not player.isPlaying() and not monitor.abortRequested():
        count += 1
        if count >= 10:
            # Waited 20 seconds and still no movie playing - assume it isn't going to..
            return
        else:
            if monitor.waitForAbort(2.0):
                return

    log_print.debug('Waiting for playback to finish')
    while player.isPlaying() and not monitor.abortRequested():
        if monitor.waitForAbort(0.5):
            break

    log_print.debug('Playback Stopped')
    log_print.debug('Stopping PMS transcode job with session: %s' % session_id)
    server.stop_transcode_session(session_id)

    return


def get_params():
    paramstring = get_argv()[2]

    param = {}
    if len(paramstring) >= 2:
        params = paramstring

        if params[0] == '?':
            cleanedparams = params[1:]
        else:
            cleanedparams = params

        # if params[len(params) - 1] == '/':
        #    params = params[0:len(params) - 2]

        pairsofparams = cleanedparams.split('&')
        for m in list(range(len(pairsofparams))):
            splitparams = pairsofparams[m].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]
            elif (len(splitparams)) == 3:
                param[splitparams[0]] = splitparams[1] + '=' + splitparams[2]
    log_print.debug('Parameters |%s| -> |%s|' % (paramstring, str(param)))
    return param


def channel_search(url, prompt):
    """
        When we encounter a search request, branch off to this function to generate the keyboard
        and accept the terms.  This URL is then fed back into the correct function for
        onward processing.
    """

    if prompt:
        prompt = unquote(prompt)
    else:
        prompt = i18n('Enter search term')

    kb = xbmc.Keyboard('', i18n('Search...'))
    kb.setHeading(prompt)
    kb.doModal()
    if kb.isConfirmed():
        text = kb.getText()
        log_print.debug('Search term input: %s' % text)
        url = url + '&query=' + quote(text)
        plex_plugins(url)
    return


def get_content(url):
    """
        This function takes teh URL, gets the XML and determines what the content is
        This XML is then redirected to the best processing function.
        If a search term is detected, then show keyboard and run search query
        @input: URL of XML page
        @return: nothing, redirects to another function
    """

    server = plex_network.get_server_from_url(url)
    lastbit = url.split('/')[-1]
    log_print.debug('URL suffix: %s' % lastbit)

    # Catch search requests, as we need to process input before getting results.
    if lastbit.startswith('search'):
        log_print.debug('This is a search URL.  Bringing up keyboard')
        kb = xbmc.Keyboard('', i18n('Search...'))
        kb.setHeading(i18n('Enter search term'))
        kb.doModal()
        if kb.isConfirmed():
            text = kb.getText()
            log_print.debug('Search term input: %s' % text)
            url = url + '&query=' + quote(text)
        else:
            return

    tree = server.processed_xml(url)

    if lastbit == 'folder' or lastbit == 'playlists':
        process_xml(url, tree)
        return

    view_group = tree.get('viewGroup')

    if view_group == 'movie':
        log_print.debug('This is movie XML, passing to Movies')
        process_movies(url, tree)
    elif view_group == 'show':
        log_print.debug('This is tv show XML')
        process_tvshows(url, tree)
    elif view_group == 'episode':
        log_print.debug('This is TV episode XML')
        process_tvepisodes(url, tree)
    elif view_group == 'artist':
        log_print.debug('This is music XML')
        artist(url, tree)
    elif view_group == 'album' or view_group == 'albums':
        albums(url, tree)
    elif view_group == 'track':
        log_print.debug('This is track XML')
        tracks(url, tree)  # sorthing is handled here
    elif view_group == 'photo':
        log_print.debug('This is a photo XML')
        photo(url, tree)
    else:
        process_directory(url, tree)

    return


def process_directory(url, tree=None):
    log_print.debug('Processing secondary menus')
    collections = '/collection' in url

    content_type = 'files'
    if collections:
        content_type = 'sets'
    xbmcplugin.setContent(get_handle(), content_type)

    server = plex_network.get_server_from_url(url)

    thumb = tree.get('thumb')

    for directory in tree:
        title = encode_utf8(directory.get('title', i18n('Unknown')))
        title = directory_item_translate(title, thumb)
        details = {'title': title}
        if collections:
            details['mediatype'] = 'set'
        extra_data = {'thumb': get_thumb_image(tree, server),
                      'fanart_image': get_fanart_image(tree, server),
                      'mode': MODES.GETCONTENT,
                      'type': 'Folder'}

        u = '%s' % (get_link_url(url, directory, server))

        add_item_to_gui(u, details, extra_data)

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=settings.get_setting('kodicache'))


def directory_item_translate(title, thumb):
    translated_title = title

    if thumb.endswith('show.png'):
        if title == 'All Shows':
            translated_title = i18n('All')
        elif title == 'Unwatched':
            translated_title = i18n('Unwatched')
        elif title == 'Recently Aired':
            translated_title = i18n('Recently Aired')
        elif title == 'Recently Added':
            translated_title = i18n('Recently Added')
        elif title == 'Recently Viewed Episodes':
            translated_title = i18n('Recently Viewed Episodes')
        elif title == 'Recently Viewed Shows':
            translated_title = i18n('Recently Viewed Shows')
        elif title == 'On Deck':
            translated_title = i18n('On Deck')
        elif title == 'By Collection':
            translated_title = i18n('By Collection')
        elif title == 'By First Letter':
            translated_title = i18n('By First Letter')
        elif title == 'By Genre':
            translated_title = i18n('By Genre')
        elif title == 'By Year':
            translated_title = i18n('By Year')
        elif title == 'By Content Rating':
            translated_title = i18n('By Content Rating')
        elif title == 'By Folder':
            translated_title = i18n('By Folder')
        elif title == 'Search Shows...':
            translated_title = i18n('Search Shows...')
        elif title == 'Search Episodes...':
            translated_title = i18n('Search Episodes...')

    if thumb.endswith('artist.png'):
        if title == 'All Artists':
            translated_title = i18n('All')
        elif title == 'By Album':
            translated_title = i18n('By Album')
        elif title == 'By Genre':
            translated_title = i18n('By Genre')
        elif title == 'By Year':
            translated_title = i18n('By Year')
        elif title == 'By Collection':
            translated_title = i18n('By Collection')
        elif title == 'Recently Added':
            translated_title = i18n('Recently Added')
        elif title == 'By Folder':
            translated_title = i18n('By Folder')
        elif title == 'Search Artists...':
            translated_title = i18n('Search Artists...')
        elif title == 'Search Albums...':
            translated_title = i18n('Search Albums...')
        elif title == 'Search Tracks...':
            translated_title = i18n('Search Tracks...')

    if thumb.endswith('movie.png') or thumb.endswith('video.png'):
        if title.startswith('All '):
            translated_title = i18n('All')
        elif title == 'Unwatched':
            translated_title = i18n('Unwatched')
        elif title == 'Recently Released':
            translated_title = i18n('Recently Released')
        elif title == 'Recently Added':
            translated_title = i18n('Recently Added')
        elif title == 'Recently Viewed':
            translated_title = i18n('Recently Viewed')
        elif title == 'On Deck':
            translated_title = i18n('On Deck')
        elif title == 'By Collection':
            translated_title = i18n('By Collection')
        elif title == 'By Genre':
            translated_title = i18n('By Genre')
        elif title == 'By Year':
            translated_title = i18n('By Year')
        elif title == 'By Decade':
            translated_title = i18n('By Decade')
        elif title == 'By Director':
            translated_title = i18n('By Director')
        elif title == 'By Starring Actor':
            translated_title = i18n('By Starring Actor')
        elif title == 'By Country':
            translated_title = i18n('By Country')
        elif title == 'By Content Rating':
            translated_title = i18n('By Content Rating')
        elif title == 'By Rating':
            translated_title = i18n('By Rating')
        elif title == 'By Resolution':
            translated_title = i18n('By Resolution')
        elif title == 'By First Letter':
            translated_title = i18n('By First Letter')
        elif title == 'By Folder':
            translated_title = i18n('By Folder')
        elif title == 'Search...':
            translated_title = i18n('Search...')

    if thumb.endswith('photo.png'):
        if title == 'All Photos':
            translated_title = i18n('All')
        elif title == 'By Year':
            translated_title = i18n('By Year')
        elif title == 'Recently Added':
            translated_title = i18n('Recently Added')
        elif title == 'Camera Make':
            translated_title = i18n('Camera Make')
        elif title == 'Camera Model':
            translated_title = i18n('Camera Model')
        elif title == 'Aperture':
            translated_title = i18n('Aperture')
        elif title == 'Shutter Speed':
            translated_title = i18n('Shutter Speed')
        elif title == 'ISO':
            translated_title = i18n('ISO')
        elif title == 'Lens':
            translated_title = i18n('Lens')

    return translated_title


def item_translate(title, source, folder):
    translated_title = title

    if folder and (source == 'tvshows' or source == 'tvseasons'):
        if title == 'All episodes':
            translated_title = i18n('All episodes')
        elif title.startswith('Season '):
            translated_title = i18n('Season') + title[6:]

    return translated_title


def artist(url, tree=None):
    """
        Process artist XML and display data
        @input: url of XML page, or existing tree of XML page
        @return: nothing
    """
    xbmcplugin.setContent(get_handle(), 'artists')
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_ARTIST_IGNORE_THE)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_LASTPLAYED)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_VIDEO_YEAR)

    # Get the URL and server name.  Get the XML and parse
    tree = get_xml(url, tree)
    if tree is None:
        return

    server = plex_network.get_server_from_url(url)
    artist_tag = tree.findall('Directory')
    for _artist in artist_tag:
        details = {'artist': encode_utf8(_artist.get('title', ''))}

        details['title'] = details['artist']

        extra_data = {'type': 'Music',
                      'thumb': get_thumb_image(_artist, server),
                      'fanart_image': get_fanart_image(_artist, server),
                      'ratingKey': _artist.get('title', ''),
                      'key': _artist.get('key', ''),
                      'mode': MODES.ALBUMS,
                      'plot': _artist.get('summary', ''),
                      'mediatype': 'artist'}

        url = '%s%s' % (server.get_url_location(), extra_data['key'])

        add_item_to_gui(url, details, extra_data)

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=settings.get_setting('kodicache'))


def albums(url, tree=None):
    xbmcplugin.setContent(get_handle(), 'albums')
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_ALBUM_IGNORE_THE)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_ARTIST_IGNORE_THE)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_LASTPLAYED)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_VIDEO_YEAR)

    # Get the URL and server name.  Get the XML and parse
    tree = get_xml(url, tree)
    if tree is None:
        return

    server = plex_network.get_server_from_url(url)
    sectionart = get_fanart_image(tree, server)
    album_tags = tree.findall('Directory')
    recent = True if 'recentlyAdded' in url else False
    for album in album_tags:

        details = {'album': encode_utf8(album.get('title', '')),
                   'year': int(album.get('year', 0)),
                   'artist': encode_utf8(tree.get('parentTitle', album.get('parentTitle', ''))),
                   'mediatype': 'album'}

        if recent:
            details['title'] = '%s - %s' % (details['artist'], details['album'])
        else:
            details['title'] = details['album']

        extra_data = {'type': 'Music',
                      'thumb': get_thumb_image(album, server),
                      'fanart_image': get_fanart_image(album, server),
                      'key': album.get('key', ''),
                      'mode': MODES.TRACKS,
                      'plot': album.get('summary', '')}

        if extra_data['fanart_image'] == '':
            extra_data['fanart_image'] = sectionart

        url = '%s%s' % (server.get_url_location(), extra_data['key'])

        add_item_to_gui(url, details, extra_data)

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=settings.get_setting('kodicache'))


def tracks(url, tree=None):
    xbmcplugin.setContent(get_handle(), 'songs')
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_TITLE_IGNORE_THE)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_DURATION)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_SONG_RATING)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_TRACKNUM)

    tree = get_xml(url, tree)
    if tree is None:
        return

    playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
    playlist.clear()

    server = plex_network.get_server_from_url(url)
    sectionart = get_fanart_image(tree, server)
    sectionthumb = get_thumb_image(tree, server)
    track_tags = tree.findall('Track')
    for track in track_tags:
        if track.get('thumb'):
            sectionthumb = get_thumb_image(track, server)

        track_tag(server, tree, track, sectionart, sectionthumb)

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=settings.get_setting('kodicache'))


def get_xml(url, tree=None):
    if tree is None:
        tree = plex_network.get_processed_xml(url)

    if tree.get('message'):
        xbmcgui.Dialog().ok(tree.get('header', i18n('Message')), tree.get('message', ''))
        return None

    return tree


def plex_plugins(url, tree=None):
    """
        Main function to parse plugin XML from PMS
        Will create dir or item links depending on what the
        main tag is.
        @input: plugin page URL
        @return: nothing, creates XBMC GUI listing
    """
    xbmcplugin.setContent(get_handle(), 'addons')
    server = plex_network.get_server_from_url(url)
    tree = get_xml(url, tree)
    if tree is None:
        return

    myplex_url = False
    if (tree.get('identifier') != 'com.plexapp.plugins.myplex') and ('node.plexapp.com' in url):
        myplex_url = True
        log_print.debug('This is a myPlex URL, attempting to locate master server')
        server = get_master_server()

    for plugin in tree:

        details = {'title': encode_utf8(plugin.get('title'))}

        if details['title']:
            details['title'] = encode_utf8(plugin.get('name', i18n('Unknown')))

        if plugin.get('summary'):
            details['plot'] = plugin.get('summary')

        extra_data = {'thumb': get_thumb_image(plugin, server),
                      'fanart_image': get_fanart_image(plugin, server),
                      'identifier': tree.get('identifier', ''),
                      'type': 'Video',
                      'key': plugin.get('key', '')}

        if myplex_url:
            extra_data['key'] = extra_data['key'].replace('node.plexapp.com:32400', server.get_location())

        if extra_data['fanart_image'] == '':
            extra_data['fanart_image'] = get_fanart_image(tree, server)

        p_url = get_link_url(url, extra_data, server)

        if plugin.tag == 'Directory' or plugin.tag == 'Podcast':

            if plugin.get('search') == '1':
                extra_data['mode'] = MODES.CHANNELSEARCH
                extra_data['parameters'] = {'prompt': encode_utf8(plugin.get('prompt', i18n('Enter search term')))}
            else:
                extra_data['mode'] = MODES.PLEXPLUGINS

            add_item_to_gui(p_url, details, extra_data)

        elif plugin.tag == 'Video':
            extra_data['mode'] = MODES.VIDEOPLUGINPLAY

            for child in plugin:
                if child.tag == 'Media':
                    extra_data['parameters'] = {'indirect': child.get('indirect', '0')}

            add_item_to_gui(p_url, details, extra_data, folder=False)

        elif plugin.tag == 'Setting':

            if plugin.get('option') == 'hidden':
                value = '********'
            elif plugin.get('type') == 'text':
                value = plugin.get('value')
            elif plugin.get('type') == 'enum':
                value = plugin.get('values').split('|')[int(plugin.get('value', 0))]
            else:
                value = plugin.get('value')

            details['title'] = '%s - [%s]' % (encode_utf8(plugin.get('label', i18n('Unknown'))), value)
            extra_data['mode'] = MODES.CHANNELPREFS
            extra_data['parameters'] = {'id': plugin.get('id')}
            add_item_to_gui(url, details, extra_data)

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=settings.get_setting('kodicache'))


def channel_settings(url, setting_id):
    """
        Take the setting XML and parse it to create an updated
        string with the new settings.  For the selected value, create
        a user input screen (text or list) to update the setting.
        @ input: url
        @ return: nothing
    """
    log_print.debug('Setting preference for ID: %s' % setting_id)

    if not setting_id:
        log_print.debug('ID not set')
        return

    tree = get_xml(url)
    if tree is None:
        return

    set_string = None
    for plugin in tree:

        if plugin.get('id') == setting_id:
            log_print.debug('Found correct id entry for: %s' % setting_id)
            sid = setting_id

            label = plugin.get('label', i18n('Enter value'))
            option = plugin.get('option')
            value = plugin.get('value')

            if plugin.get('type') == 'text':
                log_print.debug('Setting up a text entry screen')
                kb = xbmc.Keyboard(value, i18n('Enter value'))
                kb.setHeading(label)

                if option == 'hidden':
                    kb.setHiddenInput(True)
                else:
                    kb.setHiddenInput(False)

                kb.doModal()
                if kb.isConfirmed():
                    value = kb.getText()
                    log_print.debug('Value input: %s ' % value)
                else:
                    log_print.debug('User cancelled dialog')
                    return False

            elif plugin.get('type') == 'enum':
                log_print.debug('Setting up an enum entry screen')

                values = plugin.get('values').split('|')

                setting_screen = xbmcgui.Dialog()
                value = setting_screen.select(label, values)
                if value == -1:
                    log_print.debug('User cancelled dialog')
                    return False
            else:
                log_print.debug('Unknown option type: %s' % plugin.get('id'))

        else:
            value = plugin.get('value')
            sid = plugin.get('id')

        if set_string is None:
            set_string = '%s/set?%s=%s' % (url, sid, value)
        else:
            set_string = '%s&%s=%s' % (set_string, sid, value)

    log_print.debug('Settings URL: %s' % set_string)
    plex_network.talk_to_server(set_string)
    xbmc.executebuiltin('Container.Refresh')

    return False


def process_xml(url, tree=None):
    """
        Main function to parse plugin XML from PMS
        Will create dir or item links depending on what the
        main tag is.
        @input: plugin page URL
        @return: nothing, creates XBMC GUI listing
    """
    xbmcplugin.setContent(get_handle(), 'movies')
    server = plex_network.get_server_from_url(url)
    tree = get_xml(url, tree)
    if tree is None:
        return
    for plugin in tree:

        details = {'title': encode_utf8(plugin.get('title'))}

        if not details['title']:
            details['title'] = encode_utf8(plugin.get('name', i18n('Unknown')))

        extra_data = {'thumb': get_thumb_image(plugin, server),
                      'fanart_image': get_fanart_image(plugin, server),
                      'identifier': tree.get('identifier', ''),
                      'type': 'Video'}

        if extra_data['fanart_image'] == '':
            extra_data['fanart_image'] = get_fanart_image(tree, server)

        p_url = get_link_url(url, plugin, server)

        if plugin.tag == 'Directory' or plugin.tag == 'Podcast':
            extra_data['mode'] = MODES.PROCESSXML
            add_item_to_gui(p_url, details, extra_data)

        elif plugin.tag == 'Track':
            track_tag(server, tree, plugin)

        elif plugin.tag == 'Playlist':
            playlist_tag(url, server, plugin)

        elif tree.get('viewGroup') == 'movie':
            process_movies(url, tree)
            return

        elif tree.get('viewGroup') == 'episode':
            process_tvepisodes(url, tree)
            return

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=settings.get_setting('kodicache'))


def movie_tag(url, server, tree, movie, random_number):
    log_print.debug('---New Item---')
    tempgenre = []
    tempcast = []
    tempdir = []
    tempwriter = []

    mediaarguments = {}

    # Lets grab all the info we can quickly through either a dictionary, or assignment to a list
    # We'll process it later
    for child in movie:
        if child.tag == 'Media':
            mediaarguments = dict(child.items())
        elif child.tag == 'Genre' and not settings.get_setting('skipmetadata'):
            tempgenre.append(child.get('tag'))
        elif child.tag == 'Writer' and not settings.get_setting('skipmetadata'):
            tempwriter.append(child.get('tag'))
        elif child.tag == 'Director' and not settings.get_setting('skipmetadata'):
            tempdir.append(child.get('tag'))
        elif child.tag == 'Role' and not settings.get_setting('skipmetadata'):
            tempcast.append(child.get('tag'))

    log_print.debug('Media attributes are %s' % mediaarguments)

    # Gather some data
    view_offset = movie.get('viewOffset', 0)
    duration = int(mediaarguments.get('duration', movie.get('duration', 0))) / 1000

    # Required listItem entries for XBMC
    details = {'plot': encode_utf8(movie.get('summary', '')),
               'title': encode_utf8(movie.get('title', i18n('Unknown'))),
               'sorttitle': encode_utf8(movie.get('titleSort', movie.get('title', i18n('Unknown')))),
               'rating': float(movie.get('rating', 0)),
               'studio': encode_utf8(movie.get('studio', '')),
               'mpaa': encode_utf8(movie.get('contentRating', '')),
               'year': int(movie.get('year', 0)),
               'date': movie.get('originallyAvailableAt', '1970-01-01'),
               'premiered': movie.get('originallyAvailableAt', '1970-01-01'),
               'tagline': movie.get('tagline', ''),
               'dateAdded': str(datetime.datetime.fromtimestamp(int(movie.get('addedAt', 0)))),
               'mediatype': 'movie'}

    # Extra data required to manage other properties
    extra_data = {'type': 'Video',
                  'source': 'movies',
                  'thumb': get_thumb_image(movie, server),
                  'fanart_image': get_fanart_image(movie, server),
                  'key': movie.get('key', ''),
                  'ratingKey': str(movie.get('ratingKey', 0)),
                  'duration': duration,
                  'resume': int(int(view_offset) / 1000)}

    if tree.get('playlistType'):
        if movie.get('playlistItemID'):
            extra_data.update({'playlist_item_id': movie.get('playlistItemID'), 'playlist_title': tree.get('title')})

    if tree.tag == 'MediaContainer':
        extra_data.update({'library_section_uuid': tree.get('librarySectionUUID')})

    # Determine what type of watched flag [overlay] to use
    if int(movie.get('viewCount', 0)) > 0:
        details['playcount'] = 1
    elif int(movie.get('viewCount', 0)) == 0:
        details['playcount'] = 0

    # Extended Metadata
    if not settings.get_setting('skipmetadata'):
        details['cast'] = tempcast
        details['director'] = ' / '.join(tempdir)
        details['writer'] = ' / '.join(tempwriter)
        details['genre'] = ' / '.join(tempgenre)

    if movie.get('primaryExtraKey') is not None:
        details['trailer'] = 'plugin://' + CONFIG['id'] + '/?url=%s%s?t=%s&mode=%s' % (server.get_url_location(), movie.get('primaryExtraKey', ''), random_number, MODES.PLAYLIBRARY)
        log_print.debug('Trailer plugin url added: %s' % details['trailer'])

    # Add extra media flag data
    if not settings.get_setting('skipflags'):
        extra_data.update(get_media_data(mediaarguments))

    # Build any specific context menu entries
    if not settings.get_setting('skipcontextmenus'):
        context = build_context_menu(url, extra_data, server)
    else:
        context = None
    # http:// <server> <path> &mode=<mode> &t=<rnd>
    extra_data['mode'] = MODES.PLAYLIBRARY
    separator = '?'
    if '?' in extra_data['key']:
        separator = '&'
    final_url = '%s%s%st=%s' % (server.get_url_location(), extra_data['key'], separator, random_number)

    add_item_to_gui(final_url, details, extra_data, context, folder=False)
    return


def get_media_data(tag_dict):
    """
        Extra the media details from the XML
        @input: dict of <media /> tag attributes
        @output: dict of required values
    """
    return {'VideoResolution': tag_dict.get('videoResolution', ''),
            'VideoCodec': tag_dict.get('videoCodec', ''),
            'AudioCodec': tag_dict.get('audioCodec', ''),
            'AudioChannels': tag_dict.get('audioChannels', ''),
            'VideoAspect': tag_dict.get('aspectRatio', ''),
            'xbmc_height': tag_dict.get('height'),
            'xbmc_width': tag_dict.get('width'),
            'xbmc_VideoCodec': tag_dict.get('videoCodec'),
            'xbmc_AudioCodec': tag_dict.get('audioCodec'),
            'xbmc_AudioChannels': tag_dict.get('audioChannels'),
            'xbmc_VideoAspect': tag_dict.get('aspectRatio')}


def track_tag(server, tree, track, sectionart='', sectionthumb='', listing=True):
    xbmcplugin.setContent(get_handle(), 'songs')

    part_details = ()

    for child in track:
        for babies in child:
            if babies.tag == 'Part':
                part_details = (dict(babies.items()))

    log_print.debug('Part is %s' % str(part_details))

    details = {'TrackNumber': int(track.get('index', 0)),
               'discnumber': int(track.get('parentIndex', 0)),
               'title': str(track.get('index', 0)).zfill(2) + '. ' + encode_utf8(track.get('title', i18n('Unknown'))),
               'rating': float(track.get('rating', 0)),
               'album': encode_utf8(track.get('parentTitle', tree.get('parentTitle', ''))),
               'artist': encode_utf8(track.get('grandparentTitle', tree.get('grandparentTitle', ''))),
               'duration': int(track.get('duration', 0)) / 1000,
               'mediatype': 'song'}

    extra_data = {'type': 'music',
                  'fanart_image': sectionart,
                  'thumb': sectionthumb,
                  'key': track.get('key', ''),
                  'mode': MODES.PLAYLIBRARY}

    # If we are streaming, then get the virtual location
    u = '%s%s' % (server.get_url_location(), extra_data['key'])

    if listing:
        add_item_to_gui(u, details, extra_data, folder=False)
    else:
        return u, details


def playlist_tag(url, server, track, listing=True):
    details = {'title': encode_utf8(track.get('title', i18n('Unknown'))),
               'duration': int(track.get('duration', 0)) / 1000
               }

    extra_data = {'type': track.get('playlistType', ''),
                  'thumb': get_thumb_image({'thumb': track.get('composite', '')}, server)}

    if extra_data['type'] == 'video':
        extra_data['mode'] = MODES.MOVIES
    elif extra_data['type'] == 'audio':
        extra_data['mode'] = MODES.TRACKS
    else:
        extra_data['mode'] = MODES.GETCONTENT

    u = get_link_url(url, track, server)

    if listing:
        add_item_to_gui(u, details, extra_data, folder=True)
    else:
        return url, details


def photo(url, tree=None):
    server = plex_network.get_server_from_url(url)

    xbmcplugin.setContent(get_handle(), 'photo')

    tree = get_xml(url, tree)
    if tree is None:
        return

    section_art = get_fanart_image(tree, server)
    for picture in tree:

        details = {'title': encode_utf8(picture.get('title', picture.get('name', i18n('Unknown'))))}

        if not details['title']:
            details['title'] = i18n('Unknown')

        extra_data = {'thumb': get_thumb_image(picture, server),
                      'fanart_image': get_fanart_image(picture, server),
                      'type': 'image'}

        if extra_data['fanart_image'] == '':
            extra_data['fanart_image'] = section_art

        u = get_link_url(url, picture, server)

        if picture.tag == 'Directory':
            extra_data['mode'] = MODES.PHOTOS
            add_item_to_gui(u, details, extra_data)

        elif picture.tag == 'Photo':

            if tree.get('viewGroup', '') == 'photo':
                for pics in picture:
                    if pics.tag == 'Media':
                        for images in pics:
                            if images.tag == 'Part':
                                extra_data['key'] = server.get_url_location() + images.get('key', '')
                                details['size'] = int(images.get('size', 0))
                                u = extra_data['key']

            add_item_to_gui(u, details, extra_data, folder=False)

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=settings.get_setting('kodicache'))


def music(url, tree=None):
    xbmcplugin.setContent(get_handle(), 'artists')

    server = plex_network.get_server_from_url(url)

    tree = get_xml(url, tree)
    if tree is None:
        return

    for grapes in tree:

        if grapes.get('key') is None:
            continue

        details = {'genre': encode_utf8(grapes.get('genre', '')),
                   'artist': encode_utf8(grapes.get('artist', '')),
                   'year': int(grapes.get('year', 0)),
                   'album': encode_utf8(grapes.get('album', '')),
                   'tracknumber': int(grapes.get('index', 0)),
                   'title': i18n('Unknown')}

        extra_data = {'type': 'Music',
                      'thumb': get_thumb_image(grapes, server),
                      'fanart_image': get_fanart_image(grapes, server)}

        if extra_data['fanart_image'] == '':
            extra_data['fanart_image'] = get_fanart_image(tree, server)

        u = get_link_url(url, grapes, server)

        if grapes.tag == 'Track':
            log_print.debug('Track Tag')
            xbmcplugin.setContent(get_handle(), 'songs')
            details['mediatype'] = 'song'
            details['title'] = grapes.get('track', encode_utf8(grapes.get('title', i18n('Unknown'))))
            details['duration'] = int(int(grapes.get('total_time', 0)) / 1000)

            extra_data['mode'] = MODES.BASICPLAY
            add_item_to_gui(u, details, extra_data, folder=False)

        else:

            if grapes.tag == 'Artist':
                log_print.debug('Artist Tag')
                xbmcplugin.setContent(get_handle(), 'artists')
                details['mediatype'] = 'artist'
                details['title'] = encode_utf8(grapes.get('artist', i18n('Unknown')))

            elif grapes.tag == 'Album':
                log_print.debug('Album Tag')
                xbmcplugin.setContent(get_handle(), 'albums')
                details['mediatype'] = 'album'
                details['title'] = encode_utf8(grapes.get('album', i18n('Unknown')))

            elif grapes.tag == 'Genre':
                details['title'] = encode_utf8(grapes.get('genre', i18n('Unknown')))

            else:
                log_print.debug('Generic Tag: %s' % grapes.tag)
                details['title'] = encode_utf8(grapes.get('title', i18n('Unknown')))

            extra_data['mode'] = MODES.MUSIC
            add_item_to_gui(u, details, extra_data)

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=settings.get_setting('kodicache'))


def get_thumb_image(data, server, width=720, height=720):
    """
        Simply take a URL or path and determine how to format for images
        @ input: elementTree element, server name
        @ return formatted URL
    """

    if settings.get_setting('skipimages'):
        return ''

    thumbnail = encode_utf8(data.get('thumb', '').split('?t')[0])

    if thumbnail.startswith('http'):
        return thumbnail

    elif thumbnail.startswith('/'):
        if settings.get_setting('fullres_thumbs'):
            return server.get_kodi_header_formatted_url(thumbnail)
        else:
            return server.get_kodi_header_formatted_url('/photo/:/transcode?url=%s&width=%s&height=%s'
                                                        % (quote_plus('http://localhost:32400' + thumbnail),
                                                           width, height))

    return CONFIG['icon']


def get_banner_image(data, server, width=720, height=720):
    """
        Simply take a URL or path and determine how to format for images
        @ input: elementTree element, server name
        @ return formatted URL
    """

    if settings.get_setting('skipimages'):
        return ''

    thumbnail = encode_utf8(data.get('banner', '').split('?t')[0])

    if thumbnail.startswith('http'):
        return thumbnail

    elif thumbnail.startswith('/'):
        if settings.get_setting('fullres_thumbs'):
            return server.get_kodi_header_formatted_url(thumbnail)
        else:
            return server.get_kodi_header_formatted_url('/photo/:/transcode?url=%s&width=%s&height=%s'
                                                        % (quote_plus('http://localhost:32400' + thumbnail),
                                                           width, height))

    return CONFIG['icon']


def get_fanart_image(data, server, width=1280, height=720):
    """
        Simply take a URL or path and determine how to format for fanart
        @ input: elementTree element, server name
        @ return formatted URL for photo resizing
    """
    if settings.get_setting('skipimages'):
        return ''

    fanart = encode_utf8(data.get('art', ''))

    if fanart.startswith('http'):
        return fanart

    elif fanart.startswith('/'):
        if settings.get_setting('fullres_fanart'):
            return server.get_kodi_header_formatted_url(fanart)
        else:
            return server.get_kodi_header_formatted_url('/photo/:/transcode?url=%s&width=%s&height=%s' % (quote_plus('http://localhost:32400' + fanart), width, height))

    return ''


def get_link_url(url, path_data, server):
    path = path_data.get('key', '')

    log_print.debug('Path is %s' % path)

    if path == '':
        log_print.debug('Empty Path')
        return

    # If key starts with http, then return it
    if path.startswith('http'):
        log_print.debug('Detected http(s) link')
        return path

    # If key starts with a / then prefix with server address
    elif path.startswith('/'):
        log_print.debug('Detected base path link')
        return '%s%s' % (server.get_url_location(), path)

    # If key starts with plex:// then it requires transcoding
    elif path.startswith('plex:'):
        log_print.debug('Detected plex link')
        components = path.split('&')
        for m in components:
            if 'prefix=' in m:
                del components[components.index(m)]
                break
        if path_data.get('identifier') is not None:
            components.append('identifier=' + path_data['identifier'])

        path = '&'.join(components)
        return 'plex://' + server.get_location() + '/' + '/'.join(path.split('/')[3:])

    elif path.startswith('rtmp'):
        log_print.debug('Detected RTMP link')
        return path

    # Any thing else is assumed to be a relative path and is built on existing url
    else:
        log_print.debug('Detected relative link')
        return '%s/%s' % (url, path)


def plex_online(url):
    xbmcplugin.setContent(get_handle(), 'addons')

    server = plex_network.get_server_from_url(url)

    tree = server.processed_xml(url)
    if tree is None:
        return

    for plugin in tree:

        details = {'title': encode_utf8(plugin.get('title', plugin.get('name', i18n('Unknown'))))}
        extra_data = {'type': 'Video',
                      'installed': int(plugin.get('installed', 2)),
                      'key': plugin.get('key', ''),
                      'thumb': get_thumb_image(plugin, server),
                      'mode': MODES.CHANNELINSTALL}

        if extra_data['installed'] == 1:
            details['title'] = details['title'] + ' (%s)' % encode_utf8(i18n('installed'))

        elif extra_data['installed'] == 2:
            extra_data['mode'] = MODES.PLEXONLINE

        u = get_link_url(url, plugin, server)

        extra_data['parameters'] = {'name': details['title']}

        add_item_to_gui(u, details, extra_data)

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=settings.get_setting('kodicache'))


def install(url, name):
    server = plex_network.get_server_from_url(url)
    tree = server.processed_xml(url)
    if tree is None:
        return

    operations = {}
    m = 0
    for plums in tree.findall('Directory'):
        operations[m] = plums.get('title')

        # If we find an install option, switch to a yes/no dialog box
        if operations[m].lower() == 'install':
            log_print.debug('Not installed.  Print dialog')
            ret = xbmcgui.Dialog().yesno(i18n('Plex Online'), i18n('About to install') + ' ' + name)

            if ret:
                log_print.debug('Installing....')
                tree = server.processed_xml(url + '/install')

                msg = tree.get('message', '(' + i18n('blank') + ')')
                log_print.debug(msg)
                xbmcgui.Dialog().ok(i18n('Plex Online'), msg)
            return

        m += 1

    # Else continue to a selection dialog box
    ret = xbmcgui.Dialog().select(i18n('This plugin is already installed'), operations.values())

    if ret == -1:
        log_print.debug('No option selected, cancelling')
        return

    log_print.debug('Option %s selected.  Operation is %s' % (ret, operations[ret]))
    u = url + '/' + operations[ret].lower()
    tree = server.processed_xml(u)

    msg = tree.get('message')
    log_print.debug(msg)
    xbmcgui.Dialog().ok(i18n('Plex Online'), msg)
    xbmc.executebuiltin('Container.Refresh')

    return


def channel_view(url):
    server = plex_network.get_server_from_url(url)
    tree = server.processed_xml(url)

    if tree is None:
        return

    for channels in tree.getiterator('Directory'):

        if channels.get('local', '') == '0':
            continue

        # arguments = dict(channels.items())

        extra_data = {'fanart_image': get_fanart_image(channels, server),
                      'thumb': get_thumb_image(channels, server)}

        details = {'title': channels.get('title', i18n('Unknown'))}

        suffix = channels.get('key').split('/')[1]

        if channels.get('unique', '') == '0':
            details['title'] = '%s (%s)' % (details['title'], suffix)

        # Alter data sent into getlinkurl, as channels use path rather than key
        p_url = get_link_url(url, {'key': channels.get('key'), 'identifier': channels.get('key')}, server)

        if suffix == 'photos':
            extra_data['mode'] = MODES.PHOTOS
        elif suffix == 'video':
            extra_data['mode'] = MODES.PLEXPLUGINS
        elif suffix == 'music':
            extra_data['mode'] = MODES.MUSIC
        else:
            extra_data['mode'] = MODES.GETCONTENT

        add_item_to_gui(p_url, details, extra_data)

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=settings.get_setting('kodicache'))


def display_content(acceptable_level, content_level):
    """
        Takes a content Rating and decides whether it is an allowable
        level, as defined by the content filter
        @input: content rating
        @output: boolean
    """

    log_print.debug('Checking rating flag [%s] against [%s]' % (content_level, acceptable_level))

    if acceptable_level == '2':
        log_print.debug('OK to display')
        return True

    content_map = {0: i18n('Kids'),
                   1: i18n('Teens'),
                   2: i18n('Adults')}

    rating_map = {'G': 0,  # MPAA Kids
                  'PG': 0,  # MPAA Kids
                  'PG-13': 1,  # MPAA Teens
                  'R': 2,  # MPAA Adults
                  'NC-17': 2,  # MPAA Adults
                  'NR': 2,  # MPAA Adults
                  'Unrated': 2,  # MPAA Adults

                  'U': 0,  # BBFC Kids
                  # 'PG': 0,  # BBFC Kids
                  '12': 1,  # BBFC Teens
                  '12A': 1,  # BBFC Teens
                  '15': 1,  # BBFC Teens
                  '18': 2,  # BBFC Adults
                  'R18': 2,  # BBFC Adults

                  'E': 0,  # ACB Kids (hopefully)
                  # 'G': 0,  # ACB Kids
                  # 'PG': 0,  # ACB Kids
                  'M': 1,  # ACB Teens
                  'MA15+': 2,  # ADC Adults
                  'R18+': 2,  # ACB Adults
                  'X18+': 2,  # ACB Adults

                  'TV-Y': 0,  # US TV - Kids
                  'TV-Y7': 0,  # US TV - Kids
                  'TV -G': 0,  # Us TV - kids
                  'TV-PG': 1,  # US TV - Teens
                  'TV-14': 1,  # US TV - Teens
                  'TV-MA': 2,  # US TV - Adults

                  # 'G': 0,  # CAN - kids
                  # 'PG': 0,  # CAN - kids
                  '14A': 1,  # CAN - teens
                  '18A': 2,  # CAN - Adults
                  # 'R': 2,  # CAN - Adults
                  'A': 2}  # CAN - Adults

    if content_level is None or content_level == 'None':
        log_print.debug('Setting [None] rating as %s' % content_map[settings.get_setting('contentNone')])
        if settings.get_setting('contentNone') <= acceptable_level:
            log_print.debug('OK to display')
            return True
    else:
        try:
            if rating_map[content_level] <= acceptable_level:
                log_print.debug('OK to display')
                return True
        except:
            log_print.error('Unknown rating flag [%s] whilst lookuing for [%s] - will filter for now, but needs to be added' % (content_level, content_map[acceptable_level]))

    log_print.debug('NOT OK to display')
    return False


def myplex_queue():
    if not plex_network.is_myplex_signedin():
        xbmcgui.Dialog().notification(heading=CONFIG['name'],
                                      message=i18n('myPlex not configured'),
                                      icon=CONFIG['icon'])
        return

    tree = plex_network.get_myplex_queue()

    plex_plugins('https://plex.tv/playlists/queue/all', tree)
    return


def refresh_plex_library(server_uuid, section_id):
    server = plex_network.get_server_from_uuid(server_uuid)
    server.refresh_section(section_id)

    log_print.debug('Library refresh requested')
    xbmcgui.Dialog().notification(heading=CONFIG['name'],
                                  message=i18n('Library refresh started'),
                                  icon=CONFIG['icon'])
    return


def watched(server_uuid, metadata_id, watched_status='watch'):
    server = plex_network.get_server_from_uuid(server_uuid)

    if watched_status == 'watch':
        log_print.debug('Marking %s as watched' % metadata_id)
        server.mark_item_watched(metadata_id)
    else:
        log_print.debug('Marking %s as unwatched' % metadata_id)
        server.mark_item_unwatched(metadata_id)

    xbmc.executebuiltin('Container.Refresh')

    return


def delete_library_media(server_uuid, metadata_id):
    log_print.debug('Deleting media at: %s' % metadata_id)

    return_value = xbmcgui.Dialog().yesno(i18n('Confirm file delete?'), i18n('Delete this item? This action will delete media and associated data files.'))

    if return_value:
        log_print.debug('Deleting....')
        server = plex_network.get_server_from_uuid(server_uuid)
        server.delete_metadata(metadata_id)
        xbmc.executebuiltin('Container.Refresh')

    return True


def set_library_subtitiles(server_uuid, metadata_id):
    """
        Display a list of available Subtitle streams and allow a user to select one.
        The currently selected stream will be annotated with a *
    """

    server = plex_network.get_server_from_uuid(server_uuid)
    tree = server.get_metadata(metadata_id)

    sub_list = ['']
    display_list = ['None']
    fl_select = False
    part_id = ''
    for parts in tree.getiterator('Part'):

        part_id = parts.get('id')

        for streams in parts:

            if streams.get('streamType', '') == '3':

                stream_id = streams.get('id')
                lang = encode_utf8(streams.get('languageCode', i18n('Unknown')))
                log_print.debug('Detected Subtitle stream [%s] [%s]' % (stream_id, lang))

                if streams.get('format', streams.get('codec')) == 'idx':
                    log_print.debug('Stream: %s - Ignoring idx file for now' % stream_id)
                    continue
                else:
                    sub_list.append(stream_id)

                    if streams.get('selected') == '1':
                        fl_select = True
                        language = streams.get('language', i18n('Unknown')) + '*'
                    else:
                        language = streams.get('language', i18n('Unknown'))

                    display_list.append(language)
        break

    if not fl_select:
        display_list[0] = display_list[0] + '*'

    subtitle_screen = xbmcgui.Dialog()
    result = subtitle_screen.select(i18n('Select subtitle'), display_list)
    if result == -1:
        return False

    log_print.debug('User has selected stream %s' % sub_list[result])
    server.set_subtitle_stream(part_id, sub_list[result])

    return True


def set_library_audio(server_uuid, metadata_id):
    """
        Display a list of available audio streams and allow a user to select one.
        The currently selected stream will be annotated with a *
    """

    server = plex_network.get_server_from_uuid(server_uuid)
    tree = server.get_metadata(metadata_id)

    audio_list = []
    display_list = []
    part_id = ''
    for parts in tree.getiterator('Part'):

        part_id = parts.get('id')

        for streams in parts:

            if streams.get('streamType', '') == '2':

                stream_id = streams.get('id')
                audio_list.append(stream_id)
                lang = streams.get('languageCode', i18n('Unknown'))

                log_print.debug('Detected Audio stream [%s] [%s] ' % (stream_id, lang))

                if streams.get('channels', i18n('Unknown')) == '6':
                    channels = '5.1'
                elif streams.get('channels', i18n('Unknown')) == '7':
                    channels = '6.1'
                elif streams.get('channels', i18n('Unknown')) == '2':
                    channels = 'Stereo'
                else:
                    channels = streams.get('channels', i18n('Unknown'))

                if streams.get('codec', i18n('Unknown')) == 'ac3':
                    codec = 'AC3'
                elif streams.get('codec', i18n('Unknown')) == 'dca':
                    codec = 'DTS'
                else:
                    codec = streams.get('codec', i18n('Unknown'))

                language = '%s (%s %s)' % (encode_utf8(streams.get('language', i18n('Unknown'))), codec, channels)

                if streams.get('selected') == '1':
                    language = language + '*'

                display_list.append(language)
        break

    audio_screen = xbmcgui.Dialog()
    result = audio_screen.select(i18n('Select audio'), display_list)
    if result == -1:
        return False

    log_print.debug('User has selected stream %s' % audio_list[result])

    server.set_audio_stream(part_id, audio_list[result])

    return True


def get_master_server(all_servers=False):
    possible_servers = []
    current_master = settings.get_setting('masterServer')
    for serverData in plex_network.get_server_list():
        log_print.debug(str(serverData))
        if serverData.get_master() == 1:
            possible_servers.append(serverData)
    log_print.debug('Possible master servers are: %s' % possible_servers)

    if all_servers:
        return possible_servers

    if len(possible_servers) > 1:
        preferred = 'local'
        for serverData in possible_servers:
            if serverData.get_name == current_master:
                log_print.debug('Returning current master')
                return serverData
            if preferred == 'any':
                log_print.debug('Returning \'any\'')
                return serverData
            else:
                if serverData.get_discovery() == preferred:
                    log_print.debug('Returning local')
                    return serverData
    elif len(possible_servers) == 0:
        return

    return possible_servers[0]


def set_master_server():
    servers = get_master_server(True)
    log_print.debug(str(servers))

    current_master = settings.get_setting('masterServer')

    display_option_list = []
    for address in servers:
        found_server = address.get_name()
        if found_server == current_master:
            found_server = found_server + '*'
        display_option_list.append(found_server)

    audio_select_screen = xbmcgui.Dialog()
    result = audio_select_screen.select(i18n('Select master server'), display_option_list)
    if result == -1:
        return False

    log_print.debug('Setting master server to: %s' % servers[result].get_name())
    settings.update_master_server(servers[result].get_name())
    return


def display_known_servers():
    known_servers = plex_network.get_server_list()
    display_list = []

    for device in known_servers:
        name = device.get_name()
        log_status = device.get_status()
        status_label = i18n(log_status)
        if device.is_secure():
            log_secure = 'SSL'
            secure_label = i18n(log_secure)
        else:
            log_secure = 'Not Secure'
            secure_label = i18n(log_secure)

        log_print.debug('Device: %s [%s] [%s]' % (name, log_status, log_secure))
        log_print.debugplus('Full device dump [%s]' % device.__dict__)
        display_list.append('%s [%s] [%s]' % (name, status_label, secure_label))

    server_display_screen = xbmcgui.Dialog()
    server_display_screen.select(i18n('Known server list'), display_list)
    return


def display_plex_servers(url):
    ctype = url.split('/')[2]
    log_print.debug('Displaying entries for %s' % ctype)
    servers = plex_network.get_server_list()
    servers_list = len(servers)

    # For each of the servers we have identified
    for mediaserver in servers:

        if mediaserver.is_secondary():
            continue

        details = {'title': mediaserver.get_name()}

        extra_data = {}

        if ctype == 'video':
            extra_data['mode'] = MODES.PLEXPLUGINS
            s_url = '%s%s' % (mediaserver.get_url_location(), '/video')
            if servers_list == 1:
                plex_plugins(s_url)
                return

        elif ctype == 'online':
            extra_data['mode'] = MODES.PLEXONLINE
            s_url = '%s%s' % (mediaserver.get_url_location(), '/system/plexonline')
            if servers_list == 1:
                plex_online(s_url)
                return

        elif ctype == 'music':
            extra_data['mode'] = MODES.MUSIC
            s_url = '%s%s' % (mediaserver.get_url_location(), '/music')
            if servers_list == 1:
                music(s_url)
                return

        elif ctype == 'photo':
            extra_data['mode'] = MODES.PHOTOS
            s_url = '%s%s' % (mediaserver.get_url_location(), '/photos')
            if servers_list == 1:
                photo(s_url)
                return
        else:
            s_url = None

        add_item_to_gui(s_url, details, extra_data)

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=settings.get_setting('kodicache'))


def switch_user():
    # Get listof users
    user_list = plex_network.get_plex_home_users()
    # zero means we are not plexHome'd up
    if user_list is None or len(user_list) == 1:
        log_print.debug('No users listed or only one user, Plex Home not enabled')
        return False

    log_print.debug('found %s users: %s' % (len(user_list), user_list.keys()))

    # Get rid of currently logged in user.
    user_list.pop(plex_network.get_myplex_user(), None)

    select_screen = xbmcgui.Dialog()
    result = select_screen.select(i18n('Switch User'), user_list.keys())
    if result == -1:
        log_print.debug('Dialog cancelled')
        return False

    log_print.debug('user [%s] selected' % user_list.keys()[result])
    user = user_list[user_list.keys()[result]]

    pin = None
    if user['protected'] == '1':
        log_print.debug('Protected user [%s], requesting password' % user['title'])
        pin = select_screen.input(i18n('Enter PIN'), type=xbmcgui.INPUT_NUMERIC, option=xbmcgui.ALPHANUM_HIDE_INPUT)

    success, msg = plex_network.switch_plex_home_user(user['id'], pin)

    if not success:
        xbmcgui.Dialog().ok(i18n('Switch Failed'), msg)
        return False

    return True


def get_transcode_profile():
    profile_count = 3
    profile_labels = []

    for m in list(range(profile_count)):
        if m == 0 or settings.get_setting('transcode_target_enabled_%s' % str(m)):
            resolution, bitrate = settings.get_setting('transcode_target_quality_%s' % str(m)).split(',')
            sub_size = settings.get_setting('transcode_target_sub_size_%s' % str(m))
            audio_boost = settings.get_setting('transcode_target_audio_size_%s' % str(m))
            profile_labels.append('[%s] %s@%s (%s/%s)' % (str(m + 1), resolution, bitrate.strip(), sub_size, audio_boost))

    if len(profile_labels) == 1:
        return 0

    dialog = xbmcgui.Dialog()
    result = dialog.select(i18n('Transcode Profiles'), profile_labels)

    if result == -1:
        return 0
    else:
        return result


def delete_playlist_item(server_uuid, metadata_id, playlist_title, playlist_item_id, path):

    log_print.debug('== ENTER ==')
    log_print.debug('Deleting playlist item at: %s' % playlist_item_id)

    server = plex_network.get_server_from_uuid(server_uuid)
    tree = server.get_metadata(metadata_id)

    item = tree[0]
    item_title = item.get('title', '')
    item_image = server.get_formatted_url(server.get_url_location() + item.get('thumb'))

    return_value = xbmcgui.Dialog().yesno(i18n('Confirm playlist item delete?'), i18n('Delete from the playlist?') % (item_title, playlist_title))
    if return_value:
        log_print.debug('Deleting....')
        response = server.delete_playlist_item(playlist_item_id, path)
        if response and not response.get('status'):
            xbmcgui.Dialog().notification(CONFIG['name'], i18n('has been removed the playlist') % (item_title, playlist_title), item_image)
            xbmc.executebuiltin('Container.Refresh')
            return True

    xbmcgui.Dialog().notification(CONFIG['name'], i18n('Unable to remove from the playlist') % (item_title, playlist_title), item_image)
    return False


def add_playlist_item(server_uuid, metadata_id, library_section_uuid):
    log_print.debug('== ENTER ==')

    server = plex_network.get_server_from_uuid(server_uuid)
    tree = server.get_playlists()

    playlists = []
    for playlist in tree.getiterator('Playlist'):
        image = ''
        if playlist.get('composite'):
            image = server.get_formatted_url(server.get_url_location() + playlist.get('composite'))
        playlists.append({
            'title': playlist.get('title'),
            'key': playlist.get('ratingKey'),
            'image': image,
            'summary': playlist.get('summary'),
        })

    if CONFIG['kodi_version'] > 16:
        select_items = []
        for playlist in playlists:
            list_item = xbmcgui.ListItem(label=playlist.get('title'), label2=playlist.get('summary'))
            list_item.setArt({
                'icon': playlist.get('image'),
                'thumb': playlist.get('image'),
                'poster': playlist.get('image'),
            })
            select_items.append(list_item)

        return_value = xbmcgui.Dialog().select(i18n('Select playlist'), select_items, useDetails=True)
    else:
        select_items = [playlist.get('title') for playlist in playlists]
        return_value = xbmcgui.Dialog().select(i18n('Select playlist'), select_items)

    if return_value == -1:
        log_print.debug('Dialog cancelled')
        return False

    selected = playlists[return_value]
    log_print.debug('choosing playlist: %s' % selected)

    tree = server.get_metadata(metadata_id)
    item = tree[0]
    item_title = item.get('title', '')
    item_image = server.get_formatted_url(server.get_url_location() + item.get('thumb'))

    response = server.add_playlist_item(selected.get('key'), library_section_uuid, metadata_id)
    if response and not response.get('status'):
        leaf_added = int(response.get('leafCountAdded', 0))
        leaf_requested = int(response.get('leafCountRequested', 0))
        if leaf_added > 0 and leaf_added == leaf_requested:
            xbmcgui.Dialog().notification(CONFIG['name'], i18n('Added to the playlist') % (item_title, selected.get('title')), item_image)
            return True
        else:
            xbmcgui.Dialog().notification(CONFIG['name'], i18n('is already in the playlist') % (item_title, selected.get('title')), item_image)
            return False

    xbmcgui.Dialog().notification(CONFIG['name'], i18n('Failed to add to the playlist') % (item_title, selected.get('title')), item_image)
    return False


# #So this is where we really start the addon 
log_print = PrintDebug(CONFIG['name'])

log_print.debug('%s %s: Kodi %s on %s with Python %s' %
                (CONFIG['name'], CONFIG['version'], CONFIG['kodi_version'],
                 CONFIG['platform'], '.'.join([str(i) for i in sys.version_info])),
                no_privacy=True)  # force no privacy to avoid redacting version strings
wake_servers()

stream_control_map = {STREAM_CONTROL.KODI: 'Kodi', STREAM_CONTROL.PLEX: 'Plex', STREAM_CONTROL.NEVER: 'Never'}
stream_control_setting = stream_control_map.get(settings.get_setting('streamControl'))

log_print.debug('Settings:\nFullRes Thumbs |%s| Streaming |%s| Filter Menus |%s| Flatten |%s|\n'
                'Stream Control |%s| Force DVD |%s| SMB IP Override |%s| NAS IP |%s|' %
                (settings.get_setting('fullres_thumbs'), settings.get_stream(), settings.get_setting('secondary'),
                 settings.get_setting('flatten'), stream_control_setting, settings.get_setting('forcedvd'),
                 settings.get_setting('nasoverride'), settings.get_setting('nasoverrideip')))

plex_network = plex.Plex(load=False)


def start_composite(start_time):
    try:
        params = get_params()
    except:
        params = {}

    # Now try and assign some data to them
    param_url = params.get('url')
    command = None

    if param_url:
        if param_url.startswith('http') or param_url.startswith('file'):
            param_url = unquote(param_url)
        elif param_url.startswith('cmd'):
            command = unquote(param_url).split(':')[1]

    param_name = unquote_plus(params.get('name', ''))
    mode = int(params.get('mode', -1))
    play_transcode = True if int(params.get('transcode', 0)) == 1 else False
    param_identifier = params.get('identifier')
    param_indirect = params.get('indirect')
    force = params.get('force')

    if command is None:
        try:
            command = get_argv()[1]
        except:
            pass

    log_print.debug('Mode |%s| Command |%s| URL |%s| Name |%s| Identifier |%s|' %
                    (mode, command, param_url, param_name, param_identifier))

    if command == 'refresh':
        xbmc.executebuiltin('Container.Refresh')
    elif command == 'switchuser':
        if switch_user():
            xbmc.executebuiltin('Container.Refresh')
        else:
            log_print.debug('Switch User Failed')

    elif command == 'signout':
        if not plex_network.is_admin():
            return xbmcgui.Dialog().ok(i18n('Sign Out'),
                                       i18n('To sign out you must be logged in as an admin user. Switch user and try again'))

        ret = xbmcgui.Dialog().yesno(i18n('myPlex'), i18n('You are currently signed into myPlex. Are you sure you want to sign out?'))
        if ret:
            plex_network.signout()
            xbmc.executebuiltin('Container.Refresh')

    elif command == 'signin':
        from .plex import plexsignin
        signin_window = plexsignin.PlexSignin(i18n('myPlex Login'))
        signin_window.set_authentication_target(plex_network)
        signin_window.start()
        del signin_window

    elif command == 'signintemp':
        # Awful hack to get around running a script from a listitem..
        xbmc.executebuiltin('RunScript(' + CONFIG['id'] + ', signin)')

    elif command == 'managemyplex':

        if not plex_network.is_myplex_signedin():
            ret = xbmcgui.Dialog().yesno(i18n('Manage myPlex'),
                                         i18n('You are not currently logged into myPlex. Continue to sign in, or cancel to return'))
            if ret:
                xbmc.executebuiltin('RunScript(' + CONFIG['id'] + ', signin)')
            else:
                return

        elif not plex_network.is_admin():
            return xbmcgui.Dialog().ok(i18n('Manage myPlex'),
                                       i18n('To access these screens you must be logged in as an admin user. Switch user and try again'))

        from .plex import plexsignin
        manage_window = plexsignin.PlexManage(i18n('Manage myPlex'))
        manage_window.set_authentication_target(plex_network)
        manage_window.start()
        del manage_window
    elif command == 'displayservers':
        plex_network.load()
        display_known_servers()
        xbmc.executebuiltin('Container.Refresh')
    elif command == 'delete_refresh':
        plex_network.delete_cache()
        xbmc.executebuiltin('Container.Refresh')
    else:
        plex_network.load()

        if command == 'update':
            server_uuid = get_argv()[2]
            section_id = get_argv()[3]
            refresh_plex_library(server_uuid, section_id)

        # Mark an item as watched/unwatched in plex    
        elif command == 'watch':
            server_uuid = get_argv()[2]
            metadata_id = get_argv()[3]
            watch_status = get_argv()[4]
            watched(server_uuid, metadata_id, watch_status)

        # delete media from PMS    
        elif command == 'delete':
            server_uuid = get_argv()[2]
            metadata_id = get_argv()[3]
            delete_library_media(server_uuid, metadata_id)

        # Display subtitle selection screen    
        elif command == 'subs':
            server_uuid = get_argv()[2]
            metadata_id = get_argv()[3]
            set_library_subtitiles(server_uuid, metadata_id)

        # Display audio streanm selection screen    
        elif command == 'audio':
            server_uuid = get_argv()[2]
            metadata_id = get_argv()[3]
            set_library_audio(server_uuid, metadata_id)

        # Allow a mastre server to be selected (for myplex queue)    
        elif command == 'master':
            set_master_server()

        elif command == 'delete_playlist_item':
            server_uuid = get_argv()[2]
            metadata_id = get_argv()[3]
            playlist_title = get_argv()[4]
            playlist_item_id = get_argv()[5]
            path = get_argv()[6]
            delete_playlist_item(server_uuid, metadata_id, playlist_title, playlist_item_id, path)

        elif command == 'add_playlist_item':
            server_uuid = get_argv()[2]
            metadata_id = get_argv()[3]
            library_section_uuid = get_argv()[4]
            add_playlist_item(server_uuid, metadata_id, library_section_uuid)

        # else move to the main code    
        else:

            # Run a function based on the mode variable that was passed in the URL
            if (mode is None) or (param_url is None) or (len(param_url) < 1):
                display_sections()

            elif mode == MODES.GETCONTENT:
                get_content(param_url)

            elif mode == MODES.TVSHOWS:
                process_tvshows(param_url)

            elif mode == MODES.MOVIES:
                process_movies(param_url)

            elif mode == MODES.ARTISTS:
                artist(param_url)

            elif mode == MODES.TVSEASONS:
                process_tvseasons(param_url, rating_key=params.get('rating_key'))

            elif mode == MODES.PLAYLIBRARY:
                transcode_profile = 0
                if play_transcode:
                    transcode_profile = get_transcode_profile()
                play_library_media(param_url, force=force, override=play_transcode, transcode_profile=transcode_profile)

            elif mode == MODES.TVEPISODES:
                process_tvepisodes(param_url, rating_key=params.get('rating_key'))

            elif mode == MODES.PLEXPLUGINS:
                plex_plugins(param_url)

            elif mode == MODES.PROCESSXML:
                process_xml(param_url)

            elif mode == MODES.BASICPLAY:
                play_media_stream(param_url)

            elif mode == MODES.ALBUMS:
                albums(param_url)

            elif mode == MODES.TRACKS:
                tracks(param_url)

            elif mode == MODES.PHOTOS:
                photo(param_url)

            elif mode == MODES.MUSIC:
                music(param_url)

            elif mode == MODES.VIDEOPLUGINPLAY:
                play_video_channel(param_url, param_identifier, param_indirect)

            elif mode == MODES.PLEXONLINE:
                plex_online(param_url)

            elif mode == MODES.CHANNELINSTALL:
                install(param_url, param_name)

            elif mode == MODES.CHANNELVIEW:
                channel_view(param_url)

            elif mode == MODES.PLAYLIBRARY_TRANSCODE:
                play_library_media(param_url, override=True)

            elif mode == MODES.MYPLEXQUEUE:
                myplex_queue()

            elif mode == MODES.CHANNELSEARCH:
                channel_search(param_url, params.get('prompt'))

            elif mode == MODES.CHANNELPREFS:
                channel_settings(param_url, params.get('id'))

            elif mode == MODES.SHARED_MOVIES:
                display_sections(cfilter='movies', display_shared=True)

            elif mode == MODES.SHARED_SHOWS:
                display_sections(cfilter='tvshows', display_shared=True)

            elif mode == MODES.SHARED_PHOTOS:
                display_sections(cfilter='photos', display_shared=True)

            elif mode == MODES.SHARED_MUSIC:
                display_sections(cfilter='music', display_shared=True)

            elif mode == MODES.SHARED_ALL:
                display_sections(display_shared=True)

            elif mode == MODES.PLAYLISTS:
                process_xml(param_url)

            elif mode == MODES.DISPLAYSERVERS:
                display_plex_servers(param_url)

    log_print.debug('Finished. |%ss|' % (time.time() - start_time))

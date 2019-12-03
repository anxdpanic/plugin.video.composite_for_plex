# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import time

import xbmc  # pylint: disable=import-error
import xbmcplugin  # pylint: disable=import-error

from ..addon.common import CONFIG
from ..addon.common import MODES
from ..addon.common import SETTINGS
from ..addon.common import PrintDebug
from ..addon.common import encode_utf8
from ..addon.common import get_handle
from ..addon.common import i18n
from ..addon.items import create_album_item
from ..addon.items import create_artist_item
from ..addon.items import create_directory_item
from ..addon.items import create_episode_item
from ..addon.items import create_movie_item
from ..addon.items import create_music_item
from ..addon.items import create_photo_item
from ..addon.items import create_playlist_item
from ..addon.items import create_plex_online_item
from ..addon.items import create_plex_plugin_item
from ..addon.items import create_season_item
from ..addon.items import create_track_item
from ..addon.items import create_tvshow_item
from ..addon.utils import create_gui_item
from ..addon.utils import get_link_url
from ..addon.utils import get_master_server
from ..addon.utils import get_thumb_image
from ..addon.utils import get_fanart_image
from ..addon.utils import get_xml

from ..plex import plex

LOG = PrintDebug(CONFIG['name'])


def process_directories(url, tree=None, plex_network=None):
    LOG.debug('Processing secondary menus')

    if plex_network is None:
        plex_network = plex.Plex(load=True)

    content_type = 'files'
    if '/collection' in url:
        content_type = 'sets'

    xbmcplugin.setContent(get_handle(), content_type)

    server = plex_network.get_server_from_url(url)

    items = []
    for directory in tree:
        items.append(create_directory_item(server, tree, url, directory))

    if items:
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))
    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))


def process_xml(url, tree=None, plex_network=None):
    """
        Main function to parse plugin XML from PMS
        Will create dir or item links depending on what the
        main tag is.
        @input: plugin page URL
        @return: nothing, creates XBMC GUI listing
    """
    if plex_network is None:
        plex_network = plex.Plex(load=True)

    xbmcplugin.setContent(get_handle(), 'movies')

    server = plex_network.get_server_from_url(url)
    tree = get_xml(url, tree)

    if tree is None:
        return

    items = []
    for plugin in tree:

        details = {'title': encode_utf8(plugin.get('title'))}

        if not details['title']:
            details['title'] = encode_utf8(plugin.get('name', i18n('Unknown')))

        extra_data = {
            'thumb': get_thumb_image(plugin, server),
            'fanart_image': get_fanart_image(plugin, server),
            'identifier': tree.get('identifier', ''),
            'type': 'Video'
        }

        if extra_data['fanart_image'] == '':
            extra_data['fanart_image'] = get_fanart_image(tree, server)

        _url = get_link_url(url, plugin, server)

        if plugin.tag == 'Directory' or plugin.tag == 'Podcast':
            extra_data['mode'] = MODES.PROCESSXML
            items.append(create_gui_item(_url, details, extra_data))

        elif plugin.tag == 'Track':
            items.append(create_track_item(server, tree, plugin))

        elif plugin.tag == 'Playlist':
            items.append(create_playlist_item(url, server, plugin))

        elif tree.get('viewGroup') == 'movie':
            process_movies(url, tree, plex_network=plex_network)
            return

        elif tree.get('viewGroup') == 'episode':
            process_tvepisodes(url, tree, plex_network=plex_network)
            return

    if items:
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))
    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))


def process_movies(url, tree=None, plex_network=None):
    if plex_network is None:
        plex_network = plex.Plex(load=True)

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

    # Find all the video tags, as they contain the data we need to link to a file.
    start_time = time.time()
    items = []
    for movie in tree:
        if movie.tag.lower() == 'video':
            items.append(create_movie_item(url, server, tree, movie))
        elif movie.tag.lower() == 'track':
            items.append(create_track_item(server, tree, movie))

    if items:
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))
    LOG.debug('PROCESS: It took %s seconds to process %s items' %
              (time.time() - start_time, len(items)))
    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))


def process_tvepisodes(url, tree=None, rating_key=None, plex_network=None):
    if plex_network is None:
        plex_network = plex.Plex(load=True)

    xbmcplugin.setContent(get_handle(), 'episodes')

    if not url.startswith(('http', 'file')) and rating_key:
        # Get URL, XML and parse
        server = plex_network.get_server_from_uuid(url)
        url = server.get_url_location() + '/library/metadata/%s/children' % str(rating_key)
    else:
        server = plex_network.get_server_from_url(url)

    tree = get_xml(url, tree)
    if tree is None:
        return

    if tree.get('mixedParents') == '1':
        LOG.debug('Setting plex sort')
        xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_UNSORTED)
    else:
        LOG.debug('Setting KODI sort')
        xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_EPISODE)  # episode

    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_DATE)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE_IGNORE_THE)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_DATEADDED)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_VIDEO_RATING)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_VIDEO_YEAR)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_VIDEO_RUNTIME)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_MPAA_RATING)

    items = []
    show_tags = tree.findall('Video')
    for episode in show_tags:
        items.append(create_episode_item(server, tree, url, episode))

    if items:
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))
    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))


def process_tvshows(url, tree=None, plex_network=None):
    if plex_network is None:
        plex_network = plex.Plex(load=True)

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

    items = []
    # For each directory tag we find
    show_tags = tree.findall('Directory')
    for show in show_tags:
        items.append(create_tvshow_item(server, url, show))

    if items:
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))
    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))


def process_artists(url, tree=None, plex_network=None):
    """
        Process artist XML and display data
        @input: url of XML page, or existing tree of XML page
        @return: nothing
    """
    if plex_network is None:
        plex_network = plex.Plex(load=True)

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

    items = []
    artist_tags = tree.findall('Directory')
    for artist in artist_tags:
        items.append(create_artist_item(server, artist))

    if items:
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))
    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))


def process_albums(url, tree=None, plex_network=None):
    if plex_network is None:
        plex_network = plex.Plex(load=True)

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

    items = []
    album_tags = tree.findall('Directory')
    for album in album_tags:
        items.append(create_album_item(server, tree, url, album))

    if items:
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))
    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))


def process_tracks(url, tree=None, plex_network=None):
    if plex_network is None:
        plex_network = plex.Plex(load=True)

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

    items = []
    track_tags = tree.findall('Track')
    for track in track_tags:
        items.append(create_track_item(server, tree, track))

    if items:
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))
    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))


def process_photos(url, tree=None, plex_network=None):
    if plex_network is None:
        plex_network = plex.Plex(load=True)

    server = plex_network.get_server_from_url(url)

    xbmcplugin.setContent(get_handle(), 'photo')

    tree = get_xml(url, tree)
    if tree is None:
        return

    items = []
    for photo in tree:
        item = create_photo_item(server, tree, url, photo)
        if item:
            items.append(item)

    if items:
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))
    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))


def process_tvseasons(url, rating_key=None, plex_network=None):
    if plex_network is None:
        plex_network = plex.Plex(load=True)

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
    if SETTINGS.get_setting('flatten') == '1':
        # check for a single season
        if int(tree.get('size', 0)) == 1:
            LOG.debug('Flattening single season show')
            will_flatten = True

    items = []
    # For all the directory tags
    season_tags = tree.findall('Directory')
    for season in season_tags:

        if will_flatten:
            url = server.get_url_location() + season.get('key')
            process_tvepisodes(url)
            return

        if SETTINGS.get_setting('disable_all_season') and season.get('index') is None:
            continue

        items.append(create_season_item(server, tree, season))

    if items:
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))
    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))


def process_plex_plugins(url, tree=None, plex_network=None):
    """
        Main function to parse plugin XML from PMS
        Will create dir or item links depending on what the
        main tag is.
        @input: plugin page URL
        @return: nothing, creates XBMC GUI listing
    """
    if plex_network is None:
        plex_network = plex.Plex(load=True)

    xbmcplugin.setContent(get_handle(), 'addons')

    server = plex_network.get_server_from_url(url)
    tree = get_xml(url, tree)
    if tree is None:
        return

    if (tree.get('identifier') != 'com.plexapp.plugins.myplex') and ('node.plexapp.com' in url):
        LOG.debug('This is a myPlex URL, attempting to locate master server')
        server = get_master_server()

    items = []
    for plugin in tree:
        item = create_plex_plugin_item(server, tree, url, plugin)
        if item:
            items.append(item)

    if items:
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))
    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))


def process_music(url, tree=None, plex_network=None):
    if plex_network is None:
        plex_network = plex.Plex(load=True)

    server = plex_network.get_server_from_url(url)

    tree = get_xml(url, tree)
    if tree is None:
        return

    items = []
    for music in tree:

        if music.get('key') is None:
            continue

        items.append(create_music_item(server, tree, url, music))

    if items:
        content_type = items[-1][1].getProperty('content_type')
        if not content_type:
            content_type = 'artists'
        xbmcplugin.setContent(get_handle(), content_type)

        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))
    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))


def process_plex_online(url, plex_network=None):
    if plex_network is None:
        plex_network = plex.Plex(load=True)

    xbmcplugin.setContent(get_handle(), 'addons')

    server = plex_network.get_server_from_url(url)

    tree = server.processed_xml(url)
    if tree is None:
        return

    items = []
    for plugin in tree:
        items.append(create_plex_online_item(server, url, plugin))

    if items:
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))
    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))

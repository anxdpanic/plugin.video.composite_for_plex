# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import random
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
from ..addon.utils import add_item_to_gui
from ..addon.utils import get_banner_image
from ..addon.utils import get_link_url
from ..addon.utils import get_master_server
from ..addon.utils import get_thumb_image
from ..addon.utils import get_fanart_image
from ..addon.utils import get_xml
from ..addon.tagging import album_tag
from ..addon.tagging import artist_tag
from ..addon.tagging import directory_tag
from ..addon.tagging import episode_tag
from ..addon.tagging import movie_tag
from ..addon.tagging import music_tag
from ..addon.tagging import playlist_tag
from ..addon.tagging import plex_online_tag
from ..addon.tagging import plex_plugin_tag
from ..addon.tagging import season_tag
from ..addon.tagging import track_tag
from ..addon.tagging import tvshow_tag

from ..plex import plex

LOG = PrintDebug(CONFIG['name'])


def process_directories(url, tree=None, plex_network=None):
    LOG.debug('Processing secondary menus')

    if plex_network is None:
        plex_network = plex.Plex(load=True)

    collections = '/collection' in url

    content_type = 'files'
    if collections:
        content_type = 'sets'
    xbmcplugin.setContent(get_handle(), content_type)

    server = plex_network.get_server_from_url(url)

    for directory in tree:
        directory_tag(server, tree, url, directory, collections)

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
            add_item_to_gui(_url, details, extra_data)

        elif plugin.tag == 'Track':
            track_tag(server, tree, plugin)

        elif plugin.tag == 'Playlist':
            playlist_tag(url, server, plugin)

        elif tree.get('viewGroup') == 'movie':
            process_movies(url, tree, plex_network=plex_network)
            return

        elif tree.get('viewGroup') == 'episode':
            process_tvepisodes(url, tree, plex_network=plex_network)
            return

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

    random_number = str(random.randint(1000000000, 9999999999))

    # Find all the video tags, as they contain the data we need to link to a file.
    start_time = time.time()
    count = 0
    for movie in tree:
        if movie.tag.lower() == 'video':
            movie_tag(url, server, tree, movie, random_number)
            count += 1
        elif movie.tag.lower() == 'track':
            sectionthumb = get_thumb_image(tree, server)
            if movie.get('thumb'):
                sectionthumb = get_thumb_image(movie, server)
            track_tag(server, tree, movie, '', sectionthumb)
            count += 1

    LOG.debug('PROCESS: It took %s seconds to process %s items' %
              (time.time() - start_time, count))
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

    art = {
        'banner': get_banner_image(tree, server),
        'season_thumb': tree.get('thumb', ''),
        'sectionart': '',
    }

    # get season thumb for SEASON NODE
    if art['season_thumb'] == '/:/resources/show.png':
        art['season_thumb'] = ''

    if not SETTINGS.get_setting('skipimages'):
        art['sectionart'] = get_fanart_image(tree, server)

    random_number = str(random.randint(1000000000, 9999999999))

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

    show_tags = tree.findall('Video')

    for episode in show_tags:
        episode_tag(server, tree, url, episode, art, random_number)

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

    # For each directory tag we find
    show_tags = tree.findall('Directory')
    for show in show_tags:
        tvshow_tag(server, url, show)

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

    artist_tags = tree.findall('Directory')
    for artist in artist_tags:
        artist_tag(server, artist)

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

    sectionart = get_fanart_image(tree, server)
    recent = 'recentlyAdded' in url

    album_tags = tree.findall('Directory')
    for album in album_tags:
        album_tag(server, tree, album, sectionart, recent)

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

    sectionart = get_fanart_image(tree, server)
    sectionthumb = get_thumb_image(tree, server)

    track_tags = tree.findall('Track')
    for track in track_tags:
        if track.get('thumb'):
            sectionthumb = get_thumb_image(track, server)

        track_tag(server, tree, track, sectionart, sectionthumb)

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))


def process_photos(url, tree=None, plex_network=None):
    if plex_network is None:
        plex_network = plex.Plex(load=True)

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

        extra_data = {
            'thumb': get_thumb_image(picture, server),
            'fanart_image': get_fanart_image(picture, server),
            'type': 'image'
        }

        if extra_data['fanart_image'] == '':
            extra_data['fanart_image'] = section_art

        item_url = get_link_url(url, picture, server)

        if picture.tag == 'Directory':
            extra_data['mode'] = MODES.PHOTOS
            add_item_to_gui(item_url, details, extra_data)

        elif picture.tag == 'Photo' and tree.get('viewGroup', '') == 'photo':
            for pics in picture:
                if pics.tag == 'Media':
                    parts = [img for img in pics if img.tag == 'Part']
                    for part in parts:
                        extra_data['key'] = \
                            server.get_url_location() + part.get('key', '')
                        details['size'] = int(part.get('size', 0))
                        item_url = extra_data['key']

            add_item_to_gui(item_url, details, extra_data, folder=False)

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

    # For all the directory tags
    season_tags = tree.findall('Directory')
    for season in season_tags:

        if will_flatten:
            url = server.get_url_location() + season.get('key')
            process_tvepisodes(url)
            return

        if SETTINGS.get_setting('disable_all_season') and season.get('index') is None:
            continue

        season_tag(server, tree, season)

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

    is_myplex_url = False
    if (tree.get('identifier') != 'com.plexapp.plugins.myplex') and ('node.plexapp.com' in url):
        is_myplex_url = True
        LOG.debug('This is a myPlex URL, attempting to locate master server')
        server = get_master_server()

    for plugin in tree:
        plex_plugin_tag(server, tree, url, plugin, is_myplex_url)

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))


def process_music(url, tree=None, plex_network=None):
    if plex_network is None:
        plex_network = plex.Plex(load=True)

    server = plex_network.get_server_from_url(url)

    tree = get_xml(url, tree)
    if tree is None:
        return

    content_type = 'artists'
    for music in tree:

        if music.get('key') is None:
            continue

        content_type = music_tag(server, tree, url, music)

    xbmcplugin.setContent(get_handle(), content_type)

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))


def process_plex_online(url, plex_network=None):
    if plex_network is None:
        plex_network = plex.Plex(load=True)

    xbmcplugin.setContent(get_handle(), 'addons')

    server = plex_network.get_server_from_url(url)

    tree = server.processed_xml(url)
    if tree is None:
        return

    for plugin in tree:
        plex_online_tag(server, url, plugin)

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))

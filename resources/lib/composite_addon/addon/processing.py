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
from ..addon.utils import build_context_menu
from ..addon.utils import directory_item_translate
from ..addon.utils import get_banner_image
from ..addon.utils import get_link_url
from ..addon.utils import get_master_server
from ..addon.utils import get_media_data
from ..addon.utils import get_thumb_image
from ..addon.utils import get_fanart_image
from ..addon.utils import get_xml
from ..addon.tagging import movie_tag
from ..addon.tagging import playlist_tag
from ..addon.tagging import track_tag

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

    thumb = tree.get('thumb')

    for directory in tree:
        title = encode_utf8(directory.get('title', i18n('Unknown')))
        title = directory_item_translate(title, thumb)
        details = {'title': title}
        if collections:
            details['mediatype'] = 'set'
        extra_data = {
            'thumb': get_thumb_image(tree, server),
            'fanart_image': get_fanart_image(tree, server),
            'mode': MODES.GETCONTENT,
            'type': 'Folder'
        }

        item_url = '%s' % (get_link_url(url, directory, server))

        add_item_to_gui(item_url, details, extra_data)

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


def process_tvepisodes(url, tree=None, rating_key=None, plex_network=None):  # pylint: disable=too-many-locals, too-many-statements, too-many-branches
    if plex_network is None:
        plex_network = plex.Plex(load=True)

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
    if not SETTINGS.get_setting('skipimages'):
        sectionart = get_fanart_image(tree, server)

    banner = get_banner_image(tree, server)

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

    for episode in show_tags:

        LOG.debug('---New Item---')
        tempgenre = []
        tempcast = []
        tempdir = []
        tempwriter = []
        mediaarguments = {}

        for child in episode:
            if child.tag == 'Media':
                mediaarguments = dict(child.items())
            elif child.tag == 'Genre' and not SETTINGS.get_setting('skipmetadata'):
                tempgenre.append(child.get('tag'))
            elif child.tag == 'Writer' and not SETTINGS.get_setting('skipmetadata'):
                tempwriter.append(child.get('tag'))
            elif child.tag == 'Director' and not SETTINGS.get_setting('skipmetadata'):
                tempdir.append(child.get('tag'))
            elif child.tag == 'Role' and not SETTINGS.get_setting('skipmetadata'):
                tempcast.append(child.get('tag'))

        LOG.debug('Media attributes are %s' % mediaarguments)

        # Gather some data
        view_offset = episode.get('viewOffset', 0)
        duration = int(mediaarguments.get('duration', episode.get('duration', 0))) / 1000

        # Required listItem entries for XBMC
        details = {
            'plot': encode_utf8(episode.get('summary', '')),
            'title': encode_utf8(episode.get('title', i18n('Unknown'))),
            'sorttitle': encode_utf8(episode.get('titleSort',
                                                 episode.get('title', i18n('Unknown')))),
            'rating': float(episode.get('rating', 0)),
            'studio': encode_utf8(episode.get('studio', tree.get('studio', ''))),
            'mpaa': episode.get('contentRating', tree.get('grandparentContentRating', '')),
            'year': int(episode.get('year', 0)),
            'tagline': encode_utf8(episode.get('tagline', '')),
            'episode': int(episode.get('index', 0)),
            'aired': episode.get('originallyAvailableAt', ''),
            'tvshowtitle': encode_utf8(episode.get('grandparentTitle',
                                                   tree.get('grandparentTitle', ''))),
            'season': int(episode.get('parentIndex', tree.get('parentIndex', 0))),
            'mediatype': 'episode'
        }

        if episode.get('sorttitle'):
            details['sorttitle'] = encode_utf8(episode.get('sorttitle'))

        if tree.get('mixedParents') == '1':
            if tree.get('parentIndex') == '1':
                details['title'] = '%sx%s %s' % (details['season'],
                                                 str(details['episode']).zfill(2),
                                                 details['title'])
            else:
                details['title'] = '%s - %sx%s %s' % (details['tvshowtitle'],
                                                      details['season'],
                                                      str(details['episode']).zfill(2),
                                                      details['title'])

        # Extra data required to manage other properties
        extra_data = {
            'type': 'Video',
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

        if extra_data['fanart_image'] == '' and not SETTINGS.get_setting('skipimages'):
            extra_data['fanart_image'] = sectionart

        if '-1' in extra_data['fanart_image'] and not SETTINGS.get_setting('skipimages'):
            extra_data['fanart_image'] = sectionart

        if season_thumb:
            extra_data['season_thumb'] = server.get_url_location() + season_thumb

        # get ALL SEASONS or TVSHOW thumb
        if not season_thumb and episode.get('parentThumb', ''):
            extra_data['season_thumb'] = '%s%s' % (server.get_url_location(),
                                                   episode.get('parentThumb', ''))
        elif not season_thumb and episode.get('grandparentThumb', ''):
            extra_data['season_thumb'] = '%s%s' % (server.get_url_location(),
                                                   episode.get('grandparentThumb', ''))

        # Determine what tupe of watched flag [overlay] to use
        if int(episode.get('viewCount', 0)) > 0:
            details['playcount'] = 1
        else:
            details['playcount'] = 0

        # Extended Metadata
        if not SETTINGS.get_setting('skipmetadata'):
            details['cast'] = tempcast
            details['director'] = ' / '.join(tempdir)
            details['writer'] = ' / '.join(tempwriter)
            details['genre'] = ' / '.join(tempgenre)

        # Add extra media flag data
        if not SETTINGS.get_setting('skipflags'):
            extra_data.update(get_media_data(mediaarguments))

        # Build any specific context menu entries
        if not SETTINGS.get_setting('skipcontextmenus'):
            context = build_context_menu(url, extra_data, server)
        else:
            context = None

        extra_data['mode'] = MODES.PLAYLIBRARY
        separator = '?'
        if '?' in extra_data['key']:
            separator = '&'
        item_url = '%s%s%st=%s' % \
                   (server.get_url_location(), extra_data['key'], separator, random_number)

        add_item_to_gui(item_url, details, extra_data, context, folder=False)

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

        tempgenre = []

        for child in show:
            if child.tag == 'Genre':
                tempgenre.append(child.get('tag', ''))

        _watched = int(show.get('viewedLeafCount', 0))

        # Create the basic data structures to pass up
        details = {
            'title': encode_utf8(show.get('title', i18n('Unknown'))),
            'sorttitle': encode_utf8(show.get('titleSort',
                                              show.get('title', i18n('Unknown')))),
            'TVShowTitle': encode_utf8(show.get('title', i18n('Unknown'))),
            'studio': encode_utf8(show.get('studio', '')),
            'plot': encode_utf8(show.get('summary', '')),
            'season': 0,
            'episode': int(show.get('leafCount', 0)),
            'mpaa': show.get('contentRating', ''),
            'rating': float(show.get('rating', 0)),
            'aired': show.get('originallyAvailableAt', ''),
            'genre': ' / '.join(tempgenre),
            'mediatype': 'tvshow'
        }

        extra_data = {
            'type': 'video',
            'source': 'tvshows',
            'UnWatchedEpisodes': int(details['episode']) - _watched,
            'WatchedEpisodes': _watched,
            'TotalEpisodes': details['episode'],
            'thumb': get_thumb_image(show, server),
            'fanart_image': get_fanart_image(show, server),
            'banner': get_banner_image(show, server),
            'key': show.get('key', ''),
            'ratingKey': str(show.get('ratingKey', 0))
        }

        # Set up overlays for watched and unwatched episodes
        if extra_data['WatchedEpisodes'] == 0:
            details['playcount'] = 0
        elif extra_data['UnWatchedEpisodes'] == 0:
            details['playcount'] = 1
        else:
            extra_data['partialTV'] = 1

        # Create URL based on whether we are going to flatten the season view
        if SETTINGS.get_setting('flatten') == '2':
            LOG.debug('Flattening all shows')
            extra_data['mode'] = MODES.TVEPISODES
            item_url = '%s%s' % (server.get_url_location(),
                                 extra_data['key'].replace('children', 'allLeaves'))
        else:
            extra_data['mode'] = MODES.TVSEASONS
            item_url = '%s%s' % (server.get_url_location(), extra_data['key'])

        if not SETTINGS.get_setting('skipcontextmenus'):
            context = build_context_menu(url, extra_data, server)
        else:
            context = None

        add_item_to_gui(item_url, details, extra_data, context)

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
    artist_tag = tree.findall('Directory')
    for _artist in artist_tag:
        details = {'artist': encode_utf8(_artist.get('title', ''))}

        details['title'] = details['artist']

        extra_data = {
            'type': 'Music',
            'thumb': get_thumb_image(_artist, server),
            'fanart_image': get_fanart_image(_artist, server),
            'ratingKey': _artist.get('title', ''),
            'key': _artist.get('key', ''),
            'mode': MODES.ALBUMS,
            'plot': _artist.get('summary', ''),
            'mediatype': 'artist'
        }

        url = '%s%s' % (server.get_url_location(), extra_data['key'])

        add_item_to_gui(url, details, extra_data)

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
    album_tags = tree.findall('Directory')
    recent = 'recentlyAdded' in url
    for album in album_tags:

        details = {
            'album': encode_utf8(album.get('title', '')),
            'year': int(album.get('year', 0)),
            'artist': encode_utf8(tree.get('parentTitle', album.get('parentTitle', ''))),
            'mediatype': 'album'
        }

        if recent:
            details['title'] = '%s - %s' % (details['artist'], details['album'])
        else:
            details['title'] = details['album']

        extra_data = {
            'type': 'Music',
            'thumb': get_thumb_image(album, server),
            'fanart_image': get_fanart_image(album, server),
            'key': album.get('key', ''),
            'mode': MODES.TRACKS,
            'plot': album.get('summary', '')
        }

        if extra_data['fanart_image'] == '':
            extra_data['fanart_image'] = sectionart

        url = '%s%s' % (server.get_url_location(), extra_data['key'])

        add_item_to_gui(url, details, extra_data)

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


def process_tvseasons(url, rating_key=None, plex_network=None):  # pylint: disable=too-many-branches, too-many-locals
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

        if SETTINGS.get_setting('disable_all_season') and season.get('index') is None:
            continue

        _watched = int(season.get('viewedLeafCount', 0))

        # Create the basic data structures to pass up
        details = {
            'title': encode_utf8(season.get('title', i18n('Unknown'))),
            'TVShowTitle': encode_utf8(season.get('parentTitle', i18n('Unknown'))),
            'sorttitle': encode_utf8(season.get('titleSort',
                                                season.get('title', i18n('Unknown')))),
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

        extra_data = {
            'type': 'video',
            'source': 'tvseasons',
            'TotalEpisodes': details['episode'],
            'WatchedEpisodes': _watched,
            'UnWatchedEpisodes': details['episode'] - _watched,
            'thumb': get_thumb_image(season, server),
            'fanart_image': get_fanart_image(season, server),
            'banner': banner,
            'key': season.get('key', ''),
            'ratingKey': str(season.get('ratingKey', 0)),
            'mode': MODES.TVEPISODES
        }

        if extra_data['fanart_image'] == '':
            extra_data['fanart_image'] = sectionart

        # Set up overlays for watched and unwatched episodes
        if extra_data['WatchedEpisodes'] == 0:
            details['playcount'] = 0
        elif extra_data['UnWatchedEpisodes'] == 0:
            details['playcount'] = 1
        else:
            extra_data['partialTV'] = 1

        item_url = '%s%s' % (server.get_url_location(), extra_data['key'])

        if not SETTINGS.get_setting('skipcontextmenus'):
            context = build_context_menu(item_url, season, server)
        else:
            context = None

        # Build the screen directory listing
        add_item_to_gui(item_url, details, extra_data, context)

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))


def process_plex_plugins(url, tree=None, plex_network=None):  # pylint: disable=too-many-branches
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

    myplex_url = False
    if (tree.get('identifier') != 'com.plexapp.plugins.myplex') and ('node.plexapp.com' in url):
        myplex_url = True
        LOG.debug('This is a myPlex URL, attempting to locate master server')
        server = get_master_server()

    for plugin in tree:

        details = {'title': encode_utf8(plugin.get('title'))}

        if details['title']:
            details['title'] = encode_utf8(plugin.get('name', i18n('Unknown')))

        if plugin.get('summary'):
            details['plot'] = plugin.get('summary')

        extra_data = {
            'thumb': get_thumb_image(plugin, server),
            'fanart_image': get_fanart_image(plugin, server),
            'identifier': tree.get('identifier', ''),
            'type': 'Video',
            'key': plugin.get('key', '')
        }

        if myplex_url:
            extra_data['key'] = extra_data['key'].replace('node.plexapp.com:32400',
                                                          server.get_location())

        if extra_data['fanart_image'] == '':
            extra_data['fanart_image'] = get_fanart_image(tree, server)

        p_url = get_link_url(url, extra_data, server)

        if plugin.tag == 'Directory' or plugin.tag == 'Podcast':

            if plugin.get('search') == '1':
                extra_data['mode'] = MODES.CHANNELSEARCH
                extra_data['parameters'] = {
                    'prompt': encode_utf8(plugin.get('prompt', i18n('Enter search term')))
                }
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

            details['title'] = '%s - [%s]' % \
                               (encode_utf8(plugin.get('label', i18n('Unknown'))), value)
            extra_data['mode'] = MODES.CHANNELPREFS
            extra_data['parameters'] = {'id': plugin.get('id')}
            add_item_to_gui(url, details, extra_data)

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))


def process_music(url, tree=None, plex_network=None):
    if plex_network is None:
        plex_network = plex.Plex(load=True)

    xbmcplugin.setContent(get_handle(), 'artists')

    server = plex_network.get_server_from_url(url)

    tree = get_xml(url, tree)
    if tree is None:
        return

    for grapes in tree:

        if grapes.get('key') is None:
            continue

        details = {
            'genre': encode_utf8(grapes.get('genre', '')),
            'artist': encode_utf8(grapes.get('artist', '')),
            'year': int(grapes.get('year', 0)),
            'album': encode_utf8(grapes.get('album', '')),
            'tracknumber': int(grapes.get('index', 0)),
            'title': i18n('Unknown')
        }

        extra_data = {
            'type': 'Music',
            'thumb': get_thumb_image(grapes, server),
            'fanart_image': get_fanart_image(grapes, server)
        }

        if extra_data['fanart_image'] == '':
            extra_data['fanart_image'] = get_fanart_image(tree, server)

        item_url = get_link_url(url, grapes, server)

        if grapes.tag == 'Track':
            LOG.debug('Track Tag')
            xbmcplugin.setContent(get_handle(), 'songs')
            details['mediatype'] = 'song'
            details['title'] = grapes.get('track',
                                          encode_utf8(grapes.get('title', i18n('Unknown'))))
            details['duration'] = int(int(grapes.get('total_time', 0)) / 1000)

            extra_data['mode'] = MODES.BASICPLAY
            add_item_to_gui(item_url, details, extra_data, folder=False)

        else:

            if grapes.tag == 'Artist':
                LOG.debug('Artist Tag')
                xbmcplugin.setContent(get_handle(), 'artists')
                details['mediatype'] = 'artist'
                details['title'] = encode_utf8(grapes.get('artist', i18n('Unknown')))

            elif grapes.tag == 'Album':
                LOG.debug('Album Tag')
                xbmcplugin.setContent(get_handle(), 'albums')
                details['mediatype'] = 'album'
                details['title'] = encode_utf8(grapes.get('album', i18n('Unknown')))

            elif grapes.tag == 'Genre':
                details['title'] = encode_utf8(grapes.get('genre', i18n('Unknown')))

            else:
                LOG.debug('Generic Tag: %s' % grapes.tag)
                details['title'] = encode_utf8(grapes.get('title', i18n('Unknown')))

            extra_data['mode'] = MODES.MUSIC
            add_item_to_gui(item_url, details, extra_data)

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

        details = {'title': encode_utf8(plugin.get('title', plugin.get('name', i18n('Unknown'))))}
        extra_data = {
            'type': 'Video',
            'installed': int(plugin.get('installed', 2)),
            'key': plugin.get('key', ''),
            'thumb': get_thumb_image(plugin, server),
            'mode': MODES.CHANNELINSTALL
        }

        if extra_data['installed'] == 1:
            details['title'] = details['title'] + ' (%s)' % encode_utf8(i18n('installed'))

        elif extra_data['installed'] == 2:
            extra_data['mode'] = MODES.PLEXONLINE

        item_url = get_link_url(url, plugin, server)

        extra_data['parameters'] = {'name': details['title']}

        add_item_to_gui(item_url, details, extra_data)

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))

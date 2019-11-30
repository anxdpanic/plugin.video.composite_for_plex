# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import datetime
import random

from ..addon.common import CONFIG
from ..addon.common import MODES
from ..addon.common import SETTINGS
from ..addon.common import PrintDebug
from ..addon.common import encode_utf8
from ..addon.common import i18n
from ..addon.utils import add_item_to_gui
from ..addon.utils import build_context_menu
from ..addon.utils import directory_item_translate
from ..addon.utils import get_banner_image
from ..addon.utils import get_link_url
from ..addon.utils import get_thumb_image
from ..addon.utils import get_fanart_image
from ..addon.utils import get_media_data

LOG = PrintDebug(CONFIG['name'])


def create_movie_item(url, server, tree, movie):  # pylint: disable=too-many-locals, too-many-statements, too-many-branches
    temp_genre = []
    temp_cast = []
    temp_director = []
    temp_writer = []

    media_arguments = {}
    random_number = str(random.randint(1000000000, 9999999999))

    # Lets grab all the info we can quickly through either a dictionary, or assignment to a list
    # We'll process it later
    for child in movie:
        if child.tag == 'Media':
            media_arguments = dict(child.items())
        elif child.tag == 'Genre' and not SETTINGS.get_setting('skipmetadata'):
            temp_genre.append(child.get('tag'))
        elif child.tag == 'Writer' and not SETTINGS.get_setting('skipmetadata'):
            temp_writer.append(child.get('tag'))
        elif child.tag == 'Director' and not SETTINGS.get_setting('skipmetadata'):
            temp_director.append(child.get('tag'))
        elif child.tag == 'Role' and not SETTINGS.get_setting('skipmetadata'):
            temp_cast.append(child.get('tag'))

    LOG.debug('Media attributes are %s' % media_arguments)

    # Gather some data
    view_offset = movie.get('viewOffset', 0)
    duration = int(media_arguments.get('duration', movie.get('duration', 0))) / 1000

    # Required listItem entries for XBMC
    details = {
        'plot': encode_utf8(movie.get('summary', '')),
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
        'mediatype': 'movie'
    }

    # Extra data required to manage other properties
    extra_data = {
        'type': 'Video',
        'source': 'movies',
        'thumb': get_thumb_image(movie, server),
        'fanart_image': get_fanart_image(movie, server),
        'key': movie.get('key', ''),
        'ratingKey': str(movie.get('ratingKey', 0)),
        'duration': duration,
        'resume': int(int(view_offset) / 1000)
    }

    if tree.get('playlistType'):
        playlist_key = str(tree.get('ratingKey', 0))
        if movie.get('playlistItemID') and playlist_key:
            extra_data.update({
                'playlist_item_id': movie.get('playlistItemID'),
                'playlist_title': tree.get('title'),
                'playlist_url': '/playlists/%s/items' % playlist_key
            })

    if tree.tag == 'MediaContainer':
        extra_data.update({'library_section_uuid': tree.get('librarySectionUUID')})

    # Determine what type of watched flag [overlay] to use
    if int(movie.get('viewCount', 0)) > 0:
        details['playcount'] = 1
    elif int(movie.get('viewCount', 0)) == 0:
        details['playcount'] = 0

    # Extended Metadata
    if not SETTINGS.get_setting('skipmetadata'):
        details['cast'] = temp_cast
        details['director'] = ' / '.join(temp_director)
        details['writer'] = ' / '.join(temp_writer)
        details['genre'] = ' / '.join(temp_genre)

    if movie.get('primaryExtraKey') is not None:
        details['trailer'] = 'plugin://' + CONFIG['id'] + '/?url=%s%s?t=%s&mode=%s' % \
                             (server.get_url_location(), movie.get('primaryExtraKey', ''),
                              random_number, MODES.PLAYLIBRARY)
        LOG.debug('Trailer plugin url added: %s' % details['trailer'])

    # Add extra media flag data
    if not SETTINGS.get_setting('skipflags'):
        extra_data.update(get_media_data(media_arguments))

    # Build any specific context menu entries
    if not SETTINGS.get_setting('skipcontextmenus'):
        context = build_context_menu(url, extra_data, server)
    else:
        context = None
    # http:// <server> <path> &mode=<mode> &t=<rnd>
    extra_data['mode'] = MODES.PLAYLIBRARY
    separator = '?'
    if '?' in extra_data['key']:
        separator = '&'
    final_url = '%s%s%st=%s' % \
                (server.get_url_location(), extra_data['key'], separator, random_number)

    add_item_to_gui(final_url, details, extra_data, context, folder=False)


def create_track_item(server, tree, track, listing=True):
    part_details = ()

    for child in track:
        for babies in child:
            if babies.tag == 'Part':
                part_details = (dict(babies.items()))

    LOG.debug('Part is %s' % str(part_details))

    details = {
        'TrackNumber': int(track.get('index', 0)),
        'discnumber': int(track.get('parentIndex', 0)),
        'title': str(track.get('index', 0)).zfill(2) + '. ' +
                 encode_utf8(track.get('title', i18n('Unknown'))),
        'rating': float(track.get('rating', 0)),
        'album': encode_utf8(track.get('parentTitle', tree.get('parentTitle', ''))),
        'artist': encode_utf8(track.get('grandparentTitle', tree.get('grandparentTitle', ''))),
        'duration': int(track.get('duration', 0)) / 1000,
        'mediatype': 'song'
    }

    section_art = get_fanart_image(tree, server)
    if track.get('thumb'):
        section_thumb = get_thumb_image(track, server)
    else:
        section_thumb = get_thumb_image(tree, server)

    extra_data = {
        'type': 'music',
        'fanart_image': section_art,
        'thumb': section_thumb,
        'key': track.get('key', ''),
        'ratingKey': str(track.get('ratingKey', 0)),
        'mode': MODES.PLAYLIBRARY
    }

    if tree.get('playlistType'):
        playlist_key = str(tree.get('ratingKey', 0))
        if track.get('playlistItemID') and playlist_key:
            extra_data.update({
                'playlist_item_id': track.get('playlistItemID'),
                'playlist_title': tree.get('title'),
                'playlist_url': '/playlists/%s/items' % playlist_key
            })

    if tree.tag == 'MediaContainer':
        extra_data.update({'library_section_uuid': tree.get('librarySectionUUID')})

    # If we are streaming, then get the virtual location
    url = '%s%s' % (server.get_url_location(), extra_data['key'])

    # Build any specific context menu entries
    if not SETTINGS.get_setting('skipcontextmenus'):
        context = build_context_menu(url, extra_data, server)
    else:
        context = None

    if listing:
        add_item_to_gui(url, details, extra_data, context, folder=False)

    return url, details


def create_playlist_item(url, server, track, listing=True):
    details = {
        'title': encode_utf8(track.get('title', i18n('Unknown'))),
        'duration': int(track.get('duration', 0)) / 1000
    }

    extra_data = {
        'type': track.get('playlistType', ''),
        'thumb': get_thumb_image({'thumb': track.get('composite', '')}, server)
    }

    if extra_data['type'] == 'video':
        extra_data['mode'] = MODES.MOVIES
    elif extra_data['type'] == 'audio':
        extra_data['mode'] = MODES.TRACKS
    else:
        extra_data['mode'] = MODES.GETCONTENT

    item_url = get_link_url(url, track, server)

    if listing:
        add_item_to_gui(item_url, details, extra_data, folder=True)

    return url, details


def create_directory_item(server, tree, url, directory):
    title = encode_utf8(directory.get('title', i18n('Unknown')))
    title = directory_item_translate(title, tree.get('thumb'))

    details = {'title': title}

    if '/collection' in url:
        details['mediatype'] = 'set'

    extra_data = {
        'thumb': get_thumb_image(tree, server),
        'fanart_image': get_fanart_image(tree, server),
        'mode': MODES.GETCONTENT,
        'type': 'Folder'
    }

    item_url = '%s' % (get_link_url(url, directory, server))

    add_item_to_gui(item_url, details, extra_data)


def create_episode_item(server, tree, url, episode):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
    temp_genre = []
    temp_cast = []
    temp_director = []
    temp_writer = []
    media_arguments = {}

    random_number = str(random.randint(1000000000, 9999999999))

    use_go_to = url.endswith(('onDeck', 'recentlyAdded', 'recentlyViewed', 'newest'))

    for child in episode:
        if child.tag == 'Media':
            media_arguments = dict(child.items())
        elif child.tag == 'Genre' and not SETTINGS.get_setting('skipmetadata'):
            temp_genre.append(child.get('tag'))
        elif child.tag == 'Writer' and not SETTINGS.get_setting('skipmetadata'):
            temp_writer.append(child.get('tag'))
        elif child.tag == 'Director' and not SETTINGS.get_setting('skipmetadata'):
            temp_director.append(child.get('tag'))
        elif child.tag == 'Role' and not SETTINGS.get_setting('skipmetadata'):
            temp_cast.append(child.get('tag'))

    LOG.debug('Media attributes are %s' % media_arguments)

    # Gather some data
    view_offset = episode.get('viewOffset', 0)
    duration = int(media_arguments.get('duration', episode.get('duration', 0))) / 1000

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

    art = {
        'banner': get_banner_image(tree, server),
        'season_thumb': tree.get('thumb', ''),
        'section_art': '',
    }

    # get season thumb for SEASON NODE
    if art['season_thumb'] == '/:/resources/show.png':
        art['season_thumb'] = ''

    if not SETTINGS.get_setting('skipimages'):
        art['section_art'] = get_fanart_image(tree, server)

    # Extra data required to manage other properties
    extra_data = {
        'type': 'Video',
        'source': 'tvepisodes',
        'thumb': get_thumb_image(episode, server),
        'fanart_image': get_fanart_image(episode, server),
        'banner': art.get('banner', ''),
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
        extra_data['fanart_image'] = art.get('section_art', '')

    if '-1' in extra_data['fanart_image'] and not SETTINGS.get_setting('skipimages'):
        extra_data['fanart_image'] = art.get('section_art', '')

    if art.get('season_thumb', ''):
        extra_data['season_thumb'] = server.get_url_location() + art.get('season_thumb', '')

    # get ALL SEASONS or TVSHOW thumb
    if not art.get('season_thumb', '') and episode.get('parentThumb', ''):
        extra_data['season_thumb'] = '%s%s' % (server.get_url_location(),
                                               episode.get('parentThumb', ''))
    elif not art.get('season_thumb', '') and episode.get('grandparentThumb', ''):
        extra_data['season_thumb'] = '%s%s' % (server.get_url_location(),
                                               episode.get('grandparentThumb', ''))

    # Determine what type of watched flag [overlay] to use
    if int(episode.get('viewCount', 0)) > 0:
        details['playcount'] = 1
    else:
        details['playcount'] = 0

    # Extended Metadata
    if not SETTINGS.get_setting('skipmetadata'):
        details['cast'] = temp_cast
        details['director'] = ' / '.join(temp_director)
        details['writer'] = ' / '.join(temp_writer)
        details['genre'] = ' / '.join(temp_genre)

    # Add extra media flag data
    if not SETTINGS.get_setting('skipflags'):
        extra_data.update(get_media_data(media_arguments))

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


def create_tvshow_item(server, url, show):
    temp_genre = []

    for child in show:
        if child.tag == 'Genre':
            temp_genre.append(child.get('tag', ''))

    _watched = int(show.get('viewedLeafCount', 0))

    # Create the basic data structures to pass up
    details = {
        'title': encode_utf8(show.get('title', i18n('Unknown'))),
        'sorttitle': encode_utf8(show.get('titleSort', show.get('title', i18n('Unknown')))),
        'TVShowTitle': encode_utf8(show.get('title', i18n('Unknown'))),
        'studio': encode_utf8(show.get('studio', '')),
        'plot': encode_utf8(show.get('summary', '')),
        'season': 0,
        'episode': int(show.get('leafCount', 0)),
        'mpaa': show.get('contentRating', ''),
        'rating': float(show.get('rating', 0)),
        'aired': show.get('originallyAvailableAt', ''),
        'genre': ' / '.join(temp_genre),
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


def create_artist_item(server, artist):
    details = {'artist': encode_utf8(artist.get('title', ''))}

    details['title'] = details['artist']

    extra_data = {
        'type': 'Music',
        'thumb': get_thumb_image(artist, server),
        'fanart_image': get_fanart_image(artist, server),
        'ratingKey': artist.get('title', ''),
        'key': artist.get('key', ''),
        'mode': MODES.ALBUMS,
        'plot': artist.get('summary', ''),
        'mediatype': 'artist'
    }

    url = '%s%s' % (server.get_url_location(), extra_data['key'])

    add_item_to_gui(url, details, extra_data)


def create_album_item(server, tree, url, album):
    details = {
        'album': encode_utf8(album.get('title', '')),
        'year': int(album.get('year', 0)),
        'artist': encode_utf8(tree.get('parentTitle', album.get('parentTitle', ''))),
        'mediatype': 'album'
    }

    if 'recentlyAdded' in url:
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
        extra_data['fanart_image'] = get_fanart_image(tree, server)

    url = '%s%s' % (server.get_url_location(), extra_data['key'])

    add_item_to_gui(url, details, extra_data)


def create_season_item(server, tree, season):
    plot = encode_utf8(tree.get('summary', ''))

    _watched = int(season.get('viewedLeafCount', 0))

    # Create the basic data structures to pass up
    details = {
        'title': encode_utf8(season.get('title', i18n('Unknown'))),
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

    extra_data = {
        'type': 'video',
        'source': 'tvseasons',
        'TotalEpisodes': details['episode'],
        'WatchedEpisodes': _watched,
        'UnWatchedEpisodes': details['episode'] - _watched,
        'thumb': get_thumb_image(season, server),
        'fanart_image': get_fanart_image(season, server),
        'banner': get_banner_image(tree, server),
        'key': season.get('key', ''),
        'ratingKey': str(season.get('ratingKey', 0)),
        'mode': MODES.TVEPISODES
    }

    if extra_data['fanart_image'] == '':
        extra_data['fanart_image'] = get_fanart_image(tree, server)

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


def create_plex_plugin_item(server, tree, url, plugin):  # pylint: disable=too-many-branches
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

    if (tree.get('identifier') != 'com.plexapp.plugins.myplex') and ('node.plexapp.com' in url):
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

        details['title'] = '%s - [%s]' % (encode_utf8(plugin.get('label', i18n('Unknown'))), value)
        extra_data['mode'] = MODES.CHANNELPREFS
        extra_data['parameters'] = {'id': plugin.get('id')}
        add_item_to_gui(url, details, extra_data)


def create_music_item(server, tree, url, music):
    details = {
        'genre': encode_utf8(music.get('genre', '')),
        'artist': encode_utf8(music.get('artist', '')),
        'year': int(music.get('year', 0)),
        'album': encode_utf8(music.get('album', '')),
        'tracknumber': int(music.get('index', 0)),
        'title': i18n('Unknown')
    }

    extra_data = {
        'type': 'Music',
        'thumb': get_thumb_image(music, server),
        'fanart_image': get_fanart_image(music, server)
    }

    if extra_data['fanart_image'] == '':
        extra_data['fanart_image'] = get_fanart_image(tree, server)

    item_url = get_link_url(url, music, server)

    if music.tag == 'Track':
        LOG.debug('Track Tag')
        details['mediatype'] = 'song'
        details['title'] = music.get('track', encode_utf8(music.get('title', i18n('Unknown'))))
        details['duration'] = int(int(music.get('total_time', 0)) / 1000)

        extra_data['mode'] = MODES.BASICPLAY
        add_item_to_gui(item_url, details, extra_data, folder=False)

    else:

        if music.tag == 'Artist':
            LOG.debug('Artist Tag')
            details['mediatype'] = 'artist'
            details['title'] = encode_utf8(music.get('artist', i18n('Unknown')))

        elif music.tag == 'Album':
            LOG.debug('Album Tag')
            details['mediatype'] = 'album'
            details['title'] = encode_utf8(music.get('album', i18n('Unknown')))

        elif music.tag == 'Genre':
            details['title'] = encode_utf8(music.get('genre', i18n('Unknown')))

        else:
            LOG.debug('Generic Tag: %s' % music.tag)
            details['title'] = encode_utf8(music.get('title', i18n('Unknown')))

        extra_data['mode'] = MODES.MUSIC
        add_item_to_gui(item_url, details, extra_data)

    content_type = details.get('mediatype')
    if content_type:
        content_type += 's'
    else:
        content_type = 'artists'

    return content_type


def create_plex_online_item(server, url, plugin):
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


def create_photo_item(server, tree, url, photo):
    details = {'title': encode_utf8(photo.get('title', photo.get('name', i18n('Unknown'))))}

    if not details['title']:
        details['title'] = i18n('Unknown')

    extra_data = {
        'thumb': get_thumb_image(photo, server),
        'fanart_image': get_fanart_image(photo, server),
        'type': 'image'
    }

    if extra_data['fanart_image'] == '':
        extra_data['fanart_image'] = get_fanart_image(tree, server)

    item_url = get_link_url(url, photo, server)

    if photo.tag == 'Directory':
        extra_data['mode'] = MODES.PHOTOS
        add_item_to_gui(item_url, details, extra_data)

    elif photo.tag == 'Photo' and tree.get('viewGroup', '') == 'photo':
        for pics in photo:
            if pics.tag == 'Media':
                parts = [img for img in pics if img.tag == 'Part']
                for part in parts:
                    extra_data['key'] = \
                        server.get_url_location() + part.get('key', '')
                    details['size'] = int(part.get('size', 0))
                    item_url = extra_data['key']

        add_item_to_gui(item_url, details, extra_data, folder=False)

# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import datetime

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
from ..addon.utils import get_link_url
from ..addon.utils import get_thumb_image
from ..addon.utils import get_fanart_image
from ..addon.utils import get_media_data

LOG = PrintDebug(CONFIG['name'])


def movie_tag(url, server, tree, movie, random_number):  # pylint: disable=too-many-locals, too-many-statements, too-many-branches
    LOG.debug('---New Item---')
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
    view_offset = movie.get('viewOffset', 0)
    duration = int(mediaarguments.get('duration', movie.get('duration', 0))) / 1000

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
        details['cast'] = tempcast
        details['director'] = ' / '.join(tempdir)
        details['writer'] = ' / '.join(tempwriter)
        details['genre'] = ' / '.join(tempgenre)

    if movie.get('primaryExtraKey') is not None:
        details['trailer'] = 'plugin://' + CONFIG['id'] + '/?url=%s%s?t=%s&mode=%s' % \
                             (server.get_url_location(), movie.get('primaryExtraKey', ''),
                              random_number, MODES.PLAYLIBRARY)
        LOG.debug('Trailer plugin url added: %s' % details['trailer'])

    # Add extra media flag data
    if not SETTINGS.get_setting('skipflags'):
        extra_data.update(get_media_data(mediaarguments))

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


def track_tag(server, tree, track, sectionart='', sectionthumb='', listing=True):  # pylint: disable=too-many-arguments
    xbmcplugin.setContent(get_handle(), 'songs')

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
        'artist': encode_utf8(track.get('grandparentTitle',
                                        tree.get('grandparentTitle', ''))),
        'duration': int(track.get('duration', 0)) / 1000,
        'mediatype': 'song'
    }

    extra_data = {
        'type': 'music',
        'fanart_image': sectionart,
        'thumb': sectionthumb,
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


def playlist_tag(url, server, track, listing=True):
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

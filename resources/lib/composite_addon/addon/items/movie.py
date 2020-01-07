# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import datetime
import json

from ..constants import CONFIG
from ..constants import MODES
from ..logger import Logger
from ..strings import encode_utf8
from ..strings import i18n
from .common import create_gui_item
from .common import get_fanart_image
from .common import get_media_data
from .common import get_metadata
from .common import get_thumb_image
from .context_menu import ContextMenu

LOG = Logger()


def create_movie_item(context, server, tree, url, movie, library=False):  # pylint: disable=too-many-arguments

    metadata = get_metadata(context, movie)
    LOG.debug('Media attributes are %s' % json.dumps(metadata['attributes'], indent=4))

    # Gather some data
    view_offset = movie.get('viewOffset', 0)
    duration = int(metadata['attributes'].get('duration', movie.get('duration', 0))) / 1000

    # Required listItem entries for Kodi
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
        'mediatype': 'movie',
        'playcount': int(int(movie.get('viewCount', 0)) > 0),
        'cast': metadata['cast'],
        'director': ' / '.join(metadata['director']),
        'genre': ' / '.join(metadata['genre']),
        'set': ' / '.join(metadata['collections']),
        'writer': ' / '.join(metadata['writer']),
    }

    # Extra data required to manage other properties
    extra_data = {
        'type': 'Video',
        'source': 'movies',
        'thumb': get_thumb_image(context, server, movie),
        'fanart_image': get_fanart_image(context, server, movie),
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
        extra_data.update({
            'library_section_uuid': tree.get('librarySectionUUID')
        })

    if movie.get('primaryExtraKey') is not None:
        details['trailer'] = 'plugin://' + CONFIG['id'] + '/?url=%s%s?mode=%s' % \
                             (server.get_url_location(), movie.get('primaryExtraKey', ''),
                              MODES.PLAYLIBRARY)
        LOG.debug('Trailer plugin url added: %s' % details['trailer'])

    # Add extra media flag data
    if not context.settings.get_setting('skipflags'):
        extra_data.update(get_media_data(metadata['attributes']))

    # Build any specific context menu entries
    context_menu = None
    if not context.settings.get_setting('skipcontextmenus'):
        context_menu = ContextMenu(context, server, url, extra_data).menu

    # http:// <server> <path> &mode=<mode>
    extra_data['mode'] = MODES.PLAYLIBRARY
    if library:
        extra_data['path_mode'] = MODES.TXT_MOVIES_LIBRARY

    final_url = '%s%s' % (server.get_url_location(), extra_data['key'])

    return create_gui_item(context, final_url, details, extra_data, context_menu, folder=False)

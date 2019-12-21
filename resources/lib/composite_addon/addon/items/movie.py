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

from ...addon.constants import CONFIG
from ...addon.constants import MODES
from ...addon.logger import Logger
from ...addon.strings import encode_utf8
from ...addon.strings import i18n
from ...addon.utils import build_context_menu
from ...addon.utils import create_gui_item
from ...addon.utils import get_fanart_image
from ...addon.utils import get_media_data
from ...addon.utils import get_thumb_image

LOG = Logger()


def create_movie_item(context, server, tree, url, movie, library=False):  # pylint: disable=too-many-locals, too-many-statements, too-many-branches, too-many-arguments
    temp_genre = []
    temp_cast = []
    temp_collections = []
    temp_director = []
    temp_writer = []

    media_arguments = {}

    # Lets grab all the info we can quickly through either a dictionary, or assignment to a list
    # We'll process it later
    for child in movie:
        if child.tag == 'Media':
            media_arguments = dict(child.items())
        elif child.tag == 'Genre' and not context.settings.get_setting('skipmetadata'):
            temp_genre.append(child.get('tag'))
        elif child.tag == 'Writer' and not context.settings.get_setting('skipmetadata'):
            temp_writer.append(child.get('tag'))
        elif child.tag == 'Director' and not context.settings.get_setting('skipmetadata'):
            temp_director.append(child.get('tag'))
        elif child.tag == 'Role' and not context.settings.get_setting('skipmetadata'):
            temp_cast.append(child.get('tag'))
        elif child.tag == 'Collection' and not context.settings.get_setting('skipmetadata'):
            temp_collections.append(child.get('tag'))

    LOG.debug('Media attributes are %s' % json.dumps(media_arguments, indent=4))

    # Gather some data
    view_offset = movie.get('viewOffset', 0)
    duration = int(media_arguments.get('duration', movie.get('duration', 0))) / 1000

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
        'mediatype': 'movie'
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

    # Determine what type of watched flag [overlay] to use
    if int(movie.get('viewCount', 0)) > 0:
        details['playcount'] = 1
    elif int(movie.get('viewCount', 0)) == 0:
        details['playcount'] = 0

    # Extended Metadata
    if not context.settings.get_setting('skipmetadata'):
        details['cast'] = temp_cast
        details['director'] = ' / '.join(temp_director)
        details['writer'] = ' / '.join(temp_writer)
        details['genre'] = ' / '.join(temp_genre)
        if temp_collections:
            details['set'] = ' / '.join(temp_collections)

    if movie.get('primaryExtraKey') is not None:
        details['trailer'] = 'plugin://' + CONFIG['id'] + '/?url=%s%s?mode=%s' % \
                             (server.get_url_location(), movie.get('primaryExtraKey', ''),
                              MODES.PLAYLIBRARY)
        LOG.debug('Trailer plugin url added: %s' % details['trailer'])

    # Add extra media flag data
    if not context.settings.get_setting('skipflags'):
        extra_data.update(get_media_data(media_arguments))

    # Build any specific context menu entries
    context_menu = None
    if not context.settings.get_setting('skipcontextmenus'):
        context_menu = build_context_menu(context, server, url, extra_data)

    # http:// <server> <path> &mode=<mode>
    extra_data['mode'] = MODES.PLAYLIBRARY
    if library:
        extra_data['path_mode'] = MODES.TXT_MOVIES_LIBRARY

    final_url = '%s%s' % (server.get_url_location(), extra_data['key'])

    return create_gui_item(context, final_url, details, extra_data, context_menu, folder=False)

# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import hashlib

from ..constants import MODES
from ..logger import Logger
from ..strings import encode_utf8
from ..strings import i18n
from .common import create_gui_item
from .common import get_banner_image
from .common import get_fanart_image
from .common import get_metadata
from .common import get_thumb_image
from .context_menu import ContextMenu

LOG = Logger()


def create_show_item(context, server, url, show, library=False):
    metadata = get_metadata(context, show)

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
        'cast': metadata['cast'],
        'genre': ' / '.join(metadata['genre']),
        'mediatype': 'tvshow'
    }

    extra_data = {
        'type': 'video',
        'source': 'tvshows',
        'UnWatchedEpisodes': int(details['episode']) - _watched,
        'WatchedEpisodes': _watched,
        'TotalEpisodes': details['episode'],
        'thumb': get_thumb_image(context, server, show),
        'fanart_image': get_fanart_image(context, server, show),
        'banner': get_banner_image(context, server, show),
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
    if context.settings.get_setting('flatten') == '2':
        LOG.debug('Flattening all shows')
        extra_data['mode'] = MODES.TVEPISODES
        item_url = '%s%s' % (server.get_url_location(),
                             extra_data['key'].replace('children', 'allLeaves'))
    else:
        extra_data['mode'] = MODES.TVSEASONS
        item_url = '%s%s' % (server.get_url_location(), extra_data['key'])

    context_menu = None
    if not context.settings.get_setting('skipcontextmenus'):
        context_menu = ContextMenu(context, server, url, extra_data).menu

    if library:
        extra_data['hash'] = _md5_hash(show)
        extra_data['path_mode'] = MODES.TXT_TVSHOWS_LIBRARY

    return create_gui_item(context, item_url, details, extra_data, context_menu)


def _md5_hash(show):
    show_hash = hashlib.md5()
    show_hash.update(show.get('addedAt', u'').encode('utf-8'))
    show_hash.update(show.get('updatedAt', u'').encode('utf-8'))
    return show_hash.hexdigest().upper()

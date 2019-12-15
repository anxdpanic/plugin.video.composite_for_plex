# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import hashlib

from six.moves.urllib_parse import quote_plus

from ...addon.constants import MODES
from ...addon.logger import Logger
from ...addon.settings import AddonSettings
from ...addon.strings import encode_utf8
from ...addon.strings import i18n
from ...addon.utils import create_gui_item
from ...addon.utils import build_context_menu
from ...addon.utils import get_banner_image
from ...addon.utils import get_thumb_image
from ...addon.utils import get_fanart_image

LOG = Logger()
SETTINGS = AddonSettings()


def create_show_item(server, url, show, library=False):
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

    context = None
    if not SETTINGS.get_setting('skipcontextmenus'):
        context = build_context_menu(url, extra_data, server)

    if library:
        extra_data['hash'] = \
            _md5_all_episodes(server, extra_data['key'], details.get('TVShowTitle', ''))
        extra_data['path_mode'] = MODES.TXT_TVSHOWS_LIBRARY

    return create_gui_item(item_url, details, extra_data, context)


def _md5_all_episodes(server, url, title):
    url = '%s%s' % (server.get_url_location(), url.replace('children', 'allLeaves'))

    tree = server.processed_xml(url)
    if tree is None:
        return None

    show_hash = hashlib.md5()

    hash_title = title
    if not isinstance(hash_title, bytes):
        hash_title = hash_title.encode('utf-8')
    hash_title = quote_plus(hash_title).encode('utf-8')

    show_hash.update(hash_title)

    for episode in tree:
        hash_title = episode.get('title')
        if not isinstance(hash_title, bytes):
            hash_title = hash_title.encode('utf-8')
        hash_title = quote_plus(hash_title).encode('utf-8')

        show_hash.update(hash_title)

    return show_hash.hexdigest().upper()

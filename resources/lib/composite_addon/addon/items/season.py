# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from ...addon.constants import MODES
from ...addon.strings import encode_utf8
from ...addon.strings import i18n
from .common import create_gui_item
from .common import get_banner_image
from .common import get_fanart_image
from .common import get_thumb_image
from .context_menu import ContextMenu


def create_season_item(context, server, tree, season, library=False):
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
        'thumb': get_thumb_image(context, server, season),
        'fanart_image': get_fanart_image(context, server, season),
        'banner': get_banner_image(context, server, tree),
        'key': season.get('key', ''),
        'ratingKey': str(season.get('ratingKey', 0)),
        'mode': MODES.TVEPISODES
    }

    if extra_data['fanart_image'] == '':
        extra_data['fanart_image'] = get_fanart_image(context, server, tree)

    # Set up overlays for watched and unwatched episodes
    if extra_data['WatchedEpisodes'] == 0:
        details['playcount'] = 0
    elif extra_data['UnWatchedEpisodes'] == 0:
        details['playcount'] = 1
    else:
        extra_data['partialTV'] = 1

    item_url = '%s%s' % (server.get_url_location(), extra_data['key'])

    context_menu = None
    if not context.settings.get_setting('skipcontextmenus'):
        context_menu = ContextMenu(context, server, item_url, season).menu

    if library:
        extra_data['path_mode'] = MODES.TXT_TVSHOWS_LIBRARY

    # Build the screen directory listing
    return create_gui_item(context, item_url, details, extra_data, context_menu)

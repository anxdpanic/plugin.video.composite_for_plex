# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from ...addon.constants import CONFIG
from ...addon.constants import MODES
from ...addon.settings import AddonSettings
from ...addon.strings import encode_utf8
from ...addon.strings import i18n
from ...addon.utils import create_gui_item
from ...addon.utils import build_context_menu
from ...addon.utils import get_banner_image
from ...addon.utils import get_thumb_image
from ...addon.utils import get_fanart_image

SETTINGS = AddonSettings()


def create_season_item(server, tree, season, library=False):
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

    context = None
    if not SETTINGS.get_setting('skipcontextmenus'):
        context = build_context_menu(item_url, season, server)

    if library:
        extra_data['path_mode'] = MODES.TXT_TVSHOWS_LIBRARY

    # Build the screen directory listing
    return create_gui_item(item_url, details, extra_data, context)

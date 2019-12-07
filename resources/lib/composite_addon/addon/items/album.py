# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from ...addon.common import MODES
from ...addon.common import encode_utf8
from ...addon.utils import create_gui_item
from ...addon.utils import get_thumb_image
from ...addon.utils import get_fanart_image


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

    return create_gui_item(url, details, extra_data)

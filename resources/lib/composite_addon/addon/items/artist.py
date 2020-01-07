# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from ..constants import MODES
from ..strings import encode_utf8
from .common import create_gui_item
from .common import get_fanart_image
from .common import get_thumb_image


def create_artist_item(context, server, artist):
    details = {
        'artist': encode_utf8(artist.get('title', ''))
    }

    details['title'] = details['artist']

    extra_data = {
        'type': 'Music',
        'thumb': get_thumb_image(context, server, artist),
        'fanart_image': get_fanart_image(context, server, artist),
        'ratingKey': artist.get('title', ''),
        'key': artist.get('key', ''),
        'mode': MODES.ALBUMS,
        'plot': artist.get('summary', ''),
        'mediatype': 'artist'
    }

    url = '%s%s' % (server.get_url_location(), extra_data['key'])

    return create_gui_item(context, url, details, extra_data)

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

    return create_gui_item(url, details, extra_data)

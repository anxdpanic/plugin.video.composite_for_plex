# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from ..constants import MODES
from ..logger import Logger
from ..strings import encode_utf8
from ..strings import i18n
from .common import create_gui_item
from .common import get_fanart_image
from .common import get_link_url
from .common import get_thumb_image

LOG = Logger()


def create_music_item(context, server, tree, url, music):
    details = {
        'genre': encode_utf8(music.get('genre', '')),
        'artist': encode_utf8(music.get('artist', '')),
        'year': int(music.get('year', 0)),
        'album': encode_utf8(music.get('album', '')),
        'tracknumber': int(music.get('index', 0)),
        'title': i18n('Unknown')
    }

    extra_data = {
        'type': 'Music',
        'thumb': get_thumb_image(context, server, music),
        'fanart_image': get_fanart_image(context, server, music)
    }

    if extra_data['fanart_image'] == '':
        extra_data['fanart_image'] = get_fanart_image(context, server, tree)

    item_url = get_link_url(server, url, music)

    if music.tag == 'Track':
        LOG.debug('Track Tag')
        details['mediatype'] = 'song'
        details['title'] = music.get('track', encode_utf8(music.get('title', i18n('Unknown'))))
        details['duration'] = int(int(music.get('total_time', 0)) / 1000)

        extra_data['mode'] = MODES.BASICPLAY
        return create_gui_item(context, item_url, details, extra_data, folder=False)

    details['mediatype'] = 'artist'

    if music.tag == 'Artist':
        LOG.debug('Artist Tag')
        details['mediatype'] = 'artist'
        details['title'] = encode_utf8(music.get('artist', i18n('Unknown')))

    elif music.tag == 'Album':
        LOG.debug('Album Tag')
        details['mediatype'] = 'album'
        details['title'] = encode_utf8(music.get('album', i18n('Unknown')))

    elif music.tag == 'Genre':
        details['title'] = encode_utf8(music.get('genre', i18n('Unknown')))

    else:
        LOG.debug('Generic Tag: %s' % music.tag)
        details['title'] = encode_utf8(music.get('title', i18n('Unknown')))

    extra_data['mode'] = MODES.MUSIC

    return create_gui_item(context, item_url, details, extra_data)

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
from ..strings import i18n
from .common import create_gui_item
from .common import get_link_url
from .common import get_thumb_image
from .context_menu import ContextMenu


def create_playlist_item(context, url, server, track, listing=True):
    details = {
        'title': encode_utf8(track.get('title', i18n('Unknown'))),
        'duration': int(track.get('duration', 0)) / 1000
    }

    extra_data = {
        'playlist': True,
        'ratingKey': track.get('ratingKey'),
        'type': track.get('playlistType', ''),
        'thumb': get_thumb_image(context, server, {
            'thumb': track.get('composite', '')
        }),
        'mode': MODES.GETCONTENT
    }

    if extra_data['type'] == 'video':
        extra_data['mode'] = MODES.MOVIES
    elif extra_data['type'] == 'audio':
        extra_data['mode'] = MODES.TRACKS
    elif extra_data['type'] == 'photo':
        extra_data['mode'] = MODES.PHOTOS

    item_url = get_link_url(server, url, track)

    context_menu = None
    if not context.settings.get_setting('skipcontextmenus'):
        context_menu = ContextMenu(context, server, item_url, extra_data).menu

    if listing:
        return create_gui_item(context, item_url, details, extra_data, context_menu, folder=True)

    return url, details

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
from ...addon.utils import create_gui_item
from ...addon.utils import get_link_url
from ...addon.utils import get_thumb_image


def create_playlist_item(url, server, track, settings, listing=True):
    details = {
        'title': encode_utf8(track.get('title', i18n('Unknown'))),
        'duration': int(track.get('duration', 0)) / 1000
    }

    extra_data = {
        'type': track.get('playlistType', ''),
        'thumb': get_thumb_image({
            'thumb': track.get('composite', '')
        }, server, settings),
        'mode': MODES.GETCONTENT
    }

    if extra_data['type'] == 'video':
        extra_data['mode'] = MODES.MOVIES
    elif extra_data['type'] == 'audio':
        extra_data['mode'] = MODES.TRACKS

    item_url = get_link_url(url, track, server)

    if listing:
        return create_gui_item(item_url, details, extra_data, folder=True, settings=settings)

    return url, details

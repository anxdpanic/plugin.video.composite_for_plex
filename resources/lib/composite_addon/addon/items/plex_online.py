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


def create_plex_online_item(server, url, plugin, settings):
    details = {
        'title': encode_utf8(plugin.get('title', plugin.get('name', i18n('Unknown'))))
    }
    extra_data = {
        'type': 'Video',
        'installed': int(plugin.get('installed', 2)),
        'key': plugin.get('key', ''),
        'thumb': get_thumb_image(plugin, server, settings),
        'mode': MODES.CHANNELINSTALL
    }

    if extra_data['installed'] == 1:
        details['title'] = details['title'] + ' (%s)' % encode_utf8(i18n('installed'))

    elif extra_data['installed'] == 2:
        extra_data['mode'] = MODES.PLEXONLINE

    item_url = get_link_url(url, plugin, server)

    extra_data['parameters'] = {
        'name': details['title']
    }

    return create_gui_item(item_url, details, extra_data, settings=settings)

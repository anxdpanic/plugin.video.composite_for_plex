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
from ...addon.common import i18n
from ...addon.utils import create_gui_item
from ...addon.utils import get_link_url
from ...addon.utils import get_thumb_image
from ...addon.utils import get_fanart_image


def create_photo_item(server, tree, url, photo):
    details = {'title': encode_utf8(photo.get('title', photo.get('name', i18n('Unknown'))))}

    if not details['title']:
        details['title'] = i18n('Unknown')

    extra_data = {
        'thumb': get_thumb_image(photo, server),
        'fanart_image': get_fanart_image(photo, server),
        'type': 'image'
    }

    if extra_data['fanart_image'] == '':
        extra_data['fanart_image'] = get_fanart_image(tree, server)

    item_url = get_link_url(url, photo, server)

    if photo.tag == 'Directory':
        extra_data['mode'] = MODES.PHOTOS
        return create_gui_item(item_url, details, extra_data)

    if photo.tag == 'Photo' and tree.get('viewGroup', '') == 'photo':
        for pics in photo:
            if pics.tag == 'Media':
                parts = [img for img in pics if img.tag == 'Part']
                for part in parts:
                    extra_data['key'] = \
                        server.get_url_location() + part.get('key', '')
                    details['size'] = int(part.get('size', 0))
                    item_url = extra_data['key']

        return create_gui_item(item_url, details, extra_data, folder=False)

    return None

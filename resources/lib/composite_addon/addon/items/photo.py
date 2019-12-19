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
from ...addon.utils import build_context_menu
from ...addon.utils import create_gui_item
from ...addon.utils import get_fanart_image
from ...addon.utils import get_link_url
from ...addon.utils import get_thumb_image


def create_photo_item(server, tree, url, photo, settings):
    details = {
        'title': encode_utf8(photo.get('title', photo.get('name', i18n('Unknown'))))
    }

    if not details['title']:
        details['title'] = i18n('Unknown')

    extra_data = {
        'thumb': get_thumb_image(photo, server, settings),
        'fanart_image': get_fanart_image(photo, server, settings),
        'type': 'image',
        'ratingKey': photo.get('ratingKey'),
        'mode': MODES.PLAYLIBRARY
    }

    if extra_data['fanart_image'] == '':
        extra_data['fanart_image'] = get_fanart_image(tree, server, settings)

    item_url = get_link_url(url, photo, server)

    if photo.tag == 'Directory':
        extra_data['mode'] = MODES.PHOTOS
        return create_gui_item(item_url, details, extra_data, settings=settings)

    if photo.tag == 'Photo' and (tree.get('viewGroup', '') == 'photo' or
                                 tree.get('playlistType') == 'photo'):
        if tree.get('playlistType'):
            playlist_key = str(tree.get('ratingKey', 0))
            if photo.get('playlistItemID') and playlist_key:
                extra_data.update({
                    'playlist_item_id': photo.get('playlistItemID'),
                    'playlist_title': tree.get('title'),
                    'playlist_url': '/playlists/%s/items' % playlist_key
                })

        if tree.tag == 'MediaContainer':
            extra_data.update({
                'library_section_uuid': tree.get('librarySectionUUID')
            })

        context = None
        if not settings.get_setting('skipcontextmenus'):
            context = build_context_menu(item_url, extra_data, server, settings)

        photo_url = '%s%s' % (server.get_url_location(), photo.get('key'))
        return create_gui_item(photo_url, details, extra_data, context,
                               folder=False, settings=settings)

    return None

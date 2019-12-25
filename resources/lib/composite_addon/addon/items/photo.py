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
from .common import create_gui_item
from .common import get_fanart_image
from .common import get_link_url
from .common import get_thumb_image
from .context_menu import ContextMenu


def create_photo_item(context, server, tree, url, photo):
    details = {
        'title': encode_utf8(photo.get('title', photo.get('name', i18n('Unknown'))))
    }

    if not details['title']:
        details['title'] = i18n('Unknown')

    extra_data = {
        'thumb': get_thumb_image(context, server, photo),
        'fanart_image': get_fanart_image(context, server, photo),
        'type': 'image',
        'ratingKey': photo.get('ratingKey'),
    }

    if extra_data['fanart_image'] == '':
        extra_data['fanart_image'] = get_fanart_image(context, server, tree)

    item_url = get_link_url(server, url, photo)

    if photo.tag == 'Directory':
        extra_data['mode'] = MODES.PHOTOS
        extra_data['type'] = 'folder'
        return create_gui_item(context, item_url, details, extra_data)

    if photo.tag == 'Photo' and (tree.get('viewGroup', '') == 'photo' or
                                 tree.get('playlistType') == 'photo'):
        for pics in photo:
            if pics.tag == 'Media':
                parts = [img for img in pics if img.tag == 'Part']
                for part in parts:
                    extra_data['key'] = \
                        server.get_formatted_url(part.get('key', ''))
                    details['size'] = int(part.get('size', 0))
                    details['picturepath'] = extra_data['key']
                    item_url = extra_data['key']

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

        context_menu = None
        if not context.settings.get_setting('skipcontextmenus'):
            context_menu = ContextMenu(context, server, item_url, extra_data).menu

        return create_gui_item(context, item_url, details, extra_data, context_menu, folder=False)

    return None

# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from ..constants import MODES
from ..strings import directory_item_translate
from ..strings import encode_utf8
from ..strings import i18n
from .common import create_gui_item
from .common import get_fanart_image
from .common import get_link_url
from .common import get_thumb_image


def create_directory_item(context, server, tree, url, directory):
    title = encode_utf8(directory.get('title', i18n('Unknown')))
    title = directory_item_translate(title, tree.get('thumb'))

    details = {
        'title': title
    }

    if '/collection' in url:
        details['mediatype'] = 'set'

    extra_data = {
        'thumb': get_thumb_image(context, server, tree),
        'fanart_image': get_fanart_image(context, server, tree),
        'mode': MODES.GETCONTENT,
        'type': 'Folder'
    }

    item_url = '%s' % (get_link_url(server, url, directory))

    return create_gui_item(context, item_url, details, extra_data)

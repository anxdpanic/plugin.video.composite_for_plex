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
from ...addon.utils import directory_item_translate
from ...addon.utils import get_link_url
from ...addon.utils import get_thumb_image
from ...addon.utils import get_fanart_image


def create_directory_item(server, tree, url, directory):
    title = encode_utf8(directory.get('title', i18n('Unknown')))
    title = directory_item_translate(title, tree.get('thumb'))

    details = {'title': title}

    if '/collection' in url:
        details['mediatype'] = 'set'

    extra_data = {
        'thumb': get_thumb_image(tree, server),
        'fanart_image': get_fanart_image(tree, server),
        'mode': MODES.GETCONTENT,
        'type': 'Folder'
    }

    item_url = '%s' % (get_link_url(url, directory, server))

    return create_gui_item(item_url, details, extra_data)

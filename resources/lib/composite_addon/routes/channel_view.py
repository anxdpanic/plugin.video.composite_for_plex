# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from six import PY3

import xbmcplugin  # pylint: disable=import-error

from ..addon.common import MODES
from ..addon.common import SETTINGS
from ..addon.common import get_handle
from ..addon.common import i18n
from ..addon.utils import add_item_to_gui
from ..addon.utils import get_link_url
from ..addon.utils import get_fanart_image
from ..addon.utils import get_thumb_image
from ..plex import plex

PLEX_NETWORK = plex.Plex(load=False)


def run(url):
    PLEX_NETWORK.load()
    server = PLEX_NETWORK.get_server_from_url(url)
    tree = server.processed_xml(url)

    if tree is None:
        return

    if PY3:
        tree_iter = tree.iter()
    else:
        tree_iter = tree.getiterator('Directory')  # pylint: disable=deprecated-method

    for channels in tree_iter:

        if channels.get('local', '') == '0' or channels.get('size', '0') == '0':
            continue

        extra_data = {
            'fanart_image': get_fanart_image(channels, server),
            'thumb': get_thumb_image(channels, server)
        }

        details = {'title': channels.get('title', i18n('Unknown'))}

        suffix = channels.get('key').split('/')[1]

        if channels.get('unique', '') == '0':
            details['title'] = '%s (%s)' % (details['title'], suffix)

        # Alter data sent into get_link_url, as channels use path rather than key
        p_url = get_link_url(url,
                             {'key': channels.get('key'), 'identifier': channels.get('key')},
                             server)

        if suffix == 'photos':
            extra_data['mode'] = MODES.PHOTOS
        elif suffix == 'video':
            extra_data['mode'] = MODES.PLEXPLUGINS
        elif suffix == 'music':
            extra_data['mode'] = MODES.MUSIC
        else:
            extra_data['mode'] = MODES.GETCONTENT

        add_item_to_gui(p_url, details, extra_data)

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))

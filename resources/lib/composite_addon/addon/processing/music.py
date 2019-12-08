# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from kodi_six import xbmcplugin  # pylint: disable=import-error

from . import SETTINGS
from ...addon.common import get_handle
from ...addon.items.music import create_music_item
from ...addon.utils import get_xml
from ...plex import plex


def process_music(url, tree=None, plex_network=None):
    if plex_network is None:
        plex_network = plex.Plex(load=True)

    server = plex_network.get_server_from_url(url)

    tree = get_xml(url, tree)
    if tree is None:
        return

    items = []
    for music in tree:

        if music.get('key') is None:
            continue

        items.append(create_music_item(server, tree, url, music))

    if items:
        content_type = items[-1][1].getProperty('content_type')
        if not content_type:
            content_type = 'artists'
        xbmcplugin.setContent(get_handle(), content_type)

        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))

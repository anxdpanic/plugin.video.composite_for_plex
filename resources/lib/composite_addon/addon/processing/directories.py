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
from ...addon.constants import CONFIG
from ...addon.items.directory import create_directory_item
from ...addon.logger import Logger
from ...plex import plex

LOG = Logger()


def process_directories(url, tree=None, plex_network=None):
    LOG.debug('Processing secondary menus')

    if plex_network is None:
        plex_network = plex.Plex(load=True)

    content_type = 'files'
    if '/collection' in url:
        content_type = 'sets'

    xbmcplugin.setContent(get_handle(), content_type)

    server = plex_network.get_server_from_url(url)

    items = []
    for directory in tree:
        items.append(create_directory_item(server, tree, url, directory))

    if items:
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))

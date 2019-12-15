# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from kodi_six import xbmcplugin  # pylint: disable=import-error

from ...addon.common import get_handle
from ...addon.items.plex_plugin import create_plex_plugin_item
from ...addon.logger import Logger
from ...addon.utils import get_master_server
from ...addon.utils import get_xml
from ...plex import plex
from . import SETTINGS

LOG = Logger()


def process_plex_plugins(url, tree=None, plex_network=None):
    """
        Main function to parse plugin XML from PMS
        Will create dir or item links depending on what the
        main tag is.
        @input: plugin page URL
        @return: nothing, creates Kodi GUI listing
    """
    if plex_network is None:
        plex_network = plex.Plex(load=True)

    xbmcplugin.setContent(get_handle(), 'addons')

    server = plex_network.get_server_from_url(url)
    tree = get_xml(url, tree)
    if tree is None:
        return

    if (tree.get('identifier') != 'com.plexapp.plugins.myplex') and ('node.plexapp.com' in url):
        LOG.debug('This is a myPlex URL, attempting to locate master server')
        server = get_master_server()

    items = []
    for plugin in tree:
        item = create_plex_plugin_item(server, tree, url, plugin)
        if item:
            items.append(item)

    if items:
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))

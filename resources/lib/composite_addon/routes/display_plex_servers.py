# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import xbmcplugin  # pylint: disable=import-error

from ..addon.common import CONFIG
from ..addon.common import MODES
from ..addon.common import SETTINGS
from ..addon.common import PrintDebug
from ..addon.common import get_handle
from ..addon.processing.music import process_music
from ..addon.processing.photos import process_photos
from ..addon.processing.plex_online import process_plex_online
from ..addon.processing.plex_plugins import process_plex_plugins
from ..addon.utils import create_gui_item
from ..plex import plex

LOG = PrintDebug(CONFIG['name'])
PLEX_NETWORK = plex.Plex(load=False)


def run(url):
    PLEX_NETWORK.load()
    content_type = url.split('/')[2]
    LOG.debug('Displaying entries for %s' % content_type)
    servers = PLEX_NETWORK.get_server_list()
    servers_list = len(servers)

    items = []
    # For each of the servers we have identified
    for media_server in servers:

        if media_server.is_secondary():
            continue

        details = {'title': media_server.get_name()}
        extra_data = {}
        url = None

        if content_type == 'video':
            extra_data['mode'] = MODES.PLEXPLUGINS
            url = '%s%s' % (media_server.get_url_location(), '/video')
            if servers_list == 1:
                process_plex_plugins(url, plex_network=PLEX_NETWORK)
                return

        elif content_type == 'online':
            extra_data['mode'] = MODES.PLEXONLINE
            url = '%s%s' % (media_server.get_url_location(), '/system/plexonline')
            if servers_list == 1:
                process_plex_online(url, plex_network=PLEX_NETWORK)
                return

        elif content_type == 'music':
            extra_data['mode'] = MODES.MUSIC
            url = '%s%s' % (media_server.get_url_location(), '/music')
            if servers_list == 1:
                process_music(url, plex_network=PLEX_NETWORK)
                return

        elif content_type == 'photo':
            extra_data['mode'] = MODES.PHOTOS
            url = '%s%s' % (media_server.get_url_location(), '/photos')
            if servers_list == 1:
                process_photos(url, plex_network=PLEX_NETWORK)
                return

        if url:
            items.append(create_gui_item(url, details, extra_data))

    if items:
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))
    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))

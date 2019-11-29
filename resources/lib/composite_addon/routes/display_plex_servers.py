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
from ..addon.processing import process_music
from ..addon.processing import process_photos
from ..addon.processing import process_plex_online
from ..addon.processing import process_plex_plugins
from ..addon.utils import add_item_to_gui
from ..plex import plex

LOG = PrintDebug(CONFIG['name'])
PLEX_NETWORK = plex.Plex(load=False)


def run(url):
    PLEX_NETWORK.load()
    ctype = url.split('/')[2]
    LOG.debug('Displaying entries for %s' % ctype)
    servers = PLEX_NETWORK.get_server_list()
    servers_list = len(servers)

    # For each of the servers we have identified
    for mediaserver in servers:

        if mediaserver.is_secondary():
            continue

        details = {'title': mediaserver.get_name()}

        extra_data = {}

        if ctype == 'video':
            extra_data['mode'] = MODES.PLEXPLUGINS
            s_url = '%s%s' % (mediaserver.get_url_location(), '/video')
            if servers_list == 1:
                process_plex_plugins(s_url, plex_network=PLEX_NETWORK)
                return

        elif ctype == 'online':
            extra_data['mode'] = MODES.PLEXONLINE
            s_url = '%s%s' % (mediaserver.get_url_location(), '/system/plexonline')
            if servers_list == 1:
                process_plex_online(s_url, plex_network=PLEX_NETWORK)
                return

        elif ctype == 'music':
            extra_data['mode'] = MODES.MUSIC
            s_url = '%s%s' % (mediaserver.get_url_location(), '/music')
            if servers_list == 1:
                process_music(s_url, plex_network=PLEX_NETWORK)
                return

        elif ctype == 'photo':
            extra_data['mode'] = MODES.PHOTOS
            s_url = '%s%s' % (mediaserver.get_url_location(), '/photos')
            if servers_list == 1:
                process_photos(s_url, plex_network=PLEX_NETWORK)
                return
        else:
            s_url = None

        add_item_to_gui(s_url, details, extra_data)

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))

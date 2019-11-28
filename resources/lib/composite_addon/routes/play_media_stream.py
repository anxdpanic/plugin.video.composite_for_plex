# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import xbmcgui  # pylint: disable=import-error
import xbmcplugin  # pylint: disable=import-error

from ..addon.common import CONFIG
from ..addon.common import PrintDebug
from ..addon.common import get_handle
from ..plex import plex

LOG = PrintDebug(CONFIG['name'])
PLEX_NETWORK = plex.Plex(load=False)


def run(url):
    PLEX_NETWORK.load()
    if url.startswith('file'):
        LOG.debug('We are playing a local file')
        # Split out the path from the URL
        playurl = url.split(':', 1)[1]
    elif url.startswith('http'):
        LOG.debug('We are playing a stream')
        if '?' in url:
            server = PLEX_NETWORK.get_server_from_url(url)
            playurl = server.get_formatted_url(url)
        else:
            playurl = ''
    else:
        playurl = url
    if CONFIG['kodi_version'] >= 18:
        item = xbmcgui.ListItem(path=playurl, offscreen=True)
    else:
        item = xbmcgui.ListItem(path=playurl)
    resolved = playurl != ''
    xbmcplugin.setResolvedUrl(get_handle(), resolved, item)

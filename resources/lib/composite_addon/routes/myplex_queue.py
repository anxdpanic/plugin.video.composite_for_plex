# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import xbmcgui  # pylint: disable=import-error

from ..addon.common import CONFIG
from ..addon.common import i18n
from ..addon.processing import plex_plugins
from ..plex import plex

PLEX_NETWORK = plex.Plex(load=False)


def run():
    PLEX_NETWORK.load()
    if not PLEX_NETWORK.is_myplex_signedin():
        xbmcgui.Dialog().notification(heading=CONFIG['name'],
                                      message=i18n('myPlex not configured'),
                                      icon=CONFIG['icon'])
    else:
        tree = PLEX_NETWORK.get_myplex_queue()
        plex_plugins('https://plex.tv/playlists/queue/all', tree, plex_network=PLEX_NETWORK)

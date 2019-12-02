# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import xbmc  # pylint: disable=import-error

from ..addon import cache_control
from ..addon.common import CONFIG
from ..addon.common import SETTINGS
from ..addon.common import decode_utf8
from ..plex import plex

PLEX_NETWORK = plex.Plex(load=False)


def run():
    PLEX_NETWORK.delete_cache()
    cache = cache_control.CacheControl(
        decode_utf8(xbmc.translatePath(CONFIG['data_path'] + 'cache/data')),
        SETTINGS.get_setting('cache')
    )
    cache.delete_cache(True)
    xbmc.executebuiltin('Container.Refresh')

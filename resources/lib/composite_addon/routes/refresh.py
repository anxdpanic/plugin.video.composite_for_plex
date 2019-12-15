# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from kodi_six import xbmc  # pylint: disable=import-error

from ..addon.data_cache import DATA_CACHE
from ..addon.settings import AddonSettings

SETTINGS = AddonSettings()


def run():
    if SETTINGS.get_setting('clear_data_cache_refresh'):
        DATA_CACHE.delete_cache(True)
    xbmc.executebuiltin('Container.Refresh')

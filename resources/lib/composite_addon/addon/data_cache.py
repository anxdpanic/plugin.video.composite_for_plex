# -*- coding: utf-8 -*-
"""

    Copyright (C) 2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import os

from kodi_six import xbmc  # pylint: disable=import-error

from . import cache_control
from .constants import CONFIG
from .settings import AddonSettings

__SETTINGS = AddonSettings(CONFIG['id'])

DATA_CACHE = cache_control.CacheControl(
    xbmc.translatePath(os.path.join(CONFIG['data_path'], 'cache', 'data')),
    __SETTINGS.get_setting('cache')
)

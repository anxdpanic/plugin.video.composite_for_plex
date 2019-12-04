# -*- coding: utf-8 -*-
"""

    Copyright (C) 2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import os

import xbmc  # pylint: disable=import-error

from . import cache_control
from .common import CONFIG
from .common import SETTINGS
from .common import decode_utf8

DATA_CACHE = cache_control.CacheControl(
    decode_utf8(xbmc.translatePath(os.path.join(CONFIG['data_path'], 'cache', 'data'))),
    SETTINGS.get_setting('cache')
)

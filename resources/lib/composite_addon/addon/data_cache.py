# -*- coding: utf-8 -*-
"""

    Copyright (C) 2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from . import cache_control
from .settings import AddonSettings

__SETTINGS = AddonSettings()

DATA_CACHE = cache_control.CacheControl('data', __SETTINGS.get_setting('data_cache'))

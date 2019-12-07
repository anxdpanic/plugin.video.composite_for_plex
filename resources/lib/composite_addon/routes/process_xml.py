# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from ..addon.processing.xml import process_xml
from ..plex import plex

PLEX_NETWORK = plex.Plex(load=False)


def run(url):
    PLEX_NETWORK.load()
    process_xml(url, plex_network=PLEX_NETWORK)

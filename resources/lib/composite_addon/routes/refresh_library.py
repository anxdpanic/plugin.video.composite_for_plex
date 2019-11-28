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
from ..addon.common import PrintDebug
from ..addon.common import get_argv
from ..addon.common import i18n
from ..plex import plex

LOG = PrintDebug(CONFIG['name'])
PLEX_NETWORK = plex.Plex(load=False)


def run():
    PLEX_NETWORK.load()

    server_uuid = get_argv()[2]
    section_id = get_argv()[3]

    server = PLEX_NETWORK.get_server_from_uuid(server_uuid)
    server.refresh_section(section_id)

    LOG.debug('Library refresh requested')
    xbmcgui.Dialog().notification(heading=CONFIG['name'],
                                  message=i18n('Library refresh started'),
                                  icon=CONFIG['icon'])

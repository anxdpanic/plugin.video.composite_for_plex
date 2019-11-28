# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import xbmc  # pylint: disable=import-error
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
    metadata_id = get_argv()[3]

    LOG.debug('Deleting media at: %s' % metadata_id)

    return_value = xbmcgui.Dialog().yesno(i18n('Confirm file delete?'),
                                          i18n('Delete this item? This action will delete media '
                                               'and associated data files.'))

    if return_value:
        LOG.debug('Deleting....')
        server = PLEX_NETWORK.get_server_from_uuid(server_uuid)
        server.delete_metadata(metadata_id)
        xbmc.executebuiltin('Container.Refresh')

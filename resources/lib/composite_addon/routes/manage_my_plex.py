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
from ..addon.common import i18n
from ..plex import plex
from ..plex import plexsignin

LOG = PrintDebug(CONFIG['name'])
PLEX_NETWORK = plex.Plex(load=False)


def run():
    has_access = True
    if not PLEX_NETWORK.is_myplex_signedin():
        ret = xbmcgui.Dialog().yesno(i18n('Manage myPlex'),
                                     i18n('You are not currently logged into myPlex. '
                                          'Continue to sign in, or cancel to return'))
        if ret:
            xbmc.executebuiltin('RunScript(' + CONFIG['id'] + ', signin)')
        else:
            has_access = False

    elif not PLEX_NETWORK.is_admin():
        has_access = False
        _ = xbmcgui.Dialog().ok(i18n('Manage myPlex'),
                                i18n('To access these screens you must be logged in as '
                                     'an admin user. Switch user and try again'))

    if has_access:
        try:
            manage_window = plexsignin.PlexManage(i18n('Manage myPlex'))
            manage_window.set_authentication_target(PLEX_NETWORK)
            manage_window.start()
            del manage_window
        except AttributeError:
            LOG.debug('Failed to load PlexManage ...')

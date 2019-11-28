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

from ..addon.common import i18n
from ..plex import plex

PLEX_NETWORK = plex.Plex(load=False)


def run():
    can_signout = True
    if not PLEX_NETWORK.is_admin():
        can_signout = False
        _ = xbmcgui.Dialog().ok(i18n('Sign Out'),
                                i18n('To sign out you must be logged in as an admin user. '
                                     'Switch user and try again'))
    if can_signout:
        result = xbmcgui.Dialog().yesno(i18n('myPlex'),
                                        i18n('You are currently signed into myPlex.'
                                             ' Are you sure you want to sign out?'))
        if result:
            PLEX_NETWORK.signout()
            xbmc.executebuiltin('Container.Refresh')

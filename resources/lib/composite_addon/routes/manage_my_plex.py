# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from kodi_six import xbmc  # pylint: disable=import-error
from kodi_six import xbmcgui  # pylint: disable=import-error

from ..addon.constants import CONFIG
from ..addon.logger import Logger
from ..addon.strings import i18n
from ..plex import plex
from ..plex import plexsignin

LOG = Logger()


def run():
    plex_network = plex.Plex(load=False)

    has_access = True
    if not plex_network.is_myplex_signedin():
        result = xbmcgui.Dialog().yesno(i18n('Manage myPlex'),
                                        i18n('You are not currently logged into myPlex. '
                                             'Continue to sign in, or cancel to return'))
        if result:
            xbmc.executebuiltin('RunScript(' + CONFIG['id'] + ', signin)')
        else:
            has_access = False

    elif not plex_network.is_admin():
        has_access = False
        _ = xbmcgui.Dialog().ok(i18n('Manage myPlex'),
                                i18n('To access these screens you must be logged in as '
                                     'an admin user. Switch user and try again'))

    if has_access:
        try:
            with plexsignin.PlexManage(i18n('Manage myPlex'),
                                       window=xbmcgui.Window(10000)) as dialog:
                dialog.set_authentication_target(plex_network)
                dialog.start()
        except plexsignin.AlreadyActiveException:
            pass
        except AttributeError:
            LOG.debug('Failed to load PlexManage ...')

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
    try:
        signin_window = plexsignin.PlexSignin(i18n('myPlex Login'))
        signin_window.set_authentication_target(PLEX_NETWORK)
        signin_window.start()
        del signin_window
    except AttributeError:
        response = PLEX_NETWORK.get_signin_pin()
        message = i18n('From your computer, go to [B]%s[/B] and'
                       ' enter the following code: [B]%s[/B]') % \
                  ('http://plex.tv/pin', ' '.join(response.get('code', [])))
        xbmcgui.Dialog().ok(i18n('myPlex Login'), message)
        xbmc.sleep(500)
        result = PLEX_NETWORK.check_signin_status(response.get('id', ''))
        if result:
            LOG.debug('Sign in successful ...')
        else:
            LOG.debug('Sign in failed ...')
        xbmc.executebuiltin('Container.Refresh')

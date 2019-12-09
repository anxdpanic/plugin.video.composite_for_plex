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
from ..addon.logger import PrintDebug
from ..addon.strings import i18n
from ..plex import plex

LOG = PrintDebug(CONFIG['name'])
PLEX_NETWORK = plex.Plex(load=False)


def run():
    user_list = PLEX_NETWORK.get_plex_home_users()
    # zero means we are not plexHome'd up
    if user_list is None or len(user_list) == 1:
        LOG.debug('No users listed or only one user, Plex Home not enabled')
        return

    LOG.debug('found %s users: %s' % (len(user_list), user_list.keys()))

    # Get rid of currently logged in user.
    user_list.pop(PLEX_NETWORK.get_myplex_user(), None)

    result = xbmcgui.Dialog().select(i18n('Switch User'), user_list.keys())
    if result == -1:
        LOG.debug('Dialog cancelled')
        return

    LOG.debug('user [%s] selected' % user_list.keys()[result])
    user = user_list[user_list.keys()[result]]

    pin = None
    if user['protected'] == '1':
        LOG.debug('Protected user [%s], requesting password' % user['title'])
        pin = xbmcgui.Dialog().input(i18n('Enter PIN'), type=xbmcgui.INPUT_NUMERIC,
                                     option=xbmcgui.ALPHANUM_HIDE_INPUT)

    success, message = PLEX_NETWORK.switch_plex_home_user(user['id'], pin)

    if not success:
        xbmcgui.Dialog().ok(i18n('Switch Failed'), message)
        LOG.debug('Switch User Failed')
    else:
        xbmc.executebuiltin('Container.Refresh')

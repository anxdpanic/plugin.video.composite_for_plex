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
from ..addon.utils import get_xml
from ..plex import plex

LOG = PrintDebug(CONFIG['name'])
PLEX_NETWORK = plex.Plex(load=False)


def run(url, setting_id):  # pylint: disable=too-many-branches
    """
        Take the setting XML and parse it to create an updated
        string with the new settings.  For the selected value, create
        a user input screen (text or list) to update the setting.
        @ input: url
        @ return: nothing
    """

    PLEX_NETWORK.load()

    LOG.debug('Setting preference for ID: %s' % setting_id)

    if not setting_id:
        LOG.debug('ID not set')
        return

    tree = get_xml(url)
    if tree is None:
        return

    set_string = None
    for plugin in tree:

        if plugin.get('id') == setting_id:
            LOG.debug('Found correct id entry for: %s' % setting_id)
            sid = setting_id

            label = plugin.get('label', i18n('Enter value'))
            option = plugin.get('option')
            value = plugin.get('value')

            if plugin.get('type') == 'text':
                LOG.debug('Setting up a text entry screen')
                keyboard = xbmc.Keyboard(value, i18n('Enter value'))
                keyboard.setHeading(label)

                if option == 'hidden':
                    keyboard.setHiddenInput(True)
                else:
                    keyboard.setHiddenInput(False)

                keyboard.doModal()
                if keyboard.isConfirmed():
                    value = keyboard.getText()
                    LOG.debug('Value input: %s ' % value)
                else:
                    LOG.debug('User cancelled dialog')
                    return

            elif plugin.get('type') == 'enum':
                LOG.debug('Setting up an enum entry screen')

                values = plugin.get('values').split('|')

                setting_screen = xbmcgui.Dialog()
                value = setting_screen.select(label, values)
                if value == -1:
                    LOG.debug('User cancelled dialog')
                    return
            else:
                LOG.debug('Unknown option type: %s' % plugin.get('id'))

        else:
            value = plugin.get('value')
            sid = plugin.get('id')

        if set_string is None:
            set_string = '%s/set?%s=%s' % (url, sid, value)
        else:
            set_string = '%s&%s=%s' % (set_string, sid, value)

    LOG.debug('Settings URL: %s' % set_string)
    PLEX_NETWORK.talk_to_server(set_string)
    xbmc.executebuiltin('Container.Refresh')

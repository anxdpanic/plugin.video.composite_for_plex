# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from six.moves.urllib_parse import unquote_plus

import xbmc  # pylint: disable=import-error
import xbmcgui  # pylint: disable=import-error

from ..addon.common import CONFIG
from ..addon.common import PrintDebug
from ..addon.common import i18n
from ..plex import plex

LOG = PrintDebug(CONFIG['name'])
PLEX_NETWORK = plex.Plex(load=False)


def run(url, name):
    PLEX_NETWORK.load()

    server = PLEX_NETWORK.get_server_from_url(url)
    tree = server.processed_xml(url)
    if tree is None:
        return

    try:
        name = unquote_plus(name)
    except:  # pylint: disable=bare-except
        pass

    operations = {}
    idx = 0
    for plugins in tree.findall('Directory'):
        operations[idx] = plugins.get('title')

        # If we find an install option, switch to a yes/no dialog box
        if operations[idx].lower() == 'install':
            LOG.debug('Not installed.  Print dialog')
            result = \
                xbmcgui.Dialog().yesno(i18n('Plex Online'), i18n('About to install') + ' ' + name)

            if result:
                LOG.debug('Installing....')
                tree = server.processed_xml(url + '/install')

                message = tree.get('message', '(' + i18n('blank') + ')')
                LOG.debug(message)
                xbmcgui.Dialog().ok(i18n('Plex Online'), message)
            return

        idx += 1

    # Else continue to a selection dialog box
    result = xbmcgui.Dialog().select(i18n('This plugin is already installed'),
                                     list(operations.values()))

    if result == -1:
        LOG.debug('No option selected, cancelling')
        return

    LOG.debug('Option %s selected.  Operation is %s' % (result, operations[result]))
    item_url = url + '/' + operations[result].lower()
    tree = server.processed_xml(item_url)

    message = tree.get('message')
    LOG.debug(message)
    xbmcgui.Dialog().ok(i18n('Plex Online'), message)
    xbmc.executebuiltin('Container.Refresh')

# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from six.moves.urllib_parse import unquote_plus

from kodi_six import xbmc  # pylint: disable=import-error
from kodi_six import xbmcgui  # pylint: disable=import-error

from ..addon.constants import CONFIG
from ..addon.logger import PrintDebug
from ..addon.strings import i18n
from ..addon.utils import get_xml
from ..plex import plex

LOG = PrintDebug(CONFIG['name'])
PLEX_NETWORK = plex.Plex(load=False)


def run(url, name):
    PLEX_NETWORK.load()

    tree = get_xml(url, plex_network=PLEX_NETWORK)
    if tree is None:
        return

    try:
        name = unquote_plus(name)
    except:  # pylint: disable=bare-except
        pass

    operations = {}
    for idx, plugins in enumerate(tree.findall('Directory')):
        operations[idx] = plugins.get('title')

        # If we find an install option, switch to a yes/no dialog box
        if operations[idx].lower() == 'install':
            LOG.debug('Not installed.  Print dialog')
            result = \
                xbmcgui.Dialog().yesno(i18n('Plex Online'), i18n('About to install') + ' ' + name)

            if result:
                LOG.debug('Installing....')
                _ = get_xml(url + '/install', plex_network=PLEX_NETWORK)

            return

    # Else continue to a selection dialog box
    result = xbmcgui.Dialog().select(i18n('This plugin is already installed'),
                                     list(operations.values()))

    if result == -1:
        LOG.debug('No option selected, cancelling')
        return

    LOG.debug('Option %s selected.  Operation is %s' % (result, operations[result]))

    item_url = url + '/' + operations[result].lower()
    _ = get_xml(item_url, plex_network=PLEX_NETWORK)

    xbmc.executebuiltin('Container.Refresh')

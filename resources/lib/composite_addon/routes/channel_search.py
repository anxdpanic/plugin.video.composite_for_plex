# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from six.moves.urllib_parse import unquote
from six.moves.urllib_parse import quote

import xbmc  # pylint: disable=import-error

from ..addon.common import CONFIG
from ..addon.common import PrintDebug
from ..addon.common import i18n
from ..addon.processing import process_plex_plugins
from ..plex import plex

LOG = PrintDebug(CONFIG['name'])
PLEX_NETWORK = plex.Plex(load=False)


def run(url, prompt):
    """
        When we encounter a search request, branch off to this function to generate the keyboard
        and accept the terms.  This URL is then fed back into the correct function for
        onward processing.
    """
    PLEX_NETWORK.load()

    if prompt:
        prompt = unquote(prompt)
    else:
        prompt = i18n('Enter search term')

    keyboard = xbmc.Keyboard('', i18n('Search...'))
    keyboard.setHeading(prompt)
    keyboard.doModal()
    if keyboard.isConfirmed():
        text = keyboard.getText()
        LOG.debug('Search term input: %s' % text)
        url = url + '&query=' + quote(text)
        process_plex_plugins(url, plex_network=PLEX_NETWORK)

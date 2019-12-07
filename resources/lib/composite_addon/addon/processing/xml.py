# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import xbmcplugin  # pylint: disable=import-error

from .episodes import process_episodes
from .movies import process_movies
from ...addon.common import MODES
from ...addon.common import SETTINGS
from ...addon.common import encode_utf8
from ...addon.common import get_handle
from ...addon.common import i18n
from ...addon.items.playlist import create_playlist_item
from ...addon.items.track import create_track_item
from ...addon.utils import create_gui_item
from ...addon.utils import get_link_url
from ...addon.utils import get_thumb_image
from ...addon.utils import get_fanart_image
from ...addon.utils import get_xml
from ...plex import plex


def process_xml(url, tree=None, plex_network=None):
    """
        Main function to parse plugin XML from PMS
        Will create dir or item links depending on what the
        main tag is.
        @input: plugin page URL
        @return: nothing, creates XBMC GUI listing
    """
    if plex_network is None:
        plex_network = plex.Plex(load=True)

    xbmcplugin.setContent(get_handle(), 'movies')

    server = plex_network.get_server_from_url(url)
    tree = get_xml(url, tree)

    if tree is None:
        return

    items = []
    for plugin in tree:

        details = {'title': encode_utf8(plugin.get('title'))}

        if not details['title']:
            details['title'] = encode_utf8(plugin.get('name', i18n('Unknown')))

        extra_data = {
            'thumb': get_thumb_image(plugin, server),
            'fanart_image': get_fanart_image(plugin, server),
            'identifier': tree.get('identifier', ''),
            'type': 'Video'
        }

        if extra_data['fanart_image'] == '':
            extra_data['fanart_image'] = get_fanart_image(tree, server)

        _url = get_link_url(url, plugin, server)

        if plugin.tag == 'Directory' or plugin.tag == 'Podcast':
            extra_data['mode'] = MODES.PROCESSXML
            items.append(create_gui_item(_url, details, extra_data))

        elif plugin.tag == 'Track':
            items.append(create_track_item(server, tree, plugin))

        elif plugin.tag == 'Playlist':
            items.append(create_playlist_item(url, server, plugin))

        elif tree.get('viewGroup') == 'movie':
            process_movies(url, tree, plex_network=plex_network)
            return

        elif tree.get('viewGroup') == 'episode':
            process_episodes(url, tree, plex_network=plex_network)
            return

    if items:
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))

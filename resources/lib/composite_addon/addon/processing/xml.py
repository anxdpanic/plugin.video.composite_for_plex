# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2020 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from kodi_six import xbmcplugin  # pylint: disable=import-error

from ..common import get_handle
from ..constants import MODES
from ..context import Item
from ..items.common import create_gui_item
from ..items.common import get_fanart_image
from ..items.common import get_link_url
from ..items.common import get_thumb_image
from ..items.playlist import create_playlist_item
from ..items.track import create_track_item
from ..strings import encode_utf8
from ..strings import i18n
from ..utils import get_xml
from .episodes import process_episodes
from .movies import process_movies


def process_xml(context, url, tree=None):
    """
        Main function to parse plugin XML from PMS
        Will create dir or item links depending on what the
        main tag is.
        @input: plugin page URL
        @return: nothing, creates Kodi GUI listing
    """

    xbmcplugin.setContent(get_handle(), 'movies')

    server = context.plex_network.get_server_from_url(url)
    tree = get_xml(context, url, tree)

    if tree is None:
        return

    items = []
    for plugin in tree:

        details = {
            'title': encode_utf8(plugin.get('title'))
        }

        if not details['title']:
            details['title'] = encode_utf8(plugin.get('name', i18n('Unknown')))

        extra_data = {
            'thumb': get_thumb_image(context, server, plugin),
            'fanart_image': get_fanart_image(context, server, plugin),
            'identifier': tree.get('identifier', ''),
            'type': 'Video'
        }

        if extra_data['fanart_image'] == '':
            extra_data['fanart_image'] = get_fanart_image(context, server, tree)

        _url = get_link_url(server, url, plugin)

        if plugin.tag == 'Directory' or plugin.tag == 'Podcast':
            extra_data['mode'] = MODES.PROCESSXML
            items.append(create_gui_item(context, _url, details, extra_data))

        elif plugin.tag == 'Track':
            item = Item(server, url, tree, plugin)
            items.append(create_track_item(context, item))

        elif plugin.tag == 'Playlist':
            item = Item(server, url, tree, plugin)
            items.append(create_playlist_item(context, item))

        elif tree.get('viewGroup') == 'movie':
            process_movies(context, url, tree)
            return

        elif tree.get('viewGroup') == 'episode':
            process_episodes(context, url, tree)
            return

    if items:
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=context.settings.get_setting('kodicache'))

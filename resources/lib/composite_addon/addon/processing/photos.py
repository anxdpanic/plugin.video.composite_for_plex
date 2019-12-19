# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from kodi_six import xbmcplugin  # pylint: disable=import-error

from ...addon.common import get_handle
from ...addon.items.directory import create_directory_item
from ...addon.items.movie import create_movie_item
from ...addon.items.photo import create_photo_item
from ...addon.items.track import create_track_item
from ...addon.utils import get_xml
from ...plex import plex


def process_photos(settings, url, tree=None, plex_network=None):
    if plex_network is None:
        plex_network = plex.Plex(load=True)

    server = plex_network.get_server_from_url(url)

    tree = get_xml(url, tree)
    if tree is None:
        return

    content_type = 'images'
    items = []
    for photo in tree:
        if photo.tag.lower() == 'photo':
            items.append(create_photo_item(server, tree, url, photo, settings))
        elif photo.tag.lower() == 'directory':
            items.append(create_directory_item(server, tree, url, photo, settings))
        elif photo.tag.lower() == 'track':  # mixed content photo playlist
            content_type = 'movies'  # use movies for mixed content playlists
            items.append(create_track_item(server, tree, photo, settings))
        elif photo.tag.lower() == 'video':  # mixed content photo playlist
            content_type = 'movies'  # use movies for mixed content playlists
            items.append(create_movie_item(server, tree, url, photo, settings))

    xbmcplugin.setContent(get_handle(), content_type)

    if items:
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=settings.get_setting('kodicache'))

# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import time

from kodi_six import xbmcplugin  # pylint: disable=import-error

from ...addon.common import get_handle
from ...addon.items.movie import create_movie_item
from ...addon.items.track import create_track_item
from ...addon.logger import Logger
from ...addon.utils import get_xml
from ...plex import plex
from . import SETTINGS

LOG = Logger()


def process_movies(url, tree=None, plex_network=None):
    if plex_network is None:
        plex_network = plex.Plex(load=True)

    xbmcplugin.setContent(get_handle(), 'movies')

    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE_IGNORE_THE)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_DATEADDED)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_DATE)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_VIDEO_RATING)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_VIDEO_YEAR)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_VIDEO_RUNTIME)
    xbmcplugin.addSortMethod(get_handle(), xbmcplugin.SORT_METHOD_MPAA_RATING)

    # get the server name from the URL, which was passed via the on screen listing..

    server = plex_network.get_server_from_url(url)

    tree = get_xml(url, tree)
    if tree is None:
        return

    # Find all the video tags, as they contain the data we need to link to a file.
    start_time = time.time()
    items = []
    for movie in tree:
        if movie.tag.lower() == 'video':
            items.append(create_movie_item(server, tree, url, movie))
        elif movie.tag.lower() == 'track':
            items.append(create_track_item(server, tree, movie))

    if items:
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))
    LOG.debug('PROCESS: It took %s seconds to process %s items' %
              (time.time() - start_time, len(items)))

    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))

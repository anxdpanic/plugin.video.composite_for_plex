# -*- coding: utf-8 -*-
"""

    Copyright (C) 2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import xbmcgui  # pylint: disable=import-error
import xbmcplugin  # pylint: disable=import-error

from ..addon.common import CONFIG
from ..addon.common import PrintDebug
from ..addon.common import get_handle
from ..addon.items.episode import create_episode_item
from ..addon.items.movie import create_movie_item
from ..addon.items.season import create_season_item
from ..addon.items.show import create_show_item

from ..plex import plex

LOG = PrintDebug(CONFIG['name'])
PLEX_NETWORK = plex.Plex(load=False)


def run(params):
    del params['command']  # remove unrelated param

    content_type = None
    if params['mode'].endswith('movies'):
        content_type = 'movie'
    elif params['mode'].endswith('tvshows'):
        content_type = 'show'

    kodi_action = params.get('kodi_action')

    PLEX_NETWORK.load()

    if kodi_action == 'check_exists' and params.get('url'):
        exists = False
        server = PLEX_NETWORK.get_server_from_url(params.get('url'))
        if server:
            tree = server.processed_xml(params.get('url'))
            exists = tree is not None and not tree.get('message') and tree.get('size', '0') != '0'
        LOG.debug('check_exists for %s -> %s' % (params.get('url'), exists))
        xbmcplugin.setResolvedUrl(get_handle(), exists, xbmcgui.ListItem())

    elif kodi_action == 'check_exists':
        LOG.debug('check_exists for %s' % content_type)
        xbmcplugin.setResolvedUrl(get_handle(), True, xbmcgui.ListItem())

    elif kodi_action == 'refresh_info' and params.get('url'):
        LOG.debug('refresh info for %s' % params.get('url'))
        server = PLEX_NETWORK.get_server_from_url(params.get('url'))
        _list_content(server, params.get('url'))
        xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=False)

    else:
        server_list = PLEX_NETWORK.get_server_list()
        LOG.debug('Using list of %s servers: %s' % (len(server_list), server_list))

        for server in server_list:
            sections = server.get_sections()
            for section in sections:
                if section.get_type() == content_type:
                    if content_type in ['movie', 'show']:
                        _list_content(server, '%s%s/all' %
                                      (server.get_url_location(), section.get_path()))

        xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=False)


def _list_content(server, url):
    tree = server.processed_xml(url)
    if tree is None:
        return

    items = []

    tags = tree.findall('Video')
    if not tags:
        tags = tree.findall('Directory')

    for content in tags:
        if content.get('type') == 'show':
            items.append(create_show_item(server, url, content, md5_hash=True))
        elif content.get('type') == 'season':
            items.append(create_season_item(server, tree, content))
        elif content.get('type') == 'episode':
            items.append(create_episode_item(server, tree, url, content))
        elif content.get('type') == 'movie':
            items.append(create_movie_item(server, tree, url, content))

    if items:
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))

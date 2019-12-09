# -*- coding: utf-8 -*-
"""

    Copyright (C) 2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from xml.etree import ElementTree

from kodi_six import xbmc  # pylint: disable=import-error
from kodi_six import xbmcgui  # pylint: disable=import-error
from kodi_six import xbmcplugin  # pylint: disable=import-error
from kodi_six import xbmcvfs  # pylint: disable=import-error

from ..addon.common import get_handle
from ..addon.constants import CONFIG
from ..addon.constants import MODES
from ..addon.logger import PrintDebug
from ..addon.items.movie import create_movie_item
from ..addon.items.show import create_show_item

from ..plex import plex

LOG = PrintDebug(CONFIG['name'])


def run(params):  # pylint: disable=too-many-branches
    del params['command']  # remove unrelated param

    content_type = None
    if params.get('path_mode'):
        if params['path_mode'].endswith('movies'):
            content_type = 'movie'
        elif params['path_mode'].endswith('tvshows'):
            content_type = 'show'

    kodi_action = params.get('kodi_action')

    if kodi_action == 'check_exists' and params.get('url'):
        exists = False
        if not _has_source(content_type):
            LOG.debug('check_exists for %s -> %s, path removed' % (params.get('url'), exists))
            xbmcplugin.setResolvedUrl(get_handle(), exists, xbmcgui.ListItem())
            return

        plex_network = plex.Plex(load=True)
        server = plex_network.get_server_from_url(params.get('url'))
        if server:
            tree = server.processed_xml(params.get('url'))
            exists = tree is not None and not tree.get('message') and tree.get('size', '0') != '0'
        LOG.debug('check_exists for %s -> %s' % (params.get('url'), exists))
        xbmcplugin.setResolvedUrl(get_handle(), exists, xbmcgui.ListItem())

    elif kodi_action == 'check_exists':
        exists = _has_source(content_type)
        LOG.debug('check_exists for %s -> %s' % (content_type, exists))
        xbmcplugin.setResolvedUrl(get_handle(), exists, xbmcgui.ListItem())

    elif kodi_action == 'refresh_info' and params.get('url'):
        LOG.debug('refresh info for %s' % params.get('url'))
        plex_network = plex.Plex(load=True)
        server = plex_network.get_server_from_url(params.get('url'))
        _list_content(server, params.get('url'))
        xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=False)

    else:
        plex_network = plex.Plex(load=True)
        server_list = plex_network.get_server_list()
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
            items.append(create_show_item(server, url, content, library=True))
        elif content.get('type') == 'movie':
            items.append(create_movie_item(server, tree, url, content, library=True))

    if items:
        xbmcplugin.addDirectoryItems(get_handle(), items, len(items))


def _has_source(content_type):
    if xbmcvfs.exists('special://userdata/sources.xml'):
        movie_path = 'plugin://%s/%s' % (CONFIG['id'], MODES.TXT_MOVIES_LIBRARY)
        show_path = 'plugin://%s/%s' % (CONFIG['id'], MODES.TXT_TVSHOWS_LIBRARY)

        sources = []
        video_tree = None

        tree = ElementTree.parse(xbmc.translatePath('special://userdata/sources.xml'))
        if tree is not None:
            root = tree.getroot()
            video_tree = root.find('video')

        if video_tree is not None:
            sources = video_tree.findall('source')

        if sources:
            for source in sources:
                path = source.find('path')
                if path is not None:
                    if content_type == 'movie' and path.text.rstrip('/') == movie_path:
                        return True
                    if content_type == 'show' and path.text.rstrip('/') == show_path:
                        return True

    return False

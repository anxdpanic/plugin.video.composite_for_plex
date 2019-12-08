# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from kodi_six import xbmcgui  # pylint: disable=import-error

from ..addon.common import get_argv
from ..addon.constants import CONFIG
from ..addon.logger import PrintDebug
from ..addon.strings import i18n
from ..plex import plex

LOG = PrintDebug(CONFIG['name'])
PLEX_NETWORK = plex.Plex(load=False)


def run():  # pylint: disable=too-many-locals
    PLEX_NETWORK.load()

    server_uuid = get_argv()[2]
    metadata_id = get_argv()[3]
    library_section_uuid = get_argv()[4]

    server = PLEX_NETWORK.get_server_from_uuid(server_uuid)
    tree = server.get_playlists()

    playlists = []
    for playlist in tree.getiterator('Playlist'):
        image = ''
        if playlist.get('composite'):
            image = server.get_formatted_url(server.get_url_location() + playlist.get('composite'))
        playlists.append({
            'title': playlist.get('title'),
            'key': playlist.get('ratingKey'),
            'image': image,
            'summary': playlist.get('summary'),
        })

    if CONFIG['kodi_version'] > 16:
        select_items = []
        for playlist in playlists:
            list_item = xbmcgui.ListItem(label=playlist.get('title'),
                                         label2=playlist.get('summary'))
            list_item.setArt({
                'icon': playlist.get('image'),
                'thumb': playlist.get('image'),
                'poster': playlist.get('image'),
            })
            select_items.append(list_item)

        return_value = xbmcgui.Dialog().select(i18n('Select playlist'), select_items,
                                               useDetails=True)
    else:
        select_items = [playlist.get('title') for playlist in playlists]
        return_value = xbmcgui.Dialog().select(i18n('Select playlist'), select_items)

    if return_value == -1:
        LOG.debug('Dialog cancelled')
        return

    selected = playlists[return_value]
    LOG.debug('choosing playlist: %s' % selected)

    item = server.get_metadata(metadata_id)[0]
    item_title = item.get('title', '')
    item_image = server.get_kodi_header_formatted_url(server.get_url_location() + item.get('thumb'))

    response = server.add_playlist_item(selected.get('key'), library_section_uuid, metadata_id)
    if response and not response.get('status'):
        leaf_added = int(response.get('leafCountAdded', 0))
        leaf_requested = int(response.get('leafCountRequested', 0))
        if leaf_added > 0 and leaf_added == leaf_requested:
            xbmcgui.Dialog().notification(CONFIG['name'], i18n('Added to the playlist') %
                                          (item_title, selected.get('title')), item_image)
            return

        xbmcgui.Dialog().notification(CONFIG['name'], i18n('is already in the playlist') %
                                      (item_title, selected.get('title')), item_image)
        return

    xbmcgui.Dialog().notification(CONFIG['name'], i18n('Failed to add to the playlist') %
                                  (item_title, selected.get('title')), item_image)

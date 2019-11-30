# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from six.moves.urllib_parse import quote

import xbmc  # pylint: disable=import-error

from ..addon.common import CONFIG
from ..addon.common import MODES
from ..addon.common import PrintDebug
from ..addon.common import i18n
from ..addon.processing import process_artists
from ..addon.processing import process_albums
from ..addon.processing import process_tracks
from ..addon.processing import process_photos
from ..addon.processing import process_directories
from ..addon.processing import process_tvepisodes
from ..addon.processing import process_movies
from ..addon.processing import process_tvshows
from ..addon.processing import process_xml
from ..plex import plex

LOG = PrintDebug(CONFIG['name'])
PLEX_NETWORK = plex.Plex(load=False)


def run(url=None, server_uuid=None, mode=None):  # pylint: disable=too-many-branches, too-many-statements
    """
        This function takes teh URL, gets the XML and determines what the content is
        This XML is then redirected to the best processing function.
        If a search term is detected, then show keyboard and run search query
        @input: URL of XML page
        @return: nothing, redirects to another function
    """
    PLEX_NETWORK.load()

    if server_uuid and mode:
        server = PLEX_NETWORK.get_server_from_uuid(server_uuid)
        sections = server.get_sections()
        for section in sections:
            if mode == section.content_type():
                path = ''
                if mode in [MODES.TXT_TVSHOWS, MODES.TXT_MOVIES]:
                    path = '/all'
                url = server.get_url_location() + section.get_path() + path
                break
    else:
        server = PLEX_NETWORK.get_server_from_url(url)

    last_bit = url.split('/')[-1]
    LOG.debug('URL suffix: %s' % last_bit)

    # Catch search requests, as we need to process input before getting results.
    if last_bit.startswith('search'):
        LOG.debug('This is a search URL.  Bringing up keyboard')
        keyboard = xbmc.Keyboard('', i18n('Search...'))
        keyboard.setHeading(i18n('Enter search term'))
        keyboard.doModal()
        if keyboard.isConfirmed():
            text = keyboard.getText()
            LOG.debug('Search term input: %s' % text)
            url += '&query=' + quote(text)
        else:
            return

    tree = server.processed_xml(url)

    if last_bit in ['folder', 'playlists']:
        process_xml(url, tree, plex_network=PLEX_NETWORK)
        return

    view_group = tree.get('viewGroup')

    if view_group == 'movie':
        LOG.debug('This is movie XML, passing to Movies')
        process_movies(url, tree, plex_network=PLEX_NETWORK)
    elif view_group == 'show':
        LOG.debug('This is tv show XML')
        process_tvshows(url, tree, plex_network=PLEX_NETWORK)
    elif view_group == 'episode':
        LOG.debug('This is TV episode XML')
        process_tvepisodes(url, tree, plex_network=PLEX_NETWORK)
    elif view_group == 'artist':
        LOG.debug('This is music XML')
        process_artists(url, tree, plex_network=PLEX_NETWORK)
    elif view_group in ['album', 'albums']:
        process_albums(url, tree, plex_network=PLEX_NETWORK)
    elif view_group == 'track':
        LOG.debug('This is track XML')
        process_tracks(url, tree, plex_network=PLEX_NETWORK)  # sorting is handled here
    elif view_group == 'photo':
        LOG.debug('This is a photo XML')
        process_photos(url, tree, plex_network=PLEX_NETWORK)
    else:
        process_directories(url, tree, plex_network=PLEX_NETWORK)

# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import json

from ...addon.constants import CONFIG
from ...addon.constants import MODES
from ...addon.logger import Logger
from ...addon.settings import AddonSettings
from ...addon.strings import encode_utf8
from ...addon.strings import i18n
from ...addon.utils import create_gui_item
from ...addon.utils import build_context_menu
from ...addon.utils import get_thumb_image
from ...addon.utils import get_fanart_image

LOG = Logger(CONFIG['name'])
SETTINGS = AddonSettings()


def create_track_item(server, tree, track, listing=True):
    part_details = ()

    for child in track:
        for babies in child:
            if babies.tag == 'Part':
                part_details = (dict(babies.items()))

    LOG.debug('Part: %s' % json.dumps(part_details, indent=4))

    details = {
        'TrackNumber': int(track.get('index', 0)),
        'discnumber': int(track.get('parentIndex', 0)),
        'title': str(track.get('index', 0)).zfill(2) + '. ' +
                 encode_utf8(track.get('title', i18n('Unknown'))),
        'rating': float(track.get('rating', 0)),
        'album': encode_utf8(track.get('parentTitle', tree.get('parentTitle', ''))),
        'artist': encode_utf8(track.get('grandparentTitle', tree.get('grandparentTitle', ''))),
        'duration': int(track.get('duration', 0)) / 1000,
        'mediatype': 'song'
    }

    section_art = get_fanart_image(tree, server)
    if track.get('thumb'):
        section_thumb = get_thumb_image(track, server)
    else:
        section_thumb = get_thumb_image(tree, server)

    extra_data = {
        'type': 'music',
        'fanart_image': section_art,
        'thumb': section_thumb,
        'key': track.get('key', ''),
        'ratingKey': str(track.get('ratingKey', 0)),
        'mode': MODES.PLAYLIBRARY
    }

    if tree.get('playlistType'):
        playlist_key = str(tree.get('ratingKey', 0))
        if track.get('playlistItemID') and playlist_key:
            extra_data.update({
                'playlist_item_id': track.get('playlistItemID'),
                'playlist_title': tree.get('title'),
                'playlist_url': '/playlists/%s/items' % playlist_key
            })

    if tree.tag == 'MediaContainer':
        extra_data.update({'library_section_uuid': tree.get('librarySectionUUID')})

    # If we are streaming, then get the virtual location
    url = '%s%s' % (server.get_url_location(), extra_data['key'])

    # Build any specific context menu entries
    context = None
    if not SETTINGS.get_setting('skipcontextmenus'):
        context = build_context_menu(url, extra_data, server)

    if listing:
        return create_gui_item(url, details, extra_data, context, folder=False)

    return url, details

# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import json

from ...addon.constants import MODES
from ...addon.logger import Logger
from ...addon.strings import encode_utf8
from ...addon.strings import i18n
from .common import create_gui_item
from .common import get_banner_image
from .common import get_fanart_image
from .common import get_media_data
from .common import get_metadata
from .common import get_thumb_image
from .context_menu import ContextMenu

LOG = Logger()


def create_episode_item(context, server, tree, url, episode, library=False):  # pylint: disable=too-many-arguments

    metadata = get_metadata(context, episode)
    LOG.debug('Media attributes are %s' % json.dumps(metadata['attributes'], indent=4))

    use_go_to = url.endswith(('onDeck', 'recentlyAdded', 'recentlyViewed', 'newest'))

    # Gather some data
    view_offset = episode.get('viewOffset', 0)
    duration = int(metadata['attributes'].get('duration', episode.get('duration', 0))) / 1000

    # Required listItem entries for Kodi
    details = {
        'plot': encode_utf8(episode.get('summary', '')),
        'title': encode_utf8(episode.get('title', i18n('Unknown'))),
        'sorttitle': encode_utf8(episode.get('titleSort',
                                             episode.get('title', i18n('Unknown')))),
        'rating': float(episode.get('rating', 0)),
        'studio': encode_utf8(episode.get('studio', tree.get('studio', ''))),
        'mpaa': episode.get('contentRating', tree.get('grandparentContentRating', '')),
        'year': int(episode.get('year', 0)),
        'tagline': encode_utf8(episode.get('tagline', '')),
        'episode': int(episode.get('index', 0)),
        'aired': episode.get('originallyAvailableAt', ''),
        'tvshowtitle': encode_utf8(episode.get('grandparentTitle',
                                               tree.get('grandparentTitle', ''))),
        'season': int(episode.get('parentIndex', tree.get('parentIndex', 0))),
        'mediatype': 'episode',
        'playcount': int(int(episode.get('viewCount', 0)) > 0),
        'cast': metadata['cast'],
        'director': ' / '.join(metadata['director']),
        'genre': ' / '.join(metadata['genre']),
        'writer': ' / '.join(metadata['writer']),
    }

    if episode.get('sorttitle'):
        details['sorttitle'] = encode_utf8(episode.get('sorttitle'))

    if tree.get('mixedParents') == '1':
        if tree.get('parentIndex') == '1':
            details['title'] = '%sx%s %s' % (details['season'],
                                             str(details['episode']).zfill(2),
                                             details['title'])
        else:
            details['title'] = '%s - %sx%s %s' % (details['tvshowtitle'],
                                                  details['season'],
                                                  str(details['episode']).zfill(2),
                                                  details['title'])

    art = _get_art(context, server, tree, episode)

    # Extra data required to manage other properties
    extra_data = {
        'type': 'Video',
        'source': 'tvepisodes',
        'thumb': art.get('thumb', ''),
        'fanart_image': art.get('fanart', ''),
        'banner': art.get('banner', ''),
        'season_thumb': art.get('season_thumb', ''),
        'key': episode.get('key', ''),
        'ratingKey': str(episode.get('ratingKey', 0)),
        'parentRatingKey': str(episode.get('parentRatingKey', 0)),
        'grandparentRatingKey': str(episode.get('grandparentRatingKey', 0)),
        'duration': duration,
        'resume': int(int(view_offset) / 1000),
        'season': details.get('season'),
        'tvshowtitle': details.get('tvshowtitle'),
        'additional_context_menus': {
            'go_to': use_go_to
        },
    }

    if tree.tag == 'MediaContainer':
        extra_data.update({
            'library_section_uuid': tree.get('librarySectionUUID')
        })

    # Add extra media flag data
    if not context.settings.get_setting('skipflags'):
        extra_data.update(get_media_data(metadata['attributes']))

    # Build any specific context menu entries
    context_menu = None
    if not context.settings.get_setting('skipcontextmenus'):
        context_menu = ContextMenu(context, server, url, extra_data).menu

    extra_data['mode'] = MODES.PLAYLIBRARY
    if library:
        extra_data['path_mode'] = MODES.TXT_TVSHOWS_LIBRARY

    item_url = '%s%s' % (server.get_url_location(), extra_data['key'])

    return create_gui_item(context, item_url, details, extra_data, context_menu, folder=False)


def _get_art(context, server, tree, episode):
    art = {
        'banner': '',
        'fanart': '',
        'season_thumb': '',
        'section_art': '',
        'thumb': '',
    }

    if not context.settings.get_setting('skipimages'):
        art.update({
            'banner': get_banner_image(context, server, tree),
            'fanart': get_fanart_image(context, server, episode),
            'season_thumb': '',
            'section_art': get_fanart_image(context, server, tree),
            'thumb': get_thumb_image(context, server, episode),
        })

        if '/:/resources/show-fanart.jpg' in art['section_art']:
            art['section_art'] = art.get('fanart', '')

        if art['fanart'] == '' or '-1' in art['fanart']:
            art['fanart'] = art.get('section_art', '')

        if (art.get('season_thumb', '') and
                '/:/resources/show.png' not in art.get('season_thumb', '')):
            art['season_thumb'] = get_thumb_image(context, server, {
                'thumb': art.get('season_thumb')
            })

        # get ALL SEASONS or TVSHOW thumb
        if (not art.get('season_thumb', '') and episode.get('parentThumb', '') and
                '/:/resources/show.png' not in episode.get('parentThumb', '')):
            art['season_thumb'] = \
                get_thumb_image(context, server, {
                    'thumb': episode.get('parentThumb', '')
                })

        elif (not art.get('season_thumb', '') and episode.get('grandparentThumb', '') and
              '/:/resources/show.png' not in episode.get('grandparentThumb', '')):
            art['season_thumb'] = \
                get_thumb_image(context, server, {
                    'thumb': episode.get('grandparentThumb', '')
                })

    return art

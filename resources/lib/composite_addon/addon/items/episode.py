# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from ...addon.constants import CONFIG
from ...addon.constants import MODES
from ...addon.logger import PrintDebug
from ...addon.settings import AddonSettings
from ...addon.strings import encode_utf8
from ...addon.strings import i18n
from ...addon.utils import create_gui_item
from ...addon.utils import build_context_menu
from ...addon.utils import get_banner_image
from ...addon.utils import get_thumb_image
from ...addon.utils import get_fanart_image
from ...addon.utils import get_media_data

LOG = PrintDebug(CONFIG['name'])
SETTINGS = AddonSettings(CONFIG['id'])


def create_episode_item(server, tree, url, episode):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
    temp_genre = []
    temp_cast = []
    temp_director = []
    temp_writer = []
    media_arguments = {}

    use_go_to = url.endswith(('onDeck', 'recentlyAdded', 'recentlyViewed', 'newest'))

    for child in episode:
        if child.tag == 'Media':
            media_arguments = dict(child.items())
        elif child.tag == 'Genre' and not SETTINGS.get_setting('skipmetadata'):
            temp_genre.append(child.get('tag'))
        elif child.tag == 'Writer' and not SETTINGS.get_setting('skipmetadata'):
            temp_writer.append(child.get('tag'))
        elif child.tag == 'Director' and not SETTINGS.get_setting('skipmetadata'):
            temp_director.append(child.get('tag'))
        elif child.tag == 'Role' and not SETTINGS.get_setting('skipmetadata'):
            temp_cast.append(child.get('tag'))

    LOG.debug('Media attributes are %s' % media_arguments)

    # Gather some data
    view_offset = episode.get('viewOffset', 0)
    duration = int(media_arguments.get('duration', episode.get('duration', 0))) / 1000

    # Required listItem entries for XBMC
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
        'mediatype': 'episode'
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

    art = {
        'banner': '',
        'fanart': '',
        'season_thumb': '',
        'section_art': '',
        'thumb': '',
    }
    if not SETTINGS.get_setting('skipimages'):
        art.update({
            'banner': get_banner_image(tree, server),
            'fanart': get_fanart_image(episode, server),
            'season_thumb': '',
            'section_art': get_fanart_image(tree, server),
            'thumb': get_thumb_image(episode, server),
        })

        if '/:/resources/show-fanart.jpg' in art['section_art']:
            art['section_art'] = art.get('fanart', '')

    # Extra data required to manage other properties
    extra_data = {
        'type': 'Video',
        'source': 'tvepisodes',
        'thumb': art.get('thumb', ''),
        'fanart_image': art.get('fanart', ''),
        'banner': art.get('banner', ''),
        'key': episode.get('key', ''),
        'ratingKey': str(episode.get('ratingKey', 0)),
        'parentRatingKey': str(episode.get('parentRatingKey', 0)),
        'grandparentRatingKey': str(episode.get('grandparentRatingKey', 0)),
        'duration': duration,
        'resume': int(int(view_offset) / 1000),
        'season': details.get('season'),
        'tvshowtitle': details.get('tvshowtitle'),
        'additional_context_menus': {'go_to': use_go_to},
    }

    if not SETTINGS.get_setting('skipimages'):
        if extra_data['fanart_image'] == '':
            extra_data['fanart_image'] = art.get('section_art', '')

        if '-1' in extra_data['fanart_image']:
            extra_data['fanart_image'] = art.get('section_art', '')

        if (art.get('season_thumb', '') and
                '/:/resources/show.png' not in art.get('season_thumb', '')):
            extra_data['season_thumb'] = get_thumb_image({'thumb': art.get('season_thumb')}, server)

        # get ALL SEASONS or TVSHOW thumb
        if (not art.get('season_thumb', '') and episode.get('parentThumb', '') and
                '/:/resources/show.png' not in episode.get('parentThumb', '')):
            extra_data['season_thumb'] = \
                get_thumb_image({'thumb': episode.get('parentThumb', '')}, server)

        elif (not art.get('season_thumb', '') and episode.get('grandparentThumb', '') and
              '/:/resources/show.png' not in episode.get('grandparentThumb', '')):
            extra_data['season_thumb'] = \
                get_thumb_image({'thumb': episode.get('grandparentThumb', '')}, server)

    # Determine what type of watched flag [overlay] to use
    if int(episode.get('viewCount', 0)) > 0:
        details['playcount'] = 1
    else:
        details['playcount'] = 0

    # Extended Metadata
    if not SETTINGS.get_setting('skipmetadata'):
        details['cast'] = temp_cast
        details['director'] = ' / '.join(temp_director)
        details['writer'] = ' / '.join(temp_writer)
        details['genre'] = ' / '.join(temp_genre)

    # Add extra media flag data
    if not SETTINGS.get_setting('skipflags'):
        extra_data.update(get_media_data(media_arguments))

    # Build any specific context menu entries
    if not SETTINGS.get_setting('skipcontextmenus'):
        context = build_context_menu(url, extra_data, server)
    else:
        context = None

    extra_data['mode'] = MODES.PLAYLIBRARY
    item_url = '%s%s' % (server.get_url_location(), extra_data['key'])

    return create_gui_item(item_url, details, extra_data, context, folder=False)

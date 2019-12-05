# -*- coding: utf-8 -*-
"""

    Copyright (C) 2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import xml.etree.ElementTree as ETree

from six.moves.urllib_parse import unquote

import xbmc  # pylint: disable=import-error
import xbmcplugin  # pylint: disable=import-error

from ..addon.common import CONFIG
from ..addon.common import PrintDebug
from ..addon.common import decode_utf8
from ..addon.common import get_handle
from ..addon.common import wait_for_busy_dialog
from ..addon.playback import play_media_id_from_uuid
from ..addon.processing import process_tvepisodes
from ..addon.processing import process_tvseasons
from ..plex import plex

LOG = PrintDebug(CONFIG['name'])
PLEX_NETWORK = plex.Plex(load=True)


def run(params):
    for param in ['video_type', 'title', 'year']:  # check for expected common parameters
        if param not in params:
            return

    # possible params ['video_type', 'title', 'year', 'trakt_id', 'episode_id', 'season_id',
    # 'season', 'episode', 'ep_title', 'imdb_id', 'tmdb_id', 'tvdb_id']

    del params['mode']  # remove unrelated param
    del params['url']  # remove unrelated param
    del params['command']  # remove unrelated param

    LOG.debug('Running with params: %s' % params)

    search_results = search(params)
    log_results = [decode_utf8(ETree.tostring(search_result[1]))
                   for search_result in search_results]
    LOG.debug('Found search results: %s' % '\n\n'.join(log_results))

    server_uuid, media_id = get_server_uuid_and_media_id(params, search_results)
    if server_uuid and media_id:
        LOG.debug('Found a server with the requested content @ server_uuid=%s w/ media_id=%s' %
                  (server_uuid, media_id))

        if params.get('video_type') in ['show', 'season']:
            if params.get('video_type') == 'show':
                process_tvseasons(server_uuid, rating_key=media_id,
                                  plex_network=PLEX_NETWORK)
                return

            if params.get('video_type') == 'season':
                process_tvepisodes(server_uuid, rating_key=media_id,
                                   plex_network=PLEX_NETWORK)
                return

        if params.get('video_type') in ['movie', 'episode']:
            xbmcplugin.endOfDirectory(get_handle(), False, cacheToDisc=False)
            if xbmc.Player().isPlaying():
                xbmc.Player().stop()

            play = wait_for_busy_dialog()
            if play:
                play_media_id_from_uuid(server_uuid, media_id, player=True)
                return

        LOG.debug('Failed to execute TraktToKodi action')
    else:
        LOG.debug('Content not found on any server')


def _is_not_none(item):
    if item is not None and item.get('size', '0') == '0':
        item = None
    return item is not None


def _get_show(params, response):
    for show in response:
        title = show.get('title') == unquote(params.get('title'))
        year = show.get('year') == params.get('year')
        if title and year:
            return show
    return None


def _get_season(params, server, show_id):
    seasons = server.get_children(show_id)
    if _is_not_none(seasons):
        for season in seasons:
            if season.get('index') == params.get('season'):
                return season
    return None


def _get_episode(params, server, season_id=None, processed=None):
    if not season_id and not processed:
        return None

    episodes = processed
    if season_id and not episodes:
        episodes = server.get_children(season_id)

    if _is_not_none(episodes):
        for episode in episodes:
            if (episode.get('parentIndex') == params.get('season') and
                    episode.get('index') == params.get('episode')):
                return episode
    return None


def search(params):  # pylint: disable=too-many-branches, too-many-nested-blocks
    results = []

    if params.get('video_type') == 'movie':
        content_type = 'movie'
        search_type = '1'
    elif params.get('video_type') == 'show':
        content_type = 'show'
        search_type = '2'
    elif params.get('video_type') == 'season':
        content_type = 'show'
        search_type = '2'
    elif params.get('video_type') == 'episode':
        content_type = 'show'
        search_type = '4'
    else:
        return results

    server_list = PLEX_NETWORK.get_server_list()

    for server in server_list:  # pylint: disable=too-many-nested-blocks

        sections = server.get_sections()
        for section in sections:

            if section.get_type() == content_type:
                title = params.get('ep_title') if search_type == '4' else params.get('title')
                url = '%s/search?type=%s&query=%s' % (section.get_path(), search_type, title)
                processed = server.processed_xml(url)

                if not _is_not_none(processed) and params.get('video_type') == 'episode':
                    url = '%s/search?type=%s&query=%s' % \
                          (section.get_path(), '2', params.get('title'))
                    processed = server.processed_xml(url)

                if _is_not_none(processed):
                    if params.get('video_type') == 'episode':
                        episode = _get_episode(params, server, processed=processed)

                        if episode is not None:
                            results.append((server.get_uuid(), episode))
                            continue

                    if params.get('video_type') in ['episode', 'season']:
                        show = _get_show(params, processed)
                        if show is not None:

                            season = _get_season(params, server, show.get('ratingKey'))
                            if season is not None:
                                if params.get('video_type') == 'season':
                                    results.append((server.get_uuid(), season))
                                    continue

                                if params.get('video_type') == 'episode':
                                    episode = _get_episode(params, server, season.get('ratingKey'))
                                    if episode is not None:
                                        results.append((server.get_uuid(), episode))
                                        continue
                    else:
                        for result in processed:
                            results.append((server.get_uuid(), result))

    return results


def _compare_titles(plex_title, trakt_title):
    def get_lower_stripped(string):
        string = string.lower()
        string = string.replace('  ', ' ')
        string = string.strip()
        return string

    plex_title = get_lower_stripped(plex_title)
    trakt_title = get_lower_stripped(unquote(trakt_title))

    return plex_title == trakt_title


def get_server_uuid_and_media_id(params, search_results):
    for result in search_results:
        if params.get('video_type') == 'movie':
            title = _compare_titles(result[1].get('title'), params.get('title'))
            year = result[1].get('year') == params.get('year')
            if title and year:
                return result[0], result[1].get('ratingKey')

        elif params.get('video_type') == 'show':
            title = _compare_titles(result[1].get('title'), params.get('title'))
            year = result[1].get('year') == params.get('year')
            if title and year:
                return result[0], result[1].get('ratingKey')

        elif params.get('video_type') == 'season':
            title = _compare_titles(result[1].get('parentTitle'), params.get('title'))
            season = result[1].get('index') == params.get('season')
            if title and season:
                return result[0], result[1].get('ratingKey')

        elif params.get('video_type') == 'episode':
            title = _compare_titles(result[1].get('grandparentTitle'), params.get('title'))
            season = result[1].get('parentIndex') == params.get('season')
            episode = result[1].get('index') == params.get('episode')
            if title and season and episode:
                return result[0], result[1].get('ratingKey')

    return None, None

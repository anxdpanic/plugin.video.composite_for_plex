# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import copy

from six.moves import range
from six.moves.urllib_parse import quote
from six.moves.urllib_parse import quote_plus
from six.moves.urllib_parse import urlparse

import xbmcgui  # pylint: disable=import-error

from ..addon.common import CONFIG
from ..addon.common import SETTINGS
from ..addon.common import PrintDebug
from ..addon.common import encode_utf8
from ..addon.common import get_argv
from ..addon.common import i18n
from ..plex import plex

LOG = PrintDebug(CONFIG['name'])


def get_master_server(all_servers=False, plex_network=None):
    if plex_network is None:
        plex_network = plex.Plex(load=True)

    possible_servers = []
    current_master = SETTINGS.get_setting('masterServer')
    for server_data in plex_network.get_server_list():
        LOG.debug(str(server_data))
        if server_data.get_master() == 1:
            possible_servers.append(server_data)
    LOG.debug('Possible master servers are: %s' % possible_servers)

    if all_servers:
        return possible_servers

    if len(possible_servers) > 1:
        preferred = 'local'
        for server_data in possible_servers:
            if server_data.get_name == current_master:
                LOG.debug('Returning current master')
                return server_data
            if preferred == 'any':
                LOG.debug('Returning \'any\'')
                return server_data
            if server_data.get_discovery() == preferred:
                LOG.debug('Returning local')
                return server_data

    if len(possible_servers) == 0:
        return None

    return possible_servers[0]


def create_gui_item(url, details, extra_data, context=None, folder=True):  # pylint: disable=too-many-locals, too-many-statements, too-many-branches
    LOG.debug('Adding [%s]\n'
              'Passed details: %s\n'
              'Passed extra_data: %s' %
              (details.get('title', i18n('Unknown')), details, extra_data))

    is_file = url.startswith('cmd:')

    # Create the URL to pass to the item
    if not folder and extra_data['type'] == 'image':
        link_url = url
    elif url.startswith('http') or url.startswith('file'):
        link_url = '%s?url=%s&mode=%s' % (get_argv()[0], quote(url), extra_data.get('mode', 0))
    else:
        link_url = '%s?url=%s&mode=%s' % (get_argv()[0], url, extra_data.get('mode', 0))

    if extra_data.get('parameters'):
        for argument, value in extra_data.get('parameters').items():
            link_url = '%s&%s=%s' % (link_url, argument, quote(value))

    title = item_translate(details.get('title', i18n('Unknown')), extra_data.get('source'), folder)

    LOG.debug('URL to use for listing: %s' % link_url)
    if CONFIG['kodi_version'] >= 18:
        list_item = xbmcgui.ListItem(title, offscreen=True)
    else:
        list_item = xbmcgui.ListItem(title)

    set_info_type = extra_data.get('type', 'Video')
    info_labels = copy.deepcopy(details)
    if set_info_type.lower() == 'folder' or set_info_type.lower() == 'file':
        set_info_type = 'Video'

    if not info_labels.get('plot'):
        info_labels['plot'] = u'\u2008'
    if not info_labels.get('plotoutline'):
        info_labels['plotoutline'] = u'\u2008'

    # Set the properties of the item, such as summary, name, season, etc
    list_item.setInfo(type=set_info_type, infoLabels=info_labels)

    # Music related tags
    if extra_data.get('type', '').lower() == 'music':
        list_item.setProperty('Artist_Genre', details.get('genre', ''))
        list_item.setProperty('Artist_Description', extra_data.get('plot', ''))
        list_item.setProperty('Album_Description', extra_data.get('plot', ''))

    # For all end items
    if not folder:
        list_item.setProperty('IsPlayable', 'true')

        if extra_data.get('type', 'video').lower() == 'video':
            list_item.setProperty('TotalTime', str(extra_data.get('duration')))
            list_item.setProperty('ResumeTime', str(extra_data.get('resume')))

            if not SETTINGS.get_setting('skipflags'):
                LOG.debug('Setting VrR as : %s' % extra_data.get('VideoResolution', ''))
                list_item.setProperty('VideoResolution', extra_data.get('VideoResolution', ''))
                list_item.setProperty('VideoCodec', extra_data.get('VideoCodec', ''))
                list_item.setProperty('AudioCodec', extra_data.get('AudioCodec', ''))
                list_item.setProperty('AudioChannels', extra_data.get('AudioChannels', ''))
                list_item.setProperty('VideoAspect', extra_data.get('VideoAspect', ''))

                video_codec = {}
                if extra_data.get('xbmc_VideoCodec'):
                    video_codec['codec'] = extra_data.get('xbmc_VideoCodec')
                if extra_data.get('xbmc_VideoAspect'):
                    video_codec['aspect'] = float(extra_data.get('xbmc_VideoAspect'))
                if extra_data.get('xbmc_height'):
                    video_codec['height'] = int(extra_data.get('xbmc_height'))
                if extra_data.get('xbmc_width'):
                    video_codec['width'] = int(extra_data.get('xbmc_width'))
                if extra_data.get('duration'):
                    video_codec['duration'] = int(extra_data.get('duration'))

                audio_codec = {}
                if extra_data.get('xbmc_AudioCodec'):
                    audio_codec['codec'] = extra_data.get('xbmc_AudioCodec')
                if extra_data.get('xbmc_AudioChannels'):
                    audio_codec['channels'] = int(extra_data.get('xbmc_AudioChannels'))

                list_item.addStreamInfo('video', video_codec)
                list_item.addStreamInfo('audio', audio_codec)

    if extra_data.get('source') == 'tvshows' or extra_data.get('source') == 'tvseasons':
        # Then set the number of watched and unwatched, which will be displayed per season
        list_item.setProperty('TotalEpisodes', str(extra_data['TotalEpisodes']))
        list_item.setProperty('WatchedEpisodes', str(extra_data['WatchedEpisodes']))
        list_item.setProperty('UnWatchedEpisodes', str(extra_data['UnWatchedEpisodes']))

        # Hack to show partial flag for TV shows and seasons
        if extra_data.get('partialTV') == 1:
            list_item.setProperty('TotalTime', '100')
            list_item.setProperty('ResumeTime', '50')

    # assign artwork
    fanart = extra_data.get('fanart_image', '')
    thumb = extra_data.get('thumb', CONFIG['icon'])
    banner = extra_data.get('banner', '')

    # tvshow poster
    season_thumb = extra_data.get('season_thumb', '')

    if season_thumb:
        poster = season_thumb
    else:
        if not folder:
            poster = extra_data.get('thumb', 'DefaultPoster.png')
        else:
            poster = thumb

    if season_thumb:
        LOG.debug('Setting season Thumb as %s' % season_thumb)
        list_item.setProperty('seasonThumb', '%s' % season_thumb)

    list_item.setArt({
        'fanart': fanart,
        'poster': poster,
        'banner': banner,
        'thumb': thumb,
        'icon': thumb
    })

    if context is not None:
        if not folder and extra_data.get('type', 'video').lower() == 'video':
            # Play Transcoded
            context.insert(0, (i18n('Play Transcoded'), 'PlayMedia(%s&transcode=1)' % link_url,))
            LOG.debug('Setting transcode options to [%s&transcode=1]' % link_url)
        LOG.debug('Building Context Menus')
        list_item.addContextMenuItems(context, SETTINGS.get_setting('contextreplace'))

    if is_file:
        folder = False
        list_item.setProperty('IsPlayable', 'false')

    mediatype = details.get('mediatype')
    if mediatype:
        list_item.setProperty('content_type', mediatype + 's')

    if extra_data.get('hash'):
        list_item.setProperty('hash', extra_data['hash'])

    return link_url, list_item, folder


def directory_item_translate(title, thumb):  # pylint: disable=too-many-statements, too-many-branches
    translated_title = title

    if thumb.endswith('show.png'):
        if title == 'All Shows':
            translated_title = i18n('All')
        elif title == 'Unwatched':
            translated_title = i18n('Unwatched')
        elif title == 'Recently Aired':
            translated_title = i18n('Recently Aired')
        elif title == 'Recently Added':
            translated_title = i18n('Recently Added')
        elif title == 'Recently Viewed Episodes':
            translated_title = i18n('Recently Viewed Episodes')
        elif title == 'Recently Viewed Shows':
            translated_title = i18n('Recently Viewed Shows')
        elif title == 'On Deck':
            translated_title = i18n('On Deck')
        elif title == 'By Collection':
            translated_title = i18n('By Collection')
        elif title == 'By First Letter':
            translated_title = i18n('By First Letter')
        elif title == 'By Genre':
            translated_title = i18n('By Genre')
        elif title == 'By Year':
            translated_title = i18n('By Year')
        elif title == 'By Content Rating':
            translated_title = i18n('By Content Rating')
        elif title == 'By Folder':
            translated_title = i18n('By Folder')
        elif title == 'Search Shows...':
            translated_title = i18n('Search Shows...')
        elif title == 'Search Episodes...':
            translated_title = i18n('Search Episodes...')

    if thumb.endswith('artist.png'):
        if title == 'All Artists':
            translated_title = i18n('All')
        elif title == 'By Album':
            translated_title = i18n('By Album')
        elif title == 'By Genre':
            translated_title = i18n('By Genre')
        elif title == 'By Year':
            translated_title = i18n('By Year')
        elif title == 'By Collection':
            translated_title = i18n('By Collection')
        elif title == 'Recently Added':
            translated_title = i18n('Recently Added')
        elif title == 'By Folder':
            translated_title = i18n('By Folder')
        elif title == 'Search Artists...':
            translated_title = i18n('Search Artists...')
        elif title == 'Search Albums...':
            translated_title = i18n('Search Albums...')
        elif title == 'Search Tracks...':
            translated_title = i18n('Search Tracks...')

    if thumb.endswith('movie.png') or thumb.endswith('video.png'):
        if title.startswith('All '):
            translated_title = i18n('All')
        elif title == 'Unwatched':
            translated_title = i18n('Unwatched')
        elif title == 'Recently Released':
            translated_title = i18n('Recently Released')
        elif title == 'Recently Added':
            translated_title = i18n('Recently Added')
        elif title == 'Recently Viewed':
            translated_title = i18n('Recently Viewed')
        elif title == 'On Deck':
            translated_title = i18n('On Deck')
        elif title == 'By Collection':
            translated_title = i18n('By Collection')
        elif title == 'By Genre':
            translated_title = i18n('By Genre')
        elif title == 'By Year':
            translated_title = i18n('By Year')
        elif title == 'By Decade':
            translated_title = i18n('By Decade')
        elif title == 'By Director':
            translated_title = i18n('By Director')
        elif title == 'By Starring Actor':
            translated_title = i18n('By Starring Actor')
        elif title == 'By Country':
            translated_title = i18n('By Country')
        elif title == 'By Content Rating':
            translated_title = i18n('By Content Rating')
        elif title == 'By Rating':
            translated_title = i18n('By Rating')
        elif title == 'By Resolution':
            translated_title = i18n('By Resolution')
        elif title == 'By First Letter':
            translated_title = i18n('By First Letter')
        elif title == 'By Folder':
            translated_title = i18n('By Folder')
        elif title == 'Search...':
            translated_title = i18n('Search...')

    if thumb.endswith('photo.png'):
        if title == 'All Photos':
            translated_title = i18n('All')
        elif title == 'By Year':
            translated_title = i18n('By Year')
        elif title == 'Recently Added':
            translated_title = i18n('Recently Added')
        elif title == 'Camera Make':
            translated_title = i18n('Camera Make')
        elif title == 'Camera Model':
            translated_title = i18n('Camera Model')
        elif title == 'Aperture':
            translated_title = i18n('Aperture')
        elif title == 'Shutter Speed':
            translated_title = i18n('Shutter Speed')
        elif title == 'ISO':
            translated_title = i18n('ISO')
        elif title == 'Lens':
            translated_title = i18n('Lens')

    return translated_title


def item_translate(title, source, folder):
    translated_title = title

    if folder and source in ['tvshows', 'tvseasons']:
        if title == 'All episodes':
            translated_title = i18n('All episodes')
        elif title.startswith('Season '):
            translated_title = i18n('Season') + title[6:]

    return translated_title


def get_link_url(url, path_data, server):
    path = path_data.get('key', '')

    LOG.debug('Path is %s' % path)

    if path == '':
        LOG.debug('Empty Path')
        return ''

    # If key starts with http, then return it
    if path.startswith('http'):
        LOG.debug('Detected http(s) link')
        return path

    # If key starts with a / then prefix with server address
    if path.startswith('/'):
        LOG.debug('Detected base path link')
        return '%s%s' % (server.get_url_location(), path)

    # If key starts with plex:// then it requires transcoding
    if path.startswith('plex:'):
        LOG.debug('Detected plex link')
        components = path.split('&')
        for idx in components:
            if 'prefix=' in idx:
                del components[components.index(idx)]
                break
        if path_data.get('identifier') is not None:
            components.append('identifier=' + path_data['identifier'])

        path = '&'.join(components)
        return 'plex://' + server.get_location() + '/' + '/'.join(path.split('/')[3:])

    if path.startswith('rtmp'):
        LOG.debug('Detected RTMP link')
        return path

    # Any thing else is assumed to be a relative path and is built on existing url
    LOG.debug('Detected relative link')
    return '%s/%s' % (url, path)


def get_thumb_image(data, server, width=720, height=720):
    """
        Simply take a URL or path and determine how to format for images
        @ input: elementTree element, server name
        @ return formatted URL
    """

    if SETTINGS.get_setting('skipimages'):
        return ''

    thumbnail = encode_utf8(data.get('thumb', '').split('?t')[0])

    if thumbnail.startswith('http'):
        return thumbnail

    if thumbnail.startswith('/'):
        if SETTINGS.get_setting('fullres_thumbs'):
            return server.get_kodi_header_formatted_url(thumbnail)

        thumbnail = quote_plus('http://localhost:32400' + thumbnail)
        return server.get_kodi_header_formatted_url('/photo/:/transcode?url=%s&width=%s&height=%s' %
                                                    (thumbnail, width, height))

    return CONFIG['icon']


def get_banner_image(data, server, width=720, height=720):
    """
        Simply take a URL or path and determine how to format for images
        @ input: elementTree element, server name
        @ return formatted URL
    """

    if SETTINGS.get_setting('skipimages'):
        return ''

    thumbnail = encode_utf8(data.get('banner', '').split('?t')[0])

    if thumbnail.startswith('http'):
        return thumbnail

    if thumbnail.startswith('/'):
        if SETTINGS.get_setting('fullres_thumbs'):
            return server.get_kodi_header_formatted_url(thumbnail)

        thumbnail = quote_plus('http://localhost:32400' + thumbnail)
        return server.get_kodi_header_formatted_url('/photo/:/transcode?url=%s&width=%s&height=%s' %
                                                    (thumbnail, width, height))

    return CONFIG['icon']


def get_fanart_image(data, server, width=1280, height=720):
    """
        Simply take a URL or path and determine how to format for fanart
        @ input: elementTree element, server name
        @ return formatted URL for photo resizing
    """
    if SETTINGS.get_setting('skipimages'):
        return ''

    fanart = encode_utf8(data.get('art', ''))

    if fanart.startswith('http'):
        return fanart

    if fanart.startswith('/'):
        if SETTINGS.get_setting('fullres_fanart'):
            return server.get_kodi_header_formatted_url(fanart)

        return server.get_kodi_header_formatted_url('/photo/:/transcode?url=%s&width=%s&height=%s' %
                                                    (quote_plus('http://localhost:32400' + fanart),
                                                     width, height))

    return ''


def get_xml(url, tree=None, plex_network=None):
    if plex_network is None:
        plex_network = plex.Plex(load=True)

    if tree is None:
        tree = plex_network.get_processed_xml(url)

    if tree.get('message'):
        xbmcgui.Dialog().ok(tree.get('header', i18n('Message')), tree.get('message', ''))
        return None

    return tree


def build_context_menu(url, item_data, server):
    context = []
    url_parts = urlparse(url)
    section = url_parts.path.split('/')[3]

    additional_context_menus = item_data.get('additional_context_menus', {})
    item_id = item_data.get('ratingKey', '0')
    item_type = item_data.get('type', '').lower()
    item_source = item_data.get('source', '').lower()

    if additional_context_menus.get('go_to'):
        parent_id = item_data.get('parentRatingKey')
        grandparent_id = item_data.get('grandparentRatingKey')
        if parent_id and item_data.get('season') is not None:
            context.append((i18n('Go to') %
                            (i18n('Season') + ' ' + str(item_data.get('season', 0))),
                            'Container.Update(plugin://%s/?mode=6&url=%s&rating_key=%s)' %
                            (CONFIG['id'], server.get_uuid(), parent_id)))
        if grandparent_id and item_data.get('tvshowtitle'):
            context.append((i18n('Go to') % item_data.get('tvshowtitle'),
                            'Container.Update(plugin://%s/?mode=4&url=%s&rating_key=%s)' %
                            (CONFIG['id'], server.get_uuid(), grandparent_id)))

    if item_type in ['video', 'season']:
        context.append((i18n('Mark as unwatched'),
                        'RunScript(' + CONFIG['id'] + ', watch, %s, %s, %s)' %
                        (server.get_uuid(), item_id, 'unwatch')))
        context.append((i18n('Mark as watched'),
                        'RunScript(' + CONFIG['id'] + ', watch, %s, %s, %s)' %
                        (server.get_uuid(), item_id, 'watch')))

    if item_data.get('playlist_item_id'):
        playlist_title = item_data.get('playlist_title')
        playlist_url = item_data.get('playlist_url', url_parts.path)
        context.append((i18n('Delete from playlist'),
                        'RunScript(' + CONFIG['id'] + ', delete_playlist_item, %s, %s, %s, %s, %s)'
                        % (server.get_uuid(), item_id, playlist_title,
                           item_data.get('playlist_item_id'), playlist_url)))
    elif item_data.get('library_section_uuid'):
        context.append((i18n('Add to playlist'),
                        'RunScript(' + CONFIG['id'] + ', add_playlist_item, %s, %s, %s)' %
                        (server.get_uuid(), item_id, item_data.get('library_section_uuid'))))

    if SETTINGS.get_setting('showdeletecontextmenu'):
        context.append((i18n('Delete'), 'RunScript(' + CONFIG['id'] + ', delete, %s, %s)' %
                        (server.get_uuid(), item_id)))

    if item_type == 'video' and item_source in ['tvepisodes', 'movies']:
        context.append((i18n('Audio'), 'RunScript(' + CONFIG['id'] + ', audio, %s, %s)' %
                        (server.get_uuid(), item_id)))
        context.append((i18n('Subtitles'), 'RunScript(' + CONFIG['id'] + ', subs, %s, %s)' %
                        (server.get_uuid(), item_id)))

    context.append((i18n('Update library'), 'RunScript(' + CONFIG['id'] + ', update, %s, %s)' %
                    (server.get_uuid(), section)))
    context.append((i18n('Refresh'), 'RunScript(' + CONFIG['id'] + ', refresh)'))

    LOG.debug('Using context menus: %s' % context)

    return context


def get_media_data(tag_dict):
    """
        Extra the media details from the XML
        @input: dict of <media /> tag attributes
        @output: dict of required values
    """
    return {
        'VideoResolution': tag_dict.get('videoResolution', ''),
        'VideoCodec': tag_dict.get('videoCodec', ''),
        'AudioCodec': tag_dict.get('audioCodec', ''),
        'AudioChannels': tag_dict.get('audioChannels', ''),
        'VideoAspect': tag_dict.get('aspectRatio', ''),
        'xbmc_height': tag_dict.get('height'),
        'xbmc_width': tag_dict.get('width'),
        'xbmc_VideoCodec': tag_dict.get('videoCodec'),
        'xbmc_AudioCodec': tag_dict.get('audioCodec'),
        'xbmc_AudioChannels': tag_dict.get('audioChannels'),
        'xbmc_VideoAspect': tag_dict.get('aspectRatio')
    }


def get_transcode_profile():
    profile_count = 3
    profile_labels = []

    for idx in list(range(profile_count)):
        if idx == 0 or SETTINGS.get_setting('transcode_target_enabled_%s' % str(idx)):
            resolution, bitrate = SETTINGS.get_setting('transcode_target_quality_%s' %
                                                       str(idx)).split(',')
            sub_size = SETTINGS.get_setting('transcode_target_sub_size_%s' % str(idx))
            audio_boost = SETTINGS.get_setting('transcode_target_audio_size_%s' % str(idx))
            profile_labels.append('[%s] %s@%s (%s/%s)' %
                                  (str(idx + 1), resolution, bitrate.strip(),
                                   sub_size, audio_boost))

    if len(profile_labels) == 1:
        return 0

    dialog = xbmcgui.Dialog()
    result = dialog.select(i18n('Transcode Profiles'), profile_labels)

    if result == -1:
        return 0

    return result

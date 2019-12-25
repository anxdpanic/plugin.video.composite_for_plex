# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import copy
import json

from six.moves.urllib_parse import quote
from six.moves.urllib_parse import quote_plus
from six.moves.urllib_parse import urlparse

from kodi_six import xbmcgui  # pylint: disable=import-error

from ..common import get_argv
from ..constants import CONFIG
from ..logger import Logger
from ..strings import encode_utf8
from ..strings import i18n
from ..strings import item_translate

LOG = Logger()


def create_gui_item(context, url, details, extra_data, context_menu=None, folder=True):  # pylint: disable=too-many-locals, too-many-statements, too-many-branches, too-many-arguments
    LOG.debug('Adding %s\n'
              'Details: %s\n'
              'Extra_data: %s' %
              (details.get('title', i18n('Unknown')),
               json.dumps(details, indent=4),
               json.dumps(extra_data, indent=4)))

    is_file = url.startswith('cmd:')

    path_mode = extra_data.get('path_mode')
    plugin_url = get_argv()[0]
    url_parts = urlparse(plugin_url)
    plugin_url = 'plugin://%s/' % url_parts.netloc
    if path_mode and '/' in path_mode:
        plugin_url += path_mode.rstrip('/') + '/'

    # Create the URL to pass to the item
    if not folder and extra_data['type'] == 'image':
        link_url = url
    elif url.startswith('http') or url.startswith('file'):
        link_url = '%s?url=%s&mode=%s' % (plugin_url, quote(url), extra_data.get('mode', 0))
    else:
        link_url = '%s?url=%s&mode=%s' % (plugin_url, url, extra_data.get('mode', 0))

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
    elif set_info_type.lower() == 'image':
        set_info_type = 'Picture'

    if set_info_type == 'Video':
        if not info_labels.get('plot'):
            info_labels['plot'] = u'\u2008'
        if not info_labels.get('plotoutline'):
            info_labels['plotoutline'] = u'\u2008'

    # Set the properties of the item, such as summary, name, season, etc
    list_item.setInfo(type=set_info_type, infoLabels=info_labels)

    item_properties = {}
    # Music related tags
    if extra_data.get('type', '').lower() == 'music':
        item_properties['Artist_Genre'] = details.get('genre', '')
        item_properties['Artist_Description'] = extra_data.get('plot', '')
        item_properties['Album_Description'] = extra_data.get('plot', '')

    # For all end items
    if not folder:
        item_properties['IsPlayable'] = 'true'

        if extra_data.get('type', 'video').lower() == 'video':
            item_properties['TotalTime'] = str(extra_data.get('duration'))
            item_properties['ResumeTime'] = str(extra_data.get('resume'))

            if not context.settings.get_setting('skipflags'):
                LOG.debug('Setting VrR as : %s' % extra_data.get('VideoResolution', ''))
                item_properties['VideoResolution'] = extra_data.get('VideoResolution', '')
                item_properties['VideoCodec'] = extra_data.get('VideoCodec', '')
                item_properties['AudioCodec'] = extra_data.get('AudioCodec', '')
                item_properties['AudioChannels'] = extra_data.get('AudioChannels', '')
                item_properties['VideoAspect'] = extra_data.get('VideoAspect', '')

                stream_info = extra_data.get('stream_info', {})
                list_item.addStreamInfo('video', stream_info.get('video', {}))
                list_item.addStreamInfo('audio', stream_info.get('audio', {}))

    if extra_data.get('source') == 'tvshows' or extra_data.get('source') == 'tvseasons':
        # Then set the number of watched and unwatched, which will be displayed per season
        item_properties['TotalEpisodes'] = str(extra_data['TotalEpisodes'])
        item_properties['WatchedEpisodes'] = str(extra_data['WatchedEpisodes'])
        item_properties['UnWatchedEpisodes'] = str(extra_data['UnWatchedEpisodes'])

        # Hack to show partial flag for TV shows and seasons
        if extra_data.get('partialTV') == 1:
            item_properties['TotalTime'] = '100'
            item_properties['ResumeTime'] = '50'

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
        item_properties['seasonThumb'] = '%s' % season_thumb

    list_item.setArt({
        'fanart': fanart,
        'poster': poster,
        'banner': banner,
        'thumb': thumb,
        'icon': thumb
    })

    if context_menu is not None:
        if not folder and extra_data.get('type', 'video').lower() == 'video':
            # Play Transcoded
            context_menu.insert(0, (i18n('Play Transcoded'),
                                    'PlayMedia(%s&transcode=1)' % link_url))
            LOG.debug('Setting transcode options to [%s&transcode=1]' % link_url)
        LOG.debug('Building Context Menus')
        list_item.addContextMenuItems(context_menu)

    if is_file:
        folder = False
        item_properties['IsPlayable'] = 'false'

    mediatype = details.get('mediatype')
    if mediatype:
        item_properties['content_type'] = mediatype + 's'

    if extra_data.get('hash'):
        item_properties['hash'] = extra_data['hash']

    if CONFIG['kodi_version'] >= 18:
        list_item.setProperties(item_properties)
    else:
        for key, value in item_properties.items():
            list_item.setProperty(key, value)

    return link_url, list_item, folder


def get_link_url(server, url, path_data):
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


def get_thumb_image(context, server, data, width=720, height=720):
    """
        Simply take a URL or path and determine how to format for images
        @ input: elementTree element, server name
        @ return formatted URL
    """
    if context.settings.get_setting('skipimages'):
        return ''

    thumbnail = encode_utf8(data.get('thumb', '').split('?t')[0])

    if thumbnail.startswith('http'):
        return thumbnail

    if thumbnail.startswith('/'):
        if context.settings.get_setting('fullres_thumbs'):
            return server.get_kodi_header_formatted_url(thumbnail)

        thumbnail = quote_plus('http://localhost:32400' + thumbnail)
        return server.get_kodi_header_formatted_url('/photo/:/transcode?url=%s&width=%s&height=%s' %
                                                    (thumbnail, width, height))

    return CONFIG['icon']


def get_banner_image(context, server, data, width=720, height=720):
    """
        Simply take a URL or path and determine how to format for images
        @ input: elementTree element, server name
        @ return formatted URL
    """
    if context.settings.get_setting('skipimages'):
        return ''

    thumbnail = encode_utf8(data.get('banner', '').split('?t')[0])

    if thumbnail.startswith('http'):
        return thumbnail

    if thumbnail.startswith('/'):
        if context.settings.get_setting('fullres_thumbs'):
            return server.get_kodi_header_formatted_url(thumbnail)

        thumbnail = quote_plus('http://localhost:32400' + thumbnail)
        return server.get_kodi_header_formatted_url('/photo/:/transcode?url=%s&width=%s&height=%s' %
                                                    (thumbnail, width, height))

    return CONFIG['icon']


def get_fanart_image(context, server, data, width=1280, height=720):
    """
        Simply take a URL or path and determine how to format for fanart
        @ input: elementTree element, server name
        @ return formatted URL for photo resizing
    """
    if context.settings.get_setting('skipimages'):
        return ''

    fanart = encode_utf8(data.get('art', ''))

    if fanart.startswith('http'):
        return fanart

    if fanart.startswith('/'):
        if context.settings.get_setting('fullres_fanart'):
            return server.get_kodi_header_formatted_url(fanart)

        return server.get_kodi_header_formatted_url('/photo/:/transcode?url=%s&width=%s&height=%s' %
                                                    (quote_plus('http://localhost:32400' + fanart),
                                                     width, height))

    return ''


def get_media_data(tag_dict):
    """
        Extra the media details from the XML
        @input: dict of <media /> tag attributes
        @output: dict of required values
    """
    stream_info_video = {
        'codec': tag_dict.get('videoCodec', ''),
        'aspect': float(tag_dict.get('aspectRatio', '1.78')),
        'height': int(tag_dict.get('height', 0)),
        'width': int(tag_dict.get('width', 0)),
        'duration': int(tag_dict.get('duration', 0)) / 1000
    }
    stream_info_audio = {
        'codec': tag_dict.get('audioCodec', ''),
        'channels': int(tag_dict.get('audioChannels', '2'))
    }

    return {
        'VideoResolution': tag_dict.get('videoResolution', ''),
        'VideoCodec': tag_dict.get('videoCodec', ''),
        'AudioCodec': tag_dict.get('audioCodec', ''),
        'AudioChannels': tag_dict.get('audioChannels', ''),
        'VideoAspect': tag_dict.get('aspectRatio', ''),
        'stream_info': {
            'video': stream_info_video,
            'audio': stream_info_audio,
        },
    }

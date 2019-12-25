# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from ...addon.constants import MODES
from ...addon.strings import encode_utf8
from ...addon.strings import i18n
from .common import create_gui_item
from .common import get_fanart_image
from .common import get_link_url
from .common import get_thumb_image


def create_plex_plugin_item(context, server, tree, url, plugin):
    details = {
        'title': encode_utf8(plugin.get('title'))
    }

    if details['title']:
        details['title'] = encode_utf8(plugin.get('name', i18n('Unknown')))

    if plugin.get('summary'):
        details['plot'] = plugin.get('summary')

    extra_data = {
        'thumb': get_thumb_image(context, server, plugin),
        'fanart_image': get_fanart_image(context, server, plugin),
        'identifier': tree.get('identifier', ''),
        'type': 'Video',
        'key': plugin.get('key', '')
    }

    if (tree.get('identifier') != 'com.plexapp.plugins.myplex') and ('node.plexapp.com' in url):
        extra_data['key'] = extra_data['key'].replace('node.plexapp.com:32400',
                                                      server.get_location())

    if extra_data['fanart_image'] == '':
        extra_data['fanart_image'] = get_fanart_image(context, server, tree)

    p_url = get_link_url(server, url, extra_data)

    if plugin.tag in ['Directory', 'Podcast']:
        return get_directory_item(context, plugin, p_url, details, extra_data)

    if plugin.tag == 'Setting':
        return get_setting_item(context, plugin, url, details, extra_data)

    if plugin.tag == 'Video':
        return get_video_item(context, plugin, p_url, details, extra_data)

    return None


def get_directory_item(context, plugin, url, details, extra_data):
    extra_data['mode'] = MODES.PLEXPLUGINS
    if plugin.get('search') == '1':
        extra_data['mode'] = MODES.CHANNELSEARCH
        extra_data['parameters'] = {
            'prompt': encode_utf8(plugin.get('prompt', i18n('Enter search term')))
        }

    return create_gui_item(context, url, details, extra_data)


def get_setting_item(context, plugin, url, details, extra_data):
    value = plugin.get('value')
    if plugin.get('option') == 'hidden':
        value = '********'
    elif plugin.get('type') == 'text':
        value = plugin.get('value')
    elif plugin.get('type') == 'enum':
        value = plugin.get('values').split('|')[int(plugin.get('value', 0))]

    details['title'] = '%s - [%s]' % (encode_utf8(plugin.get('label', i18n('Unknown'))), value)
    extra_data['mode'] = MODES.CHANNELPREFS
    extra_data['parameters'] = {
        'id': plugin.get('id')
    }

    return create_gui_item(context, url, details, extra_data)


def get_video_item(context, plugin, url, details, extra_data):
    extra_data['mode'] = MODES.VIDEOPLUGINPLAY

    for child in plugin:
        if child.tag == 'Media':
            extra_data['parameters'] = {
                'indirect': child.get('indirect', '0')
            }

    return create_gui_item(context, url, details, extra_data, folder=False)

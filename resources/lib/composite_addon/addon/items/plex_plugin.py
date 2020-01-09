# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2020 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from ..constants import MODES
from ..containers import GUIItem
from ..strings import encode_utf8
from ..strings import i18n
from .common import get_fanart_image
from .common import get_link_url
from .common import get_thumb_image
from .gui import create_gui_item


def create_plex_plugin_item(context, item):
    info_labels = {
        'title': encode_utf8(item.data.get('title'))
    }

    if info_labels['title']:
        info_labels['title'] = encode_utf8(item.data.get('name', i18n('Unknown')))

    if item.data.get('summary'):
        info_labels['plot'] = item.data.get('summary')

    extra_data = {
        'thumb': get_thumb_image(context, item.server, item.data),
        'fanart_image': get_fanart_image(context, item.server, item.data),
        'identifier': item.tree.get('identifier', ''),
        'type': 'Video',
        'key': item.data.get('key', '')
    }

    if ((item.tree.get('identifier') != 'com.plexapp.plugins.myplex') and
            ('node.plexapp.com' in item.url)):
        extra_data['key'] = extra_data['key'].replace('node.plexapp.com:32400',
                                                      item.server.get_location())

    if extra_data['fanart_image'] == '':
        extra_data['fanart_image'] = get_fanart_image(context, item.server, item.tree)

    p_url = get_link_url(item.server, item.url, extra_data)

    if item.data.tag in ['Directory', 'Podcast']:
        return get_directory_item(context, item.data, p_url, info_labels, extra_data)

    if item.data.tag == 'Setting':
        return get_setting_item(context, item.data, item.url, info_labels, extra_data)

    if item.data.tag == 'Video':
        return get_video_item(context, item.data, p_url, info_labels, extra_data)

    return None


def get_directory_item(context, plugin, url, info_labels, extra_data):
    extra_data['mode'] = MODES.PLEXPLUGINS
    if plugin.get('search') == '1':
        extra_data['mode'] = MODES.CHANNELSEARCH
        extra_data['parameters'] = {
            'prompt': encode_utf8(plugin.get('prompt', i18n('Enter search term')))
        }

    gui_item = GUIItem(url, info_labels, extra_data)
    return create_gui_item(context, gui_item)


def get_setting_item(context, plugin, url, info_labels, extra_data):
    value = plugin.get('value')
    if plugin.get('option') == 'hidden':
        value = '********'
    elif plugin.get('type') == 'text':
        value = plugin.get('value')
    elif plugin.get('type') == 'enum':
        value = plugin.get('values').split('|')[int(plugin.get('value', 0))]

    info_labels['title'] = '%s - [%s]' % (encode_utf8(plugin.get('label', i18n('Unknown'))), value)
    extra_data['mode'] = MODES.CHANNELPREFS
    extra_data['parameters'] = {
        'id': plugin.get('id')
    }

    gui_item = GUIItem(url, info_labels, extra_data)
    return create_gui_item(context, gui_item)


def get_video_item(context, plugin, url, info_labels, extra_data):
    extra_data['mode'] = MODES.VIDEOPLUGINPLAY

    for child in plugin:
        if child.tag == 'Media':
            extra_data['parameters'] = {
                'indirect': child.get('indirect', '0')
            }

    gui_item = GUIItem(url, info_labels, extra_data)
    gui_item.is_folder = False
    return create_gui_item(context, gui_item)

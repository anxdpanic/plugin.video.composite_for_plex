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
from ...addon.utils import create_gui_item
from ...addon.utils import get_link_url
from ...addon.utils import get_thumb_image
from ...addon.utils import get_fanart_image


def create_plex_plugin_item(server, tree, url, plugin):  # pylint: disable=too-many-branches
    details = {'title': encode_utf8(plugin.get('title'))}

    if details['title']:
        details['title'] = encode_utf8(plugin.get('name', i18n('Unknown')))

    if plugin.get('summary'):
        details['plot'] = plugin.get('summary')

    extra_data = {
        'thumb': get_thumb_image(plugin, server),
        'fanart_image': get_fanart_image(plugin, server),
        'identifier': tree.get('identifier', ''),
        'type': 'Video',
        'key': plugin.get('key', '')
    }

    if (tree.get('identifier') != 'com.plexapp.plugins.myplex') and ('node.plexapp.com' in url):
        extra_data['key'] = extra_data['key'].replace('node.plexapp.com:32400',
                                                      server.get_location())

    if extra_data['fanart_image'] == '':
        extra_data['fanart_image'] = get_fanart_image(tree, server)

    p_url = get_link_url(url, extra_data, server)

    if plugin.tag == 'Directory' or plugin.tag == 'Podcast':

        if plugin.get('search') == '1':
            extra_data['mode'] = MODES.CHANNELSEARCH
            extra_data['parameters'] = {
                'prompt': encode_utf8(plugin.get('prompt', i18n('Enter search term')))
            }
        else:
            extra_data['mode'] = MODES.PLEXPLUGINS

        return create_gui_item(p_url, details, extra_data)

    if plugin.tag == 'Video':
        extra_data['mode'] = MODES.VIDEOPLUGINPLAY

        for child in plugin:
            if child.tag == 'Media':
                extra_data['parameters'] = {'indirect': child.get('indirect', '0')}

        return create_gui_item(p_url, details, extra_data, folder=False)

    if plugin.tag == 'Setting':

        if plugin.get('option') == 'hidden':
            value = '********'
        elif plugin.get('type') == 'text':
            value = plugin.get('value')
        elif plugin.get('type') == 'enum':
            value = plugin.get('values').split('|')[int(plugin.get('value', 0))]
        else:
            value = plugin.get('value')

        details['title'] = '%s - [%s]' % (encode_utf8(plugin.get('label', i18n('Unknown'))), value)
        extra_data['mode'] = MODES.CHANNELPREFS
        extra_data['parameters'] = {'id': plugin.get('id')}

        return create_gui_item(url, details, extra_data)

    return None

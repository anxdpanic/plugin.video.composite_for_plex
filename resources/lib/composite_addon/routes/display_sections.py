# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import xbmcplugin  # pylint: disable=import-error

from ..addon.common import CONFIG
from ..addon.common import MODES
from ..addon.common import SETTINGS
from ..addon.common import PrintDebug
from ..addon.common import get_handle
from ..addon.common import i18n
from ..addon.utils import add_item_to_gui
from ..plex import plex

LOG = PrintDebug(CONFIG['name'])
PLEX_NETWORK = plex.Plex(load=False)


def run(cfilter=None, display_shared=False):  # pylint: disable=too-many-branches, too-many-statements
    PLEX_NETWORK.load()
    xbmcplugin.setContent(get_handle(), 'files')

    server_list = PLEX_NETWORK.get_server_list()
    LOG.debug('Using list of %s servers: %s' % (len(server_list), server_list))

    for server in server_list:

        sections = server.get_sections()

        for section in sections:

            if ((display_shared and server.is_owned()) or
                    (cfilter is not None and section.content_type() != cfilter)):
                continue

            if section.content_type() is None:
                LOG.debug('Ignoring section %s: %s of type %s as unable to process'
                          % (server.get_name(), section.get_title(), section.get_type()))
                continue

            if not SETTINGS.prefix_server() or (SETTINGS.prefix_server() and len(server_list) > 1):
                details = {'title': '%s: %s' % (server.get_name(), section.get_title())}
            else:
                details = {'title': section.get_title()}

            extra_data = {'fanart_image': server.get_fanart(section),
                          'type': 'Folder'}

            path = section.get_path()

            if SETTINGS.get_setting('secondary'):
                mode = MODES.GETCONTENT
            else:
                mode = section.mode()
                path = path + '/all'

            extra_data['mode'] = mode
            section_url = '%s%s' % (server.get_url_location(), path)

            if not SETTINGS.get_setting('skipcontextmenus'):
                context = [(i18n('Refresh library section'),
                            'RunScript(' + CONFIG['id'] + ', update, %s, %s)' %
                            (server.get_uuid(), section.get_key()))]
            else:
                context = None

            # Build that listing..
            add_item_to_gui(section_url, details, extra_data, context)

    if display_shared:
        xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))
        return

    # For each of the servers we have identified
    if PLEX_NETWORK.is_myplex_signedin():
        details = {'title': i18n('myPlex Queue')}
        extra_data = {'type': 'Folder', 'mode': MODES.MYPLEXQUEUE}
        add_item_to_gui('http://myplexqueue', details, extra_data)

    for server in server_list:

        if server.is_offline() or server.is_secondary():
            continue

        # Plex plugin handling
        if (cfilter is not None) and (cfilter != 'plugins'):
            continue

        if not SETTINGS.prefix_server() or (SETTINGS.prefix_server() and len(server_list) > 1):
            prefix = server.get_name() + ': '
        else:
            prefix = ''

        details = {'title': prefix + i18n('Channels')}
        extra_data = {'type': 'Folder', 'mode': MODES.CHANNELVIEW}

        item_url = '%s/channels/all' % server.get_url_location()
        add_item_to_gui(item_url, details, extra_data)

        # Create plexonline link
        details = {'title': prefix + i18n('Plex Online')}
        extra_data = {'type': 'Folder', 'mode': MODES.PLEXONLINE}

        item_url = '%s/system/plexonline' % server.get_url_location()
        add_item_to_gui(item_url, details, extra_data)

        # create playlist link
        details = {'title': prefix + i18n('Playlists')}
        extra_data = {'type': 'Folder', 'mode': MODES.PLAYLISTS}

        item_url = '%s/playlists' % server.get_url_location()
        add_item_to_gui(item_url, details, extra_data)

    if PLEX_NETWORK.is_myplex_signedin():

        if PLEX_NETWORK.is_plexhome_enabled():
            details = {'title': i18n('Switch User')}
            extra_data = {'type': 'file'}

            item_url = 'cmd:switchuser'
            add_item_to_gui(item_url, details, extra_data)

        details = {'title': i18n('Sign Out')}
        extra_data = {'type': 'file'}

        item_url = 'cmd:signout'
        add_item_to_gui(item_url, details, extra_data)
    else:
        details = {'title': i18n('Sign In')}
        extra_data = {'type': 'file'}

        item_url = 'cmd:signintemp'
        add_item_to_gui(item_url, details, extra_data)

    details = {'title': i18n('Display Servers')}
    extra_data = {'type': 'file'}
    data_url = 'cmd:displayservers'
    add_item_to_gui(data_url, details, extra_data)

    if SETTINGS.get_setting('cache'):
        details = {'title': i18n('Refresh Data')}
        extra_data = {'type': 'file'}
        item_url = 'cmd:delete_refresh'
        add_item_to_gui(item_url, details, extra_data)

    # All XML entries have been parsed and we are ready to allow the user to browse around.
    # So end the screen listing.
    xbmcplugin.endOfDirectory(get_handle(), cacheToDisc=SETTINGS.get_setting('kodicache'))

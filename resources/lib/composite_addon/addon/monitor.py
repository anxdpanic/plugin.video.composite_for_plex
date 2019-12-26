# -*- coding: utf-8 -*-
"""

    Copyright (C) 2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import json

from kodi_six import xbmc  # pylint: disable=import-error

from .common import get_plugin_url
from .constants import CONFIG
from .constants import MODES
from .logger import Logger
from .utils import jsonrpc_play


class Monitor(xbmc.Monitor):
    LOG = Logger('Monitor')

    def __init__(self, settings):
        self.settings = settings

    def decode_up_next_notification(self, data):
        """
        Decode data received from Up Next notification
        """
        data = json.loads(data)
        json_data = None
        encoding = self.settings.up_next_encoding()
        if data:
            if encoding == 'base64':
                from base64 import b64decode  # pylint: disable=import-outside-toplevel
                json_data = b64decode(data[0])
            elif encoding == 'hex':
                from binascii import unhexlify  # pylint: disable=import-outside-toplevel
                json_data = unhexlify(data[0])

            if not json_data:
                return None

            if isinstance(json_data, bytes):
                json_data = json_data.decode('utf-8')

            return json.loads(json_data)

        return None

    @staticmethod
    def up_next_playback_url(data):
        """
        Create a playback url from Up Next 'play_info'
        """
        data['mode'] = MODES.PLAYLIBRARY

        if data['transcode'] is None:
            data['transcode'] = 0
        data['transcode'] = int(data['transcode'])

        data['transcode_profile'] = int(data.get('transcode_profile', 0))

        return get_plugin_url(data)

    def onNotification(self, sender, method, data):  # pylint: disable=invalid-name
        """
        Handle any notifications directed to this add-on
        """
        if CONFIG['id'] not in method:
            return

        if sender.startswith('upnextprovider') and method.endswith('_play_action'):
            # received a play notification from Up Next
            jsonrpc_play(self.up_next_playback_url(self.decode_up_next_notification(data)))

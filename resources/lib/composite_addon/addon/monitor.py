# -*- coding: utf-8 -*-
"""

    Copyright (C) 2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import base64
import json
import time

from six.moves.urllib_parse import urlencode

import xbmc  # pylint: disable=import-error
import xbmcgui  # pylint: disable=import-error

from .common import CONFIG
from .common import PrintDebug


class Monitor(xbmc.Monitor):
    LOG = PrintDebug(CONFIG['name'], 'Monitor')

    def __init__(self):
        """
        """

    @staticmethod
    def _decode_up_next_notification(data):
        """
        Decode data received from Up Next notification
        """
        data = json.loads(data)
        if data:
            json_data = base64.b64decode(data[0])
            if isinstance(json_data, bytes):
                json_data = json_data.decode('utf-8')
            return json.loads(json_data)
        return None

    @staticmethod
    def _up_next_playback_url(data):
        """
        Create a playback url from Up Next 'play_info'
        """
        data['mode'] = '5'

        if data['transcode'] is None:
            data['transcode'] = 0
        data['transcode'] = int(data['transcode'])

        data['transcode_profile'] = int(data.get('transcode_profile', 0))

        if data['force'] is None:
            del data['force']

        return 'plugin://%s/?%s' % (CONFIG['id'], urlencode(data))

    def play_media(self, url):
        """
        Use PlayMedia to start playback after busy dialogs are closed
        """
        if xbmc.Player().isPlaying():
            xbmc.Player().stop()

        play = self.wait_for_busy_dialog()
        if play:
            xbmc.executebuiltin('PlayMedia(%s)' % url)

    def wait_for_busy_dialog(self):
        """
        Wait for busy dialogs to close, starting playback while the busy dialog is active
        could crash Kodi 18 / 19 (pre-alpha)
        """
        start_time = time.time()
        xbmc.sleep(500)

        self.LOG.debug('Waiting for busy dialogs to close ...')
        while (xbmcgui.getCurrentWindowDialogId() in [10138, 10160] and
               not self.abortRequested()):
            if self.waitForAbort(3):
                break

        self.LOG.debug('Waited %.2f for busy dialogs to close.' % (time.time() - start_time))
        return (not self.abortRequested() and
                xbmcgui.getCurrentWindowDialogId() not in [10138, 10160])

    def onNotification(self, sender, method, data):  # pylint: disable=invalid-name
        """
        Handle any notifications directed to this add-on
        """
        if CONFIG['id'] not in method:
            return

        if sender.startswith('upnextprovider') and method.endswith('_play_action'):
            # received a play notification from Up Next
            self.play_media(self._up_next_playback_url(self._decode_up_next_notification(data)))
# -*- coding: utf-8 -*-
"""

    Copyright (C) 2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

from binascii import unhexlify
import json
import time

import xbmc
import xbmcgui

from six.moves.urllib_parse import urlencode

from .common import CONFIG
from .common import PrintDebug


class Monitor(xbmc.Monitor):
    def __init__(self):
        self.log = PrintDebug(CONFIG['name'], 'Monitor')

    @staticmethod
    def _process_notification_data(data):
        data = json.loads(data)
        if data:
            return json.loads(unhexlify(data[0]))

    @staticmethod
    def _create_playback_url(data):
        data['mode'] = '5'

        if data['transcode'] is None:
            data['transcode'] = 0
        data['transcode'] = int(data['transcode'])

        data['transcode_profile'] = int(data.get('transcode_profile', 0))

        if data['force'] is None:
            del data['force']

        return 'plugin://%s/?%s' % (CONFIG['id'], urlencode(data))

    def _play_media(self, url):
        if xbmc.Player().isPlaying():
            xbmc.Player().stop()

        xbmc.sleep(500)

        start_time = time.time()
        # need to wait here for busy dialogs to close or it will crash Kodi 18 / 19 (pre-alpha)
        self.log.debug('Playback is waiting for busy dialogs to close ...')
        while xbmcgui.getCurrentWindowDialogId() in [10138, 10160] and not self.abortRequested():
            if self.waitForAbort(3):
                break

        self.log.debug('Starting playback, waited %.2f for busy dialogs to close.' % (time.time() - start_time))
        xbmc.executebuiltin('PlayMedia(%s)' % url)

    def onNotification(self, sender, method, data):
        if not sender[-7:] == '.SIGNAL':
            return

        if (sender.startswith('upnextprovider') and
                method.endswith('_play_action') and
                CONFIG['id'] in method):
            self._play_media(self._create_playback_url(self._process_notification_data(data)))

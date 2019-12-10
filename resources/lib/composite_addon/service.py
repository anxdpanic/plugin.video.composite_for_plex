# -*- coding: utf-8 -*-
"""

    Copyright (C) 2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from kodi_six import xbmcgui  # pylint: disable=import-error

from .addon.constants import CONFIG
from .addon.logger import Logger
from .addon.monitor import Monitor
from .addon.player import CallbackPlayer

LOG = Logger(CONFIG['name'], 'service')


def run():
    sleep_time = 10

    LOG.debug('Service initialization...')

    window = xbmcgui.Window(10000)
    player = CallbackPlayer(window=window)
    monitor = Monitor()

    while not monitor.abortRequested():

        if monitor.waitForAbort(sleep_time):
            break

    player.cleanup_threads(only_ended=False)  # clean up any/all playback monitoring threads

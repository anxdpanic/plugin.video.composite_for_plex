"""

    Copyright (C) 2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

import xbmcgui

from .common import CONFIG
from .common import PrintDebug
from .monitor import Monitor
from .player import CallbackPlayer

log = PrintDebug(CONFIG['name'], 'service')


def run():
    sleep_time = 10

    log.debug('Service initialization...')

    window = xbmcgui.Window(10000)
    player = CallbackPlayer(window=window)
    monitor = Monitor()

    while not monitor.abortRequested():

        if monitor.waitForAbort(sleep_time):
            break

    player.cleanup_threads(only_ended=False)  # clean up any/all playback monitoring threads

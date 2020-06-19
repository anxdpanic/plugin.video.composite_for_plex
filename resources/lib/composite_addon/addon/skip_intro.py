# -*- coding: utf-8 -*-
"""

    Copyright (C) 2020-2020 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from kodi_six.xbmc import Player  # pylint: disable=import-error
from kodi_six.xbmcgui import WindowXMLDialog  # pylint: disable=import-error

from .logger import Logger


class SkipIntroDialog(WindowXMLDialog):
    LOG = Logger('SkipIntroDialog')

    def __init__(self, *args, **kwargs):
        self.intro_end = kwargs.pop('intro_end', None)
        self.showing = False
        self.LOG.debug('Dialog initialized, Intro ends at %s' % self._log_time(self.intro_end))
        WindowXMLDialog.__init__(self, *args, **kwargs)

    def show(self):
        if not self.intro_end:
            self.close()
            return

        if not self.showing:
            self.LOG.debug('Showing dialog')
            self.showing = True
            WindowXMLDialog.show(self)

    def close(self):
        if self.showing:
            self.showing = False
            self.LOG.debug('Closing dialog')
            WindowXMLDialog.close(self)

    def onClick(self, control_id):  # pylint: disable=invalid-name
        if self.intro_end and control_id == 3002:  # 3002 = Skip Intro button
            Player().seekTime(self.intro_end // 1000)

    def onAction(self, action):  # pylint: disable=invalid-name
        close_actions = [10, 13, 92]
        # 10 = previousmenu, 13 = stop, 92 = back
        if action in close_actions:
            self.close()

    @staticmethod
    def _log_time(mil):
        if not isinstance(mil, int):
            return 'undefined'
        secs = (mil // 1000) % 60
        mins = (mil // (1000 * 60)) % 60
        return '%d:%d' % (int(mins), int(secs))

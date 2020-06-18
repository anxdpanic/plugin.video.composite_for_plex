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
        cid_skip_intro = 3000

        if self.intro_end and control_id == cid_skip_intro:  # Skip intro
            Player().seekTime(self.intro_end // 1000)

    def onAction(self, action):  # pylint: disable=invalid-name
        act_player_stop = 13
        act_nav_back = 92

        if action == act_player_stop:
            self.close()
        elif action == act_nav_back:
            self.close()

    @staticmethod
    def _log_time(mil):
        if not isinstance(mil, int):
            return 'undefined'
        secs = (mil // 1000) % 60
        secs = int(secs)
        mins = (mil // (1000 * 60)) % 60
        mins = int(mins)
        return '%d:%d' % (mins, secs)

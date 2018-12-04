"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018 bPlex (plugin.video.bplex)

    This file is part of bPlex (plugin.video.bplex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

import xbmcaddon
import xbmc

from six.moves import range


class AddonSettings:

    def __init__(self, name):
        xbmc.log('bPlex.setting -> Reading settings configuration', xbmc.LOGDEBUG)
        self.settings = xbmcaddon.Addon(name)
        self.stream = self.settings.getSetting('streaming')

    def open_settings(self):
        return self.settings.openSettings()

    def get_setting(self, name):
        value = self.settings.getSetting(name)

        if value == 'true':
            return True
        elif value == 'false':
            return False
        else:
            return value

    def get_debug(self):
        return int(self.get_setting('debug'))

    def set_setting(self, name, value):
        if isinstance(value, bool):
            value = str(value).lower()

        self.settings.setSetting(name, value)

    def get_wakeservers(self):
        wakeserver = []
        for servers in list(range(1, 12)):
            wakeserver.append(self.settings.getSetting('wol%s' % servers))
        return wakeserver

    def get_stream(self):
        return self.stream

    def set_stream(self, value):
        self.stream = value

    def dump_settings(self):
        return self.__dict__

    def update_master_server(self, value):
        xbmc.log('Updating master server to %s' % value, xbmc.LOGDEBUG)
        self.settings.setSetting('masterServer', '%s' % value)

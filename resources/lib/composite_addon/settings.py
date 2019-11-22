"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

import xbmcaddon
import xbmc

from six.moves import range


class AddonSettings:

    def __init__(self, addon_id):
        self.addon_id = addon_id
        self.settings = xbmcaddon.Addon(addon_id)
        try:
            self.addon_name = self.settings.getAddonInfo('name').decode('utf-8')
        except AttributeError:
            self.addon_name = self.settings.getAddonInfo('name')
        xbmc.log(self.addon_name + '.settings -> Reading settings configuration', xbmc.LOGDEBUG)
        self.stream = self.settings.getSetting('streaming')

    def open_settings(self):
        return self.settings.openSettings()

    def get_setting(self, name, fresh=False):
        if fresh:
            value = xbmcaddon.Addon(self.addon_id).getSetting(name)
        else:
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
        xbmc.log(self.addon_name + '.settings -> Updating master server to %s' % value, xbmc.LOGDEBUG)
        self.settings.setSetting('masterServer', '%s' % value)

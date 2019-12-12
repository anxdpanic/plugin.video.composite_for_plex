# -*- coding: utf-8 -*-
"""

    Copyright (C) 2013-2019 PleXBMC Helper (script.plexbmc.helper)
        by wickning1 (aka Nick Wing), hippojay (Dave Hawes-Johnson)
    Copyright (C) 2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import uuid
from xml.dom.minidom import parse

from kodi_six import xbmc  # pylint: disable=import-error

from ..addon.constants import CONFIG
from ..addon.settings import AddonSettings

__SETTINGS = AddonSettings(CONFIG['id'])

SETTINGS = {}


class GUISettings:
    def __init__(self):
        self.settings = None

    def parse_settings(self):
        self.settings = parse(xbmc.translatePath('special://userdata/guisettings.xml'))

    def get_setting(self, name):
        if not self.settings:
            self.parse_settings()

        try:
            value = self.settings.getElementsByTagName(name)[0].firstChild.nodeValue
        except IndexError:
            value = None

        if value is None:
            value = ''
            settings = self.settings.getElementsByTagName('setting')
            for setting in settings:
                if setting.getAttribute('id') == name and setting.firstChild:
                    value = setting.firstChild.nodeValue

        if value == 'false':
            return False
        if value == 'true':
            return True

        return value


__GUI_SETTINGS = GUISettings()

if __SETTINGS.get_setting('use_kodi_devicename'):
    SETTINGS['client_name'] = __GUI_SETTINGS.get_setting('devicename')
    if SETTINGS['client_name'] == '':
        SETTINGS['client_name'] = __GUI_SETTINGS.get_setting('services.devicename')

if not SETTINGS.get('client_name') or not __SETTINGS.get_setting('use_kodi_devicename'):
    SETTINGS['client_name'] = __SETTINGS.get_setting('devicename')

# Kodi web server settings
SETTINGS['webserver_enabled'] = __GUI_SETTINGS.get_setting('webserver')
if SETTINGS['webserver_enabled'] != '':
    SETTINGS['webserver_port'] = __GUI_SETTINGS.get_setting('webserverport')
    SETTINGS['webserver_user'] = __GUI_SETTINGS.get_setting('webserverusername')
    SETTINGS['webserver_passwd'] = __GUI_SETTINGS.get_setting('webserverpassword')
    SETTINGS['webserver_ssl'] = __GUI_SETTINGS.get_setting('webserverssl')
else:
    SETTINGS['webserver_enabled'] = __GUI_SETTINGS.get_setting('services.webserver')
    SETTINGS['webserver_port'] = __GUI_SETTINGS.get_setting('services.webserverport')
    SETTINGS['webserver_user'] = __GUI_SETTINGS.get_setting('services.webserverusername')
    SETTINGS['webserver_passwd'] = __GUI_SETTINGS.get_setting('services.webserverpassword')
    SETTINGS['webserver_ssl'] = __GUI_SETTINGS.get_setting('services.webserverssl')

if SETTINGS['webserver_port']:
    SETTINGS['webserver_port'] = int(SETTINGS['webserver_port'])

SETTINGS['receiver_uuid'] = str(__SETTINGS.get_setting('receiver_uuid')) or str(uuid.uuid4())
__SETTINGS.set_setting('receiver_uuid', SETTINGS['receiver_uuid'])
SETTINGS['myplex_user'] = __SETTINGS.get_setting('myplex_user')
SETTINGS['receiver_port'] = int(__SETTINGS.get_setting('receiver_port'))

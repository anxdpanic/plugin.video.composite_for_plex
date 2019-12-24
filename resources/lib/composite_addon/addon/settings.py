# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import json
import uuid

from six.moves import range

from kodi_six import xbmc  # pylint: disable=import-error
from kodi_six import xbmcaddon  # pylint: disable=import-error
from kodi_six import xbmcgui  # pylint: disable=import-error
from kodi_six import xbmcvfs  # pylint: disable=import-error

from .constants import CONFIG


class AddonSettings:  # pylint: disable=too-many-public-methods

    def __init__(self):
        self.settings = self._get_addon()
        self.addon_name = CONFIG['name']
        xbmc.log(self.addon_name + '.settings -> Reading settings configuration', xbmc.LOGDEBUG)
        self.stream = self.settings.getSetting('streaming')
        self.picture_mode = False

    @staticmethod
    def _get_addon():
        return xbmcaddon.Addon(CONFIG['id'])

    def open_settings(self):
        return self.settings.openSettings()

    def get_setting(self, name, fresh=False):
        if fresh:
            value = self._get_addon().getSetting(name)
        else:
            value = self.settings.getSetting(name)

        if value == 'true':
            return True

        if value == 'false':
            return False

        return value

    def get_debug(self):
        return int(self.get_setting('debug'))

    def set_setting(self, name, value):
        if isinstance(value, bool):
            value = str(value).lower()

        self.settings.setSetting(name, value)

    def get_picture_mode(self):
        return self.picture_mode

    def set_picture_mode(self, value):
        self.picture_mode = bool(value)

    def get_wakeservers(self):
        servers = []
        for server in list(range(1, 12)):
            servers.append(self.settings.getSetting('wol%s' % server))
        return servers

    def get_stream(self):
        return self.stream

    def set_stream(self, value):
        self.stream = value

    def dump_settings(self):
        return self.__dict__

    def update_master_server(self, value):
        xbmc.log(self.addon_name + '.settings -> Updating master server to %s' %
                 value, xbmc.LOGDEBUG)
        self.settings.setSetting('masterServer', '%s' % value)

    def prefix_server(self):
        return self.get_setting('prefix_server') == '1'

    def use_up_next(self):
        upnext_id = 'service.upnext'
        s_upnext_enabled = self.get_setting('use_up_next', fresh=True)

        try:
            _ = xbmcaddon.Addon(upnext_id)
            has_upnext = True
            upnext_disabled = False
        except RuntimeError:
            addon_xml = xbmc.translatePath('special://home/addons/%s/addon.xml' % upnext_id)
            if xbmcvfs.exists(addon_xml):  # if addon.xml exists, add-on is disabled
                has_upnext = True
                upnext_disabled = True
            else:
                has_upnext = False
                upnext_disabled = False

        if s_upnext_enabled and has_upnext and upnext_disabled:
            enable_upnext = xbmcgui.Dialog().yesno(self.addon_name,
                                                   self.settings.getLocalizedString(30688))
            if enable_upnext:
                upnext_disabled = not self.enable_addon(upnext_id)

        if (not has_upnext or upnext_disabled) and s_upnext_enabled:
            self.set_setting('use_up_next', False)
            return False

        return s_upnext_enabled and has_upnext and not upnext_disabled

    def up_next_encoding(self):
        return self.get_setting('up_next_data_encoding', fresh=True)

    def data_cache_ttl(self):
        return int(self.get_setting('data_cache_ttl', fresh=True)) * 60

    def use_companion(self):
        return self.get_setting('use_companion_receiver', fresh=True)

    def companion_receiver(self):
        receiver_uuid = str(self.get_setting('receiver_uuid')) or str(uuid.uuid4())
        self.set_setting('receiver_uuid', receiver_uuid)

        port = self.get_setting('receiver_port')
        try:
            port = int(port)
        except ValueError:
            port = 3005

        return {
            'name': self.get_setting('receiver_name'),
            'port': port,
            'uuid': receiver_uuid,
        }

    def kodi_web_server(self):
        port = self.get_setting('web_server_port')
        try:
            port = int(port)
        except ValueError:
            port = 8080

        return {
            'name': self.get_setting('web_server_username'),
            'password': self.get_setting('web_server_password'),
            'port': port,
        }

    def addon_status(self, addon_id):
        request = {
            "jsonrpc": "2.0",
            "method": "Addons.GetAddonDetails",
            "id": 1,
            "params": {
                "addonid": "%s" % addon_id,
                "properties": ["enabled"]
            }
        }
        response = xbmc.executeJSONRPC(json.dumps(request))
        response = json.loads(response)
        try:
            is_enabled = response['result']['addon']['enabled'] is True
            xbmc.log(self.addon_name + '.settings -> %s is %s' %
                     (addon_id, 'enabled' if is_enabled else 'disabled'), xbmc.LOGDEBUG)
            return is_enabled
        except KeyError:
            xbmc.log(self.addon_name + '.settings -> addon_status received an unexpected response',
                     xbmc.LOGERROR)
            return False

    def disable_addon(self, addon_id):
        request = {
            "jsonrpc": "2.0",
            "method": "Addons.SetAddonEnabled",
            "params": {
                "addonid": "%s" % addon_id,
                "enabled": False
            },
            "id": 1
        }

        xbmc.log(self.addon_name + '.settings -> disabling %s' % addon_id, xbmc.LOGDEBUG)
        response = xbmc.executeJSONRPC(json.dumps(request))
        response = json.loads(response)
        try:
            return response['result'] == 'OK'
        except KeyError:
            xbmc.log(self.addon_name + '.settings -> disable_addon received an unexpected response',
                     xbmc.LOGERROR)
            return False

    def enable_addon(self, addon_id):
        request = {
            "jsonrpc": "2.0",
            "method": "Addons.SetAddonEnabled",
            "params": {
                "addonid": "%s" % addon_id,
                "enabled": True
            },
            "id": 1
        }

        xbmc.log(self.addon_name + '.settings -> enabling %s' % addon_id, xbmc.LOGDEBUG)

        response = xbmc.executeJSONRPC(json.dumps(request))
        response = json.loads(response)
        try:
            return response['result'] == 'OK'
        except KeyError:
            xbmc.log(self.addon_name + '.settings -> enable_addon received an unexpected response',
                     xbmc.LOGERROR)
            return False

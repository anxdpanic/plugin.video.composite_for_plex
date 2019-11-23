"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

from binascii import hexlify
import inspect
import json
import os
import platform
import re
import socket
import sys
import traceback

import xbmc
import xbmcaddon

from six import PY3
from six import string_types
from six.moves import cPickle as pickle

from .settings import AddonSettings
from .strings import strings

__id = 'plugin.video.composite_for_plex'
__addon = xbmcaddon.Addon(id=__id)


def __enum(**enums):
    return type('Enum', (), enums)


def get_argv():
    return sys.argv


def get_handle():
    try:
        return int(get_argv()[1])
    except (ValueError, IndexError):
        return -1


class PrintDebug:

    def __init__(self, main, sub=None):

        self.main = main
        if sub:
            self.sub = '.' + sub
        else:
            self.sub = ''

        self.level = settings.get_debug()
        self.privacy = settings.get_setting('privacy')

        self.DEBUG_DEBUG = 0
        self.DEBUG_DEBUGPLUS = 1
        self.LOG_ERROR = 9
        self.token_regex = re.compile(r'-Token=[a-z|0-9].*?[&|$]')
        self.ip_regex = re.compile(r'\.\d{1,3}\.\d{1,3}\.')
        self.ip_dom_regex = re.compile(r'-\d{1,3}-\d{1,3}-')
        self.user_regex = re.compile(r'-User=[a-z|0-9].*?[&|$]')

        self.DEBUG_MAP = {self.DEBUG_DEBUG: 'debug',
                          self.DEBUG_DEBUGPLUS: 'debug+',
                          self.LOG_ERROR: 'error'}

    def get_name(self, level):
        return self.DEBUG_MAP[level]

    def error(self, message, no_privacy=False):
        return self.__print_message(message, 9, no_privacy)

    def debug(self, message, no_privacy=False):
        return self.__print_message(message, 0, no_privacy)

    def debugplus(self, message, no_privacy=False):
        return self.__print_message(message, 1, no_privacy)

    def __print_message(self, msg, level=0, no_privacy=False):
        if not isinstance(msg, string_types):
            try:
                msg = str(msg)
            except:
                level = self.LOG_ERROR
                msg = 'Logging failed to coerce \'%s\' message' % type(msg)

        try:
            tag = ''
            msg = encode_utf8(msg)
        except UnicodeDecodeError:
            msg = decode_utf8(msg)
            msg = msg.encode('ascii', 'ignore')
            tag = ' [ASCII]'
        except:
            tag = ' [NONUTF8]'

        if self.privacy and not no_privacy:
            try:
                msg = self.token_regex.sub('X-Plex-Token=XXXXXXXXXX&', msg)
                msg = self.ip_regex.sub('.X.X.', msg)
                msg = self.ip_dom_regex.sub('-X-X-', msg)
                msg = self.user_regex.sub('X-Plex-User=XXXXXXX&', msg)
            except:
                msg = 'Logging failure:\n%s' % traceback.format_exc()

        if self.level >= level or level == self.LOG_ERROR:
            log_level = xbmc.LOGERROR if level == self.LOG_ERROR else xbmc.LOGDEBUG
            try:
                xbmc.log('%s%s -> %s : %s%s' %
                         (self.main, self.sub, inspect.stack(0)[2][3], msg, tag), log_level)
            except:
                msg = 'Logging failure:\n%s' % traceback.format_exc()
                xbmc.log('%s%s -> %s : %s%s' %
                         (self.main, self.sub, inspect.stack(0)[2][3], msg, tag), log_level)

    def __call__(self, msg, level=0):
        return self.__print_message(msg, level)


def decode_utf8(string):
    try:
        return string.decode('utf-8')
    except AttributeError:
        return string


def encode_utf8(string, py2_only=True):
    if py2_only and PY3:
        return string
    return string.encode('utf-8')


def i18n(string_id):
    mapped_string_id = strings.get(string_id)
    if mapped_string_id:
        string_id = mapped_string_id

    try:
        core = int(string_id) < 30000
    except ValueError:
        return string_id

    if core:
        return encode_utf8(xbmc.getLocalizedString(string_id))
    else:
        return encode_utf8(__addon.getLocalizedString(string_id))


def get_device():
    try:
        return platform.system()
    except:
        try:
            return platform.platform(terse=True)
        except:
            return sys.platform


def wake_servers():
    if settings.get_setting('wolon'):
        from .wol import wake_on_lan
        log_print = PrintDebug(CONFIG['name'], 'wake_servers')
        log_print.debug('Wake On LAN: true')
        for mac_address in settings.get_wakeservers():
            if mac_address:
                try:
                    log_print.debug('Waking server with MAC: %s' % mac_address)
                    wake_on_lan(mac_address)
                except ValueError:
                    log_print.debug('Incorrect MAC address format for server %s' % mac_address)
                except:
                    log_print.debug('Unknown wake on lan error')


def is_ip(address):
    """from http://www.seanelavelle.com/2012/04/16/checking-for-a-valid-ip-in-python/"""
    try:
        socket.inet_aton(address)
        ip = True
    except socket.error:
        ip = False

    return ip


def get_platform_ip():
    return xbmc.getIPAddress()


CONFIG = {'addon': __addon,
          'id': __id,
          'name': decode_utf8(__addon.getAddonInfo('name')),
          'icon': decode_utf8(__addon.getAddonInfo('icon')),
          'data_path': decode_utf8(__addon.getAddonInfo('profile')),
          'version': decode_utf8(__addon.getAddonInfo('version')),
          'device': get_device(),
          'platform': platform.uname()[0],
          'platform_version': platform.uname()[2],
          'media_path': 'special://home/addons/%s/resources/media/' %
                        decode_utf8(__addon.getAddonInfo('id')),
          'temp_path': decode_utf8(xbmc.translatePath('special://temp/%s/' %
                                                      decode_utf8(__addon.getAddonInfo('id')))),
          'required_revision': '1.0.7'}

try:
    CONFIG['kodi_version'] = int(xbmc.getInfoLabel('System.BuildVersion').split()[0].split('.')[0])
except:
    CONFIG['kodi_version'] = 0

settings = AddonSettings(__id)

MODES = __enum(
    GETCONTENT=0,
    TVSHOWS=1,
    MOVIES=2,
    ARTISTS=3,
    TVSEASONS=4,
    PLAYLIBRARY=5,
    TVEPISODES=6,
    PLEXPLUGINS=7,
    PROCESSXML=8,
    CHANNELSEARCH=9,
    CHANNELPREFS=10,
    PLAYSHELF=11,
    BASICPLAY=12,
    SHARED_MOVIES=13,
    ALBUMS=14,
    TRACKS=15,
    PHOTOS=16,
    MUSIC=17,
    VIDEOPLUGINPLAY=18,
    PLEXONLINE=19,
    CHANNELINSTALL=20,
    CHANNELVIEW=21,
    PLAYLIBRARY_TRANSCODE=23,
    DISPLAYSERVERS=22,
    MYPLEXQUEUE=24,
    SHARED_SHOWS=25,
    SHARED_MUSIC=26,
    SHARED_PHOTOS=27,
    SHARED_ALL=29,
    PLAYLISTS=30
)

STREAM_CONTROL = __enum(
    KODI='0',
    PLEX='1',
    NEVER='2'
)


def write_pickled(filename, data):
    try:
        os.makedirs(CONFIG['temp_path'])
    except:
        pass
    filename = os.path.join(CONFIG['temp_path'], filename)
    pickled_data = pickle.dumps(data, protocol=2)
    with open(filename, 'wb') as open_file:
        open_file.write(pickled_data)


def read_pickled(filename, delete_after=True):
    filename = os.path.join(CONFIG['temp_path'], filename)
    if not os.path.exists(filename):
        return None
    with open(filename, 'rb') as open_file:
        pickled_data = open_file.read()
    if delete_after:
        try:
            os.remove(filename)
        except:
            pass
    return pickle.loads(pickled_data)


def notify_all(method, data):
    next_data = json.dumps(data)
    if PY3:
        next_data = next_data.encode('utf-8')
        data = '\\"[\\"{0}\\"]\\"'.format(hexlify(next_data).decode('utf-8'))
    else:
        data = '\\"[\\"{0}\\"]\\"'.format(hexlify(next_data))
    command = 'NotifyAll(%s.SIGNAL,%s,%s)' % (CONFIG['id'], method, data)
    xbmc.executebuiltin(command)

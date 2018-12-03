import inspect
import platform
import socket
import sys
import re

import xbmc
import xbmcaddon

from six import PY3

from .settings import AddonSettings

__addon = xbmcaddon.Addon('plugin.video.bplex')


def __enum(**enums):
    return type('Enum', (), enums)


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
        self.token_regex = re.compile('-Token=[a-z|0-9].*?[&|$]')
        self.ip_regex = re.compile('\.\d{1,3}\.\d{1,3}\.')
        self.ip_dom_regex = re.compile('-\d{1,3}-\d{1,3}-')
        self.user_regex = re.compile('-User=[a-z|0-9].*?[&|$]')

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
        try:
            tag = ''
            msg = encode_utf8(msg)
        except:
            tag = ' [NONUTF8]'

        if self.privacy and not no_privacy:
            msg = self.token_regex.sub('X-Plex-Token=XXXXXXXXXX&', msg)
            msg = self.ip_regex.sub('.X.X.', msg)
            msg = self.ip_dom_regex.sub('-X-X-', msg)
            msg = self.user_regex.sub('X-Plex-User=XXXXXXX&', msg)

        if self.level >= level or level == self.LOG_ERROR:
            log_level = xbmc.LOGERROR if level == self.LOG_ERROR else xbmc.LOGDEBUG
            xbmc.log('%s%s -> %s : %s%s' % (self.main, self.sub, inspect.stack(0)[2][3], msg, tag), log_level)

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
    try:
        core = int(string_id) < 30000
    except ValueError:
        return ''

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
        log_print = PrintDebug('bPlex', 'wake_servers')
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


try:
    KODI_VERSION = int(xbmc.getInfoLabel('System.BuildVersion').split()[0].split('.')[0])
except:
    KODI_VERSION = 0

GLOBAL_SETUP = {'addon': __addon,
                'data_path': decode_utf8(__addon.getAddonInfo('profile')),
                'version': decode_utf8(__addon.getAddonInfo('version')),
                'device': get_device(),
                'platform': platform.uname()[0],
                'platform_version': platform.uname()[2],
                'media_path': 'special://home/addons/%s/resources/media/' % decode_utf8(__addon.getAddonInfo('id'))}

GENERIC_THUMBNAIL = decode_utf8(xbmc.translatePath(GLOBAL_SETUP['media_path'] + 'thumb.png'))
REQUIRED_REVISION = '1.0.7'
settings = AddonSettings('plugin.video.bplex')

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
    DELETE_REFRESH=28,
    SHARED_ALL=29,
    PLAYLISTS=30
)

SUB_AUDIO = __enum(
    KODI='0',
    PLEX='1',
    NEVER='2'
)

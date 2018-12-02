import inspect
import socket
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
        self.user_regex = re.compile('-User=[a-z|0-9].*?[&|$]')

        self.DEBUG_MAP = {self.DEBUG_DEBUG: 'debug',
                          self.DEBUG_DEBUGPLUS: 'debug+',
                          self.LOG_ERROR: 'error'}

    def get_name(self, level):
        return self.DEBUG_MAP[level]

    def error(self, message):
        return self.__print_message(message, 9)

    def debug(self, message):
        return self.__print_message(message, 0)

    def debugplus(self, message):
        return self.__print_message(message, 1)

    def __print_message(self, msg, level=0):
        if self.privacy:
            msg = self.token_regex.sub('X-Plex-Token=XXXXXXXXXX&', str(msg))
            msg = self.ip_regex.sub('.X.X.', msg)
            msg = self.user_regex.sub('X-Plex-User=XXXXXXX&', msg)

        if self.level >= level or level == self.LOG_ERROR:
            log_level = xbmc.LOGERROR if level == self.LOG_ERROR else xbmc.LOGDEBUG
            try:
                if PY3:
                    xbmc.log('%s%s -> %s : %s' % (self.main, self.sub, inspect.stack(0)[2][3], msg), log_level)
                else:
                    xbmc.log('%s%s -> %s : %s' % (self.main, self.sub, inspect.stack(0)[2][3], msg.encode('utf-8')), log_level)
            except:
                xbmc.log('%s%s -> %s : %s [NONUTF8]' % (self.main, self.sub, inspect.stack(0)[2][3], msg), log_level)

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


def get_platform():
    if xbmc.getCondVisibility('system.platform.osx'):
        return 'OSX'
    elif xbmc.getCondVisibility('system.platform.atv2'):
        return 'ATV2'
    elif xbmc.getCondVisibility('system.platform.ios'):
        return 'iOS'
    elif xbmc.getCondVisibility('system.platform.windows'):
        return 'Windows'
    elif xbmc.getCondVisibility('system.platform.linux'):
        return 'Linux/RPi'
    elif xbmc.getCondVisibility('system.platform.android'):
        return 'Linux/Android'
    return i18n(30636)


def wake_servers():
    if settings.get_setting('wolon'):
        from .wol import wake_on_lan
        log_print = PrintDebug('bPlex', 'wake_servers')
        log_print.debug('bPlex -> Wake On LAN: true')
        for mac_address in settings.get_wakeservers():
            if mac_address:
                try:
                    log_print.debug('bPlex -> Waking server with MAC: %s' % mac_address)
                    wake_on_lan(mac_address)
                except ValueError:
                    log_print.debug('bPlex -> Incorrect MAC address format for server %s' % mac_address)
                except:
                    log_print.debug('bPlex -> Unknown wake on lan error')


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
                'cache_dir': decode_utf8(xbmc.translatePath(__addon.getAddonInfo('profile') + 'cache/')),
                'cwd': decode_utf8(xbmc.translatePath(__addon.getAddonInfo('path'))),
                'version': decode_utf8(__addon.getAddonInfo('version')),
                'platform': decode_utf8(get_platform()),
                'media_dir': decode_utf8(xbmc.translatePath('special://home/addons/plugin.video.bplex/resources/media/'))}

GENERIC_THUMBNAIL = decode_utf8(xbmc.translatePath(GLOBAL_SETUP['media_dir'] + 'thumb.png'))
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

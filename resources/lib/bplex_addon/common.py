import inspect
import socket
import re

import xbmc
import xbmcaddon

from six import PY3

from .settings import AddonSettings

__addon = xbmcaddon.Addon('plugin.video.bplex')


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


def i18n(string_id):
    try:
        core = int(string_id) < 30000
    except ValueError:
        return ''

    if core:
        if PY3:
            return xbmc.getLocalizedString(string_id)
        else:
            return xbmc.getLocalizedString(string_id).encode('utf-8', 'ignore')
    else:
        if PY3:
            return __addon.getLocalizedString(string_id)
        else:
            return __addon.getLocalizedString(string_id).encode('utf-8', 'ignore')


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
    return 'Unknown'


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


def setup_python_locations():
    if PY3:
        setup = {'__addon__': __addon,
                 '__cachedir__': __addon.getAddonInfo('profile'),
                 '__cwd__': xbmc.translatePath(__addon.getAddonInfo('path')),
                 '__version__': __addon.getAddonInfo('version')}
    else:
        setup = {'__addon__': __addon,
                 '__cachedir__': __addon.getAddonInfo('profile').decode('utf-8'),
                 '__cwd__': xbmc.translatePath(__addon.getAddonInfo('path')).decode('utf-8'),
                 '__version__': __addon.getAddonInfo('version').decode('utf-8')}
    return setup


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

GLOBAL_SETUP = setup_python_locations()
GLOBAL_SETUP['platform'] = get_platform()
GENERIC_THUMBNAIL = xbmc.translatePath('special://home/addons/plugin.video.bplex/resources/media/thumb.png')
REQUIRED_REVISION = '1.0.7'
settings = AddonSettings('plugin.video.bplex')

# Get the setting from the appropriate file.
MODE_GETCONTENT = 0
MODE_TVSHOWS = 1
MODE_MOVIES = 2
MODE_ARTISTS = 3
MODE_TVSEASONS = 4
MODE_PLAYLIBRARY = 5
MODE_TVEPISODES = 6
MODE_PLEXPLUGINS = 7
MODE_PROCESSXML = 8
MODE_CHANNELSEARCH = 9
MODE_CHANNELPREFS = 10
MODE_PLAYSHELF = 11
MODE_BASICPLAY = 12
MODE_SHARED_MOVIES = 13
MODE_ALBUMS = 14
MODE_TRACKS = 15
MODE_PHOTOS = 16
MODE_MUSIC = 17
MODE_VIDEOPLUGINPLAY = 18
MODE_PLEXONLINE = 19
MODE_CHANNELINSTALL = 20
MODE_CHANNELVIEW = 21
MODE_PLAYLIBRARY_TRANSCODE = 23
MODE_DISPLAYSERVERS = 22
MODE_MYPLEXQUEUE = 24
MODE_SHARED_SHOWS = 25
MODE_SHARED_MUSIC = 26
MODE_SHARED_PHOTOS = 27
MODE_DELETE_REFRESH = 28
MODE_SHARED_ALL = 29
MODE_PLAYLISTS = 30

SUB_AUDIO_XBMC_CONTROL = '0'
SUB_AUDIO_PLEX_CONTROL = '1'
SUB_AUDIO_NEVER_SHOW = '2'

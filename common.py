import xbmc
import xbmcaddon
import inspect
import os
import sys
import socket

class printDebug:

    def __init__(self, main, sub=None):
    
        self.main=main
        if sub:
            self.sub="."+sub
        else:
            self.sub=''
            
        self.level=settings.get_debug()
        
        self.DEBUG_OFF=0
        self.DEBUG_INFO=1
        self.DEBUG_DEBUG=2
        self.DEBUG_DEBUGPLUS=3
        
        self.DEBUG_MAP={ self.DEBUG_OFF       : "off",
                         self.DEBUG_INFO      : "info",
                         self.DEBUG_DEBUG     : "debug",
                         self.DEBUG_DEBUGPLUS : "debug+"}

    def get_name(self, level):
        return self.DEBUG_MAP[level]

    def error(self):
        return self.__printDebug(message, 0)        
        
    def info(self, message):
        return self.__printDebug(message, 1)
    
    def debug(self, message):
        return self.__printDebug(message, 2)
    
    def dev(self, message):
        return self.__printDebug(message, 3)
        
    def debugplus(self, message):
        return self.__printDebug(message, 3)
  
    def __printDebug( self, msg, level=1 ):
        if self.level >= level :
            print "%s%s -> %s : %s" % (self.main, self.sub, inspect.stack(0)[2][3], msg)
        return
            
    def __call__(self, msg, level=1):
        return self.__printDebug(msg, level)

def get_platform( ):
    if xbmc.getCondVisibility('system.platform.osx'):
        return "OSX"
    elif xbmc.getCondVisibility('system.platform.atv2'):
        return "ATV2"
    elif xbmc.getCondVisibility('system.platform.ios'):
        return "iOS"
    elif xbmc.getCondVisibility('system.platform.windows'):
        return "Windows"
    elif xbmc.getCondVisibility('system.platform.linux'):
        return "Linux/RPi"
    elif xbmc.getCondVisibility('system.platform.android'): 
        return "Linux/Android"
    return "Unknown"

def wake_servers():
    if settings.get_setting('wolon'):
        from WOL import wake_on_lan
        printDebug("PleXBMC -> Wake On LAN: true")
        for servers in settings.get_wakeserver():
            if servers:
                try:
                    printDebug("PleXBMC -> Waking server with MAC: %s" % servers)
                    wake_on_lan(servers)
                except ValueError:
                    printDebug("PleXBMC -> Incorrect MAC address format for server %s" % servers)
                except:
                    printDebug("PleXBMC -> Unknown wake on lan error")

def setup_python_locations():
    setup={}
    setup['__addon__'] = xbmcaddon.Addon()
    setup['__cachedir__'] = setup['__addon__'].getAddonInfo('profile')
    setup['__cwd__']     = xbmc.translatePath(setup['__addon__'].getAddonInfo('path')).decode('utf-8')
    setup['__version__'] = setup['__addon__'].getAddonInfo('version')
    setup['__settings__'] = xbmcaddon.Addon(id='plugin.video.plexbmc')

    setup['__resources__'] = xbmc.translatePath(os.path.join(setup['__cwd__'], 'resources', 'lib'))
    sys.path.append(setup['__resources__'])
    return setup                
 
def is_ip(address):
    '''from http://www.seanelavelle.com/2012/04/16/checking-for-a-valid-ip-in-python/'''
    try:
        socket.inet_aton(address)
        ip = True
    except socket.error:
        ip = False

    return ip
 
GLOBAL_SETUP=setup_python_locations()
GLOBAL_SETUP['platform']=get_platform()
from settings import addonSettings
settings=addonSettings('plugin.video.plexbmc')
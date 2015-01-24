import xbmc
import xbmcaddon
import inspect
import os
import sys

class printDebug:

    def __init__(self, main, sub=None):
    
        self.main=main
        if sub:
            self.sub="."+sub
        else:
            self.sub=''
            
        self.level=settings.debug
        
        self.DEBUG_OFF=0
        self.DEBUG_INFO=1
        self.DEBUG_DEBUG=2
        self.DEBUG_DEBUGPLUS=3

        
    def info(self, message):
        return self.__printDebug(message, 1)
    
    def debug(self, message):
        return self.__printDebug(message, 2)
    
    def dev(self, message):
        return self.__printDebug(message, 3)
        
    def debugplus(self, message):
        return self.dev(message)
  
    def __printDebug( self, msg, level=1 ):
        if self.level >= level :
            print "%s%s -> %s : %s" % (self.main, self.sub, inspect.stack(0)[2][3], msg)
        return
            
    def __call__(self, msg, level=1):
        return self.__printDebug(msg, level)

def getPlatform( ):
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
    if settings.wolon:
        from WOL import wake_on_lan
        printDebug("PleXBMC -> Wake On LAN: true")
        for servers in settings.wakeserver:
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
    print sys.path
    return setup                
    
GLOBAL_SETUP=setup_python_locations()
from settings import addonSettings
settings=addonSettings('plugin.video.plexbmc')
    
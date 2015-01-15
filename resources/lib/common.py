from settings import addonSettings
settings=addonSettings('plugin.video.plexbmc')
import xbmc
import inspect

def printDebug( msg, level=1 ):
    if settings.debug >= level :
        print "PleXBMC -> " + inspect.stack()[1][3] + ": " + str(msg)

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

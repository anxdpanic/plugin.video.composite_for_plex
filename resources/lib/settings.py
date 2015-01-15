import os
import xbmcplugin
import xbmcgui
import xbmcaddon

class addonSettings:

    def __init__(self, name):
    
        print "PleXBMC -> Reading configuration"
        settings = xbmcaddon.Addon(name)
        
        self.debug = int(settings.getSetting('debug'))
        self.stream = settings.getSetting('streaming')
        self.secondary = settings.getSetting('secondary')
        self.streamControl = settings.getSetting('streamControl')
        self.channelview = settings.getSetting('channelview')
        self.flatten = settings.getSetting('flatten')
        self.forcedvd = settings.getSetting('forcedvd')
        self.wolon = settings.getSetting('wolon')
        self.wakeserver=[]
        if self.wolon == "true":
            for servers in range(1,12):
                self.wakeserver[servers] = settings.getSetting('wol'+str(i))
        
        self.fullres_thumbnails = settings.getSetting('fullres_thumbs')
        self.nasoverride = settings.getSetting('nasoverride')
        self.nasoverrideip = settings.getSetting('nasoverrideip')
        self.nasroot = settings.getSetting('nasroot')
        if settings.getSetting("contextreplace") == "true":
            self.contextReplace=True
        else:
            self.contextReplace=False
            
        self.skipcontext = settings.getSetting("skipcontextmenus")
        self.skipmetadata = settings.getSetting("skipmetadata")
        self.skipmediaflags = settings.getSetting("skipflags")
        self.skipimages = settings.getSetting("skipimages")
        self.transcode = self.__translate_bool_settings(settings.getSetting('transcode'))

    def dumpSettings(self):
        return self.__dict__

    def enable_transcode(self):
        self.transcode=True
        
    def disable_transcode(self):
        self.transcode=False
        
    def __translate_bool_settings(self,setting_value):
        if setting_value == "true":
            return True
        else:
            return False
        
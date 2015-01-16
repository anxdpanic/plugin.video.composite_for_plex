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
        self.secondary = self.__translate_bool_settings(settings.getSetting('secondary'))
        self.streamControl = settings.getSetting('streamControl')
        self.channelview = self.__translate_bool_settings(settings.getSetting('channelview'))
        self.flatten = settings.getSetting('flatten')
        self.forcedvd = self.__translate_bool_settings(settings.getSetting('forcedvd'))
        self.wolon = self.__translate_bool_settings(settings.getSetting('wolon'))
        self.wakeserver=[]
        if self.wolon:
            for servers in range(1,12):
                self.wakeserver.append(settings.getSetting('wol%s' % servers))
        
        self.fullres_thumbnails = self.__translate_bool_settings(settings.getSetting('fullres_thumbs'))
        self.fullres_fanart= self.__translate_bool_settings(settings.getSetting("fullres_fanart"))
        self.nasoverride = self.__translate_bool_settings(settings.getSetting('nasoverride'))
        self.nasoverrideip = settings.getSetting('nasoverrideip')
        self.nasroot = settings.getSetting('nasroot')
        self.nasuserid=settings.getSetting('nasuserid')
        self.naspass=settings.getSetting('naspass')
        self.contextReplace=self.__translate_bool_settings(settings.getSetting("contextreplace"))        
        self.skipcontext = self.__translate_bool_settings(settings.getSetting("skipcontextmenus"))
        self.skipmetadata = self.__translate_bool_settings(settings.getSetting("skipmetadata"))
        self.skipmediaflags = self.__translate_bool_settings(settings.getSetting("skipflags"))
        self.skipimages = self.__translate_bool_settings(settings.getSetting("skipimages"))
        self.transcode = self.__translate_bool_settings(settings.getSetting('transcode'))
        self.discovery = settings.getSetting('discovery')
        self.das_host = settings.getSetting('ipaddress')
        self.das_port = settings.getSetting('port')
        self.myplex_user = settings.getSetting('myplex_user')
        self.myplex_pass = settings.getSetting('myplex_pass')
        self.myplex_token= settings.getSetting('myplex_token')

        
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
        
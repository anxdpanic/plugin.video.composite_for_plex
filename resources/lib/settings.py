import os
import xbmcplugin
import xbmcgui
import xbmcaddon

class addonSettings:

    def __init__(self, name):
    
        print "PleXBMC -> Reading configuration"
        self.settings = xbmcaddon.Addon(name)
        
        self.debug = int(self.settings.getSetting('debug'))
        self.stream = self.settings.getSetting('streaming')
        self.secondary = self.__translate_bool_settings(self.settings.getSetting('secondary'))
        self.streamControl = self.settings.getSetting('streamControl')
        self.channelview = self.__translate_bool_settings(self.settings.getSetting('channelview'))
        self.flatten = self.settings.getSetting('flatten')
        self.forcedvd = self.__translate_bool_settings(self.settings.getSetting('forcedvd'))
        self.wolon = self.__translate_bool_settings(self.settings.getSetting('wolon'))
        self.wakeserver=[]
        if self.wolon:
            for servers in range(1,12):
                self.wakeserver.append(self.settings.getSetting('wol%s' % servers))
        
        self.fullres_thumbnails = self.__translate_bool_settings(self.settings.getSetting('fullres_thumbs'))
        self.fullres_fanart= self.__translate_bool_settings(self.settings.getSetting("fullres_fanart"))
        self.nasoverride = self.__translate_bool_settings(self.settings.getSetting('nasoverride'))
        self.nasoverrideip = self.settings.getSetting('nasoverrideip')
        self.nasroot = self.settings.getSetting('nasroot')
        self.nasuserid=self.settings.getSetting('nasuserid')
        self.naspass=self.settings.getSetting('naspass')
        self.contextReplace=self.__translate_bool_settings(self.settings.getSetting("contextreplace"))        
        self.skipcontext = self.__translate_bool_settings(self.settings.getSetting("skipcontextmenus"))
        self.skipmetadata = self.__translate_bool_settings(self.settings.getSetting("skipmetadata"))
        self.skipmediaflags = self.__translate_bool_settings(self.settings.getSetting("skipflags"))
        self.skipimages = self.__translate_bool_settings(self.settings.getSetting("skipimages"))
        self.transcode = self.__translate_bool_settings(self.settings.getSetting('transcode'))
        self.discovery = self.settings.getSetting('discovery')
        self.das_host = self.settings.getSetting('ipaddress')
        self.das_port = self.settings.getSetting('port')
        self.myplex_user = self.settings.getSetting('myplex_user')
        self.myplex_pass = self.settings.getSetting('myplex_pass')
        self.myplex_signedin = self.__translate_bool_settings(self.settings.getSetting('myplex_signedin'))
        self.myplex_token= self.settings.getSetting('myplex_token')
        self.cache=self.__translate_bool_settings(self.settings.getSetting('cache'))

        
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
        
    def update_token(self, value):
        print "Updating token %s" % value
        self.settings.setSetting('myplex_token','%s|%s' % (self.myplex_user,value))
        self.myplex_token = '%s|%s' % (self.myplex_user,value)
        print "Updated token %s" % self.myplex_token
    
    def signout(self):
        self.settings.setSettings('myplex_signedin','false')
        self.myplex_signedin=False
       
    def signin(self):
        self.settings.setSettings('myplex_signedin','true')
        self.myplex_signedin=True
    
    def is_signedin(self):
        return self.myplex_signedin

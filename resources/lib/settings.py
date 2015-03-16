import os
import xbmcplugin
import xbmcgui
import xbmcaddon

class addonSettings:

    def __init__(self, name):
    
        print "PleXBMC -> Reading settings configuration"
        self.settings = xbmcaddon.Addon(name)
        self.stream = self.settings.getSetting('stream')

    def openSettings(self):
        return self.settings.openSettings()
        
    def get_setting(self, name):
    
        value = self.settings.getSetting(name)
        
        if value is None or value == '':
            print "setting: %s is : %s" % (name, value)
        
        if value == "true":
            return True
        elif value == "false":
            return False
        else:
            return value
            
    def get_debug(self):
            
        if self.settings.getSetting('debug') == 'true':
            print "PLEXBMC < 3.6 debug setting detected - settings must be re-saved"
            self.settings.setSetting('debug','2')
            return 2
        elif self.settings.getSetting('debug') == 'false':
            print "PLEXBMC < 3.6 debug setting detected - settings must be re-saved"
            self.settings.setSetting('debug','1')
            return 0
        
        return int(self.settings.getSetting('debug'))
    
    def set_setting(self, name, value):
    
        if value == True:
            value = "true"
        elif value == False:
            value = "false"
        
        self.settings.setSetting(name,value)
    
    def get_wakeservers(self):
        wakeserver=[]
        for servers in range(1,12):
            wakeserver.append(self.settings.getSetting('wol%s' % servers))
        return wakeserver
        
    def get_stream(self):
        return self.stream
        
    def set_stream(self,value):
        self.stream = value
    
    def dumpSettings(self):
        return self.__dict__

    def enable_transcode(self):
        self.transcode=True
        
    def disable_transcode(self):
        self.transcode=False
                
    def update_token(self, value):
        print "Updating token %s" % value
        self.settings.setSetting('myplex_token','%s|%s' % (self.settings.getSetting('myplex_user'),value))
        print "Updated token %s" % self.myplex_token

    def update_master_server(self, value):
        print "Updating master server to%s" % value
        self.settings.setSetting('masterServer','%s' % value)
        
    def signout(self):
        self.settings.setSettings('myplex_signedin','false')
       
    def signin(self):
        self.settings.setSettings('myplex_signedin','true')
    
    def is_signedin(self):
        return self.myplex_signedin

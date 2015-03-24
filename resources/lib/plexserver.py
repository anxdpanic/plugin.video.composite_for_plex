import sys
import os
import xml.etree.ElementTree as etree
import urlparse
import urllib
import time
import uuid

from settings import addonSettings
from common import *
import requests

printDebug=printDebug("PleXBMC", "plexserver")

DEFAULT_PORT="32400"

printDebug.debug("Using Requests version for HTTP: %s" % requests.__version__)

class PlexMediaServer:


    def __init__(self, uuid=None, name=None, address=None, port=None, token=None, discovery=None, class_type='primary' ):

        self.__revision = REQUIRED_REVISION
        self.protocol="http"
        self.uuid=uuid
        self.server_name=name
        
        self.address={'address' : address, 'local' : None}
        self.port={'address' : port, 'local' : 32400}
        self.section_list=[]
        self.token=token
        self.discovery=discovery
        self.owned=1
        self.master=1
        self.class_type=class_type
        self.discovered=False
        self.offline=False
        self.user=None
        self.client_id=None
        self.device_name=None
        self.plex_home_enabled=False
        self.best_address='address'
   
    def get_revision(self):
        return self.__revision
   
    def get_details(self):
                 
        return {'serverName': self.server_name,
                'server'    : self.get_address(),
                'port'      : self.port[self.best_address],
                'discovery' : self.discovery,
                'token'     : self.token ,
                'uuid'      : self.uuid,
                'owned'     : self.owned,
                'master'    : self.master,
                'class'     : self.class_type}

    def plex_identification(self):

        headers = {'X-Plex-Device'            : 'PleXBMC' ,
                   'X-Plex-Client-Platform'   : 'KODI' ,
                   'X-Plex-Device-Name'       : self.get_device_name() ,
                   'X-Plex-Language'          : 'en',
                   'X-Plex-Model'             : 'unknown' ,
                   'X-Plex-Platform'          : 'KODI' ,
                   'X-Plex-Client-Identifier' : self.get_client_identifier() ,
                   'X-Plex-Product'           : 'PleXBMC' ,
                   'X-Plex-Platform-Version'  : GLOBAL_SETUP['platform'] ,
                   'X-Plex-Version'           : GLOBAL_SETUP['__version__']  ,
                   'X-Plex-Provides'          : "player"}
        
        if self.token is not None:
            headers['X-Plex-Token']=self.token

        if self.user is not None:
            headers['X-Plex-User']=self.user
                   
        return headers

    def get_client_identifier(self):
        if self.client_id is None:
            self.client_id = settings.get_setting('client_id')

            if not self.client_id:
                self.client_id = str(uuid.uuid4())
                settings.set_setting('client_id', self.client_id)

        return self.client_id

    def get_device_name(self):
        if self.device_name is None:
            self.device_name = settings.get_setting('devicename')
        return self.device_name
        
    def get_uuid(self):
        return self.uuid
        
    def get_name(self):
        return self.server_name

    def get_address(self):
        return self.address[self.best_address]

    def get_local_address(self):
        return self.address['local']

    def get_default_address(self):
        return self.address['address']
        
    def get_port(self):
        return self.port[self.best_address]

    def get_url_location(self):
        return '%s://%s:%s' % ( self.protocol, self.get_address(), self.port[self.best_address])
        
    def get_location(self):
        return '%s:%s' % ( self.get_address(), self.port[self.best_address])
    
    def get_token(self):
        return self.token

    def get_discovery(self):
        return self.discovery

    def add_local_address(self, address):
        self.address['local']=address

    def set_best_address(self, ipaddress):
    
        if self.address['address'] == ipaddress:
            printDebug.debug("new [%s] == existing [%s]" % (ipaddress, self.address['address']))
            self.set_best_address_external()
            return
        else:
            printDebug("new [%s] != existing [%s]" % (ipaddress, self.address['address']))
        
        if self.address['local'] == ipaddress:
            printDebug.debug("new [%s] == existing [%s]" % (ipaddress, self.address['local']))
            self.set_best_address_local()
            return
        else:
            printDebug.debug("new [%s] != existing [%s]" % (ipaddress, self.address['local']))
        
        printDebug.debu("new [%s] is unknown.  Possible uuid clash" % ipaddress)
        self.set_best_address_external()
        return
        
        
    def set_best_address_local(self):
        self.best_address='local'

    def set_best_address_external(self):
        self.best_address='address'

    def find_address_match(self, ipaddress,port):
    
        for address in ['address','local']:
            printDebug.debug("Checking [%s:%s] against [%s:%s]" % ( ipaddress,port, self.address[address], self.port[address]))
            if "%s:%s" % (ipaddress,port) == "%s:%s" %(self.address[address], self.port[address]):
                return True
        return False
        
    def set_user(self):
        return self.user

    def set_plex_home_enabled(self):
        self.plex_home_enabled=True

    def set_plex_home_disabled(self):
        self.plex_home_enabled=False

    def get_owned(self):
        return self.owned

    def get_class(self):
        return self.class_type

    def get_master(self):
        return self.master
        
    def add_address(self, address):
        self.address.append(address)
    
    def set_owned(self, value):
        self.owned=value

    def set_user(self, value):
        self.user=value

    def set_class(self, value):
        self.class_type=value

    def set_master(self, value):
        self.master=value
        
    def talk(self,url='/',refresh=False, type='get'):
    
        if not self.offline or refresh:
            printDebug.info("URL is: %s" % url)
        
            start_time=time.time()
            try:
                if type == 'get':
                    response = requests.get("%s://%s:%s%s" % (self.protocol, self.get_address(), self.port[self.best_address], url), params=self.plex_identification(), timeout=(2,60))
                elif type == 'put':
                    response = requests.put("%s://%s:%s%s" % (self.protocol, self.get_address(), self.port[self.best_address], url), params=self.plex_identification(), timeout=(2,60))                
                elif type == 'delete':
                    response = requests.delete("%s://%s:%s%s" % (self.protocol, self.get_address(), self.port[self.best_address], url), params=self.plex_identification(), timeout=(2,60))              
                self.offline=False
            except requests.exceptions.ConnectionError, e:
                printDebug.error("Server: %s is offline or uncontactable. error: %s" % (self.get_address(), e))
                self.offline=True
            except requests.exceptions.ReadTimeout, e:
                printDebug.info("Server: read timeout for %s on %s " % (self.get_address(), url))
            else:

                printDebug.debug("URL was: %s" % response.url)
                
                if response.status_code == requests.codes.ok:
                    printDebug.debug("Response: 200 OK - Encoding: %s" % response.encoding)                    
                    printDebug.debugplus("===XML===\n%s\n===XML===" % response.text.encode('utf-8'))
                    data = response.text.encode('utf-8')
                    
                    printDebug.info("DOWNLOAD: It took %.2f seconds to retrieve data from %s" % ((time.time() - start_time), self.get_address()))                   
                    return data
                elif response.status_code == requests.codes.unauthorized:
                    printDebug.debug("Response: 401 Unauthorized - Please log into myplex or check your myplex password")                                        
                    return '<?xml version="1.0" encoding="UTF-8"?><message status="unauthorized"></message>'
                else:
                    printDebug.debug("Unexpected Response: %s " % response.status_code)
                    
        return '<?xml version="1.0" encoding="UTF-8"?><message status="offline"></message>'

    def tell(self, url, refresh=False):
        return self.talk (url, refresh, type='put')
    
    def refresh(self):
        data=self.talk(refresh=True)
        
        tree=etree.fromstring(data)
        
        if tree is not None and not (tree.get('status') == 'offline' or tree.get('status') == 'unauthorized')  :
            self.server_name = tree.get('friendlyName').encode('utf-8')
            self.uuid=tree.get('machineIdentifier')
            self.owned=1
            self.master=1
            self.class_type=tree.get('serverClass','primary')
            self.plex_home_enabled=True if tree.get('multiuser') == '1' else False
            self.discovered=True
        else:
            self.discovered=False
            
    def is_offline(self):
        return self.offline

    def get_sections(self):            
        printDebug.debug("Returning sections: %s" % self.section_list)
        return self.section_list
        
    def discover_sections(self):
        for section in self.processed_xml("/library/sections"):
            self.section_list.append(plex_section(section))
        return
                
    def get_recently_added(self,section=-1,start=0,size=0):
        arguments="?unwatched=1"

        if section < 0:
            return self.processed_xml("/library/recentlyAdded%s" % arguments)    
            
        if size > 0:
            arguments="%s&X-Plex-Container-Start=%s&X-Plex-Container-Size=%s" % (arguments, start, size)
            
        return self.processed_xml("/library/sections/%s/recentlyAdded%s" % (section, arguments))
    
    def get_ondeck(self,section=-1,start=0,size=0):
    
        arguments=""

        if section < 0:
            return self.processed_xml("/library/onDeck%s" % arguments)    
            
        if size > 0:
            arguments="%s?X-Plex-Container-Start=%s&X-Plex-Container-Size=%s" % (arguments, start, size)
            
        return self.processed_xml("/library/sections/%s/onDeck%s" % (section, arguments))

    def get_server_recentlyadded(self):
        return self.get_recently_added(section=-1)
  
    def get_server_ondeck(self):
        return self.get_ondeck(section=-1)
  
    def get_channel_recentlyviewed(self):       
        return self.processed_xml("/channels/recentlyViewed") 
        
    def processed_xml(self,url):
        if url.startswith('http'):
            printDebug.debug("We have been passed a full URL. Parsing out path")
            url_parts = urlparse.urlparse(url)
            url=url_parts.path
        
            if url_parts.query:
                url="%s?%s" % (url, url_parts.query)
         
        data = self.talk(url)
        start_time=time.time()
        tree = etree.fromstring(data)
        printDebug.info("PARSE: it took %.2f seconds to parse data from %s" % ((time.time() - start_time), self.get_address()))
        return tree

    def raw_xml(self,url):
        if url.startswith('http'):
            printDebug.debug("We have been passed a full URL. Parsing out path")
            url_parts = urlparse.urlparse(url)
            url=url_parts.path
        
            if url_parts.query:
                url="%s?%s" % (url, url_parts.query)
         
        start_time=time.time()
         
        data = self.talk(url)
        
        printDebug.info("PROCESSING: it took %.2f seconds to process data from %s" % ((time.time() - start_time), self.get_address()))
        return data
        
    def is_owned(self):
        
        if self.owned == 1 or self.owned == '1':
            return True
        return False

    def is_secondary(self):
        
        if self.class_type == "secondary":
            return True
        return False

    def get_formatted_url(self, url, options={}):
    
        url_options=self.plex_identification()
        url_options.update(options)
        
        if url.startswith('http'):
            url_parts = urlparse.urlparse(url)
            url=url_parts.path
           
            if url_parts.query:
                url=url+'?'+url_parts.query
    
        location = "%s%s" % (self.get_url_location(), url)
        
        url_parts = urlparse.urlparse(location)

        query_args = urlparse.parse_qsl(url_parts.query)
        query_args += url_options.items()

        new_query_args = urllib.urlencode(query_args, True)

        return urlparse.urlunparse((url_parts.scheme, url_parts.netloc, url_parts.path, url_parts.params, new_query_args, url_parts.fragment))

    def get_fanart(self, section, width=1280, height=720):
        
        printDebug.debug("Getting fanart for %s" % section.get_title())
        
        if settings.get_setting('skipimages'):
            return ''
            
        if section.get_art().startswith('/'):
            if settings.get_setting('fullres_fanart'):
                return self.get_formatted_url(section.get_art())
            else:
                return self.get_formatted_url('/photo/:/transcode?url=%s&width=%s&height=%s' % (urllib.quote_plus("http://localhost:32400"+section.get_art()), width, height))

        return section.get_art()     

    def stop_transcode_session(self, session):
        self.talk ('/video/:/transcode/segmented/stop?session=%s' % session)
        return
   
    def report_playback_progress(self, id, time, state='playing', duration=0):      
        self.talk('/:/timeline?duration=%s&guid=com.plexapp.plugins.library&key=/library/metadata/%s&ratingKey=%s&state=%s&time=%s' % ( duration, id, id, state, time))
        return

    def mark_item_watched(self, id):
        self.talk('/:/scrobble?key=%s&identifier=com.plexapp.plugins.library' % id)
        return

    def mark_item_unwatched(self, id):
        self.talk('/:/unscrobble?key=%s&identifier=com.plexapp.plugins.library' % id)
        return

    def refresh_section(self, key):
        return self.talk('/library/sections/%s/refresh' % key)

    def get_metadata(self, id):
        return self.processed_xml('/library/metadata/%s' % id)
        
    def set_audio_stream(self, part_id, stream_id):
        return self.tell("/library/parts/%s?audioStreamID=%s" % (part_id, stream_id) )
        
    def set_subtitle_stream(self, part_id, stream_id):
        return self.tell("/library/parts/%s?subtitleStreamID=%s" % (part_id, stream_id) )

    def delete_metadata(self, id):
        return self.talk('/library/metadata/%s' % id, type='delete')
 
    def get_universal_transcode(self, url):
        #Check for myplex user, which we need to alter to a master server
        import uuid
        printDebug.debug("incoming URL is: %s" % url)
        resolution, bitrate = settings.get_setting('quality_uni').split(',')
        
        if bitrate.endswith('Mbps'):
            mVB=int(bitrate.strip().split('Mbps')[0])*1000        
        elif bitrate.endswith('Kbps'):
            mVB=bitrate.strip().split('Kbps')[0]
        elif bitrate.endswith('unlimited'):
            mVB=20000
        else:
            mVB=2000  # a catch all amount for missing data
        
        transcode_request="/video/:/transcode/universal/start.m3u8?"
        session=str(uuid.uuid4())
        quality="100"
        transcode_settings={ 'protocol' : 'hls' ,
                             'session' : session ,
                             'offset' : 0 ,
                             'videoResolution' : resolution,
                             'maxVideoBitrate' : mVB ,
                             'videoQuality' : quality ,
                             'directStream' : '1',
                             'directPlay' : '0',
                             'subtitleSize' : settings.get_setting('subSize').split('.')[0] ,
                             'audioBoost' : settings.get_setting('audioSize').split('.')[0] ,
                             'fastSeek' : '1' ,
                             'path' : "http://127.0.0.1:32400%s" % url }

        fullURL="%s%s" % (transcode_request, urllib.urlencode(transcode_settings))
        printDebug.debug("Transcoded media location URL: %s" % fullURL)
        return (session, self.get_formatted_url(fullURL, options={'X-Plex-Device' : 'Plex Home Theater'}))

    def get_legacy_transcode( self, id, url, identifier=None ):

        import uuid
        import hmac
        import hashlib
        import base64
        session=str(uuid.uuid4())
    
        #Check for myplex user, which we need to alter to a master server
        printDebug.debug("Using preferred transcoding server: %s " % self.get_name())
        printDebug.debug("incoming URL is: %s" % url)

        quality = str(int(settings.get_setting('quality_leg'))+3)
        printDebug.debug( "Transcode quality is %s" % quality)

        audioOutput=settings.get_setting("audiotype")
        if audioOutput == "0":
            audio="mp3,aac{bitrate:160000}"
        elif audioOutput == "1":
            audio="ac3{channels:6}"
        elif audioOutput == "2":
            audio="dts{channels:6}"

        baseCapability="http-live-streaming,http-mp4-streaming,http-streaming-video,http-streaming-video-1080p,http-mp4-video,http-mp4-video-1080p;videoDecoders=h264{profile:high&resolution:1080&level:51};audioDecoders=%s" % audio
        capability="X-Plex-Client-Capabilities=%s" % urllib.quote_plus(baseCapability)

        transcode_request="/video/:/transcode/segmented/start.m3u8"
        transcode_settings={ '3g' : 0 ,
                             'offset' : 0 ,
                             'quality' : quality ,
                             'session' : session ,
                             'identifier' : identifier ,
                             'httpCookie' : "" ,
                             'userAgent' : "" ,
                             'ratingKey' : id ,
                             'subtitleSize' : settings.get_setting('subSize').split('.')[0] ,
                             'audioBoost' : settings.get_setting('audioSize').split('.')[0] ,
                             'key' : "" }

        if identifier:
            transcode_target=url.split('url=')[1]
            transcode_settings['webkit']=1
        else:
            transcode_settings['identifier']="com.plexapp.plugins.library"
            transcode_settings['key']=urllib.quote_plus("%s/library/metadata/%s" % (self.get_url_location(), id))
            transcode_target=urllib.quote_plus("http://127.0.0.1:32400"+"/"+"/".join(url.split('/')[3:]))
            printDebug.debug("filestream URL is: %s" % transcode_target )

        transcode_request="%s?url=%s" % (transcode_request, transcode_target)

        for argument, value in transcode_settings.items():
                    transcode_request="%s&%s=%s" % ( transcode_request, argument, value )

        printDebug.debug("new transcode request is: %s" % transcode_request )

        now=str(int(round(time.time(),0)))

        msg = transcode_request+"@"+now
        printDebug.debug("Message to hash is %s" % msg)

        #These are the DEV API keys - may need to change them on release
        publicKey="KQMIY6GATPC63AIMC4R2"
        privateKey = base64.decodestring("k3U6GLkZOoNIoSgjDshPErvqMIFdE0xMTx8kgsrhnC0=")

        hash=hmac.new(privateKey,msg,digestmod=hashlib.sha256)

        printDebug.debug("HMAC after hash is %s" % hash.hexdigest())

        #Encode the binary hash in base64 for transmission
        token=base64.b64encode(hash.digest())

        #Send as part of URL to avoid the case sensitive header issue.
        fullURL="%s%s&X-Plex-Access-Key=%s&X-Plex-Access-Time=%s&X-Plex-Access-Code=%s&%s" % (self.get_url_location(),transcode_request, publicKey, now, urllib.quote_plus(token), capability)

        printDebug.debug("Transcoded media location URL: %s" % fullURL)

        return (session, fullURL)
     
class plex_section:

    def __init__(self, data=None):
    
        self.title = None
        self.sectionuuid = None
        self.path = None
        self.key = None
        self.art = None
        self.type = None
        self.location = "local"
    
        if data is not None:
            self.populate(data)
    
    def populate(self,data):
    
        path = data.get('key')
        if not path[0] == "/":
            path = '/library/sections/%s' % path
    
        self.title       = data.get('title', 'Unknown').encode('utf-8')
        self.sectionuuid = data.get('uuid', '')
        self.path        = path.encode('utf-8')
        self.key         = data.get('key')
        self.art         = data.get('art', '').encode('utf-8')
        self.type        = data.get('type', '')

    def get_details(self):
    
        return {'title'       : self.title,
                'sectionuuid' : self.sectionuuid,
                'path'       : self.path,
                'key'        : self.key,
                'location'   : self.local,
                'art'        : self.art,
                'type'       : self.type}
                
    def get_title(self):
        return self.title

    def get_uuid(self):
        return self.sectionuuid

    def get_path(self):
        return self.path

    def get_key(self):
        return self.key

    def get_art(self):
        return self.art

    def get_type(self):
        return self.type

    def is_show(self):
        if self.type == 'show':
            return True
        return False
    
    def is_movie(self):
        if self.type == 'movie':
            return True
        return False

    def is_artist(self):
        if self.type == 'artist':
            return True
        return False

    def is_photo(self):
        if self.type == 'photo':
            return True
        return False
                

import base64
import hashlib
import hmac
import time
import uuid
import urllib
import xml.etree.ElementTree as ETree

import requests
from six.moves.urllib_parse import urlparse
from six.moves.urllib_parse import urlunparse
from six.moves.urllib_parse import parse_qsl

from . import plexsection
from ..common import *


log_print = PrintDebug("PleXBMC", "plexserver")

DEFAULT_PORT = "32400"

log_print.debug("Using Requests version for HTTP: %s" % requests.__version__)


class PlexMediaServer:

    def __init__(self, server_uuid=None, name=None, address=None, port=32400, token=None, discovery=None, class_type='primary'):

        self.__revision = REQUIRED_REVISION
        self.protocol = "https"
        self.uuid = server_uuid
        self.server_name = name
        self.discovery = discovery
        self.local_address = []
        self.external_address = None

        if self.discovery == "myplex":
            self.external_address = '%s:%s' % (address, port)
        elif self.discovery == "discovery":
            self.local_address = ['%s:%s' % (address, port)]

        self.access_address = '%s:%s' % (address, port)

        self.section_list = []
        self.token = token
        self.owned = 1
        self.master = 1
        self.class_type = class_type
        self.discovered = False
        self.offline = False
        self.user = None
        self.client_id = None
        self.device_name = None
        self.plex_home_enabled = False
        self.best_address = 'address'
        self.plex_identification_header = None
        self.plex_identification_string = None
        self.update_identification()

    def update_identification(self):
        self.plex_identification_header = self.create_plex_identification()
        self.plex_identification_string = self.create_plex_identification_string()

    def get_revision(self):
        return self.__revision

    def get_status(self):
        if self.offline:
            return "Offline"
        elif self.access_address == self.external_address:
            return "Remote"
        elif self.access_address in self.local_address:
            return "Nearby"
        else:
            return "Unknown"

    def get_details(self):

        return {'serverName': self.server_name,
                'server': self.get_address(),
                'port': self.get_port(),
                'discovery': self.discovery,
                'token': self.token,
                'uuid': self.uuid,
                'owned': self.owned,
                'master': self.master,
                'class': self.class_type}

    def create_plex_identification(self):

        headers = {'X-Plex-Device': 'PleXBMC',
                   'X-Plex-Client-Platform': 'KODI',
                   'X-Plex-Device-Name': self.get_device_name(),
                   'X-Plex-Language': 'en',
                   'X-Plex-Model': 'unknown',
                   'X-Plex-Platform': 'KODI',
                   'X-Plex-Client-Identifier': self.get_client_identifier(),
                   'X-Plex-Product': 'PleXBMC',
                   'X-Plex-Platform-Version': GLOBAL_SETUP['platform'],
                   'X-Plex-Version': GLOBAL_SETUP['__version__'],
                   'X-Plex-Provides': "player"}

        if self.token is not None:
            headers['X-Plex-Token'] = self.token

        if self.user is not None:
            headers['X-Plex-User'] = self.user

        return headers

    def create_plex_identification_string(self):
        header = []
        for key, value in self.create_plex_identification().items():
            header.append("%s=%s" % (key, urllib.quote(value)))

        return "&".join(header)

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
        return self.access_address.split(':')[0]

    def get_port(self):
        return self.access_address.split(':')[1]

    def get_location(self):
        return self.get_access_address()

    def get_access_address(self):
        return self.access_address

    def get_url_location(self):
        return '%s://%s' % (self.protocol, self.access_address)

    def get_token(self):
        return self.token

    def get_discovery(self):
        return self.discovery

    def is_secure(self):
        if self.protocol == 'https':
            return True
        return False

    def find_address_match(self, ipaddress, port):
        log_print.debug("Checking [%s:%s] against [%s]" % (ipaddress, port, self.access_address))
        if "%s:%s" % (ipaddress, port) == self.access_address:
            return True

        log_print.debug("Checking [%s:%s] against [%s]" % (ipaddress, port, self.external_address))
        if "%s:%s" % (ipaddress, port) == self.external_address:
            return True

        for test_address in self.local_address:
            log_print.debug("Checking [%s:%s] against [%s:%s]" % (ipaddress, port, ipaddress, 32400))
            if "%s:%s" % (ipaddress, port) == "%s:%s" % (test_address, 32400):
                return True

        return False

    def get_user(self):
        return self.user

    def get_owned(self):
        return self.owned

    def get_class(self):
        return self.class_type

    def get_master(self):
        return self.master

    # Set and add functions:

    def set_uuid(self, _uuid):
        self.uuid = _uuid

    def set_owned(self, value):
        self.owned = int(value)

    def set_token(self, value):
        self.token = value
        self.update_identification()

    def set_user(self, value):
        self.user = value
        self.update_identification()

    def set_class(self, value):
        self.class_type = value

    def set_master(self, value):
        self.master = value

    def set_protocol(self, value):
        self.protocol = value

    def set_plex_home_enabled(self):
        self.plex_home_enabled = True

    def set_plex_home_disabled(self):
        self.plex_home_enabled = False

    def add_external_connection(self, address, port):
        self.external_address = '%s:%s' % (address, port)

    def add_internal_connection(self, address, port):
        if '%s:%s' % (address, port) not in self.local_address:
            self.local_address.append('%s:%s' % (address, port))

    def add_local_address(self, address):
        self.local_address = address.split(',')

    def set_best_address(self, ipaddress=None):

        if ipaddress is None:
            log_print.debug("[%s] No address given - setting to external" % self.uuid)
            self.access_address = self.external_address
        else:

            # Ensure that ipaddress comes in an ip:port format
            if ':' not in ipaddress:
                ipaddress = '%s:%s' % (ipaddress, DEFAULT_PORT)

            if ipaddress in self.local_address:
                log_print.debug("[%s] IP address [%s] found on existing internal list.  Selecting as default" % (self.uuid, ipaddress))
                self.access_address = ipaddress
            elif ipaddress == self.external_address:
                log_print.debug("[%s] IP address [%s] found in existing external list.  selecting as default" % (self.uuid, ipaddress))
                self.access_address = self.external_address
            else:
                log_print.debug("[%s] Address [%s] is not currently on list.  Possible uuid clash?" % (self.uuid, ipaddress))

        return

    def talk(self, url='/', refresh=False, method='get'):

        if not settings.get_setting('secureconn'):
            self.set_protocol('http')
        if not self.offline or refresh:
            log_print.debug("URL is: %s using %s" % (url, self.protocol))

            start_time = time.time()
            try:
                if method == 'get':
                    response = requests.get("%s://%s:%s%s" % (self.protocol, self.get_address(), self.get_port(), url), params=self.plex_identification_header, verify=False, timeout=(2, 60))
                elif method == 'put':
                    response = requests.put("%s://%s:%s%s" % (self.protocol, self.get_address(), self.get_port(), url), params=self.plex_identification_header, verify=False, timeout=(2, 60))
                elif method == 'delete':
                    response = requests.delete("%s://%s:%s%s" % (self.protocol, self.get_address(), self.get_port(), url), params=self.plex_identification_header, verify=False, timeout=(2, 60))
                else:
                    response = None
                self.offline = False
            except requests.exceptions.ConnectionError as e:
                log_print.error("Server: %s is offline or uncontactable. error: %s" % (self.get_address(), e))

                if self.protocol == "https" and refresh:
                    log_print.debug("Server: %s - switching to http" % self.get_address())
                    self.protocol = "http"
                    return self.talk(url, refresh, method)
                else:
                    self.offline = True

            except requests.exceptions.ReadTimeout:
                log_print.debug("Server: read timeout for %s on %s " % (self.get_address(), url))
            else:

                log_print.debug("URL was: %s" % response.url)

                if response.status_code == requests.codes.ok:
                    log_print.debug("Response: 200 OK - Encoding: %s" % response.encoding)
                    log_print.debugplus("XML: \n%s" % response.text.encode('utf-8'))
                    data = response.text.encode('utf-8')

                    log_print.debug("DOWNLOAD: It took %.2f seconds to retrieve data from %s" % ((time.time() - start_time), self.get_address()))
                    return data
                elif response.status_code == requests.codes.unauthorized:
                    log_print.debug("Response: 401 Unauthorized - Please log into myplex or check your myplex password")
                    return '<?xml version="1.0" encoding="UTF-8"?><message status="unauthorized"></message>'
                else:
                    log_print.debug("Unexpected Response: %s " % response.status_code)

        return '<?xml version="1.0" encoding="UTF-8"?><message status="offline"></message>'

    def tell(self, url, refresh=False):
        return self.talk(url, refresh, method='put')

    def refresh(self):
        data = self.talk(refresh=True)

        tree = ETree.fromstring(data)

        if tree is not None and not (tree.get('status') == 'offline' or tree.get('status') == 'unauthorized'):
            self.server_name = tree.get('friendlyName').encode('utf-8')
            self.uuid = tree.get('machineIdentifier')
            self.owned = 1
            self.master = 1
            self.class_type = tree.get('serverClass', 'primary')
            self.plex_home_enabled = True if tree.get('multiuser') == '1' else False
            self.discovered = True
        else:
            self.discovered = False

    def is_offline(self):
        return self.offline

    def get_sections(self):
        log_print.debug("Returning sections: %s" % self.section_list)
        return self.section_list

    def discover_sections(self):
        for section in self.processed_xml("/library/sections"):
            self.section_list.append(plexsection.PlexSection(section))
        return

    def get_recently_added(self, section=-1, start=0, size=0, hide_watched=True):

        if hide_watched:
            arguments = "?unwatched=1"
        else:
            arguments = '?unwatched=0'

        if section < 0:
            return self.processed_xml("/library/recentlyAdded%s" % arguments)

        if size > 0:
            arguments = "%s&X-Plex-Container-Start=%s&X-Plex-Container-Size=%s" % (arguments, start, size)

        return self.processed_xml("/library/sections/%s/recentlyAdded%s" % (section, arguments))

    def get_ondeck(self, section=-1, start=0, size=0):

        arguments = ""

        if section < 0:
            return self.processed_xml("/library/onDeck%s" % arguments)

        if size > 0:
            arguments = "%s?X-Plex-Container-Start=%s&X-Plex-Container-Size=%s" % (arguments, start, size)

        return self.processed_xml("/library/sections/%s/onDeck%s" % (section, arguments))

    def get_recently_viewed_shows(self, section=-1, start=0, size=0):

        arguments = ""

        if section < 0:
            return self.processed_xml("/library/recentlyViewedShows%s" % arguments)

        if size > 0:
            arguments = "%s?X-Plex-Container-Start=%s&X-Plex-Container-Size=%s" % (arguments, start, size)

        return self.processed_xml("/library/sections/%s/recentlyViewedShows%s" % (section, arguments))

    def get_server_recentlyadded(self):
        return self.get_recently_added(section=-1)

    def get_server_ondeck(self):
        return self.get_ondeck(section=-1)

    def get_channel_recentlyviewed(self):
        return self.processed_xml("/channels/recentlyViewed")

    def processed_xml(self, url):
        if url.startswith('http'):
            log_print.debug("We have been passed a full URL. Parsing out path")
            url_parts = urlparse(url)
            url = url_parts.path

            if url_parts.query:
                url = "%s?%s" % (url, url_parts.query)

        data = self.talk(url)
        start_time = time.time()
        tree = ETree.fromstring(data)
        log_print.debug("PARSE: it took %.2f seconds to parse data from %s" % ((time.time() - start_time), self.get_address()))
        return tree

    def raw_xml(self, url):
        if url.startswith('http'):
            log_print.debug("We have been passed a full URL. Parsing out path")
            url_parts = urlparse(url)
            url = url_parts.path

            if url_parts.query:
                url = "%s?%s" % (url, url_parts.query)

        start_time = time.time()

        data = self.talk(url)

        log_print.debug("PROCESSING: it took %.2f seconds to process data from %s" % ((time.time() - start_time), self.get_address()))
        return data

    def is_owned(self):

        if self.owned == 1 or self.owned == '1':
            return True
        return False

    def is_secondary(self):

        if self.class_type == "secondary":
            return True
        return False

    def get_formatted_url(self, url, options=None):

        if options is None:
            options = {}

        url_options = self.plex_identification_header
        url_options.update(options)

        if url.startswith('http'):
            url_parts = urlparse(url)
            url = url_parts.path

            if url_parts.query:
                url = url + '?' + url_parts.query

        location = "%s%s" % (self.get_url_location(), url)

        url_parts = urlparse(location)

        query_args = parse_qsl(url_parts.query)
        query_args += url_options.items()

        new_query_args = urllib.urlencode(query_args, True)

        return urlunparse((url_parts.scheme, url_parts.netloc, url_parts.path, url_parts.params, new_query_args, url_parts.fragment))

    def get_kodi_header_formatted_url(self, url, options=None):

        if options is None:
            options = {}

        if url.startswith('http'):
            url_parts = urlparse(url)
            url = url_parts.path

            if url_parts.query:
                url = url + '?' + url_parts.query

        location = "%s%s" % (self.get_url_location(), url)

        url_parts = urlparse(location)

        query_args = parse_qsl(url_parts.query)
        query_args += options.items()

        if self.token is not None:
            query_args += {'X-Plex-Token': self.token}.items()

        new_query_args = urllib.urlencode(query_args, True)

        return "%s | %s" % (urlunparse((url_parts.scheme, url_parts.netloc, url_parts.path, url_parts.params, new_query_args, url_parts.fragment)), self.plex_identification_string)

    def get_fanart(self, section, width=1280, height=720):

        log_print.debug("Getting fanart for %s" % section.get_title())

        if settings.get_setting('skipimages'):
            return ''

        if section.get_art().startswith('/'):
            if settings.get_setting('fullres_fanart'):
                return self.get_formatted_url(section.get_art())
            else:
                return self.get_formatted_url('/photo/:/transcode?url=%s&width=%s&height=%s' % (urllib.quote_plus("http://localhost:32400" + section.get_art()), width, height))

        return section.get_art()

    def stop_transcode_session(self, session):
        self.talk('/video/:/transcode/segmented/stop?session=%s' % session)
        return

    def report_playback_progress(self, _id, _time, state='playing', duration=0):

        try:
            if state == 'stopped' and int((float(_time) / float(duration)) * 100) > 98:
                _time = duration
        except:
            pass

        self.talk('/:/timeline?duration=%s&guid=com.plexapp.plugins.library&key=/library/metadata/%s&ratingKey=%s&state=%s&time=%s' % (duration, _id, _id, state, _time))
        return

    def mark_item_watched(self, _id):
        self.talk('/:/scrobble?key=%s&identifier=com.plexapp.plugins.library' % _id)
        return

    def mark_item_unwatched(self, _id):
        self.talk('/:/unscrobble?key=%s&identifier=com.plexapp.plugins.library' % _id)
        return

    def refresh_section(self, key):
        return self.talk('/library/sections/%s/refresh' % key)

    def get_metadata(self, _id):
        return self.processed_xml('/library/metadata/%s' % _id)

    def set_audio_stream(self, part_id, stream_id):
        return self.tell("/library/parts/%s?audioStreamID=%s" % (part_id, stream_id))

    def set_subtitle_stream(self, part_id, stream_id):
        return self.tell("/library/parts/%s?subtitleStreamID=%s" % (part_id, stream_id))

    def delete_metadata(self, _id):
        return self.talk('/library/metadata/%s' % _id, method='delete')

    def get_universal_transcode(self, url):
        # Check for myplex user, which we need to alter to a master server
        log_print.debug("incoming URL is: %s" % url)
        resolution, bitrate = settings.get_setting('quality_uni').split(',')

        if bitrate.endswith('Mbps'):
            max_video_bitrate = float(bitrate.strip().split('Mbps')[0]) * 1000
        elif bitrate.endswith('Kbps'):
            max_video_bitrate = bitrate.strip().split('Kbps')[0]
        elif bitrate.endswith('unlimited'):
            max_video_bitrate = 20000
        else:
            max_video_bitrate = 2000  # a catch all amount for missing data

        transcode_request = "/video/:/transcode/universal/start.m3u8?"
        session = str(uuid.uuid4())
        quality = "100"
        transcode_settings = {'protocol': 'hls',
                              'session': session,
                              'offset': 0,
                              'videoResolution': resolution,
                              'maxVideoBitrate': max_video_bitrate,
                              'videoQuality': quality,
                              'directStream': '1',
                              'directPlay': '0',
                              'subtitleSize': settings.get_setting('subSize').split('.')[0],
                              'audioBoost': settings.get_setting('audioSize').split('.')[0],
                              'fastSeek': '1',
                              'path': "http://127.0.0.1:32400%s" % url}

        full_url = "%s%s" % (transcode_request, urllib.urlencode(transcode_settings))
        log_print.debug("Transcoded media location URL: %s" % full_url)
        return session, self.get_formatted_url(full_url, options={'X-Plex-Device': 'Plex Home Theater'})

    def get_legacy_transcode(self, _id, url, identifier=None):

        session = str(uuid.uuid4())

        # Check for myplex user, which we need to alter to a master server
        log_print.debug("Using preferred transcoding server: %s " % self.get_name())
        log_print.debug("incoming URL is: %s" % url)

        quality = str(float(settings.get_setting('quality_leg')) + 3)
        log_print.debug("Transcode quality is %s" % quality)

        audio_output = settings.get_setting("audiotype")
        if audio_output == "0":
            audio = "mp3,aac{bitrate:160000}"
        elif audio_output == "1":
            audio = "ac3{channels:6}"
        elif audio_output == "2":
            audio = "dts{channels:6}"
        else:
            audio = "mp3"

        base_capability = "http-live-streaming,http-mp4-streaming,http-streaming-video,http-streaming-video-1080p,http-mp4-video,http-mp4-video-1080p;videoDecoders=h264{profile:high&resolution:1080&level:51};audioDecoders=%s" % audio
        capability = "X-Plex-Client-Capabilities=%s" % urllib.quote_plus(base_capability)

        transcode_request = "/video/:/transcode/segmented/start.m3u8"
        transcode_settings = {'3g': 0,
                              'offset': 0,
                              'quality': quality,
                              'session': session,
                              'identifier': identifier,
                              'httpCookie': "",
                              'userAgent': "",
                              'ratingKey': _id,
                              'subtitleSize': settings.get_setting('subSize').split('.')[0],
                              'audioBoost': settings.get_setting('audioSize').split('.')[0],
                              'key': ""}

        if identifier:
            transcode_target = url.split('url=')[1]
            transcode_settings['webkit'] = 1
        else:
            transcode_settings['identifier'] = "com.plexapp.plugins.library"
            transcode_settings['key'] = urllib.quote_plus("%s/library/metadata/%s" % (self.get_url_location(), _id))
            transcode_target = urllib.quote_plus("http://127.0.0.1:32400" + "/" + "/".join(url.split('/')[3:]))
            log_print.debug("filestream URL is: %s" % transcode_target)

        transcode_request = "%s?url=%s" % (transcode_request, transcode_target)

        for argument, value in transcode_settings.items():
            transcode_request = "%s&%s=%s" % (transcode_request, argument, value)

        log_print.debug("new transcode request is: %s" % transcode_request)

        now = str(float(round(time.time(), 0)))

        msg = transcode_request + "@" + now
        log_print.debug("Message to hash is %s" % msg)

        # These are the DEV API keys - may need to change them on release
        public_key = "KQMIY6GATPC63AIMC4R2"
        private_key = base64.decodestring("k3U6GLkZOoNIoSgjDshPErvqMIFdE0xMTx8kgsrhnC0=")

        sha256_hash = hmac.new(private_key, msg, digestmod=hashlib.sha256)

        log_print.debug("HMAC after hash is %s" % sha256_hash.hexdigest())

        # Encode the binary hash in base64 for transmission
        token = base64.b64encode(sha256_hash.digest())

        # Send as part of URL to avoid the case sensitive header issue.
        full_url = "%s%s&X-Plex-Access-Key=%s&X-Plex-Access-Time=%s&X-Plex-Access-Code=%s&%s" % (self.get_url_location(), transcode_request, public_key, now, urllib.quote_plus(token), capability)

        log_print.debug("Transcoded media location URL: %s" % full_url)

        return session, full_url

import sys
import os
import xml.etree.ElementTree as etree
import base64
import resources.lib.plex.plexgdm
from resources.lib.settings import addonSettings
from resources.lib.common import *
import resources.lib.CacheControl
import requests
from resources.lib.plex.plexserver import PlexMediaServer
import urlparse
import uuid

printDebug=printDebug("PleXBMC", "plex")
DEFAULT_PORT="32400"

class Plex:

    def __init__(self, load=False):

        # Provide an interface into Plex
        self.cache= resources.lib.CacheControl.CacheControl(GLOBAL_SETUP['__cachedir__']+"cache/servers", settings.get_setting('cache'))
        self.myplex_server='https://plex.tv'
        self.myplex_user=None
        self.myplex_token=None
        self.effective_user=None
        self.effective_token=None
        self.server_list={}
        self.discovered=False
        self.server_list_cache="discovered_plex_servers.cache"
        self.plexhome_cache="plexhome_user.pcache"
        self.client_id=None
        self.user_list=dict()
        self.plexhome_settings={'myplex_signedin'      : False,
                                'plexhome_enabled'     : False,
                                'myplex_user_cache'    : '',
                                'plexhome_user_cache'  : '',
                                'plexhome_user_avatar' : '' }

        self.setup_user_token()
        if load:
            self.load()

    def is_plexhome_enabled(self):
        return self.plexhome_settings['plexhome_enabled']

    def is_myplex_signedin(self):
        return self.plexhome_settings['myplex_signedin']

    def get_myplex_user(self):
        return self.effective_user

    def get_myplex_avatar(self):
        return self.plexhome_settings['plexhome_user_avatar']

    def signout(self):
        self.plexhome_settings={'myplex_signedin'      : False,
                                'plexhome_enabled'     : False,
                                'myplex_user_cache'    : '',
                                'plexhome_user_cache'  : '',
                                'plexhome_user_avatar' : '' }

        self.delete_cache(True)
        printDebug.info("Signed out from myPlex")

    def get_signin_pin(self):
        data = self.talk_to_myplex('/pins.xml', type="post")
        try:
            xml = etree.fromstring(data)
            code=xml.find('code').text
            identifier=xml.find('id').text
        except:
            code = None
            identifier = None

        if code is None:
            printDebug.debug("Error, no code provided")
            code = "----"
            identifier="error"

        printDebug.debug("code is: %s" % code)
        printDebug.debug("id   is: %s" % identifier)

        return { 'id'   : identifier ,
                 'code' : list(code) }

    def check_signin_status(self,identifier):
        data = self.talk_to_myplex('/pins/%s.xml' % identifier, type="get2")
        xml = etree.fromstring(data)
        temp_token=xml.find('auth_token').text

        printDebug.debugplus("Temp token is: %s" % temp_token)

        if temp_token:
            response = requests.get("%s/users/account?X-Plex-Token=%s" % ( self.myplex_server, temp_token), headers=self.plex_identification())

            printDebug.debug("Status Code: %s" % response.status_code)

            if response.status_code == 200:
                try:
                    printDebug.debugplus(response.text.encode('utf-8'))
                    printDebug.info("Received new plex token")
                    xml=etree.fromstring(response.text.encode('utf-8'))
                    home=xml.get('home','0')
                    username=xml.get('username','')

                    avatar = xml.get('thumb')
                    #Required because plex.tv doesn;t return content-length and KODI requires it for cache
                    #Ifixed in KODI 15 (isengard)
                    if avatar.startswith('https://plex.tv') or avatar.startswith('http://plex.tv'):
                        avatar = avatar.replace('//','//i2.wp.com/',1)
                    self.plexhome_settings['plexhome_user_avatar']=avatar

                    if home == '1':
                        self.plexhome_settings['plexhome_enabled']=True
                        printDebug.debug("Setting PlexHome enabled.")
                    else:
                        self.plexhome_settings['plexhome_enabled']=False
                        printDebug.debug("Setting PlexHome disabled.")

                    token = xml.findtext('authentication-token')
                    self.plexhome_settings['myplex_user_cache']="%s|%s" % ( username , token)
                    self.plexhome_settings['myplex_signedin']=True
                    self.save_tokencache()
                    return True
                except:
                    printDebug.info("No authentication token found")

        return False

    def load(self):
        printDebug.info("Loading cached server list")
        data_ok, self.server_list = self.cache.checkCache(self.server_list_cache)

        if data_ok:
            if not self.check_server_version():
                printDebug.info("Refreshing for new versions")
                data_ok=False

            if not self.check_user():
                printDebug.info("User Switch, refreshing for new authorisation settings")
                data_ok=False

        if not data_ok or not len(self.server_list):
            printDebug.info("unsuccessful")
            self.server_list={}
            if not self.discover():
                self.server_list={}

        printDebug.debug("Server list is now: %s" % self.server_list)

    def setup_user_token(self):

        self.load_tokencache()

        if self.plexhome_settings['myplex_signedin']:
            printDebug.debug("Myplex is logged in")
        else:
            return

        self.myplex_user, self.myplex_token = self.plexhome_settings['myplex_user_cache'].split('|')

        if self.plexhome_settings['plexhome_enabled']:
            printDebug.debug("Plexhome is enabled")

        try:
            self.effective_user, self.effective_token = self.plexhome_settings['plexhome_user_cache'].split('|')
        except:
            printDebug.info("No user set.  Will default to admin user")
            self.effective_user = self.myplex_user
            self.effective_token = self.myplex_token
            self.save_tokencache()

        printDebug.info("myplex userid: %s" % self.myplex_user)
        printDebug.info("effective userid: %s" % self.effective_user)

    def load_tokencache(self):

        data_ok, token_cache = self.cache.readCache(self.plexhome_cache)

        if data_ok:
            try:
                if not isinstance(token_cache['myplex_signedin'], int):
                    raise
                if not isinstance(token_cache['plexhome_enabled'], int):
                    raise
                if not isinstance(token_cache['myplex_user_cache'], basestring):
                    raise
                if not isinstance(token_cache['plexhome_user_cache'], basestring):
                    raise
                if not isinstance(token_cache['plexhome_user_avatar'], basestring):
                    raise

                self.plexhome_settings = token_cache
                printDebug("plexhome_cache data loaded successfully")
            except:
                printDebug("plexhome_cache data is corrupt. Will not use.")
        else:
            printDebug.debug("plexhome cache data not loaded")

    def save_tokencache(self):
        self.cache.writeCache(self.plexhome_cache,self.plexhome_settings)

    def check_server_version(self):
        for uuid, servers in self.server_list.iteritems():
            try:
                if not servers.get_revision() == REQUIRED_REVISION:
                    printDebug.debug("Old object revision found")
                    return False
            except:
                    printDebug.debug("No revision found")
                    return False
        return True

    def check_user(self):

        if self.effective_user is None:
            return True

        for uuid, servers in self.server_list.iteritems():
            if not servers.get_user() == self.effective_user:
                printDebug.debug("authorized user mismatch")
                return False
        return True

    def discover(self):
        self.discover_all_servers()

        if self.server_list:
            self.discovered=True

        return self.discovered

    def get_server_list(self):
        return self.server_list.values()

    def plex_identification(self):
        header = {'X-Plex-Device'            : 'PleXBMC' ,
                  'X-Plex-Client-Platform'   : 'KODI' ,
                  'X-Plex-Device-Name'       : settings.get_setting('devicename') ,
                  'X-Plex-Language'          : 'en',
                  'X-Plex-Model'             : 'unknown' ,
                  'X-Plex-Platform'          : 'PleXBMC' ,
                  'X-Plex-Client-Identifier' : self.get_client_identifier() ,
                  'X-Plex-Product'           : 'PleXBMC' ,
                  'X-Plex-Platform-Version'  : GLOBAL_SETUP['platform'],
                  'X-Plex-Version'           : GLOBAL_SETUP['__version__']  ,
                  'X-Plex-Provides'          : "player"}
        if self.effective_token is not None:
            header['X-Plex-Token'] = self.effective_token

        return header

    def get_client_identifier(self):

        if self.client_id is None:
            self.client_id = settings.get_setting('client_id')

            if not self.client_id:
                self.client_id = str(uuid.uuid4())
                settings.set_setting('client_id', self.client_id)

        return self.client_id

    def talk_direct_to_server(self, ip="localhost", port=DEFAULT_PORT, url=None):
        response = requests.get("http://%s:%s%s" % (ip, port, url), params=self.plex_identification(), timeout=2)

        printDebug.debug("URL was: %s" % response.url)

        if response.status_code == requests.codes.ok:
            printDebug.debugplus("===XML===\n%s\n===XML===" % response.text)
            return response.text

    def get_processed_myplex_xml(self, url):
        data = self.talk_to_myplex (url)
        return etree.fromstring(data)

    def discover_all_servers(self):

        self.server_list = {}

        if settings.get_setting('discovery') == "1":
            printDebug.info("local GDM discovery setting enabled.")
            printDebug.info("Attempting GDM lookup on multicast")
            if settings.get_debug() >= printDebug.DEBUG_INFO:
                GDM_debug=3
            else:
                GDM_debug=0

            try:
                gdm_client = resources.lib.plex.plexgdm.plexgdm(GDM_debug)
                gdm_client.discover()
                gdm_server_name = gdm_client.getServerList()
            except Exception, e:
                print "PleXBMC -> GDM Issue [%s]" % e
            else:
                if gdm_client.discovery_complete and gdm_server_name :
                    printDebug.info("GDM discovery completed")

                    for device in gdm_server_name:
                        new_server=PlexMediaServer(name=device['serverName'],address=device['server'], port=device['port'], discovery='discovery', uuid=device['uuid'])
                        new_server.set_user(self.effective_user)
                        new_server.set_token(self.effective_token)

                        self.server_list[new_server.get_uuid()] = new_server

                else:
                    printDebug.info("GDM was not able to discover any servers")

        #Set to Disabled
        else:
            if settings.get_setting('ipaddress'):

                if not settings.get_setting('port'):
                    printDebug.info( "PleXBMC -> No port defined.  Using default of " + DEFAULT_PORT)

                printDebug.info( "PleXBMC -> Settings hostname and port: %s : %s" % ( settings.get_setting('ipaddress'), settings.get_setting('port')))

                local_server=PlexMediaServer(address=settings.get_setting('ipaddress'), port=settings.get_setting('port'), discovery='local')
                local_server.set_user(self.effective_user)
                local_server.set_token(self.effective_token)
                local_server.refresh()
                if local_server.discovered:
                    self.server_list[local_server.get_uuid()] = local_server
                else:
                    printDebug.warn("Error: Unable to discovery server %s" % settings.get_setting('ipaddress'))

        if self.is_myplex_signedin():
                printDebug.info( "PleXBMC -> Adding myplex as a server location")

                for remote_server in self.get_myplex_servers():
                    self.merge_server(remote_server)

                if self.server_list:
                    printDebug.info("MyPlex discovery completed")


        for refresh_server in self.server_list.values():
            if not refresh_server.discovered:
                refresh_server.refresh()

                if refresh_server.discovered:
                    self.server_list[refresh_server.get_uuid()]=refresh_server

        self.cache.writeCache(self.server_list_cache, self.server_list)
        printDebug.info("PleXBMC -> serverList is: %s " % self.server_list)

        return

    def get_myplex_queue(self):
        return self.get_processed_myplex_xml('/pms/playlists/queue/all')

    def get_myplex_sections(self):
        xml = self.talk_to_myplex('/pms/system/library/sections')
        if xml is False:
            return {}
        return xml

    def get_myplex_servers(self):
        tempServers = []
        xml = self.talk_to_myplex("/pms/servers")

        if xml is False:
            return {}

        server_list = etree.fromstring(xml)

        count = 0
        for server in server_list:

            myplex_server=PlexMediaServer( name = server.get('name').encode('utf-8'),
                                           address = server.get('address') ,
                                           port = server.get('port'),
                                           discovery = "myplex" ,
                                           token = server.get('accessToken'),
                                           uuid = server.get('machineIdentifier'))

            if server.get('owned') == "0":
                myplex_server.set_owned(0)

            if server.get('localAddresses') is not None:
                myplex_server.add_local_address(server.get('localAddresses'))

            myplex_server.set_user(self.effective_user)

            tempServers.append(myplex_server)
            printDebug.info("Discovered myplex server %s %s" % (myplex_server.get_name(), myplex_server.get_uuid()))

        return tempServers

    def merge_server(self, server):
        printDebug.info("merging server with uuid %s" % server.get_uuid())

        try:
            existing=self.get_server_from_uuid(server.get_uuid())
        except:
            printDebug.debug("Adding new server %s %s" % (server.get_name(), server.get_uuid()))
            server.refresh()
            if server.discovered:
                self.server_list[server.get_uuid()]=server
        else:
            printDebug.info("Found existing server %s %s" % (existing.get_name(), existing.get_uuid()))

            #existing.set_best_address(server.get_address())
            #existing.refresh()
            #self.server_list[existing.get_uuid()]=existing

        return

    def talk_to_myplex(self, path, renew=False, type='get'):
        printDebug.info("url = %s%s" % (self.myplex_server, path))
        link=False
        try:
            if type == 'get':
                response = requests.get("%s%s" % (self.myplex_server, path), params=self.plex_identification(), verify=True, timeout=(3,10))
            elif type == 'get2':
                response = requests.get("%s%s" % (self.myplex_server, path), headers=self.plex_identification(), verify=True, timeout=(3,10))
            elif type == 'post':
                response = requests.post("%s%s" % (self.myplex_server, path), data='', headers=self.plex_identification(), verify=True, timeout=(3,10))
        except requests.exceptions.ConnectionError, e:
            printDebug.error("myplex: %s is offline or uncontactable. error: %s" % (self.myplex_server, e))
            return '<?xml version="1.0" encoding="UTF-8"?><message status="error"></message>'
        except requests.exceptions.ReadTimeout, e:
            printDebug.info("myplex: read timeout for %s on %s " % (self.myplex_server, path))
            return '<?xml version="1.0" encoding="UTF-8"?><message status="error"></message>'

        else:

            printDebug.debugplus("Full URL was: %s" % response.url)
            printDebug.debugplus("Full header sent was: %s" % response.request.headers)
            printDebug.debugplus("Full header recieved was: %s" % response.headers)

            if response.status_code == 401  and not ( renew ):
                return self.talk_to_myplex(path,True)

            if response.status_code >= 400:
                error = "HTTP response error: %s" % ( response.status_code )
                print error
                if response.status_code == 404:
                    return '<?xml version="1.0" encoding="UTF-8"?><message status="unauthorized"></message>'
                else:
                    return '<?xml version="1.0" encoding="UTF-8"?><message status="error"></message>'
            else:
                link=response.text.encode('utf-8')
                printDebug.debugplus("====== XML returned =======\n%s====== XML finished ======" % link)

        return link

    def get_myplex_token(self,renew=False):

        if self.plexhome_settings['myplex_signedin']:
            return { 'X-Plex-Token' : self.effective_token }

        printDebug.debug("Myplex not in use")
        return {}

    def sign_into_myplex(self, username=None, password=None):
        printDebug.info("Getting New token")

        if username is None:
            printDebug.info("No myplex details in provided..")
            return None

        base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
        token = False

        myplex_headers={'Authorization': "Basic %s" % base64string}

        response = requests.post("%s/users/sign_in.xml" % self.myplex_server, headers=dict(self.plex_identification(), **myplex_headers))

        if response.status_code == 201:
            try:
                printDebug.debugplus(response.text.encode('utf-8'))
                printDebug.info("Received new plex token")
                xml=etree.fromstring(response.text.encode('utf-8'))
                home=xml.get('home','0')

                avatar = xml.get('thumb')
                #Required because plex.tv doesn;t return content-length and KODI requires it for cache
                #Ifixed in KODI 15 (isengard)
                if avatar.startswith('https://plex.tv') or avatar.startswith('http://plex.tv'):
                    avatar = avatar.replace('//','//i2.wp.com/',1)
                self.plexhome_settings['plexhome_user_avatar']=avatar

                if home == '1':
                    self.plexhome_settings['plexhome_enabled']=True
                    printDebug.debug("Setting PlexHome enabled.")
                else:
                    self.plexhome_settings['plexhome_enabled']=False
                    printDebug.debug("Setting PlexHome disabled.")

                token = xml.findtext('authentication-token')
                self.plexhome_settings['myplex_user_cache']="%s|%s" % ( username , token)
                self.plexhome_settings['myplex_signedin']=True
                self.save_tokencache()
            except:
                printDebug.info("No authentication token found")
        else:
            error = "HTTP response error: %s %s" % (response.status_code, response.reason)
            print error
            return None

        return token

    def get_server_from_ip(self, ip):
        printDebug.debug("IP to lookup: %s" % ip)

        if ':' in ip:
            #We probably have an IP:port being passed
            ip, port = ip.split(':')

        if not is_ip(ip):
            try:
                import socket
                ip = socket.gethostbyname(ip)
            except:
                printDebug.info("Unable to lookup hostname: %s and not an IP Address" % ip)
                return PlexMediaServer(name="dummy",address='127.0.0.1', port=32400, discovery='local')

        for server in self.server_list.values():

            printDebug.debug("[%s] - checking ip:%s against server ip %s" % (server.get_name(), ip, server.get_address()))

            if server.find_address_match(ip,port):
                return server

        printDebug.info("Unable to translate - Returning new plexserver set to %s" % ip )

        return PlexMediaServer(name="Unknown",address=ip, port=port, discovery='local')

    def get_server_from_url(self, url):
        url_parts = urlparse.urlparse(url)
        return self.get_server_from_ip(url_parts.netloc)

    def get_server_from_uuid(self, uuid):
        return self.server_list[uuid]

    def get_processed_xml(self, url):
        url_parts = urlparse.urlparse(url)
        server = self.get_server_from_ip(url_parts.netloc)

        if server:
            return server.processed_xml(url)
        return ''

    def talk_to_server(self, url):
        url_parts = urlparse.urlparse(url)
        server = self.get_server_from_ip(url_parts.netloc)

        if server:
            return server.raw_xml(url)
        return ''

    def delete_cache(self, force=False):
        return self.cache.deleteCache(force)

    def set_plex_home_users(self):

        #<User id="X" admin="1" restricted="0" protected="1" title="" username="" email="X" thumb="http://www.gravatar.com/avatar/918266bcdee2b60c447c6bbe2e2460ca?d=https%3A%2F%2Fplex.tv%2Fusers%2Fid%2Favatar"/>
        #<User id="X" admin="0" restricted="1" protected="0" title="Kids" username="" email="" thumb="https://plex.tv/users/id/avatar"/>

        data=etree.fromstring(self.talk_to_myplex('/api/home/users'))
        self.user_list=dict()
        for users in data:
            add={ 'id'         : users.get('id') ,
                  'admin'      : users.get('admin') ,
                  'restricted' : users.get('restricted') ,
                  'protected'  : users.get('protected') ,
                  'title'      : users.get('title') ,
                  'username'   : users.get('username') ,
                  'email'      : users.get('email') ,
                  'thumb'      : users.get('thumb') }
            self.user_list[users.get('id')]=add

    def get_plex_home_users(self):
        data=etree.fromstring(self.talk_to_myplex('/api/home/users'))
        self.user_list=dict()
        for users in data:
            add={ 'id'         : users.get('id') ,
                  'admin'      : users.get('admin') ,
                  'restricted' : users.get('restricted') ,
                  'protected'  : users.get('protected') ,
                  'title'      : users.get('title') ,
                  'username'   : users.get('username') ,
                  'email'      : users.get('email') ,
                  'thumb'      : users.get('thumb') }
            self.user_list[users.get('title')]=add

        return self.user_list

    def switch_plex_home_user(self,id,pin):
        if pin is None:
            pin_arg="?X-Plex-Token=%s" % self.effective_token
        else:
            pin_arg="?pin=%s&X-Plex-Token=%s" % (pin,self.effective_token)

        data = self.talk_to_myplex('/api/home/users/%s/switch%s' % (id, pin_arg), type='post')
        tree=etree.fromstring(data)

        if tree.get('status') == "unauthorized":
            return False, "Unauthorised"
        elif tree.get('status') == "error":
            return False, "Unknown error"
        else:
            username=None
            for users in self.user_list.values():
                if id == users['id']:
                    username=users['title']
                    break

            avatar = tree.get('thumb')
            #Required because plex.tv doesn;t return content-length and KODI requires it for cache
            #Ifixed in KODI 15 (isengard)
            if avatar.startswith('https://plex.tv') or avatar.startswith('http://plex.tv'):
                avatar = avatar.replace('//','//i2.wp.com/',1)
            self.plexhome_settings['plexhome_user_avatar']=avatar

            token=tree.findtext('authentication-token')
            self.plexhome_settings['plexhome_user_cache']="%s|%s" % (username,token)
            self.effective_user = username
            self.save_tokencache()
            return True,None

    def is_admin(self):
        if self.effective_user == self.myplex_user:
            return True
        return False

    def get_myplex_information(self):
        data = self.talk_to_myplex('/users/account')
        xml = etree.fromstring(data)

        result=dict()
        result['username'] = xml.get('username','unknown')
        result['email'] = xml.get('email','unknown')
        result['thumb'] = xml.get('thumb')

        subscription = xml.find('subscription')
        if subscription is not None:
            result['plexpass'] = subscription.get('plan')
        else:
            result['plexpass'] = "No Subscription"

        date= xml.find('joined-at').text
        result['membersince'] = date.split(' ')[0]

        printDebug("Gathered information: %s" % result)

        return result

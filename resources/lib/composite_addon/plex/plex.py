"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

import base64
import uuid
import socket
import traceback
import xml.etree.ElementTree as ETree

import requests
from six import PY3
from six import iteritems
from six import string_types
from six.moves.urllib_parse import urlparse

import xbmc  # pylint: disable=import-error
import xbmcgui  # pylint: disable=import-error

from ..common import CONFIG
from ..common import PrintDebug
from ..common import decode_utf8
from ..common import encode_utf8
from ..common import get_platform_ip
from ..common import i18n
from ..common import is_ip
from ..common import SETTINGS

from .. import cache_control
from .plexgdm import PlexGDM
from .plexserver import PlexMediaServer

LOG = PrintDebug(CONFIG['name'], 'plex')
DEFAULT_PORT = '32400'


class Plex:  # pylint: disable=too-many-public-methods

    def __init__(self, load=False):

        # Provide an interface into Plex
        self.cache = cache_control.CacheControl(
            decode_utf8(xbmc.translatePath(CONFIG['data_path'] + 'cache/servers')),
            SETTINGS.get_setting('cache')
        )
        self.myplex_server = 'https://plex.tv'
        self.myplex_user = None
        self.myplex_token = None
        self.effective_user = None
        self.effective_token = None
        self.server_list = {}
        self.discovered = False
        self.server_list_cache = 'discovered_plex_servers.cache'
        self.plexhome_cache = 'plexhome_user.pcache'
        self.client_id = None
        self.user_list = dict()
        self.plexhome_settings = {'myplex_signedin': False,
                                  'plexhome_enabled': False,
                                  'myplex_user_cache': '',
                                  'plexhome_user_cache': '',
                                  'plexhome_user_avatar': ''}

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
        self.plexhome_settings = {'myplex_signedin': False,
                                  'plexhome_enabled': False,
                                  'myplex_user_cache': '',
                                  'plexhome_user_cache': '',
                                  'plexhome_user_avatar': ''}

        self.delete_cache(True)
        LOG.debug('Signed out from myPlex')

    def get_signin_pin(self):
        data = self.talk_to_myplex('/pins.xml', method='post')
        try:
            xml = ETree.fromstring(data)
            code = xml.find('code').text
            identifier = xml.find('id').text
        except:  # pylint: disable=bare-except
            code = None
            identifier = None

        if code is None:
            LOG.debug('Error, no code provided')
            code = '----'
            identifier = 'error'

        LOG.debug('code is: %s' % code)
        LOG.debug('id   is: %s' % identifier)

        return {'id': identifier,
                'code': list(code)}

    def check_signin_status(self, identifier):
        data = self.talk_to_myplex('/pins/%s.xml' % identifier, method='get2')
        xml = ETree.fromstring(data)
        temp_token = xml.find('auth_token').text

        LOG.debugplus('Temp token is: %s' % temp_token)

        if temp_token:
            response = requests.get('%s/users/account?X-Plex-Token=%s' %
                                    (self.myplex_server, temp_token),
                                    headers=self.plex_identification())

            LOG.debug('Status Code: %s' % response.status_code)

            if response.status_code == 200:
                try:
                    LOG.debugplus(encode_utf8(response.text, py2_only=False))
                    LOG.debug('Received new plex token')
                    xml = ETree.fromstring(encode_utf8(response.text))
                    home = xml.get('home', '0')
                    username = xml.get('username', '')

                    avatar = xml.get('thumb')
                    # Required because plex.tv doesn;t return content-length and
                    # KODI requires it for cache
                    # fixed in KODI 15 (isengard)
                    if avatar.startswith('https://plex.tv') or avatar.startswith('http://plex.tv'):
                        avatar = avatar.replace('//', '//i2.wp.com/', 1)
                    self.plexhome_settings['plexhome_user_avatar'] = avatar

                    if home == '1':
                        self.plexhome_settings['plexhome_enabled'] = True
                        LOG.debug('Setting Plex Home enabled.')
                    else:
                        self.plexhome_settings['plexhome_enabled'] = False
                        LOG.debug('Setting Plex Home disabled.')

                    token = xml.findtext('authentication-token')
                    self.plexhome_settings['myplex_user_cache'] = '%s|%s' % (username, token)
                    self.plexhome_settings['myplex_signedin'] = True
                    self.save_tokencache()
                    return True
                except:  # pylint: disable=bare-except
                    LOG.debug('No authentication token found')

        return False

    def load(self):
        LOG.debug('Loading cached server list')

        try:
            ttl = int(SETTINGS.get_setting('cache_ttl')) * 60
        except ValueError:
            ttl = 3600

        data_ok, self.server_list = self.cache.check_cache(self.server_list_cache, ttl)

        if data_ok:
            if not self.check_server_version():
                LOG.debug('Refreshing for new versions')
                data_ok = False

            if not self.check_user():
                LOG.debug('User Switch, refreshing for new authorization settings')
                data_ok = False

        if not data_ok or not self.server_list:
            LOG.debug('unsuccessful')
            self.server_list = {}
            if not self.discover():
                self.server_list = {}

        LOG.debug('Server list is now: %s' % self.server_list)

    def setup_user_token(self):

        self.load_tokencache()

        if self.plexhome_settings['myplex_signedin']:
            LOG.debug('myPlex is logged in')
        else:
            return

        self.myplex_user, self.myplex_token = self.plexhome_settings['myplex_user_cache'].split('|')

        if self.plexhome_settings['plexhome_enabled']:
            LOG.debug('Plexhome is enabled')

        try:
            self.effective_user, self.effective_token = \
                self.plexhome_settings['plexhome_user_cache'].split('|')
        except:  # pylint: disable=bare-except
            LOG.debug('No user set.  Will default to admin user')
            self.effective_user = self.myplex_user
            self.effective_token = self.myplex_token
            self.save_tokencache()

        LOG.debug('myPlex userid: %s' % self.myplex_user)
        LOG.debug('effective userid: %s' % self.effective_user)

    def load_tokencache(self):

        data_ok, token_cache = self.cache.read_cache(self.plexhome_cache)

        if data_ok:
            try:
                if not isinstance(token_cache['myplex_signedin'], int):
                    raise TypeError
                if not isinstance(token_cache['plexhome_enabled'], int):
                    raise TypeError
                if not isinstance(token_cache['myplex_user_cache'], string_types):
                    raise TypeError
                if not isinstance(token_cache['plexhome_user_cache'], string_types):
                    raise TypeError
                if not isinstance(token_cache['plexhome_user_avatar'], string_types):
                    raise TypeError

                self.plexhome_settings = token_cache
                LOG.debug('plexhome_cache data loaded successfully')
            except:  # pylint: disable=bare-except
                LOG.debug('plexhome_cache data is corrupt. Will not use.')
        else:
            LOG.debug('plexhome cache data not loaded')

    def save_tokencache(self):
        self.cache.write_cache(self.plexhome_cache, self.plexhome_settings)

    def check_server_version(self):
        for _uuid, servers in iteritems(self.server_list):
            try:
                if not servers.get_revision() == CONFIG['required_revision']:
                    LOG.debug('Old object revision found')
                    return False
            except:  # pylint: disable=bare-except
                LOG.debug('No revision found')
                return False
        return True

    def check_user(self):

        if self.effective_user is None:
            return True

        for _uuid, servers in iteritems(self.server_list):
            if not servers.get_user() == self.effective_user:
                LOG.debug('authorized user mismatch')
                return False
        return True

    def discover(self):
        self.discover_all_servers()

        if self.server_list:
            self.discovered = True

        return self.discovered

    def get_server_list(self):
        return self.server_list.values()

    def plex_identification(self):

        header = {'X-Plex-Device': CONFIG['device'],
                  'X-Plex-Client-Platform': 'Kodi',
                  'X-Plex-Device-Name': SETTINGS.get_setting('devicename'),
                  'X-Plex-Language': 'en',
                  'X-Plex-Platform': CONFIG['platform'],
                  'X-Plex-Client-Identifier': self.get_client_identifier(),
                  'X-Plex-Product': CONFIG['name'],
                  'X-Plex-Platform-Version': CONFIG['platform_version'],
                  'X-Plex-Version': '0.0.0a1',
                  'X-Plex-Provides': 'player,controller'}

        if self.effective_token is not None:
            header['X-Plex-Token'] = self.effective_token

        return header

    def get_client_identifier(self):

        if self.client_id is None:
            self.client_id = SETTINGS.get_setting('client_id')

            if not self.client_id:
                self.client_id = str(uuid.uuid4())
                SETTINGS.set_setting('client_id', self.client_id)

        return self.client_id

    def talk_direct_to_server(self, ip_address='localhost', port=DEFAULT_PORT, url=None):
        response = requests.get('http://%s:%s%s' % (ip_address, port, url),
                                params=self.plex_identification(), timeout=2)

        LOG.debug('URL was: %s' % response.url)

        if response.status_code == requests.codes.ok:  # pylint: disable=no-member
            LOG.debugplus('XML: \n%s' % encode_utf8(response.text, py2_only=False))
            return response.text

        return ''

    def get_processed_myplex_xml(self, url):
        data = self.talk_to_myplex(url)
        return ETree.fromstring(data)

    def discover_all_servers(self):
        progress_dialog = xbmcgui.DialogProgressBG()
        progress_dialog.create(heading=CONFIG['name'] + ' ' + i18n('Server Discovery'),
                               message=i18n('Please wait...'))

        try:
            percent = 0
            self.server_list = {}
            # First discover the servers we should know about from myplex
            if self.is_myplex_signedin():
                LOG.debug('Adding myPlex as a server location')
                progress_dialog.update(percent=percent, message=i18n('myPlex discovery...'))

                self.server_list = self.get_myplex_servers()

                if self.server_list:
                    LOG.debug('MyPlex discovery completed sucecssfully')
                else:
                    LOG.debug('MyPlex discovery found no servers')

            # Now grab any local devices we can find
            if SETTINGS.get_setting('discovery') == '1':
                LOG.debug('local GDM discovery setting enabled.')
                LOG.debug('Attempting GDM lookup on multicast')
                percent += 40
                progress_dialog.update(percent=percent, message=i18n('GDM discovery...'))
                try:
                    interface_address = get_platform_ip()
                    LOG.debug('Using interface: %s for GDM discovery' % interface_address)
                except:  # pylint: disable=bare-except
                    interface_address = None
                    LOG.debug('Using systems default interface for GDM discovery')

                try:
                    gdm_client = PlexGDM(interface=interface_address)
                    gdm_client.discover()
                    gdm_server_name = gdm_client.get_server_list()
                except Exception as error:  # pylint: disable=broad-except
                    LOG.error('GDM Issue [%s]' % error)
                    traceback.print_exc()
                else:
                    if gdm_client.discovery_complete and gdm_server_name:
                        LOG.debug('GDM discovery completed')

                        for device in gdm_server_name:
                            new_server = PlexMediaServer(name=device['serverName'],
                                                         address=device['server'],
                                                         port=device['port'],
                                                         discovery='discovery',
                                                         server_uuid=device['uuid'])
                            new_server.set_user(self.effective_user)
                            new_server.set_token(self.effective_token)

                            self.merge_server(new_server)
                    else:
                        LOG.debug('GDM was not able to discover any servers')

            # Get any manually configured servers
            else:
                if SETTINGS.get_setting('ipaddress'):
                    percent += 40
                    progress_dialog.update(percent=percent, message=i18n('User provided...'))

                    port = SETTINGS.get_setting('port')
                    if not port:
                        LOG.debug('No port defined.  Using default of ' + DEFAULT_PORT)
                        port = DEFAULT_PORT

                    LOG.debug('Settings hostname and port: %s : %s' %
                              (SETTINGS.get_setting('ipaddress'), port))

                    local_server = PlexMediaServer(address=SETTINGS.get_setting('ipaddress'),
                                                   port=port, discovery='local')
                    local_server.set_user(self.effective_user)
                    local_server.set_token(self.effective_token)
                    local_server.refresh()
                    if local_server.discovered:
                        self.merge_server(local_server)
                    else:
                        LOG.error('Error: Unable to discover server %s' %
                                  SETTINGS.get_setting('ipaddress'))

            percent += 40
            progress_dialog.update(percent=percent, message=i18n('Caching results...'))
            self.cache.write_cache(self.server_list_cache, self.server_list)

            servers = [(self.server_list[key].get_name(), key)
                       for key in list(self.server_list.keys())]
            server_names = ', '.join([server[0] for server in servers])

            LOG.debug('serverList is: %s ' % servers)
        finally:
            progress_dialog.update(percent=100, message=i18n('Finished'))
            progress_dialog.close()

        if SETTINGS.get_setting('detected_notification'):
            if server_names:
                msg = i18n('Found servers:') + ' ' + server_names
            else:
                msg = i18n('No servers found')

            xbmcgui.Dialog().notification(heading=CONFIG['name'],
                                          message=msg,
                                          icon=CONFIG['icon'],
                                          sound=False)

    def get_myplex_queue(self):
        return self.get_processed_myplex_xml('/pms/playlists/queue/all')

    def get_myplex_sections(self):
        xml = self.talk_to_myplex('/pms/system/library/sections')
        if xml is False:
            return {}
        return xml

    def get_myplex_servers(self):
        temp_servers = dict()
        xml = self.talk_to_myplex('/api/resources?includeHttps=1')

        if xml is False:
            return {}

        server_list = ETree.fromstring(xml)

        for device in server_list.findall('Device'):

            LOG.debug('[%s] Found device' % device.get('name'))

            if 'server' not in device.get('provides'):
                LOG.debug('[%s] Skipping as not a server [%s]' %
                          (device.get('name'), device.get('provides')))
                continue

            discovered_server = PlexMediaServer(name=encode_utf8(device.get('name')),
                                                discovery='myplex')
            discovered_server.set_uuid(device.get('clientIdentifier'))
            discovered_server.set_owned(device.get('owned'))
            discovered_server.set_token(device.get('accessToken'))
            discovered_server.set_user(self.effective_user)

            for connection in device.findall('Connection'):
                LOG.debug('[%s] Found server connection' % device.get('name'))

                if connection.get('local') == '0':
                    discovered_server.add_external_connection(connection.get('address'),
                                                              connection.get('port'),
                                                              connection.get('uri'))
                else:
                    discovered_server.add_internal_connection(connection.get('address'),
                                                              connection.get('port'),
                                                              connection.get('uri'))

                if connection.get('protocol') == 'http':
                    LOG.debug('[%s] Dropping back to http' % device.get('name'))
                    discovered_server.set_protocol('http')

            discovered_server.set_best_address()  # Default to external address

            temp_servers[discovered_server.get_uuid()] = discovered_server
            LOG.debug('[%s] Discovered server via myPlex: %s' %
                      (discovered_server.get_name(), discovered_server.get_uuid()))

        return temp_servers

    def merge_server(self, server):
        LOG.debug('merging server with uuid %s' % server.get_uuid())

        try:
            existing = self.get_server_from_uuid(server.get_uuid())
        except:  # pylint: disable=bare-except
            LOG.debug('Adding new server %s %s' %
                      (server.get_name(), server.get_uuid()))
            server.refresh()
            if server.discovered:
                self.server_list[server.get_uuid()] = server
        else:
            LOG.debug('Found existing server %s %s' %
                      (existing.get_name(), existing.get_uuid()))

            existing.set_best_address(server.get_access_address())
            existing.refresh()
            self.server_list[existing.get_uuid()] = existing

    def talk_to_myplex(self, path, renew=False, method='get'):
        LOG.debug('url = %s%s' % (self.myplex_server, path))

        try:
            if method == 'get':
                response = requests.get('%s%s' % (self.myplex_server, path),
                                        params=self.plex_identification(),
                                        verify=True, timeout=(3, 10))
            elif method == 'get2':
                response = requests.get('%s%s' % (self.myplex_server, path),
                                        headers=self.plex_identification(),
                                        verify=True, timeout=(3, 10))
            elif method == 'post':
                response = requests.post('%s%s' % (self.myplex_server, path), data='',
                                         headers=self.plex_identification(),
                                         verify=True, timeout=(3, 10))
            else:
                LOG.error('Unknown HTTP method requested: %s' % method)
                response = None
        except requests.exceptions.ConnectionError as error:
            LOG.error('myPlex: %s is offline or uncontactable. error: %s' %
                      (self.myplex_server, error))
            return '<?xml version="1.0" encoding="UTF-8"?><message status="error"></message>'
        except requests.exceptions.ReadTimeout:
            LOG.debug('myPlex: read timeout for %s on %s ' % (self.myplex_server, path))
            return '<?xml version="1.0" encoding="UTF-8"?><message status="error"></message>'

        else:

            LOG.debugplus('Full URL was: %s' % response.url)
            LOG.debugplus('Full header sent was: %s' % response.request.headers)
            LOG.debugplus('Full header recieved was: %s' % response.headers)

            if response.status_code == 401 and not renew:
                return self.talk_to_myplex(path, True)

            if response.status_code >= 400:
                error = 'HTTP response error: %s' % response.status_code
                LOG.error(error)
                if response.status_code == 404:
                    return '<?xml version="1.0" encoding="UTF-8"?>' \
                           '<message status="unauthorized">' \
                           '</message>'

                return '<?xml version="1.0" encoding="UTF-8"?>' \
                       '<message status="error">' \
                       '</message>'

            link = encode_utf8(response.text, py2_only=False)
            LOG.debugplus('XML: \n%s' % link)

        return link

    def get_myplex_token(self):

        if self.plexhome_settings['myplex_signedin']:
            return {'X-Plex-Token': self.effective_token}

        LOG.debug('Myplex not in use')
        return {}

    def sign_into_myplex(self, username=None, password=None):
        LOG.debug('Getting New token')

        if username is None:
            LOG.debug('No myPlex details in provided..')
            return None

        credentials = '%s:%s' % (username, password)
        if PY3:
            credentials = credentials.encode('utf-8')
            base64bytes = base64.encodebytes(credentials)
            base64string = base64bytes.decode('utf-8').replace('\n', '')
        else:
            base64string = base64.encodestring(credentials).replace('\n', '')  # pylint: disable=deprecated-method

        token = False
        myplex_headers = {'Authorization': 'Basic %s' % base64string}

        response = requests.post('%s/users/sign_in.xml' % self.myplex_server,
                                 headers=dict(self.plex_identification(), **myplex_headers))

        if response.status_code == 201:
            try:
                LOG.debugplus(encode_utf8(response.text, py2_only=False))
                LOG.debug('Received new plex token')
                xml = ETree.fromstring(encode_utf8(response.text))
                home = xml.get('home', '0')

                avatar = xml.get('thumb')
                # Required because plex.tv doesnst return content-length and
                # KODI requires it for cache
                # fixed in KODI 15 (isengard)
                if avatar.startswith('https://plex.tv') or avatar.startswith('http://plex.tv'):
                    avatar = avatar.replace('//', '//i2.wp.com/', 1)
                self.plexhome_settings['plexhome_user_avatar'] = avatar

                if home == '1':
                    self.plexhome_settings['plexhome_enabled'] = True
                    LOG.debug('Setting Plex Home enabled.')
                else:
                    self.plexhome_settings['plexhome_enabled'] = False
                    LOG.debug('Setting Plex Home disabled.')

                token = xml.findtext('authentication-token')
                self.plexhome_settings['myplex_user_cache'] = '%s|%s' % (username, token)
                self.plexhome_settings['myplex_signedin'] = True
                self.save_tokencache()
            except:  # pylint: disable=bare-except
                LOG.debug('No authentication token found')
        else:
            error = 'HTTP response error: %s %s' % (response.status_code, response.reason)
            LOG.error(error)
            return None

        return token

    def get_server_from_ip(self, uri):
        LOG.debug('IP to lookup: %s' % uri)

        if ':' in uri:
            # We probably have an address:port being passed
            uri, port = uri.split(':')
        else:
            port = 32400

        if is_ip(uri):
            LOG.debug('IP address detected - passing through')
        elif 'plex.direct' in uri:
            LOG.debug('Plex.direct name detected - attempting look up')

            address = uri.split('.')[0]
            clean_address = address.replace('-', '.')

            if is_ip(clean_address):
                uri = clean_address
            else:
                LOG.debug('Unable to clean plex.direct name')

        else:
            try:
                socket.gethostbyname(uri)
            except:  # pylint: disable=bare-except
                LOG.debug('Unable to lookup hostname: %s' % uri)
                return PlexMediaServer(name='dummy', address='127.0.0.1',
                                       port=32400, discovery='local')

        for server in self.server_list.values():

            LOG.debug('[%s] - checking ip:%s against server ip %s' %
                      (server.get_name(), uri, server.get_address()))

            if server.find_address_match(uri, port):
                return server

        LOG.debug('Unable to translate - Returning new plex server set to %s' % uri)

        return PlexMediaServer(name=i18n('Unknown'), address=uri, port=port, discovery='local')

    def get_server_from_url(self, url):
        url_parts = urlparse(url)
        return self.get_server_from_ip(url_parts.netloc)

    def get_server_from_uuid(self, _uuid):
        return self.server_list[_uuid]

    def get_processed_xml(self, url):
        url_parts = urlparse(url)
        server = self.get_server_from_ip(url_parts.netloc)

        if server:
            return server.processed_xml(url)
        return ''

    def talk_to_server(self, url):
        url_parts = urlparse(url)
        server = self.get_server_from_ip(url_parts.netloc)

        if server:
            return server.raw_xml(url)
        return ''

    def delete_cache(self, force=False):
        return self.cache.delete_cache(force)

    def set_plex_home_users(self):
        data = ETree.fromstring(self.talk_to_myplex('/api/home/users'))
        self.user_list = dict()
        for users in data:
            add = {'id': users.get('id'),
                   'admin': users.get('admin'),
                   'restricted': users.get('restricted'),
                   'protected': users.get('protected'),
                   'title': users.get('title'),
                   'username': users.get('username'),
                   'email': users.get('email'),
                   'thumb': users.get('thumb')}
            self.user_list[users.get('id')] = add

    def get_plex_home_users(self):
        data = ETree.fromstring(self.talk_to_myplex('/api/home/users'))
        self.user_list = dict()
        for users in data:
            add = {'id': users.get('id'),
                   'admin': users.get('admin'),
                   'restricted': users.get('restricted'),
                   'protected': users.get('protected'),
                   'title': users.get('title'),
                   'username': users.get('username'),
                   'email': users.get('email'),
                   'thumb': users.get('thumb')}
            self.user_list[users.get('title')] = add

        return self.user_list

    def switch_plex_home_user(self, uid, pin):
        if pin is None:
            pin_arg = '?X-Plex-Token=%s' % self.effective_token
        else:
            pin_arg = '?pin=%s&X-Plex-Token=%s' % (pin, self.effective_token)

        data = self.talk_to_myplex('/api/home/users/%s/switch%s' % (uid, pin_arg), method='post')
        tree = ETree.fromstring(data)

        if tree.get('status') == 'unauthorized':
            return False, 'Unauthorised'

        if tree.get('status') == 'error':
            return False, 'Unknown error'

        username = None
        for users in self.user_list.values():
            if uid == users['id']:
                username = users['title']
                break

        avatar = tree.get('thumb')
        # Required because plex.tv doesn;t return content-length and KODI requires it for cache
        # fixed in KODI 15 (isengard)
        if avatar.startswith('https://plex.tv') or avatar.startswith('http://plex.tv'):
            avatar = avatar.replace('//', '//i2.wp.com/', 1)
        self.plexhome_settings['plexhome_user_avatar'] = avatar

        token = tree.findtext('authentication-token')
        self.plexhome_settings['plexhome_user_cache'] = '%s|%s' % (username, token)
        self.effective_user = username
        self.save_tokencache()
        return True, None

    def is_admin(self):
        if self.effective_user == self.myplex_user:
            return True
        return False

    def get_myplex_information(self):
        data = self.talk_to_myplex('/users/account')
        xml = ETree.fromstring(data)

        result = dict()
        result['username'] = xml.get('username', 'unknown')
        result['email'] = xml.get('email', 'unknown')
        result['thumb'] = xml.get('thumb')

        subscription = xml.find('subscription')
        if subscription is not None:
            result['plexpass'] = subscription.get('plan')
        else:
            result['plexpass'] = 'No Subscription'

        try:
            date = xml.find('joined-at').text
            result['membersince'] = date.split(' ')[0]
        except:  # pylint: disable=bare-except
            result['membersince'] = i18n('Unknown')

        LOG.debug('Gathered information: %s' % result)

        return result

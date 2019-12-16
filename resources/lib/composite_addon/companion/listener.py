# -*- coding: utf-8 -*-
"""

    Copyright (C) 2013-2019 PleXBMC Helper (script.plexbmc.helper)
        by wickning1 (aka Nick Wing), hippojay (Dave Hawes-Johnson)
    Copyright (C) 2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import re
import traceback

from six.moves.BaseHTTPServer import BaseHTTPRequestHandler
from six.moves.BaseHTTPServer import HTTPServer
from six.moves.socketserver import ThreadingMixIn
from six.moves.urllib_parse import parse_qs
from six.moves.urllib_parse import urlparse

from kodi_six import xbmc  # pylint: disable=import-error

from ..addon.constants import CONFIG
from ..addon.logger import Logger
from ..addon.settings import AddonSettings
from .utils import get_ok_message
from .utils import get_platform
from .utils import get_player_ids
from .utils import get_players
from .utils import get_plex_headers
from .utils import get_xml_header
from .utils import jsonrpc
from .utils import millis_to_time

LOG = Logger()


class PlexCompanionHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def __init__(self, *args, **kwargs):
        self.server_list = []
        self.client_details = AddonSettings().companion_receiver()
        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)

    def log_message(self, format, *args):  # pylint: disable=redefined-builtin, unused-argument, no-self-use
        # I have my own logging, suppressing BaseHTTPRequestHandler's
        # LOG.debug(format % args)
        return True

    def do_HEAD(self):  # pylint: disable=invalid-name
        LOG.debug('Serving HEAD request...')
        self.answer_request(0)

    def do_GET(self):  # pylint: disable=invalid-name
        LOG.debug('Serving GET request...')
        self.answer_request(1)

    def do_OPTIONS(self):  # pylint: disable=invalid-name
        self.send_response(200)
        self.send_header('Content-Length', '0')
        self.send_header('X-Plex-Client-Identifier', self.client_details['uuid'])
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Connection', 'close')
        self.send_header('Access-Control-Max-Age', '1209600')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, DELETE, PUT, HEAD')
        self.send_header('Access-Control-Allow-Headers', 'x-plex-version, '
                                                         'x-plex-platform-version, '
                                                         'x-plex-username, '
                                                         'x-plex-client-identifier, '
                                                         'x-plex-target-client-identifier, '
                                                         'x-plex-device-name, '
                                                         'x-plex-platform, '
                                                         'x-plex-product, '
                                                         'accept, '
                                                         'x-plex-device')
        self.end_headers()
        self.wfile.close()

    def response(self, body, headers=None, code=200):
        if headers is None:
            headers = {}

        try:
            self.send_response(code)
            for key in headers:
                self.send_header(key, headers[key])
            self.send_header('Content-Length', len(body))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(body)
            self.wfile.close()
        except:  # pylint: disable=bare-except
            pass

    def answer_request(self, send_data):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        _ = send_data
        self.server_list = self.server.client.get_server_list()
        try:
            request_path = self.path[1:]
            request_path = re.sub(r'\?.*', '', request_path)
            url = urlparse(self.path)
            param_arrays = parse_qs(url.query)
            params = {}
            for key in param_arrays:
                params[key] = param_arrays[key][0]
            LOG.debug('request path is: [%s]' % (request_path,))
            LOG.debug('params are: %s' % params)
            self.server.subscription_manager.update_command_id(
                self.headers.get('X-Plex-Client-Identifier', self.client_address[0]),
                params.get('commandID', False)
            )
            if request_path == 'version':
                self.response('Remote Redirector: Running\r\nVersion: %s' % CONFIG['version'])
            elif request_path == 'verify':
                result = jsonrpc('ping')
                self.response('Kodi JSON connection test:\r\n' + result)
            elif request_path == 'resources':
                response = get_xml_header()
                response += '<MediaContainer>'
                response += '<Player'
                response += ' title="%s"' % self.client_details['name']
                response += ' protocol="plex"'
                response += ' protocolVersion="1"'
                response += ' protocolCapabilities="navigation,playback,timeline"'
                response += ' machineIdentifier="%s"' % self.client_details['uuid']
                response += ' product="%s"' % CONFIG['name']
                response += ' platform="%s"' % get_platform()
                response += ' platformVersion="%s"' % CONFIG['version']
                response += ' deviceClass="pc"'
                response += '/>'
                response += '</MediaContainer>'
                LOG.debug('crafted resources response: %s' % response)
                self.response(response, get_plex_headers())
            elif '/subscribe' in request_path:
                self.response(get_ok_message(), get_plex_headers())
                protocol = params.get('protocol', False)
                host = self.client_address[0]
                port = params.get('port', False)
                uuid = self.headers.get('X-Plex-Client-Identifier', '')
                command_id = params.get('commandID', 0)
                self.server.subscription_manager.add_subscriber(protocol, host, port,
                                                                uuid, command_id)
            elif '/poll' in request_path:
                if params.get('wait', False) == '1':
                    xbmc.sleep(950)
                command_id = params.get('commandID', 0)
                self.response(
                    re.sub(r'INSERTCOMMANDID', str(command_id),
                           self.server.subscription_manager.msg(get_players())),
                    {
                        'X-Plex-Client-Identifier': self.client_details['uuid'],
                        'Access-Control-Expose-Headers': 'X-Plex-Client-Identifier',
                        'Access-Control-Allow-Origin': '*',
                        'Content-Type': 'text/xml'
                    }
                )
            elif '/unsubscribe' in request_path:
                self.response(get_ok_message(), get_plex_headers())
                uuid = self.headers.get('X-Plex-Client-Identifier', False) or self.client_address[0]
                self.server.subscription_manager.remove_subscriber(uuid)
            elif request_path == 'player/playback/setParameters':
                self.response(get_ok_message(), get_plex_headers())
                if 'volume' in params:
                    volume = int(params['volume'])
                    LOG.debug('adjusting the volume to %s%%' % volume)
                    jsonrpc('Application.SetVolume', {
                        'volume': volume
                    })
            elif '/playMedia' in request_path:
                self.response(get_ok_message(), get_plex_headers())
                resume = params.get('viewOffset', params.get('offset', '0'))
                protocol = params.get('protocol', 'http')
                address = params.get('address', self.client_address[0])
                server = self.server.subscription_manager.get_server_by_host(address)
                port = params.get('port', server.get('port', '32400'))
                full_url = protocol + '://' + address + ':' + port + params['key']
                LOG.debug('playMedia command -> full url: %s' % full_url)
                jsonrpc('playmedia', [full_url, resume])
                self.server.subscription_manager.last_key = params['key']
                self.server.subscription_manager.server = server.get('server', 'localhost')
                self.server.subscription_manager.port = port
                self.server.subscription_manager.protocol = protocol
                self.server.subscription_manager.notify()
            elif request_path == 'player/playback/play':
                self.response(get_ok_message(), get_plex_headers())
                for player_id in get_player_ids():
                    jsonrpc('Player.PlayPause', {
                        'playerid': player_id,
                        'play': True
                    })
            elif request_path == 'player/playback/pause':
                self.response(get_ok_message(), get_plex_headers())
                for player_id in get_player_ids():
                    jsonrpc('Player.PlayPause', {
                        'playerid': player_id,
                        'play': False
                    })
            elif request_path == 'player/playback/stop':
                self.response(get_ok_message(), get_plex_headers())
                for player_id in get_player_ids():
                    jsonrpc('Player.Stop', {
                        'playerid': player_id
                    })
            elif request_path == 'player/playback/seekTo':
                self.response(get_ok_message(), get_plex_headers())
                for player_id in get_player_ids():
                    jsonrpc('Player.Seek', {
                        'playerid': player_id,
                        'value': millis_to_time(params.get('offset', 0))
                    })
                self.server.subscription_manager.notify()
            elif request_path == 'player/playback/stepForward':
                self.response(get_ok_message(), get_plex_headers())
                for player_id in get_player_ids():
                    jsonrpc('Player.Seek', {
                        'playerid': player_id,
                        'value': 'smallforward'
                    })
                self.server.subscription_manager.notify()
            elif request_path == 'player/playback/stepBack':
                self.response(get_ok_message(), get_plex_headers())
                for player_id in get_player_ids():
                    jsonrpc('Player.Seek', {
                        'playerid': player_id,
                        'value': 'smallbackward'
                    })
                self.server.subscription_manager.notify()
            elif request_path == 'player/playback/skipNext':
                self.response(get_ok_message(), get_plex_headers())
                for player_id in get_player_ids():
                    jsonrpc('Player.Seek', {
                        'playerid': player_id,
                        'value': 'bigforward'
                    })
                self.server.subscription_manager.notify()
            elif request_path == 'player/playback/skipPrevious':
                self.response(get_ok_message(), get_plex_headers())
                for player_id in get_player_ids():
                    jsonrpc('Player.Seek', {
                        'playerid': player_id,
                        'value': 'bigbackward'
                    })
                self.server.subscription_manager.notify()
            elif request_path == 'player/navigation/moveUp':
                self.response(get_ok_message(), get_plex_headers())
                jsonrpc('Input.Up')
            elif request_path == 'player/navigation/moveDown':
                self.response(get_ok_message(), get_plex_headers())
                jsonrpc('Input.Down')
            elif request_path == 'player/navigation/moveLeft':
                self.response(get_ok_message(), get_plex_headers())
                jsonrpc('Input.Left')
            elif request_path == 'player/navigation/moveRight':
                self.response(get_ok_message(), get_plex_headers())
                jsonrpc('Input.Right')
            elif request_path == 'player/navigation/select':
                self.response(get_ok_message(), get_plex_headers())
                jsonrpc('Input.Select')
            elif request_path == 'player/navigation/home':
                self.response(get_ok_message(), get_plex_headers())
                jsonrpc('Input.Home')
            elif request_path == 'player/navigation/back':
                self.response(get_ok_message(), get_plex_headers())
                jsonrpc('Input.Back')
        except:  # pylint: disable=bare-except
            LOG.debug(traceback.print_exc())


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

    def __init__(self, client, subscription_manager, *args, **kwargs):
        self.client = client
        self.subscription_manager = subscription_manager
        HTTPServer.__init__(self, *args, **kwargs)

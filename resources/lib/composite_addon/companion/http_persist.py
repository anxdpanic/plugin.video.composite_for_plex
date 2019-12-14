# -*- coding: utf-8 -*-
"""

    Copyright (C) 2013-2019 PleXBMC Helper (script.plexbmc.helper)
        by wickning1 (aka Nick Wing), hippojay (Dave Hawes-Johnson)
    Copyright (C) 2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import socket
import traceback

from six.moves import http_client

from ..addon.constants import CONFIG
from ..addon.logger import Logger

LOG = Logger(CONFIG['name'])


class RequestManager:
    def __init__(self):
        self.connections = {}

    def get_connection(self, protocol, host, port):
        connection = self.connections.get(protocol + host + str(port), False)
        if not connection:
            if protocol == 'https':
                connection = http_client.HTTPSConnection(host, port)
            else:
                connection = http_client.HTTPConnection(host, port)
            self.connections[protocol + host + str(port)] = connection
        return connection

    def close_connection(self, protocol, host, port):
        connection = self.connections.get(protocol + host + str(port), False)
        if connection and not isinstance(connection, bool):
            connection.close()
            self.connections.pop(protocol + host + str(port), None)

    def dump_connections(self):
        for connection in self.connections.values():
            connection.close()
        self.connections = {}

    def post(self, host, port, path, body, header=None, protocol='http'):  # pylint: disable=too-many-arguments
        if header is None:
            header = {}

        connection = None
        try:
            connection = self.get_connection(protocol, host, port)
            header['Connection'] = 'keep-alive'
            connection.request('POST', path, body, header)
            data = connection.getresponse()
            if int(data.status) >= 400:
                LOG.debug('HTTP response error: ' + str(data.status))
                # this should return false, but I'm hacking it since iOS returns 404 no matter what
                return data.read() or True

            return data.read() or True
        except:  # pylint: disable=bare-except
            LOG.debug('Unable to connect to %s\nReason:' % host)
            LOG.debug(traceback.print_exc())
            self.connections.pop(protocol + host + str(port), None)
            if connection:
                connection.close()
            return False

    def get_with_params(self, host, port, path, params, header=None, protocol='http'):  # pylint: disable=too-many-arguments
        if header is None:
            header = {}

        new_path = path + '?'
        pairs = []
        for key in params:
            pairs.append(str(key) + '=' + str(params[key]))
        new_path += '&'.join(pairs)
        return self.get(host, port, new_path, header, protocol)

    def get(self, host, port, path, header=None, protocol='http'):  # pylint: disable=too-many-arguments
        if header is None:
            header = {}

        connection = None
        try:
            connection = self.get_connection(protocol, host, port)
            header['Connection'] = 'keep-alive'
            connection.request('GET', path, headers=header)
            data = connection.getresponse()
            if int(data.status) >= 400:
                LOG.debug('HTTP response error: ' + str(data.status))
                result = False
            else:
                result = data.read() or True
        except socket.error as error:
            if error.errno not in [10061, 10053]:
                LOG.debug('Unable to connect to %s\nReason: %s' % (host, traceback.print_exc()))
                self.connections.pop(protocol + host + str(port), None)
            result = False
        finally:
            if connection:
                connection.close()

        return result

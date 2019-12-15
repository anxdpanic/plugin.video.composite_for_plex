# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import base64
import json
import os
import socket
import sys
import time

from six import PY3
from six.moves.urllib_parse import unquote
from six.moves import cPickle as pickle
from six.moves import range

from kodi_six import xbmc  # pylint: disable=import-error
from kodi_six import xbmcaddon  # pylint: disable=import-error
from kodi_six import xbmcgui  # pylint: disable=import-error

from .constants import COMMANDS
from .constants import CONFIG
from .logger import Logger

__ID = 'plugin.video.composite_for_plex'
__ADDON = xbmcaddon.Addon(id=__ID)

LOG = Logger()


def get_argv():
    return sys.argv


def get_handle():
    try:
        return int(get_argv()[1])
    except (ValueError, IndexError):
        return -1


def get_params():
    try:
        param_string = get_argv()[2]
    except IndexError:
        param_string = ''

    params = {}
    if len(param_string) >= 2:
        _params = param_string

        pairs_of_params = _params.lstrip('?').split('&')
        for idx in list(range(len(pairs_of_params))):
            split_params = pairs_of_params[idx].split('=')

            if (len(split_params)) == 2:
                params[split_params[0]] = split_params[1]
            elif (len(split_params)) == 3:
                params[split_params[0]] = split_params[1] + '=' + split_params[2]

    url = params.get('url')
    if url:
        if url.startswith('http') or url.startswith('file'):
            url = unquote(url)

    params['url'] = url
    params['command'] = _get_command_parameter(url)
    params['path_mode'] = get_plugin_url_path()

    LOG.debug('Parameters |%s| -> |%s|' % (param_string, str(params)))
    return params


def _get_command_parameter(url):
    command = None
    if url and url.startswith('cmd'):
        command = url.split(':')[1]

    if command is None:
        try:
            command = get_argv()[1]
        except:  # pylint: disable=bare-except
            pass

    try:
        _ = int(command)
        command = COMMANDS.UNSET
    except ValueError:
        pass

    return command


def get_plugin_url_path():
    plugin_url = get_argv()[0]
    path = plugin_url.replace('plugin://%s/' % CONFIG['id'], '').rstrip('/')
    if not path or (path and path.endswith('.py')):
        return None
    return path


def is_ip(address):
    """from http://www.seanelavelle.com/2012/04/16/checking-for-a-valid-ip-in-python/"""
    try:
        socket.inet_aton(address)
        return True
    except socket.error:
        return False


def get_platform_ip():
    return xbmc.getIPAddress()


def write_pickled(filename, data):
    try:
        os.makedirs(CONFIG['temp_path'])
    except:  # pylint: disable=bare-except
        pass
    filename = os.path.join(CONFIG['temp_path'], filename)
    pickled_data = pickle.dumps(data, protocol=2)
    with open(filename, 'wb') as open_file:
        open_file.write(pickled_data)


def read_pickled(filename, delete_after=True):
    filename = os.path.join(CONFIG['temp_path'], filename)
    if not os.path.exists(filename):
        return None
    with open(filename, 'rb') as open_file:
        pickled_data = open_file.read()
    if delete_after:
        try:
            os.remove(filename)
        except:  # pylint: disable=bare-except
            pass
    return pickle.loads(pickled_data)


def notify_all(method, data):
    next_data = json.dumps(data)
    if not isinstance(next_data, bytes):
        next_data = next_data.encode('utf-8')

    data = base64.b64encode(next_data)
    if PY3:
        data = data.decode('ascii')
    data = '\\"[\\"{0}\\"]\\"'.format(data)

    command = 'NotifyAll(%s.SIGNAL,%s,%s)' % (CONFIG['id'], method, data)
    xbmc.executebuiltin(command)


def jsonrpc_play(url):
    jsonrpc_request = {
        "jsonrpc": "2.0",
        "method": "player.open",
        "params": {
            "item": {
                "file": url
            }
        }
    }

    _ = xbmc.executeJSONRPC(json.dumps(jsonrpc_request))


def wait_for_busy_dialog():
    """
    Wait for busy dialogs to close, starting playback while the busy dialog is active
    could crash Kodi 18 / 19 (pre-alpha)
    """
    monitor = xbmc.Monitor()
    start_time = time.time()
    xbmc.sleep(500)

    LOG.debug('Waiting for busy dialogs to close ...')
    while (xbmcgui.getCurrentWindowDialogId() in [10138, 10160] and
           not monitor.abortRequested()):
        if monitor.waitForAbort(3):
            break

    LOG.debug('Waited %.2f for busy dialogs to close.' % (time.time() - start_time))
    return (not monitor.abortRequested() and
            xbmcgui.getCurrentWindowDialogId() not in [10138, 10160])

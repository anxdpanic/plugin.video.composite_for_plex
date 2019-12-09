# -*- coding: utf-8 -*-
"""
    Class: CacheControl

    Implementation of file based caching for python objects.
    Utilises pickle to store object data as file within the KODI virtual file system.

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

import hashlib
import time

from six import PY3
# noinspection PyPep8Naming
from six.moves import cPickle as pickle

import xbmcvfs  # pylint: disable=import-error

from .common import CONFIG
from .common import PrintDebug

LOG = PrintDebug(CONFIG['name'], 'cachecontrol')


class CacheControl:

    def __init__(self, cache_location, enabled=True):

        self.cache_location = cache_location
        self.enabled = enabled

        if self.enabled:

            delimiter = '/' if self.cache_location.find('/') > -1 else '\\'
            if self.cache_location[-1] != delimiter:
                self.cache_location += delimiter

            if not xbmcvfs.exists(self.cache_location):
                LOG.debug('CACHE [%s]: Location does not exist.  Creating' %
                          self.cache_location)
                if not xbmcvfs.mkdirs(self.cache_location):
                    LOG.debug('CACHE [%s]: Location cannot be created' %
                              self.cache_location)
                    self.cache_location = None
                    return
            LOG.debug('Running with cache location: %s' % self.cache_location)

        else:
            self.cache_location = None
            LOG.debug('Cache is disabled')

    def read_cache(self, cache_name):
        if self.cache_location is None:
            return False, None

        LOG.debug('CACHE [%s]: attempting to read' % cache_name)
        cache = xbmcvfs.File(self.cache_location + cache_name)
        try:
            if PY3:
                cache_data = cache.readBytes()
            else:
                cache_data = cache.read()
        except Exception as error:  # pylint: disable=broad-except
            LOG.debug('CACHE [%s]: read error [%s]' % (cache_name, error))
            cache_data = False
        finally:
            cache.close()

        if cache_data:
            LOG.debug('CACHE [%s]: read' % cache_name)
            LOG.debugplus('CACHE [%s]: data: [%s]' %
                          (cache_name, cache_data.decode('utf-8', 'ignore')))
            try:
                cache_object = pickle.loads(cache_data)
            except TypeError:
                return False, None
            return True, cache_object

        LOG.debug('CACHE [%s]: empty' % cache_name)
        return False, None

    def write_cache(self, cache_name, obj):

        if self.cache_location is None:
            return True

        LOG.debug('CACHE [%s]: Writing file' % cache_name)
        cache = xbmcvfs.File(self.cache_location + cache_name, 'w')
        try:
            if PY3:
                cache.write(bytearray(pickle.dumps(obj)))
            else:
                cache.write(pickle.dumps(obj))
        except Exception as error:  # pylint: disable=broad-except
            LOG.debug('CACHE [%s]: Writing error [%s]' %
                      (self.cache_location + cache_name, error))
        finally:
            cache.close()
        return True

    def is_valid(self, cache_name, ttl=3600):
        if self.cache_location is None:
            return None

        if xbmcvfs.exists(self.cache_location + cache_name):
            LOG.debug('CACHE [%s]: exists, ttl: |%s|' % (cache_name, str(ttl)))
            now = int(round(time.time(), 0))
            modified = int(xbmcvfs.Stat(self.cache_location + cache_name).st_mtime())
            LOG.debug('CACHE [%s]: mod[%s] now[%s] diff[%s]' %
                      (cache_name, modified, now, now - modified))

            if (modified < 0) or (now - modified) > ttl:
                return False

            return True

        LOG.debug('CACHE [%s]: does not exist' % cache_name)
        return None

    def check_cache(self, cache_name, ttl=3600):
        if self.cache_location is None:
            return False, None

        cache_valid = self.is_valid(cache_name, ttl)

        if cache_valid is False:
            LOG.debug('CACHE [%s]: too old, delete' % cache_name)
            if xbmcvfs.delete(self.cache_location + cache_name):
                LOG.debug('CACHE [%s]: deleted' % cache_name)
            else:
                LOG.debug('CACHE [%s]: not deleted' % cache_name)

        elif cache_valid:
            LOG.debug('CACHE [%s]: current' % cache_name)
            return self.read_cache(cache_name)

        return False, None

    def delete_cache(self, force=False):
        cache_suffix = '.cache'
        persistent_cache_suffix = '.pcache'
        dirs, file_list = xbmcvfs.listdir(self.cache_location)

        LOG.debug('List of file: [%s]' % file_list)
        LOG.debug('List of dirs: [%s]' % dirs)

        for cache_file in file_list:

            if force and persistent_cache_suffix in cache_file:
                LOG.debug('Force deletion of persistent cache file')
            elif cache_suffix not in cache_file:
                continue

            if xbmcvfs.delete(self.cache_location + cache_file):
                LOG.debug('SUCCESSFUL: removed %s' % cache_file)
            else:
                LOG.debug('UNSUCCESSFUL: did not remove %s' % cache_file)

    @staticmethod
    def sha512_cache_name(name, unique_id, data):
        if PY3:
            if not isinstance(name, bytes):
                name = name.encode('utf-8')
            if not isinstance(unique_id, bytes):
                unique_id = unique_id.encode('utf-8')
            if not isinstance(data, bytes):
                data = data.encode('utf-8')

        name_hash = hashlib.sha512()
        name_hash.update(name + unique_id + data)
        cache_name = name_hash.hexdigest()

        if isinstance(cache_name, bytes):
            cache_name = cache_name.decode('utf-8')

        return cache_name + '.cache'

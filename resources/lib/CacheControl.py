"""
Class: CacheControl

Author: Hippojay (kodex@h-jay.com)
Version: 1
Requires: Kodex/Plexbmc

Implementation of file based caching for python objects.  
Utilises pickle to store object data as file within the KODI virtual file system.
"""

import time

import xbmcvfs

from six.moves import cPickle as pickle

from .common import PrintDebug


log_print = PrintDebug("PleXBMC", "cachecontrol")


class CacheControl:

    def __init__(self, cache_location, enabled=True):

        self.cache_location = cache_location
        self.enabled = enabled

        if self.enabled:

            if self.cache_location[-1] != "/":
                self.cache_location += "/"

            if not xbmcvfs.exists(self.cache_location):
                log_print.debug("CACHE [%s]: Location does not exist.  Creating" % self.cache_location)
                if not xbmcvfs.mkdirs(self.cache_location):
                    log_print.debug("CACHE [%s]: Location cannot be created" % self.cache_location)
                    self.cache_location = None
                    return
            log_print.debug("Running with cache location: %s" % self.cache_location)

        else:
            self.cache_location = None
            log_print.debug("Cache is disabled")

    def read_cache(self, cache_name):
        if self.cache_location is None:
            return False, None

        log_print.debug("CACHE [%s]: attempting to read" % cache_name)
        try:
            cache = xbmcvfs.File(self.cache_location + cache_name)
            cachedata = cache.read()
            cache.close()
        except Exception as e:
            log_print.debug("CACHE [%s]: read error [%s]" % (cache_name, e))
            cachedata = False

        if cachedata:
            log_print.debug("CACHE [%s]: read" % cache_name)
            log_print.debugplus("CACHE [%s]: data: [%s]" % (cache_name, cachedata))
            cacheobject = pickle.loads(cachedata)
            return True, cacheobject

        log_print.debug("CACHE [%s]: empty" % cache_name)
        return False, None

    def write_cache(self, cache_name, obj):

        if self.cache_location is None:
            return True

        log_print.debug("CACHE [%s]: Writing file" % cache_name)
        try:
            cache = xbmcvfs.File(self.cache_location + cache_name, 'w')
            cache.write(pickle.dumps(obj))
            cache.close()
        except Exception as e:
            log_print.debug("CACHE [%s]: Writing error [%s]" % (self.cache_location + cache_name, e))

        return True

    def check_cache(self, cache_name, life=3600):

        if self.cache_location is None:
            return False, None

        if xbmcvfs.exists(self.cache_location + cache_name):
            log_print.debug("CACHE [%s]: exists" % cache_name)
            now = int(round(time.time(), 0))
            modified = int(xbmcvfs.Stat(self.cache_location + cache_name).st_mtime())
            log_print.debug("CACHE [%s]: mod[%s] now[%s] diff[%s]" % (cache_name, modified, now, now - modified))

            if (modified < 0) or (now - modified) > life:
                log_print.debug("CACHE [%s]: too old, delete" % cache_name)

                if xbmcvfs.delete(self.cache_location + cache_name):
                    log_print.debug("CACHE [%s]: deleted" % cache_name)
                else:
                    log_print.debug("CACHE [%s]: not deleted" % cache_name)
            else:
                log_print.debug("CACHE [%s]: current" % cache_name)

                return self.read_cache(cache_name)
        else:
            log_print.debug("CACHE [%s]: does not exist" % cache_name)

        return False, None

    def delete_cache(self, force=False):
        log_print.debug("== ENTER: deleteCache ==")
        cache_suffix = ".cache"
        persistant_cache_suffix = ".pcache"
        dirs, file_list = xbmcvfs.listdir(self.cache_location)

        log_print.debug("List of file: [%s]" % file_list)
        log_print.debug("List of dirs: [%s]" % dirs)

        for f in file_list:

            if force and persistant_cache_suffix in f:
                log_print.debug("Force deletion of persistent cache file")
            elif cache_suffix not in f:
                continue

            if xbmcvfs.delete(self.cache_location + f):
                log_print.debug("SUCCESSFUL: removed %s" % f)
            else:
                log_print.debug("UNSUCESSFUL: did not remove %s" % f)

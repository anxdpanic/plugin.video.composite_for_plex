'''
Class: CacheControl

Author: Hippojay (kodex@h-jay.com)
Version: 1
Requires: Kodex/Plexbmc

Implementation of file based caching for python objects.  
Utilises pickle to store object data as file within the KODI virtual file system.

'''

import xbmcvfs
import inspect
import time
try:
    import cPickle as pickle
except ImportError:
    import pickle

class CacheControl:

	def __init__(self, cache_location, debug=0, enabled=True):
	
		self.cache_location=cache_location
		
		self.DEBUG_OFF=0
		self.DEBUG_INFO=1
		self.DEBUG_DEBUG=2
		self.DEBUG_DEBUGPLUS=3
		
		self.debug=debug
		self.enabled=enabled

		if self.enabled:
		
			if self.cache_location[-1] != "/":
				self.cache_location+="/"

			if not xbmcvfs.exists(self.cache_location):
				if not xbmcvfs.mkdir(self.cache_location):
					self.__printDebug("CACHE [%s]: Location does not exist" % self.cache_location)
					self.cache_location=None
			self.__printDebug("Running with cache location: %s" % self.cache_location)

		else:
			self.cache_location=None
			self.__printDebug("Cache is disabled")
		
	def __printDebug(self, msg, level=1):
		if self.debug >= level:
			print "KodeX -> %s: %s" % (inspect.stack()[1][3], msg)
		
	def readCache(self, cache_name):
		if self.cache_location is None:
			return (False, None)

		self.__printDebug("CACHE [%s]: attempting to read" % cache_name)
		try:
			cache=xbmcvfs.File(self.cache_location+cache_name)
			cachedata = cache.read()
			cache.close()
		except Exception, e:
			self.__printDebug("CACHE [%s]: read error [%s]" % ( cache_name, e))
		
		if cachedata:
			self.__printDebug("CACHE [%s]: read" % cache_name)
			self.__printDebug("CACHE [%s]: data: [%s]" % ( cache_name, cachedata), level=self.DEBUG_DEBUGPLUS)
			cacheobject = pickle.loads(cachedata)
			return (True, cacheobject)

		self.__printDebug("CACHE [%s]: empty" % cache_name)
		return (False, None)

	def writeCache(self,cache_name,object):

		if self.cache_location is None:
			return True

		self.__printDebug("CACHE [%s]: Writing file" % cache_name)
		try:
			cache=xbmcvfs.File(self.cache_location+cache_name,'w')
			cache.write(pickle.dumps(object))
			cache.close()
		except Exception, e:
			self.__printDebug("CACHE [%s]: Writing error [%s]" % (self.cache_location+cache_name, e))
			
			
		return True

	def checkCache(self,cache_name, life=3600):

		if self.cache_location is None:
			return (False, None)

		if xbmcvfs.exists(self.cache_location+cache_name):
			self.__printDebug("CACHE [%s]: exists" % cache_name)
			now = int(round(time.time(),0))
			modified = int(xbmcvfs.Stat(self.cache_location+cache_name).st_mtime())
			self.__printDebug ("CACHE [%s]: mod[%s] now[%s] diff[%s]" % ( cache_name, modified, now, now - modified))

			if ( modified < 0) or ( now - modified ) > life:
				self.__printDebug("CACHE [%s]: too old, delete" % cache_name)
				
				if xbmcvfs.delete(self.cache_location+cache_name):
					self.__printDebug("CACHE [%s]: deleted" % cache_name)
				else:
					self.__printDebug("CACHE [%s]: not deleted" % cache_name)
			else:
				self.__printDebug("CACHE [%s]: current" % cache_name)

				return self.readCache(cache_name)
		else:
			self.__printDebug("CACHE [%s]: does not exist" % cache_name)

		return (False, None)
		
	def deleteCache(self):
		self.__printDebug("== ENTER: deleteCache ==")
		cache_suffix = "cache"
		dirs, files = xbmcvfs.listdir(self.cache_location)

		self.__printDebug("List of file: [%s]" % files)
		self.__printDebug("List of dirs: [%s]" % dirs)
		
		for i in files:

			if cache_suffix not in i:
				continue

			if xbmcvfs.delete(self.cache_location+i):
				self.__printDebug("SUCCESSFUL: removed %s" % i)
			else:
				self.__printDebug("UNSUCESSFUL: did not remove %s" % i )
		
import time
import types

try:
    import StorageServer
except:
    import storageserverdummy as StorageServer

class timedcache:

    def __init__ (self, table, timeout=3600):
        self.cache = StorageServer.StorageServer(table)
        self.cache.table_name = table
        self.timeout = timeout

    def store_value (self, name, value):

        expire_time = int(time.time() + self.timeout)

        type="other"
        if type(value) == types.DictType:
            value=repr(value)
            type="dict"
        
        result = { "data"       : value ,
                   "timeout"    : expire_time,
                   "value_type" : value_type } 
        self.cache.set(name, repr(result))
        return True

    def return_value (self, name ):

        result = self.cache.get(name)
        
        if not result:
            return (False, None)
        
        now = int(time.time())
        if result['timeout'] < now:
            return (True, result['data'])
        else:
            return (False, None)
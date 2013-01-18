"""

Python helper class for interfacing with Bonjour.

bonjour.py provides a simple way of advertising a service on a known registration
type and then also browses the current network to find clients of the same 
registration type.

"""

__author__ = 'Michael Carroll <carroll.michael@gmail.com>'

import pybonjour
import select
import socket
import threading
import sys
import logging

class BonjourClient():
     def __init__(self):
         self.serviceName = None
         self.hostname = None
         self.ip = None
         self.port = None
         self.resolved = False
 
     def __str__(self):
         string = "ServiceName: %s\n" % self.serviceName
         string += "Hostname:    %s\n" % self.hostname
         string += "IP:          %s\n" % self.ip
         string += "Port:        %s\n" % self.port
         return string
 
class Bonjour():
     """
     Wraps the pybonjour package to provide helper functions for registering a 
     Bonjour service and browsing the network for services matching a certain 
     regtype.
     """
     def __init__(self, name, port, regtype, debug=None, info=None, error=None):
         """
         Initialize a Bonjour object.  
 
         @type name: UTF-8 String
         @param name: The name of the service to be advertised
         @type port: 16-bit unsigned integer
         @param port: The port of the service to be advertised
         @type regtype: str
         @param regtype: An mDNS-compliant registration type.  The service type 
                         followed by the protocol, separated by a dot (e.g. "_osc.
                         _udp").  A list of service types is available at:
                         U{http://www.dns-sd.org/ServiceTypes.html}
         """
         self.debug = logging.debug
         self.info = logging.info
         self.error = logging.error
 
         if debug:
             self.debug = debug
         if error:
             self.error = error
         if info:
             self.info = info
 
         assert type(name) is str
         self.name = name
         assert type(port) is str or int
         self.port = int(port)
         assert type(regtype) is str
         self.regtype = regtype
         self.domain = "local"
         self.fullname = pybonjour.DNSServiceConstructFullName(self.name,
                                                               self.regtype,
                                                               'local.')
         # Sometimes the fullname doesn't come out with a trailing period. This 
         # will cause comparisons in the browse/resolve/query callbacks to fail.
         if not self.fullname.endswith(u'.'):
             self.fullname += u'.'
 
         self.timeout = 2
         self.queried = []
         self.resolved = []
         self._isBrowserRunning = False
         self._isRegisterRunning = False
         #: Dictionary of clients detected by the Bonjour browser.  The browser
         # will maintain a list of the clients that are currently active, and 
         # will prune clients as they leave the network.
         self.clients = dict()
         self.clientLock = threading.Lock()
         self.client_callback = None

     def getClients(self):
         """
         Get the current list of clients active on the network

         @rtype: dict
         @return: List of clients currently active on the network
         """
         with self.clientLock:
             return self.__getClients()
 
     def __getClients(self):
         returnDict = {}
         for serviceName, client in self.clients.iteritems():
             if client.resolved:
                 returnDict[serviceName] = {"servicename": serviceName,
                                            "hostname": client.hostname,
                                            "ip": client.ip,
                                            "port": client.port}
         return returnDict
 
     def setClientCallback(self, callback):
         """
         Set a callback for when clients are added/removed from the client list
         
         Callback signature is: callback(clientDict)
         """
         self.client_callback = callback
 
     def run_browser(self, daemon=False):
         """
         Run the Bonjour service browser
         """
         if not self._isBrowserRunning:
             self._isBrowserRunning = True
             self.browser_t = threading.Thread(target=self.browser)
             self.browser_t.setDaemon(daemon)
             self.browser_t.start()
 
     def stop_browser(self):
         """
         Stop the Bonjour service browser
         """
         if self._isBrowserRunning:
             self._isBrowserRunning = False
             self.browser_t.join()
             del self.browser_t
 
     def run_register(self, daemon=False):
         """
         Run the Bonjour service registration
         """
         if not self._isRegisterRunning:
             self._isRegisterRunning = True
             self.register_t = threading.Thread(target=self.register)
             self.register_t.setDaemon(daemon)
             self.register_t.start()
 
     def stop_register(self):
         """
         Stop the Bonjour service registration
         """
         if self._isRegisterRunning:
             self._isRegisterRunning = False
             self.register_t.join()
             del self.register_t
 
     def run(self, daemon=False):
         """
         Run both the worker threads for registration and browsing
         """
         self.run_browser(daemon)
         self.run_register(daemon)
 
     def shutdown(self):
         """
         Stop both the worker threads for registration and browsing
         """
         self.debug("Received shutdown signal")
         self.stop_browser()
         self.stop_register()
 
     def browser(self):
         """
         Routine for browsing the network for matching clients of type "regtype"
         """
         browse_sdRef = pybonjour.DNSServiceBrowse(regtype=self.regtype,
                                                   callBack=self.browse_callback)
         self.debug("Browser Service Started")
         try:
             try:
                 while self._isBrowserRunning:
                     ready = select.select([browse_sdRef], [], [], self.timeout)
                     if browse_sdRef in ready[0]:
                         pybonjour.DNSServiceProcessResult(browse_sdRef)
             except Exception:
                 self.error("Exception in Browser")
                 pass
         finally:
             browse_sdRef.close()
             self.debug("Browser Service Stopped")
 
     def register(self):
         """
         Register a service on the network for type "regtype"
         """
         reg_sdRef = pybonjour.DNSServiceRegister(name=self.name,
                                                 regtype=self.regtype,
                                                 port=self.port,
                                                 callBack=self.register_callback)
         self.debug("Registration Service Started")
         try:
             try:
                 while self._isRegisterRunning:
                     ready = select.select([reg_sdRef], [], [], self.timeout)
                     if reg_sdRef in ready[0]:
                         pybonjour.DNSServiceProcessResult(reg_sdRef)
             except Exception:
                 self.error("Exception in Registration")
                 pass
         finally:
             reg_sdRef.close()
             self.debug("Registration Service Stopped")
 
 
     def register_callback(self, sdRef, flags, errorCode, name, regtype, domain):
         """
         Callback used by the run_regsiter routine.
         """
         if errorCode == pybonjour.kDNSServiceErr_NoError:
             self.info("Bonjour Service Registered at %s" %
                       (self.fullname.decode('utf-8')))
 
     def query_record_callback(self, sdRef, flags, interfaceIndex, errorCode,
                               fullname, rrtype, rrclass, rdata, ttl):
         """
         Callback for querying hosts IP addresses that come from the resolution
         routine
         """
         if errorCode == pybonjour.kDNSServiceErr_NoError:
             if not fullname.endswith(u'.'):
                 fullname += u'.'
 
             for client in self.clients.itervalues():
                 if sdRef == client.query_sdRef:
                     client.ip = socket.inet_ntoa(rdata)
                     client.resolved = True
                     break;
 
             if self.client_callback:
                 self.client_callback(self.__getClients())
             self.queried.append(True)
 
     def removed_callback(self, sdRef, flags, interfaceIndex, errorCode,
                          fullname, hosttarget, port, txtRecord):
         """
         Callback for removing hosts that have been detected through the browse 
         routine.
         """
         if errorCode == pybonjour.kDNSServiceErr_NoError:
             with self.clientLock:
                 for client in self.clients.itervalues():
                     if sdRef == client.resolve_sdRef:
                         removed = True
                         break;
                 if removed:
                     del self.clients[client.serviceName]
 
                 if self.client_callback:
                     self.client_callback(self.__getClients())
 
     def resolve_callback(self, sdRef, flags, interfaceIndex, errorCode,
                          fullname, hosttarget, port, txtRecord):
         """
         Callback for resolving hosts that have been detected through the browse 
         routine.
         """
         if errorCode == pybonjour.kDNSServiceErr_NoError:
             if self.fullname == fullname:
                 localhost = True
                 self.debug("Resolved Self")
             else:
                 localhost = False
             for client in self.clients.itervalues():
                 if sdRef == client.resolve_sdRef:
                     client.hostname = hosttarget.decode('utf-8')
                     client.port = port
                     break;
             if localhost:
                 if self.clients.has_key(client.serviceName):
                     del self.clients[client.serviceName]
                 return
 
             client.query_sdRef = \
                     pybonjour.DNSServiceQueryRecord(interfaceIndex=interfaceIndex,
                                                     fullname=hosttarget,
                                                     rrtype=pybonjour.kDNSServiceType_A,
                                                     callBack=self.query_record_callback)
             try:
                 while not self.queried:
                     ready = select.select([client.query_sdRef], [], [], self.timeout)
                     if client.query_sdRef not in ready[0]:
                         self.debug("Query record timed out")
                         break
                     pybonjour.DNSServiceProcessResult(client.query_sdRef)
                 else:
                     self.queried.pop()
             finally:
                 client.query_sdRef.close()
             self.resolved.append(True)
         else:
             self.error("Resolve failed with code: %s" % errorCode)
 
     def browse_callback(self, sdRef, flags, interfaceIndex, errorCode,
                         serviceName, regtype, replyDomain):
         """
         Callback for browsing hosts of type "regtype" on the network.
         """
         if errorCode != pybonjour.kDNSServiceErr_NoError:
             return
 
         # Handle a removed client
         if not (flags & pybonjour.kDNSServiceFlagsAdd):
             with self.clientLock:
                 if self.clients.has_key(serviceName):
                     c = self.clients[serviceName]
                 else:
                     return
             c.resolve_sdRef = pybonjour.DNSServiceResolve(0,
                                                           interfaceIndex,
                                                           serviceName,
                                                           regtype,
                                                           replyDomain,
                                                           self.removed_callback)
             try:
                 while not self.resolved:
                     ready = select.select([c.resolve_sdRef], [], [], self.timeout)
                     if c.resolve_sdRef not in ready[0]:
                         self.debug("Remove resolve timed out")
                         break
                     pybonjour.DNSServiceProcessResult(c.resolve_sdRef)
                 else:
                     self.resolved.pop()
             finally:
                 c.resolve_sdRef.close()
             return
 
 
         with self.clientLock:
             if self.clients.has_key(serviceName):
                 if self.clients[serviceName].resolved:
                     return
                 c = self.clients[serviceName]
             else:
                 self.clients[serviceName] = BonjourClient()
                 c = self.clients[serviceName]
         c.serviceName = serviceName
         c.resolve_sdRef = pybonjour.DNSServiceResolve(0,
                                                       interfaceIndex,
                                                       serviceName,
                                                       regtype,
                                                       replyDomain,
                                                       self.resolve_callback)
         try:
             while not self.resolved:
                 ready = select.select([c.resolve_sdRef], [], [], self.timeout)
                 if c.resolve_sdRef not in ready[0]:
                     self.debug("Resolve timed out")
                     break
                 pybonjour.DNSServiceProcessResult(c.resolve_sdRef)
             else:
                 self.resolved.pop()
         finally:
             c.resolve_sdRef.close()
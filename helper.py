'''
    @document   : helper.py
    @package    : PleXBMC Helper add-on
    @author     : wickning1 (aka Nick Wing)
    @author     : hippojay (aka Dave Hawes-Johnson)
    @copyright  : 2013, wickning1
    @version    : 3.2.0 (frodo)

    @license    : Gnu General Public License - see LICENSE.TXT
    @description: pleXBMC Helper XBMC add-on

    This is a significant overhaul of the plugin originally developed by
    Hippojay (https://github.com/hippojay/script.plexbmc.helper).

    PleXBMC Helper Script is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 2 of the License, or
    (at your option) any later version.

    PleXBMC Plugin is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with PleXBMC Plugin.  If not, see <http://www.gnu.org/licenses/>.

'''
#system includes
# import sys
# import socket
# import traceback
# import os
# from resources.lib.common import *
# from resources.lib.helper.httppersist import requests
# from resources.lib.helper.functions import *
# from resources.lib.helper.subscribers import subMgr
# from resources.lib.helper.listener import *
# from resources.lib.plex.plexgdm import PlexGDM
# import resources.lib.CacheControl as CacheControl
# log_print = PrintDebug("PleXBMC Helper")
#
# helper_cache = CacheControl.CacheControl(GLOBAL_SETUP['__cachedir__']+"cache/servers", settings.get_setting('cache'))
# helper_cache_name = "helper_server_list"
#
# print "===== PLEXBMC HELPER START ====="
#
# # Start GDM for server/client discovery
# try:
#     interface_address = get_platform_ip()
#     log_print.debug("Using interface: %s for GDM discovery" % interface_address)
# except:
#     interface_address = None
#     log_print.debug("Using systems default interface for GDM discovery")
#
# client = PlexGDM()
# client.clientDetails(settings.get_setting('client_id'), settings.get_setting('devicename'), 3005, "PleXBMC", GLOBAL_SETUP['__version__'])
# log_print.debug("PleXBMC Helper -> registration string is: %s " % client.getClientDetails())
#
# start_count = 0
# while True:
#     try:
#         httpd = ThreadedHTTPServer(('', 3005), MyHandler)
#         httpd.timeout = 0.95
#         break
#     except:
#         log_print.warn("PleXBMC Helper -> Unable to start web helper.  Sleep and Retry...")
#         settings.set_setting("webserver_restart", True)
#
#     xbmc.sleep(3000)
#
#     if start_count == 3:
#         print "PleXBMC Helper -> Unable to start web helper. Giving up."
#         xbmc.executebuiltin("XBMC.Notification(PleXBMC Helper - Helper Web unable to start due to port clash,)")
#         httpd = False
#         break
#
#     start_count += 1
#
# if httpd:
#     client.start_all()
#     settings.set_setting("webserver_restart", False)
#     message_count = 0
#     is_running = False
#     while not xbmc.abortRequested and not settings.get_setting("webserver_restart"):
#         try:
#
#             httpd.handle_request()
#             message_count += 1
#
#             if message_count > 30:
#                 if client.check_client_registration():
#                     log_print.debug("Client is still registered")
#                 else:
#                     log_print.debug("Client is no longer registered")
#                 log_print.debug("PlexBMC Helper still running on port %s" % 3005)
#                 message_count = 0
#
#             if not is_running:
#                 log_print.info("PleXBMC Helper -> PleXBMC Helper has started")
#                 xbmc.executebuiltin("XBMC.Notification(PleXBMC Helper has started,)")
#
#             is_running = True
#             if message_count % 1 == 0:
#                 subMgr.notify()
#             helper_cache.write_cache(helper_cache_name, client.getServerList())
#         except:
#             log_print.debug("Error in loop, continuing anyway")
#             print traceback.print_exc()
#
#     try:
#         httpd.socket.shutdown(socket.SHUT_RDWR)
#     finally:
#         httpd.socket.close()
#     requests.dumpConnections()
#     client.stop_all()
#     log_print.info("PleXBMC Helper -> PleXBMC Helper has been stopped")
#     xbmc.executebuiltin("XBMC.Notification(PleXBMC Helper has been stopped,)")

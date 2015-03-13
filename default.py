
import xbmcaddon
import os

print "===== PLEXBMC START ====="

from common import *  #Needed first to setup import locations
import plexbmc
import time

plexbmc_start = time.time()

plexbmc.start_plexbmc()
print "===== PLEXBMC STOP: %s seconds =====" % ( time.time() - plexbmc_start )

sys.modules.clear()
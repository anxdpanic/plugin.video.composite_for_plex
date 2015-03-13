
import xbmcaddon
import os
from common import *  #Needed first to setup import locations
import plexbmc
import time

plexbmc_start = time.time()

print "===== PLEXBMC START ====="
plexbmc.start_plexbmc()
print "===== PLEXBMC STOP: %s seconds =====" % ( time.time() - plexbmc_start )

sys.modules.clear()
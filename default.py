
import xbmcaddon
import os
import time
print "===== PLEXBMC START ====="
plexbmc_start = time.time()
#import StringIO
#import cProfile
#import pstats
from common import *  #Needed first to setup import locations
import plexbmc

plexbmc.start_plexbmc()
#cProfile.run('plexbmc.start_plexbmc()', 'statsfile')
#stream = StringIO.StringIO()
#stats = pstats.Stats('statsfile', stream=stream)
#stats.sort_stats('tottime')
#stats.print_stats()

# Stream now contains the report text.
# Can be accessed with stream.getvalue()

#print stream.getvalue()
print "===== PLEXBMC STOP: %s seconds =====" % ( time.time() - plexbmc_start )

sys.modules.clear()
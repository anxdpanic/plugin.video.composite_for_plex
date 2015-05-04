
import xbmcaddon
import os
import time
plexbmc_start = time.time()
print "===== PLEXBMC START [id: %s] =====" % plexbmc_start
#import StringIO
#import cProfile
#import pstats
from common import GLOBAL_SETUP  #Needed first to setup import locations
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
print "===== PLEXBMC STOP [id: %s]: %s seconds =====" % (plexbmc_start , ( time.time() - plexbmc_start ))

sys.modules.clear()
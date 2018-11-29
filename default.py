import sys
import time

plexbmc_start = time.time()
print "===== PLEXBMC START [id: %s] =====" % plexbmc_start
from resources.lib import plexbmc

profile = False

if not profile:
    print "PleXBMC -> Script argument is %s" % sys.argv
    plexbmc.start_plexbmc(sys.argv)
else:
    # Enable extra profile information
    import StringIO
    import cProfile
    import pstats

    cProfile.run('plexbmc.start_plexbmc()', 'statsfile')
    stream = StringIO.StringIO()
    stats = pstats.Stats('statsfile', stream=stream)
    stats.sort_stats('tottime')
    stats.print_stats()

    # Stream now contains the report text.
    # Can be accessed with stream.getvalue()

    print stream.getvalue()

print "===== PLEXBMC STOP [id: %s]: %s seconds =====" % (plexbmc_start, (time.time() - plexbmc_start))

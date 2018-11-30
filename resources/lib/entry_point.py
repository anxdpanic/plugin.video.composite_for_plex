import sys
import time

import xbmc

plexbmc_start = time.time()
from plexbmc_addon import plexbmc

profile = False

if not profile:
    xbmc.log("PleXBMC -> Script argument is %s" % sys.argv, xbmc.LOGDEBUG)
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

    xbmc.log(stream.getvalue(), xbmc.LOGDEBUG)

xbmc.log("PLEXBMC STOP [id: %s]: %s seconds" % (plexbmc_start, (time.time() - plexbmc_start)), xbmc.LOGDEBUG)

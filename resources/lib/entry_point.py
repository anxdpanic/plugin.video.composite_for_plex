import sys
import time

import xbmc

bplex_start = time.time()
from bplex_addon import bplex

profile = False

if not profile:
    xbmc.log('bPlex -> Script argument is %s' % sys.argv, xbmc.LOGDEBUG)
    bplex.start_bplex(sys.argv)
else:
    # Enable extra profile information
    import StringIO
    import cProfile
    import pstats

    cProfile.run('bplex.start_bplex()', 'statsfile')
    stream = StringIO.StringIO()
    stats = pstats.Stats('statsfile', stream=stream)
    stats.sort_stats('tottime')
    stats.print_stats()

    # Stream now contains the report text.
    # Can be accessed with stream.getvalue()

    xbmc.log(stream.getvalue(), xbmc.LOGDEBUG)

xbmc.log('bPlex STOP [id: %s]: %s seconds' % (bplex_start, (time.time() - bplex_start)), xbmc.LOGDEBUG)

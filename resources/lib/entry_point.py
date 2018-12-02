import sys
import time

import xbmc

bplex_start = time.time()

from bplex_addon import bplex

bplex.start_bplex(sys.argv)

xbmc.log('bPlex finished. |%ss|' % (time.time() - bplex_start), xbmc.LOGDEBUG)

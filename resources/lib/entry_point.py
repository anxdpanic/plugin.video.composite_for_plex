"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018 bPlex (plugin.video.bplex)

    This file is part of bPlex (plugin.video.bplex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later for more information.
"""

import sys
import time

import xbmc

bplex_start = time.time()

from bplex_addon import bplex

bplex.start_bplex(sys.argv)

xbmc.log('bPlex finished. |%ss|' % (time.time() - bplex_start), xbmc.LOGDEBUG)

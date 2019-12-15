# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2018 PleXBMC (plugin.video.plexbmc) by hippojay (Dave Hawes-Johnson)
    Copyright (C) 2018-2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""

from ..addon.data_cache import DATA_CACHE
from ..addon.playback import play_library_media
from ..addon.playback import play_media_id_from_uuid
from ..addon.utils import get_transcode_profile
from ..plex import plex

PLEX_NETWORK = plex.Plex(load=False)


def run(url=None, server_uuid=None, media_id=None, force=None, transcode=False,  # pylint: disable=too-many-arguments
        transcode_profile=0):
    PLEX_NETWORK.load()

    if transcode and transcode_profile is None:
        transcode_profile = get_transcode_profile()
    if transcode_profile is None:
        transcode_profile = 0

    if url is None and (server_uuid and media_id):
        play_media_id_from_uuid(server_uuid=server_uuid, media_id=media_id, force=force,
                                transcode=transcode, transcode_profile=transcode_profile,
                                plex_network=PLEX_NETWORK)
        DATA_CACHE.delete_cache(True)
        return

    if url:
        play_library_media(url=url, force=force, transcode=transcode,
                           transcode_profile=transcode_profile, plex_network=PLEX_NETWORK)
        DATA_CACHE.delete_cache(True)

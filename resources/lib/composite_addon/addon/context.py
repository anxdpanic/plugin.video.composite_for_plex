# -*- coding: utf-8 -*-
"""

    Copyright (C) 2019 Composite (plugin.video.composite_for_plex)

    This file is part of Composite (plugin.video.composite_for_plex)

    SPDX-License-Identifier: GPL-2.0-or-later
    See LICENSES/GPL-2.0-or-later.txt for more information.
"""


class Context:
    """
    Context values are set during creation, used to simplify passing objects to functions/methods
    """

    def __init__(self):
        self._params = None
        self._settings = None
        self._plex_network = None

    @property
    def params(self):
        if not self._params:
            raise ContextPropertyUnavailable
        return self._params

    @params.setter
    def params(self, value):
        """
        :param value: sys.argv[2] dict
        """
        self._params = value

    @property
    def settings(self):
        if not self._settings:
            raise ContextPropertyUnavailable
        return self._settings

    @settings.setter
    def settings(self, value):
        """
        :param value: resources/lib/composite_addon/addon/settings.AddonSettings()
        """
        self._settings = value

    @property
    def plex_network(self):
        if not self._plex_network:
            raise ContextPropertyUnavailable
        return self._plex_network

    @plex_network.setter
    def plex_network(self, value):
        """
        :param value: resources/lib/composite_addon/plex/plex.Plex()
        """
        self._plex_network = value


class ContextPropertyUnavailable(Exception):
    pass

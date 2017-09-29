# -*- coding: utf-8 -*-
# @author: vuolter

from __future__ import absolute_import, unicode_literals

from builtins import object

from future import standard_library

from ...utils.layer.safethreading import Lock

standard_library.install_aliases()


class BaseManager(object):
    """
    Base manager
    """
    def __init__(self, core):
        """
        Constructor.
        """
        self.__pyload = core
        self._ = core._
        self.lock = Lock()

    @property
    def pyload(self):
        return self.__pyload

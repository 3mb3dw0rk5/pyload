# -*- coding: utf-8 -*-

from module.plugins.internal.DeadCrypter import DeadCrypter, create_getInfo


class Movie2KTo(DeadCrypter):
    __name__    = "Movie2KTo"
    __type__    = "crypter"
    __version__ = "0.52"
    __status__  = "testing"

    __pattern__ = r'http://(?:www\.)?movie2k\.to/(.+)\.html'
    __config__  = []  #@TODO: Remove in 0.4.10

    __description__ = """Movie2k.to decrypter plugin"""
    __license__     = "GPLv3"
    __authors__     = [("4Christopher", "4Christopher@gmx.de")]


getInfo = create_getInfo(Movie2KTo)

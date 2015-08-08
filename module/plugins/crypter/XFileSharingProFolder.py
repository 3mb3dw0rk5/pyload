# -*- coding: utf-8 -*-

import re

from module.plugins.internal.XFSCrypter import XFSCrypter, create_getInfo


class XFileSharingProFolder(XFSCrypter):
    __name__    = "XFileSharingProFolder"
    __type__    = "crypter"
    __version__ = "0.13"
    __status__  = "testing"

    __pattern__ = r'https?://(?:www\.)?(?:\w+\.)*?(?P<DOMAIN>(?:[\d.]+|[\w\-^_]{3,}(?:\.[a-zA-Z]{2,}){1,2})(?:\:\d+)?)/(?:user|folder)s?/\w+'
    __config__  = [("use_subfolder"     , "bool", "Save package to subfolder"          , True),
                   ("subfolder_per_pack", "bool", "Create a subfolder for each package", True)]

    __description__ = """XFileSharingPro dummy folder decrypter plugin for hook"""
    __license__     = "GPLv3"
    __authors__     = [("Walter Purcaro", "vuolter@gmail.com")]


    def _log(self, level, plugintype, pluginname, messages):
        return super(XFileSharingProFolder, self)._log(level,
                                                       plugintype,
                                                       "%s: %s" % (pluginname, self.HOSTER_NAME),
                                                       messages)


    def init(self):
        super(XFileSharingProFolder, self).init()

        self.__pattern__ = self.pyload.pluginManager.crypterPlugins[self.__name__]['pattern']

        self.HOSTER_DOMAIN = re.match(self.__pattern__, self.pyfile.url).group("DOMAIN").lower()
        self.HOSTER_NAME   = "".join(part.capitalize() for part in re.split(r'(\.|\d+|\-)', self.HOSTER_DOMAIN) if part != '.')


    def _setup(self):
        account_name     = self.__name__ if self.account.HOSTER_DOMAIN is None else self.HOSTER_NAME
        self.chunk_limit = 1
        self.multiDL     = True

        if self.account:
            self.req             = self.pyload.requestFactory.getRequest(accountname, self.user)
            self.premium         = self.account.is_premium(self.user)
            self.resume_download = self.premium
        else:
            self.req             = self.pyload.requestFactory.getRequest(account_name)
            self.premium         = False
            self.resume_download = False


    def load_account(self):
        if self.req:
            self.req.close()

        if not self.account:
            self.account = self.pyload.accountManager.getAccountPlugin(self.HOSTER_NAME)

        if not self.account:
            self.account = self.pyload.accountManager.getAccountPlugin(self.__name__)

        if self.account:
            if not self.account.HOSTER_DOMAIN:
                self.account.HOSTER_DOMAIN = self.HOSTER_DOMAIN

            if not self.user:
                self.user = self.account.select()[0]

            if not self.user or not self.account.is_logged(self.user, True):
                self.account = False


getInfo = create_getInfo(XFileSharingProFolder)

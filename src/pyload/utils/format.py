# -*- coding: utf-8 -*-
# @author: vuolter

from __future__ import absolute_import, unicode_literals

import datetime
import os
import re
import urllib.parse
from builtins import int, map, str

from future import standard_library

from . import purge
from .check import isiterable
from .fs import fullpath

standard_library.install_aliases()


try:
    import bitmath
except ImportError:
    pass


def attributes(obj, ignore=None):
    if ignore is None:
        attrs = (str(x) for x in obj)
    else:
        ignored = ignore if isiterable(ignore) else (ignore,)
        attrs = (str(x) for x in obj if x not in ignored)
    return attrs


def items(obj, ignore=None):
    if ignore is None:
        items = ("{0}={1}".format(k, v) for k, v in obj.items())
    else:
        ignored = ignore if isiterable(ignore) else (ignore,)
        items = ("{0}={1}".format(k, v)
                for k, v in obj.items() if k not in ignored)
    return items


def path(*paths):
    return os.path.normcase(fullpath(os.path.join(*paths)))


__byte_prefixes = ('', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi')

def size(obj):
    KIB = 1024.0
    num = float(obj)
    try:
        return bitmath.Byte(num).best_prefix()
    except NameError:
        for prefix in __byte_prefixes[:-1]:
            if abs(num) < KIB:
                return "{0:3.2f} {1}B".format(num, prefix)
            else:
                num /= KIB
        return "{0:.2f} {1}B".format(num, __byte_prefixes[-1])


def speed(obj):
    return '{0}/s'.format(size(obj))


def time(obj):
    sec = abs(int(obj))
    dt = datetime.datetime(1, 1, 1) + datetime.timedelta(seconds=sec)
    days = dt.day - 1 if dt.day else 0
    attrlist = ('hour', 'minute', 'second')
    timelist = (
        "{0:d} {1}s".format(getattr(dt, attr), attr)
        for attr in attrlist if getattr(dt, attr))
    if days:
        timelist.append("{0:d} days".format(days))
    return timelist


__re_url = re.compile(r'(?<!:)/{2,}')

def url(obj):
    from .web import purge
    url = urllib.parse.unquote(str(obj).decode('unicode-escape'))
    url = purge.text(url).lstrip('.').lower()
    url = __re_url.sub('/', url).rstrip('/')
    return url

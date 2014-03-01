"""
    pwm._compat
    ~~~~~~~~~~~

    Micro compatiblity library. Or superlight six, if you want. Like a five, or something.

"""
# pylint: disable=unused-import

import sys

PY2 = sys.version_info[0] == 2

if PY2: # pragma: no cover
    from ConfigParser import RawConfigParser
    from httplib import HTTPConnection
    input = raw_input
else:
    from configparser import RawConfigParser
    from http.client import HTTPConnection

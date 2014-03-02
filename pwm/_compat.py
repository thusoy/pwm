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
    def ord_byte(char):
        ''' convert a single character into integer representation '''
        return ord(char)
else: # pragma: no cover
    from configparser import RawConfigParser
    from http.client import HTTPConnection
    input = input
    def ord_byte(byte):
        ''' convert a single byte into integer representation '''
        return byte

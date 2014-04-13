"""
    pwm
    ~~~

    Expose public APIs.

"""
# pylint: disable=unused-import

__version__ = '0.1.6' # When bumping, also bump version in setup.py

from .core import (
    Domain,
    PWM,
)

from .exceptions import (
    DuplicateDomainException,
    NotReadyException,
    NoSuchDomainException,
)

from .encoding import (
    ceildiv,
    calc_chunklen,
    Encoder,
    lookup_alphabet,
    PRESETS,
)

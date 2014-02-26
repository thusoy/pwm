#!/usr/bin/env python
"""
    pwm
    ~~~~~~~~~~~~~~

    pwm is a simple, secure password manager that can't disclose your passwords - since it's doesn't know them.

"""

import sys
from setuptools import setup, find_packages

install_requires = [
    'sqlalchemy',
]

if sys.version_info < (2, 7, 0):
    install_requires.append('argparse')

setup(
    name='pwm',
    version='0.1.0',
    author='Tarjei Husøy',
    author_email='tarjei@roms.no',
    url='https://github.com/thusoy/pwm',
    description="A superlight password manager",
    packages=find_packages(),
    install_requires=install_requires,
    extras_require={
        'test': ['mock', 'nose', 'coverage'],
    },
    entry_points={
        'console_scripts': [
            'pwm = pwm:main',
        ]
    },
)

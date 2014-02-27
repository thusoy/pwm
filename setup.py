#!/usr/bin/env python
# coding: utf-8
"""
    pwm
    ~~~~~~~~~~~~~~

    pwm is a simple, secure password manager that can't disclose your passwords - since it's doesn't know them.

"""

import sys
from setuptools import setup

install_requires = [
    'sqlalchemy',
    'requests',
]

if sys.version_info < (2, 7, 0):
    install_requires.append('argparse')

setup(
    name='pwm',
    version='0.1.2',
    author='Tarjei Husøy',
    author_email='tarjei@roms.no',
    url='https://github.com/thusoy/pwm',
    description="A superlight password manager",
    py_modules=['pwm'],
    install_requires=install_requires,
    extras_require={
        'test': ['nose', 'nosy', 'coverage'],
    },
    entry_points={
        'console_scripts': [
            'pwm = pwm:main',
        ]
    },
    classifiers=[
        # 'Development Status :: 1 - Planning',
        'Development Status :: 2 - Pre-Alpha',
        # 'Development Status :: 3 - Alpha',
        # 'Development Status :: 4 - Beta',
        # 'Development Status :: 5 - Production/Stable',
        # 'Development Status :: 6 - Mature',
        # 'Development Status :: 7 - Inactive',
        # 'Intended Audience :: Customer Service',
        'Intended Audience :: Developers',
        # 'Intended Audience :: Education',
        'Intended Audience :: End Users/Desktop',
        # 'Intended Audience :: Financial and Insurance Industry',
        # 'Intended Audience :: Healthcare Industry',
        # 'Intended Audience :: Information Technology',
        # 'Intended Audience :: Legal Industry',
        # 'Intended Audience :: Manufacturing',
        # 'Intended Audience :: Other Audience',
        # 'Intended Audience :: Religion',
        # 'Intended Audience :: Science/Research',
        # 'Intended Audience :: System Administrators',
        # 'Intended Audience :: Telecommunications Industry',
        'License :: OSI Approved :: MIT License',
        # 'Programming Language :: Python :: 2.6',
        # 'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        # 'Programming Language :: Python :: 3.4',
        # 'Topic :: Internet :: WWW/HTTP :: HTTP Servers',
        # 'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
        # 'Topic :: Security',
    ],

)

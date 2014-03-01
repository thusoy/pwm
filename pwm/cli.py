from . import PWM, encoding, Base
from ._compat import HTTPConnection, RawConfigParser

import argparse
import os
import sys
import logging.config
import textwrap
import sqlalchemy as sa


def main():
    """ Main entry point for the CLI. """
    args = get_args()
    ret_code = args.target(args)
    sys.exit(ret_code)


def get_args():
    argparser = argparse.ArgumentParser(prog='pwm')
    argparser.add_argument('-v', '--verbose',
        action='store_true',
        help='Increase verbosity',
    )
    default_config_file = os.path.join(os.path.expanduser('~'), '.pwm', 'config')
    argparser.add_argument('-c', '--config-file',
        metavar='<config-file>',
        help='Path to config file to use. Default: %(default)s',
        default=default_config_file,
    )

    # Add subparserss
    subparsers = argparser.add_subparsers(dest='action',
        title='Action',
        help='What do you want to do?',
    )
    add_get_parser(subparsers)
    add_search_parser(subparsers)
    add_create_parser(subparsers)

    args = argparser.parse_args()
    _init_logging(verbose=args.verbose)
    return args


def add_create_parser(subparsers):
    parser = subparsers.add_parser('create',
        help='Create keys for a new domain',
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument('domain',
        help='The domain to create a key for',
    )
    parser.add_argument('-l', '--length',
        metavar='<length>',
        help='Set length of generated key. Default: %(default)d',
        type=int,
        default=encoding.DEFAULT_LENGTH,
    )
    parser.add_argument('-c', '--charset',
        metavar='<charset>',
        help='Use this (named or custom) charset. Named presets include:\n\n%s' %
            '\n'.join("'%s': '%s'" % (name, alphabet.replace('%', '%%')) for name, alphabet in encoding.PRESETS.items()),
        default='full',
    )
    parser.set_defaults(target=create)


def add_get_parser(subparsers):
    parser = subparsers.add_parser('get',
        help='Get the key for a domain',
    )
    parser.add_argument('domain',
        help='The domain to retrieve the password for',
    )
    parser.set_defaults(target=get)


def add_search_parser(subparsers):
    parser = subparsers.add_parser('search',
        help='Search for existing domains',
    )
    parser.add_argument('query',
        help='The query string to search for',
    )
    parser.set_defaults(target=search)


def search(args):
    pwm = PWM(config_file=args.config_file)
    results = pwm.search(args.query)
    for result in results:
        print(result.name)
    return 0 if results else 1


def get(args):
    pwm = PWM(config_file=args.config_file)
    domain = pwm.get_domain(args.domain)
    if domain:
        print(domain.get_key())
        return 0
    else:
        print("Couldn't find any entries for '%s', are you sure you have created any?" % args.domain)
        return 1


def create(args):
    pwm = PWM(config_file=args.config_file)
    length = args.length
    domain = pwm.create_domain(args.domain, args.charset, length)
    if domain:
        print('New domain successfully created.')
        print(domain.get_key())
        return 0
    else:
        return 1


def run_setup(self, config_file):
    print(textwrap.dedent("""\
        Hi, it looks like it's the first time you're using pwm on this machine. Let's take a little
        moment to set things up before we begin."""))
    db_uri = input('Which database do you want to use (default: local sqlite at ~/.pwm/db.sqlite) ').strip() or 'local'
    rc_dir = os.path.dirname(config_file)

    if db_uri == 'local':

        # normalize windows-style paths for sqlalchemy:
        rc_dir = rc_dir.replace('\\', '/')

        # Create the local database
        db_uri = 'sqlite:///%s/db.sqlite' % rc_dir
    if not '://' in db_uri:
        # Not a sqlalchemy-compatible connection string or https URI, assume it's a local path and make a sqlite
        # uri out of it
        db_uri = 'sqlite:///%s' % db_uri
    if not (db_uri.startswith('https:') or db_uri.startswith('http:')):
        # It's a local db, make sure our tables exist
        db = sa.create_engine(db_uri)
        Base.metadata.create_all(db)

    config_parser = RawConfigParser()
    config_parser.add_section('pwm')
    config_parser.set('pwm', 'database', db_uri)

    with open(config_file, 'w') as config_file_fh:
        config_parser.write(config_file_fh)


def _init_logging(verbose=False):
    """ Initialize loggers. """
    config = {
        'version': 1,
        'formatters': {
            'console': {
                'format': '* %(message)s',
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'console',
                'stream': 'ext://sys.stdout',
            }
        },
        'loggers': {
            'pwm': {
                'level': 'DEBUG' if verbose else 'INFO',
                'handlers': ['console'],
                'propagate': True,
            },
            'requests.packages.urllib3': {
                'level': 'INFO' if verbose else 'WARNING',
                'handlers': ['console'],
                'propagate': True,
            }
        }
    }
    logging.config.dictConfig(config)
    HTTPConnection.debuglevel = 1 if verbose else 0

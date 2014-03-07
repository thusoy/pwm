from . import PWM, encoding, Domain, NoSuchDomainException
from ._compat import HTTPConnection, RawConfigParser, input

import argparse
import os
import sys
import logging.config
import textwrap
from logging import getLogger

_logger = getLogger('pwm.cli')

# The base parsers the other parsers can inherit from. Add options here
# that should work no matter where they are passed, like
# 'pwm -v get facebook' == 'pwm get -v facebook'
_VERBOSE_PARSER = argparse.ArgumentParser(add_help=False)
_VERBOSE_PARSER.add_argument('-v', '--verbose',
    action='store_true',
    help='Increase verbosity',
)

_DB_PARSER = argparse.ArgumentParser(add_help=False)
_DB_PARSER.add_argument('-d', '--database',
    metavar='<database>',
    help='Path to the database to use. Can also be set with the PWM_DATABASE env var. ' +
        'If neither is set, will fall back to ~/.pwm/db.sqlite',
)


def main():
    """ Main entry point for the CLI. """
    args = get_args()
    ret_code = args.target(args)
    _logger.debug('Exiting with code %d', ret_code)
    sys.exit(ret_code)


def get_args():
    argparser = argparse.ArgumentParser(prog='pwm',
        parents=[_VERBOSE_PARSER, _DB_PARSER],
    )

    # Add subparserss
    subparsers = argparser.add_subparsers(dest='action',
        title='Action',
        help='What do you want to do?',
    )
    add_get_parser(subparsers)
    add_search_parser(subparsers)
    add_create_parser(subparsers)
    add_init_parser(subparsers)
    add_modify_parser(subparsers)

    args = argparser.parse_args()
    _init_logging(verbose=args.verbose)
    return args


def add_create_parser(subparsers):
    parser = subparsers.add_parser('create',
        help='Create keys for a new domain',
        formatter_class=argparse.RawTextHelpFormatter,
        parents=[_VERBOSE_PARSER, _DB_PARSER],
    )
    parser.add_argument('domain',
        help='The domain to create a key for',
    )
    parser.add_argument('-u', '--username',
        metavar='<username>',
        help='The username to associate with this domain',
    )
    parser.add_argument('-l', '--length',
        metavar='<length>',
        help='Set length of generated key. Default: %(default)d',
        type=int,
        default=Domain.DEFAULT_KEY_LENGTH,
    )
    parser.add_argument('-c', '--charset',
        metavar='<charset>',
        help='Use this (named or custom) charset. Named presets include:\n\n%s' %
            '\n'.join("'%s': '%s'" % (name, alphabet.replace('%', '%%')) for name, alphabet
                in encoding.PRESETS.items()),
        default='full',
    )
    parser.set_defaults(target=create)


def add_get_parser(subparsers):
    parser = subparsers.add_parser('get',
        help='Get the key for a domain',
        parents=[_VERBOSE_PARSER, _DB_PARSER],
    )
    parser.add_argument('domain',
        help='The domain to retrieve the password for',
    )
    parser.set_defaults(target=get)


def add_modify_parser(subparsers):
    parser = subparsers.add_parser('modify',
        help='Modify an existing domain',
        parents=[_VERBOSE_PARSER, _DB_PARSER],
    )
    parser.add_argument('domain',
        help='The domain to modify',
    )
    parser.add_argument('-s', '--new-salt',
        action='store_true',
        default=False,
        help='Generate a new salt for this domain. Default: %(default)s',
    )
    parser.add_argument('-u', '--username',
        metavar='<username>',
        help='Set a new username for this domain',
    )
    parser.set_defaults(target=modify)


def add_search_parser(subparsers):
    parser = subparsers.add_parser('search',
        help='Search for existing domains',
        parents=[_VERBOSE_PARSER, _DB_PARSER],
    )
    parser.add_argument('query',
        help='The query string to search for',
    )
    parser.set_defaults(target=search)


def add_init_parser(subparsers):
    parser = subparsers.add_parser('init',
        help='Initialize a new database',
        parents=[_VERBOSE_PARSER],
    )
    parser.add_argument('database',
        help='The path to the database to initialize',
    )
    parser.set_defaults(target=init)


def init(args):
    pwm = PWM()
    _logger.debug('Initializing database at %s', args.database)
    pwm.bootstrap(args.database)
    return 0


def search(args):
    pwm = _get_pwm(args.database)
    results = pwm.search(args.query)
    for result in results:
        print(result.name)
    return 1


def get(args):
    pwm = _get_pwm(args.database)
    domain = pwm.get_domain(args.domain)
    if domain:
        key = domain.get_key()
        if domain.username:
            print('Username: %s' % domain.username)
        print(key)
        return 0
    else:
        print("Couldn't find any entries for '%s', are you sure you have created any?" % args.domain)
        return 1


def create(args):
    pwm = _get_pwm(args.database)
    length = args.length
    domain = pwm.create_domain(args.domain, username=args.username, alphabet=args.charset,
        length=length)
    if domain:
        print('New domain successfully created, key has %d bits of entropy' % domain.entropy)
        print(domain.get_key())
        return 0
    else:
        return 1


def modify(args):
    pwm = _get_pwm(args.database)
    try:
        pwm.modify_domain(args.domain, new_salt=args.new_salt, username=args.username)
        print('Domain updated successfully.')
        return 0
    except NoSuchDomainException:
        print("Couldn't find a domain with this name.")
        return 1


def _get_pwm(cli_database):
    default_database = os.path.join(os.path.expanduser('~'), '.pwm', 'db.sqlite')
    database = cli_database or os.environ.get('PWM_DATABASE') or default_database
    pwm = PWM(database_path=database)
    return pwm


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

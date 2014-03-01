from . import get, search, encoding

import argparse
import os
import logging.config

try:
    from http.client import HTTPConnection
except:
    # python 2
    from httplib import HTTPConnection


def main():
    """ Main entry point for the CLI. """
    args = get_args()
    args.target(args)


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

    args = argparser.parse_args()
    _init_logging(verbose=args.verbose)
    return args


def add_get_parser(subparsers):
    parser = subparsers.add_parser('get',
        help='Get the key for a domain',
    )
    parser.add_argument('-c', '--charset',
        help='Use this (named or custom) charset',
        default=encoding.DEFAULT_CHARSET,
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

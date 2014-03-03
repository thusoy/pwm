from . import PWM, encoding, Domain
from ._compat import HTTPConnection, RawConfigParser, input

import argparse
import os
import sys
import logging.config
import textwrap


def main():
    """ Main entry point for the CLI. """
    args = get_args()
    if not _is_configured(args.config_file):
        run_setup(args.config_file)
    ret_code = args.target(args)
    sys.exit(ret_code)


def _is_configured(config_file):
    return os.path.exists(config_file)


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
    pwm = _get_pwm_from_config(args.config_file)
    results = pwm.search(args.query)
    for result in results:
        print(result.name)
    return 0 if results else 1


def get(args):
    pwm = _get_pwm_from_config(args.config_file)
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
    pwm = _get_pwm_from_config(args.config_file)
    length = args.length
    domain = pwm.create_domain(args.domain, username=args.username, alphabet=args.charset,
        length=length)
    if domain:
        print('New domain successfully created.')
        print(domain.get_key())
        return 0
    else:
        return 1


def _get_pwm_from_config(config_file):
    config = _read_config(config_file)
    pwm = PWM(database_path=config['database'])
    return pwm


def run_setup(config_file):
    if not os.path.exists(os.path.dirname(config_file)):
        os.makedirs(os.path.dirname(config_file))
    print(textwrap.dedent("""\
        Hi, it looks like it's the first time you're using pwm on this machine. Let's take a little
        moment to set things up before we begin."""))
    db_uri = input('Which database do you want to use (default: local sqlite at ' +
        '~/.pwm/db.sqlite) ').strip() or 'local'
    rc_dir = os.path.dirname(config_file)

    if db_uri == 'local':
        db_path = 'db.sqlite'
    else:
        db_path = db_uri

    config_parser = RawConfigParser()
    config_parser.add_section('pwm')
    config_parser.set('pwm', 'database', db_path)

    with open(config_file, 'w') as config_file_fh:
        config_parser.write(config_file_fh)


def _read_config(config_file):
        defaults = {
            'server-certificate': None,
            'client-certificate': None,
            'client-key': None,
        }
        config_parser = RawConfigParser(defaults=defaults)
        config = {}
        config_parser.read(config_file)
        db_path = config_parser.get('pwm', 'database')
        config['database'] = os.path.join(os.path.dirname(config_file), db_path)

        client_certificate = config_parser.get('pwm', 'client-certificate')
        client_key = config_parser.get('pwm', 'client-key')
        if client_certificate and client_key:
            client_certificate_path = os.path.join(os.path.dirname(config_file), client_certificate)
            client_key_path = os.path.join(os.path.dirname(config_file), client_key)
            config['auth'] = (client_certificate_path, client_key_path)

        if config_parser.get('pwm', 'server-certificate'):
            config['server_certificate'] = os.path.join(os.path.dirname(config_file), config_parser.get('pwm', 'server-certificate'))
        return config


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

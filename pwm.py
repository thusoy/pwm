import argparse
import getpass
import hashlib
import logging.config
import os
import requests
import sys
import textwrap
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from logging import getLogger

try:
    from configparser import RawConfigParser
    from http.client import HTTPConnection
except:
    # python 2
    from ConfigParser import RawConfigParser
    from httplib import HTTPConnection
    input = raw_input


Base = declarative_base()
_logger = getLogger('pwm')


class DomainPassword(Base):
    __tablename__ = 'domainpassword'
    id = sa.Column(sa.Integer, primary_key=True)
    domain = sa.Column(sa.String(30))
    salt = sa.Column(sa.String(128))


    def __init__(self, **kwargs):
        super(DomainPassword, self).__init__(**kwargs)
        if not 'salt' in kwargs:
            self.new_salt()


    def new_salt(self):
        self.salt = os.urandom(128).encode('base64')


    def derive_domain_key(self, master_password):
        bytes = ('%s:%s:%s' % (master_password, self.domain, self.salt)).encode('utf8')
        key = hashlib.sha1(bytes).hexdigest()
        return key


    def __repr__(self):
        return 'DomainPassword(domain=%s, salt=%s)' % (self.domain, self.salt)


def main():
    args = get_args()
    pwm = PWM(config_file=args.config_file)
    domain_password = pwm.get_domain_salt(args.domain)
    master_password = getpass.getpass('Enter your master password: ')
    print(domain_password.derive_domain_key(master_password))


def get_args():
    argparser = argparse.ArgumentParser(prog='pwm')
    argparser.add_argument('domain',
        help='The domain to retrieve the password for',
    )
    argparser.add_argument('-v', '--verbose', action='store_true',
        help='Increase verbosity',
    )
    default_config_file = os.path.join(os.path.expanduser('~'), '.pwm', 'config')
    argparser.add_argument('-c', '--config-file', metavar='<config-file>',
        help='Path to config file to use. Default: %(default)s',
        default=default_config_file,
    )
    args = argparser.parse_args()
    _init_logging(verbose=args.verbose)
    return args


class PWM(object):

    def __init__(self, config_file=None):
        if not os.path.exists(config_file):
            if not os.path.exists(os.path.dirname(config_file)):
                os.makedirs(os.path.dirname(config_file))
            self.run_setup(config_file)
        self.read_config(config_file)


    def read_config(self, config_file):
        defaults = {
            'server-certificate': None,
            'client-certificate': None,
            'client-key': None,
        }
        config_parser = RawConfigParser(defaults=defaults)
        config = {}
        config_parser.read(config_file)
        config['database'] = config_parser.get('pwm', 'database')

        client_certificate = config_parser.get('pwm', 'client-certificate')
        client_key = config_parser.get('pwm', 'client-key')
        if client_certificate and client_key:
            client_certificate_path = os.path.join(os.path.dirname(config_file), client_certificate)
            client_key_path = os.path.join(os.path.dirname(config_file), client_key)
            config['auth'] = (client_certificate_path, client_key_path)

        if config_parser.get('pwm', 'server-certificate'):
            config['server_certificate'] = os.path.join(os.path.dirname(config_file), config_parser.get('pwm', 'server-certificate'))
        self.config = config


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


    def get_domain_salt(self, domain):
        protocol = self.config['database'].split(':', 1)[0]
        if protocol in ('https', 'http'):
            return self.get_salt_from_rest_api(domain)
        else:
            return self.get_salt_from_db(domain)


    def get_salt_from_rest_api(self, domain):
        request_args = {
            'params': {'domain': domain}
        }
        verify = True
        server_certificate = self.config.get('server_certificate')
        if server_certificate:
            verify = os.path.join(os.path.dirname(server_certificate), server_certificate)
            _logger.debug('Pinning server with certificate at %s', verify)

        # Test for SNI support on python 2
        if sys.version_info < (3, 0, 0):
            try:
                import urllib3.contrib.pyopenssl
                urllib3.contrib.pyopenssl.inject_into_urllib3()
            except ImportError:
                _logger.warning("Running on python 2 without SNI support, can't verify server certificates.")
                verify = False
        request_args['verify'] = verify

        if self.config.get('auth'):
            request_args['cert'] = self.config['auth']
        response = requests.get(self.config['database'] + '/get', **request_args)
        domain_password = DomainPassword(domain=domain, salt=response.json()['salt'])
        return domain_password


    def get_salt_from_db(self, domain):
        session = self.get_db_session()
        domain_password = self.get_salt(session, domain)
        return domain_password


    def get_salt(self, session, domain):
        domain_password = session.query(DomainPassword).filter(DomainPassword.domain == domain).first()
        if domain_password is None:
            domain_password = DomainPassword(domain=domain)
            session.add(domain_password)
            session.commit()
        return domain_password


    def get_db_session(self):
        db = sa.create_engine(self.config['database'])
        DBSession = sessionmaker(bind=db)
        session = DBSession()
        return session


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

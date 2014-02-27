import argparse
import getpass
import hashlib
import httplib
import logging.config
import os
import requests
import textwrap
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from logging import getLogger

try:
    import configparser
except:
    # python 2
    import ConfigParser as configparser
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
        self.new_salt()


    def new_salt(self):
        self.salt = os.urandom(128).encode('base64')


    def derive_domain_key(self, master_password):
        key_bytes = hashlib.sha1('%s:%s' % (master_password, self.domain)).digest()
        return key_bytes.encode('hex')


    def __repr__(self):
        return 'DomainPassword(domain=%s, salt=%s)' % (self.domain, self.salt)



def main():
    args = get_args()
    domain_password = get_domain_password(args)
    master_password = getpass.getpass('Enter your master password: ')
    print domain_password.derive_domain_key(master_password)


def get_args():
    argparser = argparse.ArgumentParser(prog='pwm')
    argparser.add_argument('domain',
        help='The domain to retrieve the password for',
    )
    argparser.add_argument('-v', '--verbose', action='store_true',
        help='Increase verbosity',
    )
    rc_dir = os.path.join(os.path.expanduser('~'), '.pwm')
    args = argparser.parse_args()
    _init_logging(verbose=args.verbose)
    if not os.path.exists(rc_dir):
        os.makedirs(rc_dir)
        run_setup()
    config = read_config()
    args.database = config.get('pwm', 'database')
    client_certificate = os.path.join(rc_dir, config.get('pwm', 'certificate'))
    client_key = os.path.join(rc_dir, config.get('pwm', 'key'))
    args.auth = (client_certificate, client_key)
    return args


def run_setup():
    print textwrap.dedent("""\
        Hi, it looks like it's the first time you're using pwm on this machine. Let's take a little
        moment to set things up before we begin.""")
    db_uri = input('Which database do you want to use? Default: local') or 'local'
    rc_dir = os.path.join(os.path.expanduser('~'), '.pwm')

    if db_uri == 'local':

        # normalize windows-style paths for sqlalchemy:
        rc_dir = rc_dir.replace('\\', '/')

        # Create the local database
        db_uri = 'sqlite:///%s/db.sqlite' % rc_dir
        db = sa.create_engine(db_uri)
        Base.metadata.create_all(db)

    config = configparser.RawConfigParser()
    config.add_section('pwm')
    config.set('pwm', 'database', db_uri)

    with open(os.path.join(rc_dir, 'config'), 'w') as configfile:
        config.write(configfile)


def read_config():
    config_file = os.path.join(os.path.expanduser('~'), '.pwm', 'config')
    config = configparser.RawConfigParser()
    config.read(config_file)
    return config


def get_domain_password(args):
    protocol = args.database.split(':', 1)[0]
    if protocol in ('https', 'http'):
        return get_salt_from_rest_api(args.database, args.domain, auth=args.auth)
    else:
        return get_salt_from_db(args.database, args.domain)


def get_salt_from_rest_api(api_url, domain, auth):
    payload = {'domain': domain}
    response = requests.get(api_url + '/get', params=payload)
    domain_password = DomainPassword(domain=domain, salt=response.json()['salt'])
    return domain_password


def get_salt_from_db(database, domain):
    session = get_db_session(database)
    domain_password = get_salt(session, domain)
    return domain_password


def get_salt(session, domain):
    domain_password = session.query(DomainPassword).filter(DomainPassword.domain == domain).first()
    if domain_password is None:
        domain_password = DomainPassword(domain=domain)
        session.add(domain_password)
        session.commit()
    return domain_password


def get_db_session(database):
    db = sa.create_engine(database)
    DBSession = sessionmaker(bind=db)
    session = DBSession()
    return session


def _init_logging(verbose=False):
    """ Initialize loggers. """
    config = {
        'version': 1,
        'formatters': {
            'normal': {
                'format': '%(asctime)s %(levelname)-10s %(name)s %(message)s',
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'normal',
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
    httplib.HTTPConnection.debuglevel = 1 if verbose else 0

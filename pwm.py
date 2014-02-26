import argparse
import getpass
import hashlib
import os
import textwrap
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

try:
    import configparser
except:
    # python 2
    import ConfigParser as configparser
    input = raw_input


Base = declarative_base()


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
    rc_dir = os.path.join(os.path.expanduser('~'), '.pwm')
    args = argparser.parse_args()
    if not os.path.exists(rc_dir):
        os.makedirs(rc_dir)
        run_setup()
    config = read_config()
    args.database = config.get('pwm', 'database')
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
    session = get_db_session(args.database)
    domain_password = get_salt(session, args.domain)
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

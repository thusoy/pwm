import argparse
import getpass
import hashlib
import os
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
db = sa.create_engine('sqlite:///testdb.sqlite')


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


Base.metadata.create_all(db)

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
    argparser.add_argument('-d', '--database', metavar='<database>',
        help='The database to store the salts in',
    )
    return argparser.parse_args()


def get_domain_password(args):
    session = get_db_session(args.database)
    dp = get_salt(session, args.domain)
    return dp


def get_salt(session, domain):
    domain_password = session.query(DomainPassword).filter(DomainPassword.domain == domain).first()
    if domain_password is None:
        domain_password = DomainPassword(domain=domain)
        session.add(domain_password)
        session.commit()
    return domain_password


def get_db_session(database):
    DBSession = sessionmaker(bind=db)
    session = DBSession()
    return session

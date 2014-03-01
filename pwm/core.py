from . import encoding
from ._compat import RawConfigParser
from .exceptions import DuplicateDomainException

import base64
import getpass
import hashlib
import requests
import os
import sys
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from logging import getLogger


Base = declarative_base()
_logger = getLogger('pwm')


class Domain(Base):
    """ Domain objects hold all the data for a given domain name.

    Domain names can in theory be anything, from user selected aliases to actual domain names like
    facebook.com or twitter.com, however the latter is probably recommended as it opens up the
    possiblity to automatically extract the relevant objects if the user visists the site, such as
    in a browser extension of similar.

    :param name: The identifier for this domain.
    :param charset: The characters the key will consist of.
    :param length: The length of the computed key. Can be useful if the site imposes restrictions
        on password length.
    """
    __tablename__ = 'domain'
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(30), unique=True)
    salt = sa.Column(sa.String(128))
    charset = sa.Column(sa.String(128))
    encoding_length = sa.Column(sa.Integer())


    def __init__(self, **kwargs):
        super(Domain, self).__init__(**kwargs)
        if not 'encoding_length' in kwargs:
            self.encoding_length = encoding.DEFAULT_LENGTH
        if not 'charset' in kwargs:
            self.charset = encoding.DEFAULT_CHARSET
        if not 'salt' in kwargs:
            self.new_salt()


    def new_salt(self):
        self.salt = base64.b64encode(os.urandom(32))


    def derive_key(self, master_password):
        """ Computes the key from the salt and the master password. """
        encoder = encoding.Encoder(self.charset)
        bytes = ('%s:%s:%s' % (master_password, self.name, self.salt)).encode('utf8')
        return encoder.encode(hashlib.sha1(bytes), self.encoding_length)


    def get_key(self):
        """ Fetches the key for the domain. Prompts the user for password.

        Thin wrapper around `Domain.derive_key`.
        """
        master_password = getpass.getpass('Enter your master password: ')
        return self.derive_key(master_password)


    def __repr__(self):
        return 'Domain(name=%s, salt=%s, charset=%s, length=%s)' \
                % (self.name, self.salt, self.charset, self.encoding_length)


class PWM(object):
    """ This is the main object for interfacing with a pwm database. """

    def __init__(self, config_file=None, session=None):
        if not os.path.exists(config_file):
            if not os.path.exists(os.path.dirname(config_file)):
                os.makedirs(os.path.dirname(config_file))
            self.run_setup(config_file)
        self._read_config(config_file)
        self.session = session


    def _read_config(self, config_file):
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


    def search(self, query):
        """ Search the database for the given query. Will find partial matches. """
        if not self.session:
            self._init_db_session()
        results = self.session.query(Domain).filter(Domain.name.ilike('%%%s%%' % query)).all()
        return results


    def get_domain(self, domain):
        """ Get the :class:`Domain <pwm.Domain>` object from a name.

        :param domain: The domain name to fetch the object for.
        """
        protocol = self.config['database'].split(':', 1)[0]
        if protocol in ('https', 'http'):
            return self._get_domain_from_rest_api(domain)
        else:
            return self._get_domain_from_db(domain)


    def _get_domain_from_rest_api(self, domain):
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
        domain = Domain(name=domain, salt=response.json()['salt'])
        return domain


    def _get_domain_from_db(self, domain_name):
        if not self.session:
            self._init_db_session()
        domain = self.session.query(Domain).filter(Domain.name == domain_name).first()
        return domain


    def create_domain(self, domain_name, charset=encoding.DEFAULT_CHARSET, length=encoding.DEFAULT_LENGTH):
        full_charset = encoding.lookup_alphabet(charset)
        domain = Domain(name=domain_name, encoding_length=length, charset=full_charset)
        if not self.session:
            self._init_db_session()
        try:
            self.session.add(domain)
            self.session.commit()
        except Exception as ex:
            _logger.warn("Inserting new domain failed: %s", ex)
            raise DuplicateDomainException
        return domain


    def _init_db_session(self):
        db = sa.create_engine(self.config['database'])
        DBSession = sessionmaker(bind=db)
        self.session = DBSession()

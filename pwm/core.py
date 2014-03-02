from . import encoding
from ._compat import RawConfigParser
from .exceptions import DuplicateDomainException, NotReadyException

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
    username = sa.Column(sa.String(40))


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

        Thin wrapper around :func:`Domain.derive_key <pwm.core.Domain.derive_key>`.
        """
        master_password = getpass.getpass('Enter your master password: ')
        return self.derive_key(master_password)


    def __repr__(self): # pragma: no cover
        return 'Domain(name=%s, salt=%s, charset=%s, length=%s)' \
                % (self.name, self.salt, self.charset, self.encoding_length)


def _db_uri_from_path(database_path):
    """ Get a SQLAlchemy compatible database URI given a path to a file. """
    return 'sqlite:///%s' % database_path


def _uses_db(func):
    """ Use as a decorator for operations on the database, to ensure connection setup and
    teardown.
    """
    def wrapped_func(self, *args, **kwargs):
        if not self.session:
            self._init_db_session()
        ret = func(self, *args, **kwargs)
        try:
            self.session.commit()
        except:
            self.session.rollback()
            raise
        finally:
            self.session.close()
        return ret

    return wrapped_func


class PWM(object):
    """ This is the main object for interfacing with a pwm database.

    :param database_path: The absolute path to the database to use. If not given or None,
        :func:`PWM.bootstrap <pwm.core.PWM.bootstrap` must be called before doing any operations
        that operate on the database. If there's no file at the given path, a new database will be
        created there.
    """

    def __init__(self, database_path=None):
        self.session = None
        self.database_uri = None
        if database_path:
            # Bootstrap a new database if it doesn't exists already
            self.database_uri = _db_uri_from_path(database_path)
            if not os.path.exists(database_path):
                self.bootstrap(database_path)


    def bootstrap(self, database_path):
        """ Initialize a database.

        :param database_path: The absolute path to the database to initialize.
        """
        self.database_uri = _db_uri_from_path(database_path)
        db = sa.create_engine(self.database_uri)
        Base.metadata.create_all(db)


    @_uses_db
    def search(self, query):
        """ Search the database for the given query. Will find partial matches. """
        results = self.session.query(Domain).filter(Domain.name.ilike('%%%s%%' % query)).all()
        return results


    @_uses_db
    def get_domain(self, domain):
        """ Get the :class:`Domain <pwm.Domain>` object from a name.

        :param domain: The domain name to fetch the object for.
        """
        protocol = self.database_uri.split(':', 1)[0]
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


    def create_domain(self, domain_name, username=None, charset=encoding.DEFAULT_CHARSET,
            length=encoding.DEFAULT_LENGTH):
        """ Create a new domain entry in the database.

        :param username: The username to associate with this domain.
        :param charset: A character set restriction to impose on keys generated for this domain.
        :param length: The length of the generated key, in case of restrictions on the site.
        """
        # Wrap the actual implementation to do some error handling
        try:
            return self._create_domain(domain_name, username, charset, length)
        except Exception as ex:
            _logger.warn("Inserting new domain failed: %s", ex)
            raise DuplicateDomainException


    @_uses_db
    def _create_domain(self, domain_name, username, charset, length):
        full_charset = encoding.lookup_alphabet(charset)
        domain = Domain(name=domain_name, username=username, encoding_length=length,
            charset=full_charset)
        self.session.add(domain)
        return domain


    def _init_db_session(self):
        if not self.database_uri:
            raise NotReadyException()
        db = sa.create_engine(self.database_uri)
        DBSession = sessionmaker(bind=db, expire_on_commit=False)
        self.session = DBSession()

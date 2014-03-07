from . import encoding
from .exceptions import DuplicateDomainException, NotReadyException, NoSuchDomainException

import base64
import decorator
import getpass
import hashlib
import math
import os
import requests
import sqlalchemy as sa
import sys
import time
import traceback
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from logging import getLogger


Base = declarative_base()
_logger = getLogger('pwm.core')


class Domain(Base):
    """ Domain objects hold all the data for a given domain name.

    Domain names can in theory be anything, from user selected aliases to actual domain names like
    facebook.com or twitter.com, however the latter is probably recommended as it opens up the
    possiblity to automatically extract the relevant objects if the user visists the site, such as
    in a browser extension of similar.

    :param name: The identifier for this domain.
    :param alpabet: The alpabet to restrict key contents to. Default: 'full'
    :param key_length: The length of the computed key. Can be useful if the site imposes restrictions
        on password length. Default: 16
    """
    DEFAULT_KEY_LENGTH = 16
    DEFAULT_ALPHABET = 'full'

    __tablename__ = 'domain'
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(30), unique=True)
    salt = sa.Column(sa.String(128))
    charset = sa.Column(sa.String(128))
    key_length = sa.Column(sa.Integer())
    username = sa.Column(sa.String(40))


    def __init__(self, alphabet=DEFAULT_ALPHABET, key_length=DEFAULT_KEY_LENGTH, **kwargs):
        if alphabet:
            self.charset = encoding.lookup_alphabet(alphabet)
        super(Domain, self).__init__(key_length=key_length, **kwargs)
        if not 'salt' in kwargs:
            self.new_salt()


    @property
    def entropy(self):
        unique_chars = len(set(self.charset))
        entropy = -math.log(1.0/(unique_chars**self.key_length), 2)
        return entropy


    def new_salt(self):
        self.salt = base64.b64encode(os.urandom(32))


    def derive_key(self, master_password):
        """ Computes the key from the salt and the master password. """
        encoder = encoding.Encoder(self.charset)
        bytes = ('%s:%s:%s' % (master_password, self.name, self.salt)).encode('utf8')
        start_time = time.clock()
        key = encoder.encode(hashlib.sha1(bytes), self.key_length)
        derivation_time_in_s = time.clock() - start_time
        _logger.debug('Key derivation took %.2fms', derivation_time_in_s*1000)
        return key


    def get_key(self):
        """ Fetches the key for the domain. Prompts the user for password.

        Thin wrapper around :func:`Domain.derive_key <pwm.core.Domain.derive_key>`.
        """
        master_password = getpass.getpass('Enter your master password: ')
        return self.derive_key(master_password)


    def __repr__(self): # pragma: no cover
        return 'Domain(name=%s, salt=%s, charset=%s, key_length=%s)' \
                % (self.name, self.salt, self.charset, self.key_length)


def _db_uri_from_path(database_path):
    """ Get a SQLAlchemy compatible database URI given a path to a file. """
    return 'sqlite:///%s' % database_path


@decorator.decorator
def _uses_db(func, self, *args, **kwargs):
    """ Use as a decorator for operations on the database, to ensure connection setup and
    teardown. Can only be used on methods on objects with a `self.session` attribute.
    """
    if not self.session:
        _logger.debug('Creating new db session')
        self._init_db_session()
    try:
        ret = func(self, *args, **kwargs)
        self.session.commit()
    except:
        self.session.rollback()
        tb = traceback.format_exc()
        _logger.debug(tb)
        raise
    finally:
        _logger.debug('Closing db session')
        self.session.close()
    return ret


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
            _logger.debug('Using database at %s', database_path)


    def bootstrap(self, database_path):
        """ Initialize a database.

        :param database_path: The absolute path to the database to initialize.
        """
        _logger.debug("Bootstrapping new database at %s", database_path)
        self.database_uri = _db_uri_from_path(database_path)
        db = sa.create_engine(self.database_uri)
        Base.metadata.create_all(db)


    @_uses_db
    def search(self, query):
        """ Search the database for the given query. Will find partial matches. """
        results = self.session.query(Domain).filter(Domain.name.ilike('%%%s%%' % query)).all()
        return results


    @_uses_db
    def get_domain(self, domain_name):
        """ Get the :class:`Domain <pwm.Domain>` object from a name.

        :param domain_name: The domain name to fetch the object for.
        :returns: The :class:`Domain <pwm.core.Domain>` class with this domain_name if found, else
            None.
        """
        protocol = self.database_uri.split(':', 1)[0]
        if protocol in ('https', 'http'):
            return self._get_domain_from_rest_api(domain_name)
        else:
            return self._get_domain_from_db(domain_name)


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
        domain = self.session.query(Domain).filter(Domain.name == domain_name).first()
        return domain


    @_uses_db
    def modify_domain(self, domain_name, new_salt=False, username=None):
        """ Modify an existing domain.

        :param domain_name: The name of the domain to modify.
        :param new_salt: Whether to generate a new salt for the domain.
        :param username: If given, change domain username to this value.
        :returns: The modified :class:`Domain <pwm.core.Domain>` object.
        """
        domain = self._get_domain_from_db(domain_name)
        if domain is None:
            raise NoSuchDomainException
        if new_salt:
            _logger.info("Generating new salt..")
            domain.new_salt()
        if username is not None:
            domain.username = username
        return domain


    def create_domain(self, domain_name, username=None, alphabet=Domain.DEFAULT_ALPHABET,
            length=Domain.DEFAULT_KEY_LENGTH):
        """ Create a new domain entry in the database.

        :param username: The username to associate with this domain.
        :param alphabet: A character set restriction to impose on keys generated for this domain.
        :param length: The length of the generated key, in case of restrictions on the site.
        """
        # Wrap the actual implementation to do some error handling
        try:
            return self._create_domain(domain_name, username, alphabet, length)
        except Exception as ex:
            _logger.warn("Inserting new domain failed: %s", ex)
            raise DuplicateDomainException


    @_uses_db
    def _create_domain(self, domain_name, username, alphabet, length):
        domain = Domain(name=domain_name, username=username, key_length=length,
            alphabet=alphabet)
        self.session.add(domain)
        return domain


    def _init_db_session(self):
        if not self.database_uri:
            raise NotReadyException()
        db = sa.create_engine(self.database_uri)
        DBSession = sessionmaker(bind=db, expire_on_commit=False)
        self.session = DBSession()

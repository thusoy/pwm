import pwm

import os
import tempfile
import unittest
import textwrap
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker


class PWMTest(unittest.TestCase):

    def setUp(self):
        self.tmp_config = tempfile.NamedTemporaryFile(delete=False)
        self.tmp_config.write(textwrap.dedent("""\
        [pwm]
        database = sqlite://
        """).encode('utf-8'))
        self.tmp_config.close()
        db = sa.create_engine('sqlite://')
        pwm.Base.metadata.create_all(db)
        DBSession = sessionmaker(bind=db)
        self.session = DBSession()
        self.session.add(pwm.Domain(name='example.com', salt='NaCl'))
        self.session.commit()
        self.pwm = pwm.PWM(config_file=self.tmp_config.name, session=self.session)


    def tearDown(self):
        os.remove(self.tmp_config.name)


    def test_get_salt(self):
        # sha1 hexdigest of secret:example.com:NaCl
        expected = 'e7b5038ba1a704e19b8326bc9592329d73ed7351'
        salt = self.pwm.get_domain('example.com').salt
        self.assertEqual(salt, 'NaCl')

    def test_add_domain(self):
        new_domain = self.pwm.get_domain('othersite.com')
        key = new_domain.derive_key('secret')

        # should now get the same key on second attempt
        db_domain = pwm.Domain(name='othersite.com', salt=new_domain.salt)
        self.assertEqual(db_domain.derive_key('secret'), key)

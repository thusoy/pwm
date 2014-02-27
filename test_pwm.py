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
        """))
        self.tmp_config.close()
        db = sa.create_engine('sqlite://')
        pwm.Base.metadata.create_all(db)
        DBSession = sessionmaker(bind=db)
        self.session = DBSession()
        self.session.add(pwm.Domain(domain='example.com', salt='NaCl'))
        self.session.commit()
        self.pwm = pwm.PWM(config_file=self.tmp_config.name, session=self.session)


    def tearDown(self):
        os.remove(self.tmp_config.name)


    def test_get_salt(self):
        # sha1 hexdigest of secret:example.com:NaCl
        expected = 'e7b5038ba1a704e19b8326bc9592329d73ed7351'
        salt = self.pwm.get_domain_salt('example.com').salt
        self.assertEqual(salt, 'NaCl')

    def test_add_domain(self):
        new_dp = self.pwm.get_domain_salt('othersite.com')
        key = new_dp.derive_key('secret')

        # should now get the same key on second attempt
        dp = pwm.Domain(domain='othersite.com', salt=new_dp.salt)
        self.assertEqual(dp.derive_key('secret'), key)

from pwm import cli, Domain

import os
import sys
import tempfile
import unittest
from collections import namedtuple
from contextlib import contextmanager
from mock import MagicMock, patch

CLIRun = namedtuple('CLIRun', ['pwm', 'sys'])

def run_cli_args(args, pwm=None):
    """ Run the CLI with the args given.

    :param args: A string like 'get example.com' to be tested.
    :returns: A CLIRun tuple with two attributes, `sys` and `pwm`, which holds mock objects from
        the execution.
    """
    if pwm is None:
        pwm = MagicMock()
    pwm_constructor = MagicMock(return_value=pwm)
    sys_mock = MagicMock()
    getpass = MagicMock(return_value='secret')
    pwm_patch = patch('pwm.cli.PWM', pwm_constructor)
    sys_patch = patch('pwm.cli.sys', sys_mock)
    getpass_patch = patch('pwm.core.getpass', getpass)
    with pwm_patch, sys_patch, getpass_patch:
        print("running CLI with args: %s" % args.split())
        cli.main(args.split())
    print("Sysmock: %s" % sys_mock.mock_calls)
    return CLIRun(pwm=pwm, sys=sys_mock)


@contextmanager
def ignored(*exceptions):
    """ Context manager you can use when you're doing something risky, but don't care if it fails.

    Use like this:

        > with ignored(IOError):
        >   os.remove('debug.log')

    If file doesn't exist it will be silently ignored.
    """
    try:
        yield
    except exceptions:
        pass


class CLIInitTest(unittest.TestCase):

    def tearDown(self):
        with ignored(OSError):
            os.remove('mytestdb.sqlite')


    def test_init(self):
        cli_run = run_cli_args('init mytestdb.sqlite')
        cli_run.sys.exit.assert_called_with(0)
        self.assertTrue(os.path.exists('mytestdb.sqlite'))


class BadCLIInitTest(unittest.TestCase):

    def setUp(self):
        self.existing_file = tempfile.NamedTemporaryFile(delete=False)
        self.existing_file.write('spam and eggs')
        self.existing_file.close()


    def tearDown(self):
        with ignored(OSError):
            os.remove(self.existing_file)


    def test_init_on_existing_file(self):
        cli_run = run_cli_args('init %s' % self.existing_file.name)
        cli_run.sys.exit.assert_called_with(1)


class CLITest(unittest.TestCase):

    def setUp(self):
        self.tmp_db = tempfile.NamedTemporaryFile(delete=False)
        self.tmp_db.close()
        cli_run = run_cli_args('init %s' % self.tmp_db.name)


    def tearDown(self):
        os.remove(self.tmp_db.name)


    def _run_with_db(self, args):
        db_args = '--database %s -v ' % self.tmp_db.name
        return run_cli_args(db_args + args)


    def test_create_command(self):
        cli_run = self._run_with_db('create example.com')
        cli_run.pwm.create_domain.assert_called_with('example.com')
        cli_run.sys.exit.assert_called_with(0)


    def test_get_domain_miss(self):
        pwm_attrs = {
            'get_domain.return_value': None,
        }
        pwm = MagicMock(**pwm_attrs)
        cli_run = self._run_with_db('get example.com', pwm=pwm)
        pwm.get_domain.assert_called_with('example.com')
        cli_run.sys.exit.assert_called_with(1)


    def test_get_domain_success(self):
        domain = Domain(name='example.com', salt='NaCl')
        pwm_attrs = {
            'get_domain.return_value': domain,
        }
        cli_run = run_cli_args('get example.com')
        cli_run.sys.exit.assert_called_with(0)
        print(cli_run.sys.stdout.write.mock_calls)
        self.fail()


    def test_search(self):
        cli_run = self._run_with_db('search example.com')
        cli_run.pwm.search.assert_called_with('example.com')
        cli_run.sys.exit.assert_called_with(1)

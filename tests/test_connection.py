from . import *
from jyboss import *
from jyboss.exceptions import ContextError


class TestConnection(JBossTest):
    def setUp(self):
        print ('Running test %s' % self._testMethodName)

    @unittest.skip("testing skipping")
    @jboss_context(mode=MODE_STANDALONE)
    def test_connect_managed(self):
        with self.connection:
            print cd("/")
            print ls()

    @unittest.skip("testing skipping")
    @jboss_context(mode=MODE_STANDALONE)
    def test_connect_unmanaged(self):
        self.connection.connect()
        print cd("/")
        print ls()
        disconnect()

    @unittest.skip("testing skipping")
    def test_connection_exists(self):
        # TODO review test
        standalone.connect()
        print ls('')
        with self.assertRaises(ContextError):
            standalone.connect()

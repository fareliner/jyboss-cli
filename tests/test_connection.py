import unittest
from jyboss import *


class TestConnection(unittest.TestCase):
    def setUp(self):
        print ('Running test %s' % self._testMethodName)
        ctx = JyBossCLI.context()
        ctx.jboss_home = 'c:\\opt\\keycloak\\keycloak-1.9.8.Final'

    def test_connect_managed(self):
        with ServerConnection():
            print cd("/")
            print ls()

    def test_connect_unmanaged(self):
        connect()
        print cd("/")
        print ls()
        disconnect()

    def test_connection_exists(self):
        connect()
        print ls('')
        with self.assertRaises(ContextError):
            connect()

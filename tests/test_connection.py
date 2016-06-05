import unittest
from jyboss import *


class TestConnection(unittest.TestCase):
    def test_connect_managed(self):
        with Connection():
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

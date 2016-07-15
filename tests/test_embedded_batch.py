import unittest
from jyboss import *


class TestEmbeddedBatch(unittest.TestCase):
    def setUp(self):
        print ('Running test %s' % self._testMethodName)
        ctx = JyBossCLI.context()
        ctx.jboss_home = 'c:\\opt\\keycloak\\keycloak-1.9.8.Final'
        ctx.config_file = 'standalone-ha.xml'

    def test_connect_managed(self):
        with EmbeddedConnection():
            print cd('/subsystem=jgroups')
            print ls()
            batch()
            batch_add_cmd('/subsystem=jgroups/stack=tcpping:add()')
            batch_add_cmd('/subsystem=jgroups/stack=tcpping/transport=TCP:add(type="TCP",socket-binding=jgroups-tcp)')
            cmd('run-batch')

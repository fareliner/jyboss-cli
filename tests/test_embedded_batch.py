import unittest
from jyboss import *


class TestEmbeddedBatch(unittest.TestCase):
    def setUp(self):
        print ('Running test %s' % self._testMethodName)
        ctx = JyBossCLI.instance()
        ctx.jboss_home = 'c:\\opt\\keycloak\\keycloak-1.9.8.Final'
        ctx.config_file = 'standalone-ha.xml'

    def test_batch_create(self):
        with EmbeddedConnection():
            cd('/subsystem=jgroups', silent=True)
            batch()
            batch_add_cmd('/subsystem=jgroups/stack=tcpping:add()')
            batch_add_cmd('/subsystem=jgroups/stack=tcpping/transport=TCP:add(type="TCP",socket-binding=jgroups-tcp)')
            r = batch_run(silent=True)
            print('noninteractive result: \n%s' % json.dumps(r, indent=4))

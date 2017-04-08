from . import *
import simplejson as json

from jyboss import *
from jyboss.command import batch


class TestEmbeddedBatch(JBossTest):
    def setUp(self):
        print ('Running test %s' % self._testMethodName)

    @jboss_context(config_file='test-embedded-batch-create.xml', mode=MODE_EMBEDDED)
    def test_batch_create(self):
        with self.connection:
            cd('/subsystem=jgroups', silent=True)
            ls()
            batch.start()
            batch.add_cmd('/subsystem=jgroups/stack=tcpping:add()')
            batch.add_cmd('/subsystem=jgroups/stack=tcpping/transport=TCP:add(type="TCP",socket-binding=jgroups-tcp)')
            r = batch.run(silent=True)
            print('result: \n%s' % json.dumps(r, indent=4))

from tests import *

from jyboss.command import InfinispanModule


class TestInfinispanModule(JBossTest):
    def setUp(self):
        super(TestInfinispanModule, self).setUp()

    @jboss_context(mode=MODE_EMBEDDED, interactive=False)
    def test_container_added(self):
        with self.connection:
            args = self.load_yaml()
            changes = InfinispanModule(self.context).apply(**args)
            self.context.interactive = True
            print('container.present(add): %r' % changes)
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            self.assertTrue(1, 'subsystem' in changes[0])
            self.assertEquals('infinispan', changes[0]['subsystem'])
            self.assertTrue(1, 'changes' in changes[0])
            self.assertEqual(1, len(changes[0]['changes']))
            pass

from . import *

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
            print('container.present(add): \n%s\n----\n' % json.dumps(changes, indent=2))
            self.assertIsNotNone(changes)
            self.assertEqual(3, len(changes))
            change = changes[0]
            self.assertTrue('cache-container' in change)
            self.assertEquals('FancyCache', change['cache-container'])
            self.assertTrue('action' in change)
            self.assertEquals('add', change['action'])
            # test the next on
            change = changes[1]
            self.assertTrue('cache-container' in change)
            self.assertEquals('web', change['cache-container'])
            self.assertTrue('action' in change)
            self.assertEquals('update', change['action'])
            self.assertTrue('changes' in change)
            self.assertEquals(1, len(change['changes']))
            # test the next on
            change = changes[2]
            self.assertTrue('cache-container' in change)
            self.assertEquals('NotSoFancy', change['cache-container'])
            self.assertTrue('action' in change)
            self.assertEquals('add', change['action'])
            self.assertTrue('changes' in change)
            self.assertEquals(4, len(change['changes']))
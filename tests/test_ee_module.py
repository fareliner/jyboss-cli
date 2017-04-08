from . import *

from jyboss.command import EEModule


class TestEEModule(JBossTest):
    def setUp(self):
        super(TestEEModule, self).setUp()

    @jboss_context(mode=MODE_EMBEDDED, interactive=False)
    def test_default_datasource_updated(self):
        with self.connection:
            args = self.load_yaml()
            changes = EEModule(self.context).apply(**args)
            self.context.interactive = True
            print('ee.present(update): %r' % changes)
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            change = changes[0]
            self.assertTrue('service' in change)
            self.assertEqual('default-bindings', change['service'])
            self.assertTrue('changes' in change)
            self.assertEqual(1, len(change['changes']))
            action = change['changes'][0]
            self.assertTrue('action' in action)
            self.assertEqual('delete', action['action'])
            self.assertTrue('attribute' in action)
            self.assertEqual('datasource', action['attribute'])
            self.assertTrue('old_value' in action)
            # TODO validate that the xml configuration written reflects these changes
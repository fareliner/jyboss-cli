from tests import *

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
            self.assertTrue('ee' in changes)
            self.assertEqual(1, len(changes['ee']))
            self.assertEqual('default-bindings', changes['ee'][0]['service'])
            self.assertTrue('action' in changes['ee'][0])
            self.assertEqual('updated', changes['ee'][0]['action'])
            # TODO validate that the xml configuration written reflects these changes

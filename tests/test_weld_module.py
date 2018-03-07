from . import *

from jyboss.command import WeldModule


class TestWeldModule(JBossTest):
    def setUp(self):
        super(TestWeldModule, self).setUp()

    @jboss_context(config_file='standalone-weld-absent.xml', mode=MODE_EMBEDDED, interactive=False)
    def test_weld_added(self):
        with self.connection:
            args = self.load_yaml()
            changes = WeldModule(self.context).apply(**args)
            self.context.interactive = True
            print('weld.present(add): \n%s\n----\n' % json.dumps(changes, indent=2))
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            change = changes[0]
            self.assertTrue('subsystem' in change)
            self.assertEqual('weld', change['subsystem'])
            self.assertTrue('action' in change)
            self.assertEqual('add', change['action'])
            # TODO validate that the xml configuration written reflects these changes

    @jboss_context(config_file='standalone-weld-present.xml', mode=MODE_EMBEDDED, interactive=False)
    def test_weld_deleted(self):
        with self.connection:
            args = self.load_yaml()
            changes = WeldModule(self.context).apply(**args)
            self.context.interactive = True
            print('weld.present(delete): \n%s\n----\n' % json.dumps(changes, indent=2))
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            change = changes[0]
            self.assertTrue('subsystem' in change)
            self.assertEqual('weld', change['subsystem'])
            self.assertTrue('action' in change)
            self.assertEqual('delete', change['action'])
            # TODO validate that the xml configuration written reflects these changes

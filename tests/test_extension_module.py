from . import *

from jyboss.command import ExtensionModule


class TestExtensionModule(JBossTest):
    def setUp(self):
        super(TestExtensionModule, self).setUp()

    @jboss_context(mode=MODE_EMBEDDED, interactive=False)
    def test_extension_present(self):
        with self.connection:
            args = self.load_yaml()
            changes = ExtensionModule(self.context).apply(**args)
            self.context.interactive = True
            print('ext.present(): \n%s\n----\n' % json.dumps(changes, indent=2))
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            self.assertTrue('extension' in changes[0])
            self.assertTrue('action' in changes[0])
            self.assertEqual('add', changes[0]['action'])
            # TODO validate that the xml configuration written reflects these changes

    @jboss_context(mode=MODE_EMBEDDED, interactive=False)
    def test_extension_absent(self):
        with self.connection:
            args = self.load_yaml()
            changes = ExtensionModule(self.context).apply(**args)
            self.context.interactive = True
            print('ext.absent(): \n%s\n----\n' % json.dumps(changes, indent=2))
            self.assertIsNotNone(changes)
            self.assertEqual(2, len(changes))
            self.assertTrue('extension' in changes[1])
            self.assertTrue('action' in changes[1])
            self.assertEqual('delete', changes[1]['action'])
            # TODO validate that the xml configuration written reflects these changes

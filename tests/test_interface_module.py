from . import *

from jyboss.command import InterfaceModule


class TestInterfaceModule(JBossTest):
    def setUp(self):
        super(TestInterfaceModule, self).setUp()

    @jboss_context(mode=MODE_EMBEDDED, interactive=False)
    def test_interface_added(self):
        with self.connection:
            args = self.load_yaml()
            changes = InterfaceModule(self.context).apply(**args)
            self.context.interactive = True
            print('interfaces.present(add): \n%s\n----\n' % json.dumps(changes, indent=2))
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            change = changes[0]
            self.assertTrue('interface' in change)
            self.assertTrue('nictest', change['interface'])
            self.assertTrue('action' in change)
            self.assertEqual('add', change['action'])
            # TODO validate that the xml configuration written reflects these changes

    @jboss_context(mode=MODE_EMBEDDED, interactive=False)
    def test_interface_updated(self):
        with self.connection:
            args = self.load_yaml()
            changes = InterfaceModule(self.context).apply(**args)
            self.context.interactive = True
            print('interfaces.present(update): \n%s\n----\n' % json.dumps(changes, indent=2))
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            change = changes[0]
            self.assertTrue('interface' in change)
            self.assertTrue('public', change['interface'])
            self.assertTrue('action' in change)
            self.assertEqual('update', change['action'])
            # TODO validate that the xml configuration written reflects these changes

    @jboss_context(mode=MODE_EMBEDDED, interactive=False)
    def test_interface_deleted(self):
        with self.connection:
            args = self.load_yaml()
            changes = InterfaceModule(self.context).apply(**args)
            self.context.interactive = True
            print('interfaces.absent(): \n%s\n----\n' % json.dumps(changes, indent=2))
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            change = changes[0]
            self.assertTrue('interface' in change)
            self.assertTrue('public', change['interface'])
            self.assertTrue('action' in change)
            self.assertEqual('delete', change['action'])
            # TODO validate that the xml configuration written reflects these changes

    @jboss_context(mode=MODE_EMBEDDED, interactive=False)
    def test_interface_update_nic(self):
        with self.connection:
            args = self.load_yaml()
            changes = InterfaceModule(self.context).apply(**args)
            self.context.interactive = True
            print('interfaces.update(): \n%s\n----\n' % json.dumps(changes, indent=2))
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            change = changes[0]
            self.assertTrue('interface' in change)
            self.assertTrue('public', change['interface'])
            self.assertTrue('action' in change)
            self.assertEqual('update', change['action'])
            # TODO validate that the xml configuration written reflects these changes
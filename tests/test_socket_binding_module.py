from . import *

from jyboss.command import SocketBindingModule


class TestSocketBindingModule(JBossTest):
    def setUp(self):
        super(TestSocketBindingModule, self).setUp()

    @jboss_context(mode=MODE_EMBEDDED, interactive=False)
    def test_binding_add(self):
        with self.connection:
            args = self.load_yaml()
            changes = SocketBindingModule(self.context).apply(**args)
            self.context.interactive = True
            print('binding.present(added): %r' % changes)
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            self.assertTrue('socket-binding' in changes[0])
            self.assertTrue('action' in changes[0])
            self.assertEqual('add', changes[0]['action'])
            # TODO validate that the xml configuration written reflects these changes

    @jboss_context(mode=MODE_EMBEDDED, interactive=False)
    def test_binding_add_expression(self):
        with self.connection:
            args = self.load_yaml()
            changes = SocketBindingModule(self.context).apply(**args)
            self.context.interactive = True
            print('binding.present(added): %r' % changes)
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            self.assertTrue('socket-binding' in changes[0])
            self.assertTrue('action' in changes[0])
            self.assertEqual('add', changes[0]['action'])
            # TODO validate that the xml configuration written reflects these changes

    @jboss_context(mode=MODE_EMBEDDED, interactive=False)
    def test_binding_updated(self):
        with self.connection:
            args = self.load_yaml()
            changes = SocketBindingModule(self.context).apply(**args)
            self.context.interactive = True
            print('binding.present(added): %r' % changes)
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            self.assertTrue('socket-binding' in changes[0])
            self.assertTrue('action' in changes[0])
            self.assertEqual('update', changes[0]['action'])
            # TODO validate that the xml configuration written reflects these changes

    @jboss_context(mode=MODE_EMBEDDED, interactive=False)
    def test_binding_updated_expression(self):
        with self.connection:
            args = self.load_yaml()
            changes = SocketBindingModule(self.context).apply(**args)
            self.context.interactive = True
            print('binding.present(added): %r' % changes)
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            self.assertTrue('socket-binding' in changes[0])
            self.assertTrue('action' in changes[0])
            self.assertEqual('update', changes[0]['action'])
            # TODO validate that the xml configuration written reflects these changes

    @jboss_context(mode=MODE_EMBEDDED, interactive=False)
    def test_binding_delete_not_found(self):
        with self.connection:
            args = self.load_yaml()
            changes = SocketBindingModule(self.context).apply(**args)
            self.context.interactive = True
            print('binding.absent(not found): %r' % changes)
            self.assertIsNone(changes)

    @jboss_context(mode=MODE_EMBEDDED, interactive=False)
    def test_binding_delete(self):
        with self.connection:
            args = self.load_yaml()
            changes = SocketBindingModule(self.context).apply(**args)
            self.context.interactive = True
            print('binding.absent(deleted): %r' % changes)
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            self.assertTrue('socket-binding' in changes[0])
            self.assertTrue('action' in changes[0])
            self.assertEqual('delete', changes[0]['action'])
            # TODO validate that the xml configuration written reflects these changes

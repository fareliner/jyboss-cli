from . import *

from jyboss.command import JGroupsModule


class TestJGroupsModule(JBossTest):
    def setUp(self):
        super(TestJGroupsModule, self).setUp()

    @jboss_context(config_file='test_update_tcpping_properties.xml', mode=MODE_EMBEDDED, interactive=False)
    def test_update_tcpping_properties(self):
        with self.connection:
            args = self.load_yaml()
            changes = JGroupsModule(self.context).apply(**args)
            self.context.interactive = True
            print('stack.present(add): %r' % changes)
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            self.assertTrue('stack' in changes[0])

    @jboss_context(config_file='test_add_null_property.xml', mode=MODE_EMBEDDED, interactive=False)
    def test_add_null_property(self):
        with self.connection:
            args = self.load_yaml()
            changes = JGroupsModule(self.context).apply(**args)
            self.context.interactive = True
            print('stack.present(add): %r' % changes)
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            self.assertTrue('stack' in changes[0])

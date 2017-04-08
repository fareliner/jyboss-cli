from . import *

from jyboss.command import UndertowFilterModule


class TestUndertowModule(JBossTest):
    def setUp(self):
        super(TestUndertowModule, self).setUp()

    @jboss_context(mode=MODE_EMBEDDED, interactive=False)
    def test_filter_add(self):
        with self.connection:
            args = self.load_yaml()
            changes = UndertowFilterModule(self.context).apply(**args)
            self.context.interactive = True
            print('filter.present(added): %r' % changes)
            self.assertIsNotNone(changes)
            self.assertEqual(2, len(changes))
            self.assertTrue('filter' in changes[0])
            self.assertTrue('action' in changes[0])
            self.assertEqual('add', changes[0]['action'])
            self.assertTrue('filter-ref' in changes[1])
            self.assertTrue('action' in changes[1])
            self.assertEqual('add', changes[1]['action'])
            # TODO validate that the xml configuration written reflects these changes

    @jboss_context(mode=MODE_EMBEDDED, interactive=False)
    def test_response_header_update(self):
        with self.connection:
            args = self.load_yaml()
            changes = UndertowFilterModule(self.context).apply(**args)
            self.context.interactive = True
            print('filter.present(added): %r' % changes)
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            self.assertTrue('filter' in changes[0])
            self.assertTrue('action' in changes[0])
            self.assertEqual('update', changes[0]['action'])

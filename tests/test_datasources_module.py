from tests import *

from jyboss.command import DatasourcesModule


class TestDatasourcesModule(JBossTest):
    def setUp(self):
        super(TestDatasourcesModule, self).setUp()

    @jboss_context(mode=MODE_EMBEDDED, interactive=False)
    def test_datasource_added(self):
        with self.connection:
            args = self.load_yaml()
            changes = DatasourcesModule(self.context).apply(**args)
            self.context.interactive = True
            print('datasources.present(update): %r' % changes)
            self.assertIsNotNone(changes)
            self.assertTrue('datasources' in changes)
            self.assertEqual(1, len(changes['datasources']))
            change = changes['datasources'][0]
            self.assertTrue('datasource' in change)
            self.assertTrue('TestDS', change['datasource'])
            self.assertTrue('action' in change)
            self.assertEqual('added', change['action'])
            # TODO validate that the xml configuration written reflects these changes

    @jboss_context(mode=MODE_EMBEDDED, interactive=False)
    def test_datasource_updated(self):
        with self.connection:
            args = self.load_yaml()
            changes = DatasourcesModule(self.context).apply(**args)
            self.context.interactive = True
            print('datasource.present(update): %r' % changes)
            self.assertIsNotNone(changes)
            self.assertTrue('datasources' in changes)
            self.assertEqual(1, len(changes['datasources']))
            change = changes['datasources'][0]
            self.assertTrue('datasource' in change)
            self.assertTrue('ExampleDS', change['datasource'])
            self.assertTrue('action' in change)
            self.assertEqual('updated', change['action'])
            # TODO validate that the xml configuration written reflects these changes

    @jboss_context(mode=MODE_EMBEDDED, interactive=False)
    def test_datasource_deleted(self):
        with self.connection:
            args = self.load_yaml()
            changes = DatasourcesModule(self.context).apply(**args)
            self.context.interactive = True
            print('datasource.absent(): %r' % changes)
            self.assertIsNotNone(changes)
            self.assertTrue('datasources' in changes)
            self.assertEqual(1, len(changes['datasources']))
            change = changes['datasources'][0]
            self.assertTrue('datasource' in change)
            self.assertTrue('ExampleDS', change['datasource'])
            self.assertTrue('action' in change)
            self.assertEqual('deleted', change['action'])
            # TODO validate that the xml configuration written reflects these changes

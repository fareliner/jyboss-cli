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
            print('datasource.present(add): %r' % changes)
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

    @jboss_context(mode=MODE_EMBEDDED, interactive=False)
    def test_jdbc_driver_added(self):
        with self.connection:
            args = self.load_yaml()
            changes = DatasourcesModule(self.context).apply(**args)
            self.context.interactive = True
            print('jdbc-driver.present(add): %r' % changes)
            self.assertIsNotNone(changes)
            self.assertTrue('datasources' in changes)
            self.assertEqual(1, len(changes['datasources']))
            change = changes['datasources'][0]
            self.assertTrue('jdbc-driver' in change)
            self.assertTrue('h2e', change['jdbc-driver'])
            self.assertTrue('action' in change)
            self.assertEqual('added', change['action'])
            # TODO validate that the xml configuration written reflects these changes

    @jboss_context(config_file='test_jdbc_driver_updated.xml', mode=MODE_EMBEDDED, interactive=False)
    # from all it looks like JDBC module in JBoss cannot be updated
    def test_jdbc_driver_updated(self):
        with self.connection:
            args = self.load_yaml()
            changes = DatasourcesModule(self.context).apply(**args)
            self.context.interactive = True
            self.assertIsNone(changes)

    @jboss_context(config_file='test_jdbc_driver_deleted.xml', mode=MODE_EMBEDDED, interactive=False)
    def test_jdbc_driver_deleted(self):
        with self.connection:
            args = self.load_yaml()
            changes = DatasourcesModule(self.context).apply(**args)
            self.context.interactive = True
            print('datasource.absent(): %r' % changes)
            self.assertIsNotNone(changes)
            self.assertTrue('datasources' in changes)
            self.assertEqual(1, len(changes['datasources']))
            change = changes['datasources'][0]
            self.assertTrue('jdbc-driver' in change)
            self.assertTrue('h2e', change['jdbc-driver'])
            self.assertTrue('action' in change)
            self.assertEqual('deleted', change['action'])
            # TODO validate that the xml configuration written reflects these changes

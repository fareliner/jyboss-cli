from . import *

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
            print('datasource.present(add): \n%s\n----\n' % json.dumps(changes, indent=2))
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            change = changes[0]
            self.assertTrue('datasource' in change)
            self.assertTrue('TestDS', change['datasource'])
            self.assertTrue('action' in change)
            self.assertEqual('add', change['action'])
            # TODO validate that the xml configuration written reflects these changes

    @jboss_context(mode=MODE_EMBEDDED, interactive=False)
    def test_xa_datasource_added(self):
        with self.connection:
            args = self.load_yaml()
            changes = DatasourcesModule(self.context).apply(**args)
            self.context.interactive = True
            print('datasource.present(add): \n%s\n----\n' % json.dumps(changes, indent=2))
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            change = changes[0]
            self.assertTrue('datasource' in change)
            self.assertTrue('type' in change)
            self.assertTrue('xa-data-source', change['type'])
            self.assertTrue('XATestDS', change['datasource'])
            self.assertTrue('action' in change)
            self.assertEqual('add', change['action'])
            # TODO validate that the xml configuration written reflects these changes

    @jboss_context(mode=MODE_EMBEDDED, interactive=False)
    def test_datasource_updated(self):
        with self.connection:
            args = self.load_yaml()
            changes = DatasourcesModule(self.context).apply(**args)
            self.context.interactive = True
            print('datasource.present(update): \n%s\n----\n' % json.dumps(changes, indent=2))
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            change = changes[0]
            self.assertTrue('datasource' in change)
            self.assertTrue('ExampleDS', change['datasource'])
            self.assertTrue('action' in change)
            self.assertEqual('update', change['action'])
            # TODO validate that the xml configuration written reflects these changes

    @jboss_context(config_file='test_xa_datasource_updated.xml', mode=MODE_EMBEDDED, interactive=False)
    def test_xa_datasource_updated(self):
        with self.connection:
            args = self.load_yaml()
            changes = DatasourcesModule(self.context).apply(**args)
            self.context.interactive = True
            print('datasource.present(update): \n%s\n----\n' % json.dumps(changes, indent=2))
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            change = changes[0]
            self.assertTrue('datasource' in change)
            self.assertTrue('type' in change)
            self.assertTrue('xa-data-source', change['type'])
            self.assertTrue('XATestDS', change['datasource'])
            self.assertTrue('action' in change)
            self.assertEqual('update', change['action'])
            # expect a set of changes
            self.assertTrue('changes' in change)
            updates = change['changes']
            self.assertEqual(7, len(updates))
            update = updates[5]
            self.assertTrue('action' in update)
            self.assertEqual('update', update['action'])
            self.assertTrue('new_value' in update)
            self.assertEqual('jdbc:h2:mem:update', update['new_value'])
            update = updates[6]
            self.assertTrue('action' in update)
            self.assertEqual('delete', update['action'])
            self.assertTrue('old_value' in update)
            self.assertEqual('test-value', update['old_value'])
            # TODO validate that the xml configuration written reflects these changes


@jboss_context(mode=MODE_EMBEDDED, interactive=False)
def test_datasource_deleted(self):
    with self.connection:
        args = self.load_yaml()
        changes = DatasourcesModule(self.context).apply(**args)
        self.context.interactive = True
        print('datasource.absent(): \n%s\n----\n' % json.dumps(changes, indent=2))
        self.assertIsNotNone(changes)
        self.assertEqual(1, len(changes))
        change = changes[0]
        self.assertTrue('datasource' in change)
        self.assertTrue('ExampleDS', change['datasource'])
        self.assertTrue('action' in change)
        self.assertEqual('delete', change['action'])
        # TODO validate that the xml configuration written reflects these changes


@jboss_context(mode=MODE_EMBEDDED, interactive=False)
def test_jdbc_driver_added(self):
    with self.connection:
        args = self.load_yaml()
        changes = DatasourcesModule(self.context).apply(**args)
        self.context.interactive = True
        print('jdbc-driver.present(add): \n%s\n----\n' % json.dumps(changes, indent=2))
        self.assertIsNotNone(changes)
        self.assertEqual(1, len(changes))
        change = changes[0]
        self.assertTrue('jdbc-driver' in change)
        self.assertTrue('h2e', change['jdbc-driver'])
        self.assertTrue('action' in change)
        self.assertEqual('add', change['action'])
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
        print('datasource.absent(): \n%s\n----\n' % json.dumps(changes, indent=2))
        self.assertIsNotNone(changes)
        self.assertEqual(1, len(changes))
        change = changes[0]
        self.assertTrue('jdbc-driver' in change)
        self.assertTrue('h2e', change['jdbc-driver'])
        self.assertTrue('action' in change)
        self.assertEqual('delete', change['action'])
        # TODO validate that the xml configuration written reflects these changes

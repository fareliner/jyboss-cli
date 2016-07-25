from tests import *

from jyboss.command import ModuleModule


class TestModuleModule(JBossTest):
    def setUp(self):
        super(TestModuleModule, self).setUp()

    @jboss_context(mode=MODE_EMBEDDED, interactive=False)
    def test_module_actions(self):
        with self.connection:
            args = self.load_yaml()
            # inject real files that we can deploy to the app server
            args['module'][0]['resources'] = [
                os.path.join(self.test_dir, 'configurations', self.__class__.__name__, 'some-module.jar'),
                os.path.join(self.test_dir, 'configurations', self.__class__.__name__, 'some-module.properties')
            ]

            changes = ModuleModule(self.context).apply(**args)
            self.context.interactive = True
            print('module.combo(add): %r' % changes)
            self.assertIsNotNone(changes)
            self.assertTrue('module' in changes)
            self.assertEqual(2, len(changes['module']))

            add_change = changes['module'][0]
            self.assertEqual('added', add_change.get('action', None))

            del_change = changes['module'][1]
            self.assertEqual('deleted', del_change.get('action', None))

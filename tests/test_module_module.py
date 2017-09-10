from . import *

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
            print('module.actions(add): \n%s\n----\n' % json.dumps(changes, indent=2))
            self.assertIsNotNone(changes)
            self.assertEqual(2, len(changes))

            add_change = changes[0]
            self.assertEqual('add', add_change.get('action', None))

            del_change = changes[1]
            self.assertEqual('delete', del_change.get('action', None))

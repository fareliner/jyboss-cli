from . import *

from jyboss.command import KeycloakAdapterModule


class TestKeycloakAdapterModule(JBossTest):
    """
    This test requires the keycloak adapter overlay to be installed on the target wildfly test environment.
    """

    def setUp(self):
        super(TestKeycloakAdapterModule, self).setUp()

    @jboss_context(config_file='test_keycloak_adapter_added.xml', mode=MODE_EMBEDDED, interactive=False)
    def test_keycloak_adapter_added(self):
        with self.connection:
            args = self.load_yaml()
            changes = KeycloakAdapterModule(self.context).apply(**args)
            self.context.interactive = True
            print('container.present(add): \n%s\n----\n' % json.dumps(changes, indent=2))
            self.assertIsNotNone(changes)
            self.assertEqual(4, len(changes))
            self.assertTrue(1, 'subsystem' in changes[0])
            self.assertEquals('keycloak', changes[0]['subsystem'])
            # TODO check realm and deployment added

from . import *

from jyboss.command import KeycloakServerModule


class TestKeycloakServerModule(JBossTest):
    """
    This test requires the keycloak adapter overlay to be installed on the target wildfly test environment.
    """

    def setUp(self):
        super(TestKeycloakServerModule, self).setUp()

    @jboss_context(config_file='standalone-kc.xml', interactive=False)
    def test_keycloak_server_change_context_root(self):
        with self.connection:
            args = self.load_yaml()
            changes = KeycloakServerModule(self.context).apply(**args)
            self.context.interactive = True
            print('server.present(add): \n%s\n----\n' % json.dumps(changes, indent=2))
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            self.assertEqual('update', changes[0]['action'])
            self.assertTrue('changes' in changes[0])
            sub_changes = changes[0]['changes']
            self.assertEquals(1, len(sub_changes))
            self.assertEquals('web-context', sub_changes[0]['attribute'])
            # TODO check xml

    @jboss_context(config_file='standalone-kc.xml', interactive=False)
    def test_keycloak_server_change_provider_list(self):
        with self.connection:
            args = self.load_yaml()
            changes = KeycloakServerModule(self.context).apply(**args)
            self.context.interactive = True
            print('server.providers(update): \n%s\n----\n' % json.dumps(changes, indent=2))
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            subsystem_change = changes[0]
            self.assertEqual('update', subsystem_change['action'])
            self.assertTrue('changes' in subsystem_change)
            self.assertEquals(1, len(subsystem_change['changes']))
            provider_change = subsystem_change['changes'][0]
            self.assertEquals('update', provider_change['action'])
            self.assertEquals('providers', provider_change['attribute'])
            self.assertEquals(1, len(provider_change['old_value']))
            self.assertEquals(2, len(provider_change['new_value']))

            # TODO check xml

    @jboss_context(config_file='standalone-kc.xml', interactive=False)
    def test_keycloak_server_add_spi(self):
        with self.connection:
            args = self.load_yaml()
            changes = KeycloakServerModule(self.context).apply(**args)
            self.context.interactive = True
            print('spi.present(add): \n%s\n----\n' % json.dumps(changes, indent=2))
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            spi_change = changes[0]
            self.assertEqual('add', spi_change['action'])
            self.assertEqual('test', spi_change['spi'])
            self.assertTrue('changes' in spi_change)
            self.assertEqual(2, len(spi_change['changes']))
            prov_changes = spi_change['changes']
            for prov_change in prov_changes:
                self.assertTrue('provider' in prov_change)
                self.assertTrue(prov_change['provider'] in ['testProviderOne', 'testProviderTwo'])
                # TODO check xml

    @jboss_context(config_file='standalone-kc-test-provider.xml', interactive=False)
    def test_keycloak_server_update_spi_provider_properties(self):
        with self.connection:
            args = self.load_yaml()
            changes = KeycloakServerModule(self.context).apply(**args)
            self.context.interactive = True
            print('spi.provider(update): \n%s\n----\n' % json.dumps(changes, indent=2))
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            spi_change = changes[0]
            self.assertTrue('action' in spi_change)
            self.assertEqual('update', spi_change['action'])
            self.assertTrue('changes' in spi_change)
            # test the spi provider default attribute change
            attr_change = next(
                iter([c for c in spi_change['changes'] if 'attribute' in c and c['attribute'] == 'default-provider']),
                None)
            self.assertIsNotNone(attr_change, 'Expected attribute default-provider to be changed')
            self.assertTrue('action' in attr_change)
            self.assertEqual('update', attr_change['action'])
            # test the first provider change
            prov1_change = next(
                iter([c for c in spi_change['changes'] if 'provider' in c and c['provider'] == 'testProviderOne']),
                None)
            self.assertIsNotNone(prov1_change)
            self.assertTrue('action' in prov1_change)
            self.assertEqual('update', prov1_change['action'])
            self.assertTrue('changes' in prov1_change)
            prov1_changes = prov1_change['changes']
            self.assertEqual(1, len(prov1_changes))
            attr_enabled_change = next(
                iter([c for c in prov1_changes if 'attribute' in c and c['attribute'] == 'enabled']), None)
            self.assertIsNotNone(attr_enabled_change, 'Expected attribute enabled to be changed')
            self.assertTrue('action' in attr_enabled_change)
            self.assertEqual('update', attr_enabled_change['action'])
            self.assertTrue('old_value' in attr_enabled_change)
            self.assertFalse(attr_enabled_change['old_value'], 'Expected old value to be false')
            self.assertTrue('new_value' in attr_enabled_change)
            self.assertTrue(attr_enabled_change['new_value'], 'Expected new value to be true')
            # test the second provider change
            prov2_change = next(
                iter([c for c in spi_change['changes'] if 'provider' in c and c['provider'] == 'testProviderTwo']),
                None)
            self.assertIsNotNone(prov2_change)
            self.assertTrue('action' in prov2_change)
            self.assertEqual('update', prov2_change['action'])
            self.assertTrue('changes' in prov2_change)
            prov2_changes = prov2_change['changes']
            self.assertEqual(2, len(prov2_changes))
            attr_enabled_change = next(
                iter([c for c in prov2_changes if 'attribute' in c and c['attribute'] == 'enabled']), None)
            self.assertIsNotNone(attr_enabled_change, 'Expected attribute enabled to be changed')
            self.assertTrue('action' in attr_enabled_change)
            self.assertEqual('update', attr_enabled_change['action'])
            self.assertTrue('old_value' in attr_enabled_change)
            self.assertTrue(attr_enabled_change['old_value'], 'Expected old value to be true')
            self.assertTrue('new_value' in attr_enabled_change)
            self.assertFalse(attr_enabled_change['new_value'], 'Expected new value to be false')
            # also test the properties changes on the 2nd provider
            attr_properties_change = next(
                iter([c for c in prov2_changes if 'attribute' in c and c['attribute'] == 'properties']), None)
            self.assertIsNotNone(attr_properties_change, 'Expected attribute properties to be changed')
            self.assertTrue('action' in attr_properties_change)
            self.assertEqual('update', attr_properties_change['action'])
            self.assertTrue('new_value' in attr_properties_change)
            self.assertTrue('update' in attr_properties_change['new_value'])
            self.assertTrue(attr_properties_change['new_value']['update'])
            self.assertTrue('reason' in attr_properties_change['new_value'])
            self.assertEqual('changed during testing', attr_properties_change['new_value']['reason'])
            # TODO check xml

    @jboss_context(config_file='standalone-kc-test-provider.xml', interactive=False)
    def test_keycloak_server_delete_spi_provider_property(self):
        with self.connection:
            args = self.load_yaml()
            changes = KeycloakServerModule(self.context).apply(**args)
            self.context.interactive = True
            print('spi.provider(update): \n%s\n----\n' % json.dumps(changes, indent=2))
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            spi_change = changes[0]
            self.assertEqual('update', spi_change['action'])
            self.assertTrue('changes' in spi_change)
            self.assertEquals(1, len(spi_change['changes']))
            provider_change = spi_change['changes'][0]
            self.assertTrue('provider' in provider_change)
            self.assertEqual('testProviderTwo', provider_change['provider'])
            self.assertTrue('action' in provider_change)
            self.assertEqual('update', provider_change['action'])
            self.assertEquals(1, len(provider_change['changes']))
            attribute_change = provider_change['changes'][0]
            self.assertTrue('action' in attribute_change)
            self.assertEqual('update', attribute_change['action'])
            self.assertTrue('old_value' in attribute_change)
            self.assertTrue('update' in attribute_change['old_value'])
            self.assertTrue('reason' in attribute_change['old_value'])
            self.assertTrue('new_value' in attribute_change)
            self.assertTrue('update' in attribute_change['new_value'])
            self.assertFalse('reason' in attribute_change['new_value'])
            # TODO check xml

    @jboss_context(config_file='standalone-kc.xml', interactive=False)
    def test_keycloak_server_update_disable_theme_cache(self):
        with self.connection:
            args = self.load_yaml()
            changes = KeycloakServerModule(self.context).apply(**args)
            self.context.interactive = True
            print('theme.present(update): \n%s\n----\n' % json.dumps(changes, indent=2))
            self.assertIsNotNone(changes)
            self.assertEqual(1, len(changes))
            change = changes[0]
            self.assertEqual('update', change['action'])
            self.assertEqual('defaults', change['theme'])
            self.assertTrue('changes' in change)
            self.assertEqual(1, len(change['changes']))
            theme_change = change['changes'][0]
            self.assertEqual('update', theme_change['action'])
            self.assertEqual('cacheThemes', theme_change['attribute'])
            self.assertTrue(theme_change['old_value'])
            self.assertFalse(theme_change['new_value'])
            # TODO check xml

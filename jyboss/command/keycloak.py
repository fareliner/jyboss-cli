# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

from abc import ABCMeta

from jyboss.exceptions import ParameterError, NotFoundError
from jyboss.command.core import BaseJBossModule

__metaclass__ = type

try:
    dict.iteritems
except AttributeError:
    # Python 3
    def iteritems(d):
        return d.items()
else:
    # Python 2
    def iteritems(d):
        return d.iteritems()


class KeycloakAdapterModule(BaseJBossModule):
    __metaclass__ = ABCMeta

    # TODO add all others from the sources
    KC_REALM_PARAMS = {
        'realm',
        'allow-any-hostname',
        'client-keystore-password',
        'cors-max-age',
        'realm-public-key',
        'truststore-password',
        'always-refresh-token',
        'client-keystore',
        'disable-trust-manager',
        'register-node-at-startup',
        'truststore',
        'auth-server-url-for-backend-requests',
        'connection-pool-size',
        'enable-cors',
        'register-node-period',
        'auth-server-url',
        'cors-allowed-headers',
        'expose-token',
        'ssl-required',
        'client-key-password',
        'cors-allowed-methods',
        'principal-attribute',
        'token-store'
    }

    KC_DEPLOYMENT_PARAMS = {
        'allow-any-hostname',
        'client-keystore-password',
        'disable-trust-manager',
        'realm-public-key',
        'token-store',
        'always-refresh-token',
        'client-keystore',
        'enable-basic-auth',
        'realm',
        'truststore-password',
        'auth-server-url-for-backend-requests',
        'connection-pool-size',
        'enable-cors',
        'register-node-at-startup',
        'truststore',
        'auth-server-url',
        'cors-allowed-headers',
        'expose-token',
        'register-node-period',
        'turn-off-change-session-id-on-login',
        'bearer-only',
        'cors-allowed-methods',
        'principal-attribute',
        'resource',
        'use-resource-role-mappings',
        'client-key-password',
        'cors-max-age',
        'public-client',
        'ssl-required'
    }

    def __init__(self, context=None):
        super(KeycloakAdapterModule, self).__init__(path='/subsystem=keycloak', context=context)

    def apply(self, keycloak_adapter=None, **kwargs):
        """
        Apply a keycloak adapter subsystem configuration:

        Example:
            keycloak_adapter:
              realm:
                - name: myrealm
                  state: present
                  realm_public_key: "MIIBIjANBgkq...A"
                  auth_server_url: 'https://login.server.com/auth'
                  ssl_required: none
                  enable_cors: false
                  principal_attribute: preferred_username
              secure_deployment:
                - name: myapp.war
                  state: present
                  resource: myrealm
                  credential:
                    type: secret
                    value: "5af5458f-0a96-4251-8f92-08ebcc3a8aa2"
                  disable_trust_manager: true
                  bearer_only: true
                  enable_basic_auth: true

        :param keycloak_adapter: the keycloak subsystem configuration to configure
        :param kwargs: any other args that may be useful
        :return: changed flag and a list of changes that have been applied to the security domain
        """

        keycloak = self.unescape_keys(keycloak_adapter)
        changes = []

        if keycloak is None or 'realm' not in keycloak or keycloak['realm'] is None:
            raise ParameterError(
                '%s.apply(): No valid keycloak subsystem configuration provided: %r' % (
                    self.__class__.__name__, keycloak))

        state = self._get_param(keycloak, 'state', 'present')

        if state not in ['present', 'absent']:
            raise ParameterError('security domain state is not one of [present|absent]')

        if state == 'present':
            changes += self.apply_keycloak_subsystem_present()

            if 'realm' in keycloak:
                changes += self.apply_realm(keycloak['realm'])

            if 'secure-deployment' in keycloak:
                changes += self.apply_secure_deployment(keycloak['secure-deployment'])

        elif state == 'absent':
            changes += self.apply_keycloak_subsystem_absent()

        # caller of apply will expect None if nothing changed, else a list of changes
        return None if len(changes) < 1 else changes

    def apply_keycloak_subsystem_present(self):
        try:
            self.read_resource_dmr(self.path)
            return []
        except NotFoundError:
            # create realm
            self.cmd('%s:add' % self.path)
            return [{'subsystem': 'keycloak', 'action': 'add'}]

    def apply_keycloak_subsystem_absent(self):
        changes = []
        try:
            self.cmd('%s:remove' % self.path)
            changes.append({'subsystem': 'keycloak', 'action': 'delete'})
        except NotFoundError:
            pass
        return changes

    def apply_realm(self, realm=None):
        # lets sync the realm configuration
        if isinstance(realm, dict):
            realms = [realm]
        elif isinstance(realm, list):
            realms = realm
        else:
            raise ParameterError(
                '%s.apply(keycloak.realm:%s): The keycloak subsystem configuration is not valid.' % (
                    self.__class__.__name__, type(realm)))

        changes = []

        for realm in realms:

            state = self._get_param(realm, 'state')

            if state not in ['present', 'absent']:
                raise ParameterError('The keycloak realm state is not one of [present|absent]')

            name = self._get_param(realm, 'name')

            if state == 'present':
                changes += self.apply_realm_present(realm)
            elif state == 'absent':
                changes += self.apply_realm_absent(name)

        return changes

    def apply_realm_present(self, realm=None):

        name = self._get_param(realm, 'name')
        realm_path = '%s/realm=%s' % (self.path, name)

        changes = []

        try:
            realm_dmr = self.read_resource_dmr(realm_path, True)
            fc = dict(
                (k, v) for (k, v) in iteritems(realm) if k in self.KC_REALM_PARAMS)
            a_changes = self._sync_attributes(parent_node=realm_dmr,
                                              parent_path=realm_path,
                                              target_state=fc,
                                              allowable_attributes=self.KC_REALM_PARAMS)
            if len(a_changes) > 0:
                changes.append({'realm': name, 'action': 'update', 'changes': a_changes})

        except NotFoundError:
            # create the domain and add auth modules if present
            realm_params = self.convert_to_dmr_params(realm, self.KC_REALM_PARAMS)

            self.cmd('%s:add(%s)' % (realm_path, realm_params))
            changes.append({'realm': name, 'action': 'add', 'params': realm_params})

        return changes

    def apply_realm_absent(self, name):
        try:
            self.cmd('%s/realm=%s:remove' % (self.path, name))
            # TODO also remove secure deployments with it
            return [{'keycloak-realm': name, 'action': 'delete'}]
        except NotFoundError:
            return []

    def apply_secure_deployment(self, deployment):
        deployments = []
        if isinstance(deployment, dict):
            deployments.append(deployment)
        elif isinstance(deployment, list) or deployment is None:
            deployments += deployment
        else:
            raise ParameterError('Deployment is not valid: %s' % (type(deployment)))

        changes = []

        for deployment in deployments:
            state = self._get_param(deployment, 'state')

            if state not in ['present', 'absent']:
                raise ParameterError('The deployment state is not one of [present|absent]')

            name = self._get_param(deployment, 'name')

            if state == 'present':
                changes += self.apply_secure_deployment_present(deployment)
            elif state == 'absent':
                changes += self.apply_secure_deployment_absent(name)

        return changes

    def apply_secure_deployment_present(self, deployment):

        name = self._get_param(deployment, 'name')

        depl_path = '%s/secure-deployment=%s' % (self.path, name)

        changes = []

        try:
            depl_dmr = self.read_resource_dmr(depl_path, True)
            fc = dict(
                (k, v) for (k, v) in iteritems(deployment) if k in self.KC_REALM_PARAMS)
            a_changes = self._sync_attributes(parent_node=depl_dmr,
                                              parent_path=depl_path,
                                              target_state=fc,
                                              allowable_attributes=self.KC_REALM_PARAMS)
            if len(a_changes) > 0:
                changes.append({'secure-deployment': name, 'action': 'update', 'changes': a_changes})

            if 'credential' in deployment:
                changes += self._apply_credentials(name, deployment['credential'])

        except NotFoundError:
            # create the domain and add auth modules if present
            depl_params = self.convert_to_dmr_params(deployment, self.KC_DEPLOYMENT_PARAMS)
            self.cmd('%s:add(%s)' % (depl_path, depl_params))

            if 'credential' in deployment:
                changes += self._apply_credentials(name, deployment['credential'])

            changes.append({'secure-deployment': name, 'action': 'add', 'params': depl_params})

        return changes

    def _apply_credentials(self, deployment_name, credential):

        cred_type = self._get_param(credential, 'type')
        cred_value = self._get_param(credential, 'value')

        cred_path = '%s/secure-deployment=%s/credential=%s' % (self.path, deployment_name, cred_type)

        changes = []

        if cred_value is None:
            try:
                self.cmd('%s:remove()' % cred_path)
                changes.append({'deployment': deployment_name, 'credential': cred_type, 'action': 'delete'})
            except NotFoundError:
                pass
        else:
            try:
                cred = self.read_resource(cred_path)
                if 'value' in cred and cred['value'] != cred_value:
                    self.cmd(
                        '%s:write-attribute(name=value, value=%s)' % (cred_path, cred_value))
                    changes.append({'deployment': deployment_name, 'credential': cred_type, 'action': 'update'})

            except NotFoundError:
                self.cmd('%s:add(value=%s)' % (cred_path, cred_value))
                changes.append({'deployment': deployment_name, 'credential': cred_type, 'action': 'update'})

        return changes

    def apply_secure_deployment_absent(self, name):
        try:
            self.cmd('%s/secure-deployment=%s:remove' % (self.path, name))
            return [{'secure-deployment': name, 'action': 'delete'}]
        except NotFoundError:
            return []


class KeycloakServerModule(BaseJBossModule):
    __metaclass__ = ABCMeta

    KC_PARAMS = [
        'master-realm-name',
        'web-context',
        'scheduled-task-interval',
        'providers'
    ]

    def __init__(self, context=None):
        super(KeycloakServerModule, self).__init__(path='/subsystem=keycloak-server', context=context)
        self.submodules = {
            'spi': KeycloakServerSpiModule(context=context),
            'theme': KeycloakServerThemeModule(context=context)
        }

    def apply(self, keycloak_server=None, **kwargs):
        """
        Apply a keycloak adapter subsystem configuration:

        Example:
            keycloak_server:
              web_context: '/auth'

        :param keycloak_server: the keycloak subsystem configuration to apply
        :param kwargs: any other args that may be useful
        :return: changed flag and a list of changes that have been applied to the security domain
        """

        keycloak = self.unescape_keys(keycloak_server)

        if not isinstance(keycloak, dict):
            raise ParameterError('%s.apply(): No valid keycloak-server subsystem configuration provided: %r' % (
                self.__class__.__name__, keycloak))

        changes = []

        state = self._get_param(keycloak, 'state')
        if state not in ['present', 'absent']:
            raise ParameterError('The keycloak-server state is not one of [present|absent]')

        if state == 'present':
            changes += self.apply_present(keycloak)
        elif state == 'absent':
            changes += self.apply_absent()

        return changes if len(changes) > 0 else None

    def apply_present(self, keycloak):
        changes = []

        try:
            kc_dmr = self.read_resource_dmr(self.path, recursive=False)
            fc = dict((k, v) for (k, v) in iteritems(keycloak) if k in self.KC_PARAMS)
            a_changes = self._sync_attributes(parent_node=kc_dmr,
                                              parent_path=self.path,
                                              target_state=fc,
                                              allowable_attributes=self.KC_PARAMS)
            if len(a_changes) > 0:
                changes.append({'subsystem': 'keycloak-server', 'action': 'update', 'changes': a_changes})

        except NotFoundError:
            self.cmd('%s:add()' % self.path)
            changes.append({'subsystem': 'keycloak-server', 'action': 'add'})
            # TODO add all attributes to the subsystem as well

        # apply submodule configuration
        for key in keycloak:
            # first check if a submodule handler exists for the key element
            if key in self.submodules:
                handler = self.submodules[key]
                handler_changes = handler.apply(keycloak[key])
                if len(handler_changes) > 0:
                    changes += handler_changes
            elif key in ['state'] or key in self.KC_PARAMS:
                pass
            else:
                raise ParameterError('%s cannot handle configuration %s' % (self.__class__.__name__, key))

        return changes

    def apply_absent(self):
        changes = []

        try:
            self.read_resource_dmr(self.path)
            self.cmd('%s:remove()' % self.path)
            changes.append({'subsystem': 'keycloak-server', 'action': 'delete'})
        except NotFoundError:
            pass

        return changes


class KeycloakServerSpiModule(BaseJBossModule):
    __metaclass__ = ABCMeta

    SPI_PARAMS = [
        'default-provider'
    ]

    def __init__(self, context=None):
        super(KeycloakServerSpiModule, self).__init__(path='/subsystem=keycloak-server/spi=%s', context=context)
        self.submodules = {
            'providers': KeycloakServerSpiProviderModule(context=context)
        }

    def apply(self, spi=None, **kwargs):
        changes = []

        spi = self._format_apply_param(spi)

        for spi_module in spi:
            state = self._get_param(spi_module, 'state')
            if state == 'present':
                changes += self.apply_present(spi_module)
            elif state == 'absent':
                changes += self.apply_absent(spi_module)
            else:
                raise ParameterError('The spi state is not one of [present|absent]')

        return changes

    def apply_present(self, spi_module):
        name = self._get_param(spi_module, 'name')
        spi_path = self.path % name
        change = None

        try:
            spi_dmr = self.read_resource_dmr(spi_path, recursive=True)
            fc = dict((k, v) for (k, v) in iteritems(spi_module) if k in self.SPI_PARAMS)
            a_changes = self._sync_attributes(parent_node=spi_dmr,
                                              parent_path=spi_path,
                                              target_state=fc,
                                              allowable_attributes=self.SPI_PARAMS)
            if len(a_changes) > 0:
                change = {
                    'spi': name,
                    'action': 'update',
                    'changes': a_changes
                }
        except NotFoundError:
            spi_params = self.convert_to_dmr_params(spi_module, self.SPI_PARAMS)
            self.cmd('%s:add(%s)' % (spi_path, spi_params))
            change = {
                'spi': name,
                'action': 'add',
                'attributes': dict((k, v) for (k, v) in iteritems(spi_module) if k in self.SPI_PARAMS)
            }

        a_changes = self.submodules['providers'].apply(**spi_module)
        if len(a_changes) > 0:
            if change is None:
                change = {'spi': name, 'action': 'update'}
            # if other changes exist from parameter synching we add else we just
            if 'changes' in change:
                change['changes'] += a_changes
            else:
                change['changes'] = a_changes

        return [] if change is None else [change]

    def apply_absent(self, spi_module):
        name = self._get_param(spi_module, 'name')
        spi_path = self.path % name
        changes = []

        try:
            self.read_resource_dmr(spi_path)
            self.cmd('%s:remove()' % spi_path)
            changes.append({'spi': name, 'action': 'delete'})
        except NotFoundError:
            pass

        return changes


class KeycloakServerSpiProviderModule(BaseJBossModule):
    __metaclass__ = ABCMeta

    PROVIDER_PARAMS = [
        'enabled',
        'properties'
    ]

    def __init__(self, context=None):
        super(KeycloakServerSpiProviderModule, self).__init__(path='/subsystem=keycloak-server/spi=%s/provider=%s',
                                                              context=context)

    def apply(self, name=None, providers=None, **kwargs):
        changes = []

        providers = self._format_apply_param(providers)

        for provider in providers:
            state = self._get_param(provider, 'state')
            if state == 'present':
                changes += self.apply_present(name, provider)
            elif state == 'absent':
                changes += self.apply_absent(name, provider)
            else:
                raise ParameterError('The spi provider state is not one of [present|absent]')

        return changes

    def apply_present(self, spi_name, provider):
        name = self._get_param(provider, 'name')
        provider_path = self.path % (spi_name, name)
        changes = []

        try:
            provider_dmr = self.read_resource_dmr(provider_path, recursive=True)
            fc = dict((k, v) for (k, v) in iteritems(provider) if k in self.PROVIDER_PARAMS)
            a_changes = self._sync_attributes(parent_node=provider_dmr,
                                              parent_path=provider_path,
                                              target_state=fc,
                                              allowable_attributes=self.PROVIDER_PARAMS)
            if len(a_changes) > 0:
                changes.append({
                    'provider': name,
                    'action': 'update',
                    'changes': a_changes
                })

        except NotFoundError:
            provider_args = self.convert_to_dmr_params(provider, self.PROVIDER_PARAMS)
            self.cmd('%s:add(%s)' % (provider_path, provider_args))
            changes.append({
                'provider': name,
                'action': 'add',
                'attributes': dict((k, v) for (k, v) in iteritems(provider) if k in self.PROVIDER_PARAMS)
            })

        return changes

    def apply_absent(self, spi_name, provider):
        name = self._get_param(provider, 'name')
        provider_path = self.path % (spi_name, name)
        changes = []

        try:
            self.read_resource_dmr(provider_path)
            self.cmd('%s:remove()' % provider_path)
            changes.append({'provider': name, 'action': 'delete'})
        except NotFoundError:
            pass

        return changes


class KeycloakServerThemeModule(BaseJBossModule):
    __metaclass__ = ABCMeta

    THEME_PARAMS = [
        'cacheTemplates',
        'cacheThemes',
        'dir',
        'modules',
        'staticMaxAge',
        'welcomeTheme'
    ]

    def __init__(self, context=None):
        # this is really only a singular property and the name is hardcoded to defaults
        super(KeycloakServerThemeModule, self) \
            .__init__(path='/subsystem=keycloak-server/theme=defaults', context=context)

    def apply(self, theme=None, **kwargs):
        changes = []

        theme = self.unescape_keys(theme)

        state = self._get_param(theme, 'state')
        if state == 'present':
            changes += self.apply_present(theme)
        elif state == 'absent':
            changes += self.apply_absent()
        else:
            raise ParameterError('The theme state is not one of [present|absent]')

        return changes

    def apply_present(self, theme):
        change = None

        try:
            theme_dmr = self.read_resource_dmr(self.path, recursive=True)
            fc = dict((k, v) for (k, v) in iteritems(theme) if k in self.THEME_PARAMS)
            a_changes = self._sync_attributes(parent_node=theme_dmr,
                                              parent_path=self.path,
                                              target_state=fc,
                                              allowable_attributes=self.THEME_PARAMS)
            if len(a_changes) > 0:
                change = {
                    'theme': 'defaults',
                    'action': 'update',
                    'changes': a_changes
                }
        except NotFoundError:
            theme_params = self.convert_to_dmr_params(theme, self.THEME_PARAMS)
            self.cmd('%s:add(%s)' % (self.path, theme_params))
            change = {
                'theme': 'defaults',
                'action': 'add',
                'attributes': dict((k, v) for (k, v) in iteritems(theme) if k in self.THEME_PARAMS)
            }

        return [] if change is None else [change]

    def apply_absent(self):
        changes = []

        try:
            self.read_resource_dmr(self.path)
            self.cmd('%s:remove()' % self.path)
            changes.append({'theme': 'defaults', 'action': 'delete'})
        except NotFoundError:
            pass

        return changes

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


class KeycloakModule(BaseJBossModule):
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
        super(KeycloakModule, self).__init__(path='/subsystem=keycloak', context=context)

    def apply(self, keycloak=None, **kwargs):
        """
        Apply a keycloak subsystem configuration:

        Example:
            keycloak:
              realm:
                - name: apiman
                  state: present
                  realm_public_key: "MIIBIjANBgkq...A"
                  auth_server_url: 'https://login.server.com/auth'
                  ssl_required: none
                  enable_cors: false
                  principal_attribute: preferred_username
              secure_deployment:
                - name: apiman.war
                  state: present
                  resource: apiman
                  credential:
                    type: secret
                    value: "5af5458f-0a96-4251-8f92-08ebcc3a8aa2"
                  disable_trust_manager: true
                  bearer_only: true
                  enable_basic_auth: true

        :param keycloak: the keycloak subsystem configuration to configure
        :param kwargs: any other args that may be useful
        :return: changed flag and a list of changes that have been applied to the security domain
        """

        keycloak = self.unescape_keys(keycloak)
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
            return [{'subsystem': 'keycloak', 'action': 'added'}]

    def apply_keycloak_subsystem_absent(self):
        changes = []
        try:
            self.cmd('%s:remove' % self.path)
            changes.append({'subsystem': 'keycloak', 'action': 'deleted'})
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
                changes.append({'realm': name, 'action': 'updated', 'changes': a_changes})

        except NotFoundError:
            # create the domain and add auth modules if present
            realm_params = self.convert_to_dmr_params(realm, self.KC_REALM_PARAMS)

            self.cmd('%s:add(%s)' % (realm_path, realm_params))
            changes.append({'realm': name, 'action': 'added', 'params': realm_params})

        return changes

    def apply_realm_absent(self, name):
        try:
            self.cmd('%s/realm=%s:remove' % (self.path, name))
            # TODO also remove secure deployments with it
            return [{'keycloak-realm': name, 'action': 'deleted'}]
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
                changes.append({'secure-deployment': name, 'action': 'updated', 'changes': a_changes})

            if 'credential' in deployment:
                changes += self._apply_credentials(name, deployment['credential'])

        except NotFoundError:
            # create the domain and add auth modules if present
            depl_params = self.convert_to_dmr_params(deployment, self.KC_DEPLOYMENT_PARAMS)
            self.cmd('%s:add(%s)' % (depl_path, depl_params))

            if 'credential' in deployment:
                changes += self._apply_credentials(name, deployment['credential'])

            changes.append({'secure-deployment': name, 'action': 'added', 'params': depl_params})

        return changes

    def _apply_credentials(self, deployment_name, credential):

        cred_type = self._get_param(credential, 'type')
        cred_value = self._get_param(credential, 'value')

        cred_path = '%s/secure-deployment=%s/credential=%s' % (self.path, deployment_name, cred_type)

        changes = []

        if cred_value is None:
            try:
                self.cmd('%s:remove()' % cred_path)
                changes.append({'deployment': deployment_name, 'credential': cred_type, 'action': 'deleted'})
            except NotFoundError:
                pass
        else:
            try:
                cred = self.read_resource(cred_path)
                if 'value' in cred and cred['value'] != cred_value:
                    self.cmd(
                        '%s:write-attribute(name=value, value=%s)' % (cred_path, cred_value))
                    changes.append({'deployment': deployment_name, 'credential': cred_type, 'action': 'updated'})

            except NotFoundError:
                self.cmd('%s:add(value=%s)' % (cred_path, cred_value))
                changes.append({'deployment': deployment_name, 'credential': cred_type, 'action': 'updated'})

        return changes

    def apply_secure_deployment_absent(self, name):
        try:
            self.cmd('%s/secure-deployment=%s:remove' % (self.path, name))
            return [{'secure-deployment': name, 'action': 'deleted'}]
        except NotFoundError:
            return []

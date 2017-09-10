# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

from abc import ABCMeta

from jyboss.exceptions import ParameterError, NotFoundError
from jyboss.command.core import BaseJBossModule

__metaclass__ = type


class SecurityModule(BaseJBossModule):
    __metaclass__ = ABCMeta

    def __init__(self, context=None):
        super(SecurityModule, self).__init__(path='/subsystem=security', context=context)

    def apply(self, security=None, **kwargs):
        """
        Apply an extension operation:

        Example:

        security:
          security-domain:
            - name: keycloak
              state: present
              authentication:
                name: classic
                login-modules:
                  - code: "org.keycloak.adapters.jboss.KeycloakLoginModule"
                    flag: required

        :param security: a single dict of an extension
        :param kwargs: any other args that may be useful
        :return: changed flag and a list of changes that have been applied to the security domain
        """

        security = self.unescape_keys(security)
        changes = []

        if security is None or 'security-domain' not in security or security['security-domain'] is None:
            raise ParameterError(
                '%s.apply(): No valid security configuration provided: %r' % (self.__class__.__name__, security))

        if not isinstance(security['security-domain'], list):
            raise ParameterError(
                '%s.apply(security.security-domain:%s): The security domain is not a valid list.' % (
                    self.__class__.__name__, type(security['security-domain'])))

        for domain in security['security-domain']:

            state = self._get_param(domain, 'state')

            if state not in ['present', 'absent']:
                raise ParameterError('security domain state is not one of [present|absent]')

            name = self._get_param(domain, 'name')

            if state == 'present':
                changes += self.apply_security_domain_present(**domain)
            elif state == 'absent':
                changes += self.apply_security_domain_absent(name)

        return None if len(changes) < 1 else changes

    def apply_security_domain_present(self, name=None, authentication=None, **kwargs):

        resource_path = '%s/security-domain=%s' % (self.path, name)
        try:
            self.read_resource_dmr(resource_path, True)
            # TODO sync authentication configuration
            return []
        except NotFoundError:
            # create the domain and add auth modules if present
            self.cmd('%s:add' % resource_path)
            if authentication is not None:
                auth_type = authentication.get('type', 'classic')
                modules = authentication.get('login-modules', [])
                self.cmd('%s/authentication=%s:add(login-modules=%s)' % (
                    # FIXME use convert_to_dmr_params
                    resource_path, auth_type, self.converts_to_dmr(modules)))
            return [{'security-domain': name, 'action': 'add'}]

    def apply_security_domain_absent(self, name):
        try:
            self.cmd('%s/security-domain=%s:remove' % (self.path, name))
            return [{'security-domain': name, 'action': 'delete'}]
        except NotFoundError:
            return []

# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

from abc import ABCMeta

from jyboss.exceptions import ParameterError, NotFoundError
from jyboss.command.core import BaseJBossModule

__metaclass__ = type


class ExtensionModule(BaseJBossModule):
    __metaclass__ = ABCMeta

    def __init__(self):
        super(ExtensionModule, self).__init__('/extension')

    def apply(self, extension=None, **kwargs):
        """
        Apply an extension operation:

        Example:
        extension = [
                {
                    'name': 'org.keycloak.keycloak-adapter-subsystem',
                    'state': 'present',
                    'module': 'org.keycloak.keycloak-adapter-subsystem'
                },
                {
                    'name': 'org.keycloak.keycloak-adapter-subsystem',
                    'state': 'absent'
                }
            ]

        :param extension: a list or single dict of an extension
        :param kwargs: any other args that may be useful
        :return: changed flag and a list of changes that have been applied
        """

        extension = self.unescape_keys(extension)

        changes = []

        if type(extension) is dict:
            extension = [extension]
        elif type(extension) is list:
            pass
        else:
            raise ParameterError('%s provided to %s is not an allowable type' % (extension, self.__class__.__name__))

        for ext in extension:

            state = self._get_param(ext, 'state')

            if state not in ['present', 'absent']:
                raise ParameterError('Extension state is not one of [present|absent]')

            name = self._get_param(ext, 'name')

            if state == 'present':
                module = self._get_param(ext, 'module')
                changes += self.apply_extension_present(name, module)
            elif state == 'absent':
                changes += self.apply_extension_absent(name)

        return None if len(changes) < 1 else changes

    def apply_extension_absent(self, name):
        try:
            self.cmd('%s=%s:remove()' % (self.path, name))
            return [{'extension': name, 'action': 'deleted'}]
        except NotFoundError:
            return []

    def apply_extension_present(self, name, module):
        try:
            ext = self.read_resource('%s=%s' % (self.path, name))
            if ext.get('module', None) != module:
                raise ParameterError('WFLYCTL0048: Attribute module is not writable')
            else:
                return []
        except NotFoundError:
            self.cmd('%s=%s:add(module=%s)' % (self.path, name, module))
            return [{'extension': name, 'action': 'added'}]

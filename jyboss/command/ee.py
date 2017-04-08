# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

from jyboss.exceptions import ParameterError, NotFoundError
from jyboss.command.core import BaseJBossModule

try:
    # Python 2
    unicode
except NameError:
    # Python 3
    unicode = str

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

__metaclass__ = type


class EEModule(BaseJBossModule):
    EE_PARAMS = [
        'service'
    ]

    EE_SERVICE_PARAMS = [
        'datasource'
    ]

    def __init__(self, context=None):
        super(EEModule, self).__init__(path='/subsystem=ee', context=context)

    def apply(self, ee=None, **kwargs):
        """
        Apply an ee subsystem operation:

        Example:

        """
        if not isinstance(ee, dict):
            raise ParameterError('%s provided to %s is not an allowable type' % (ee, self.__class__.__name__))

        changes = []

        for key in ee.keys():
            if key in self.EE_PARAMS and key == 'service':
                services = self._format_apply_param(ee['service'])
                changes += self.apply_ee_service(services)
                # handle service

        return changes if len(changes) > 0 else None

    def apply_ee_service(self, services):

        changes = []
        for service in services:
            name = self._get_param(service, 'name')
            try:
                service_dmr = self.read_resource_dmr('%s/service=%s' % (self.path, name))
                fc = dict(
                    (k, v) for (k, v) in iteritems(service) if k in self.EE_SERVICE_PARAMS)
                a_changes = self._sync_attributes(parent_node=service_dmr,
                                                  parent_path='%s/service=%s' % (self.path, name),
                                                  target_state=fc,
                                                  allowable_attributes=self.EE_SERVICE_PARAMS)
                if len(a_changes) > 0:
                    changes.append({'service': name, 'action': 'update', 'changes': a_changes})

            except NotFoundError as e:
                raise ParameterError('Failed to update EE default bindings: %s' % e.message)

        return changes

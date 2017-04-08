# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

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

try:
    import simplejson as json
except ImportError:
    import json


class InterfaceModule(BaseJBossModule):
    INTERFACE_PARAMS = [
        'any-address',
        'inet-address',
        'loopback-address',
        'multicast',
        'nic',
        'point-to-point',
        'site-local-address',
        'up',
        'any',
        'link-local-address',
        'loopback',
        'nic-match',
        'not',
        'public-address',
        'subnet-match',
        'virtual'
    ]

    def __init__(self, context=None):
        super(InterfaceModule, self).__init__(path='/interface=%s', context=context)

    def apply(self, interface=None, **kwargs):

        interfaces = self._format_apply_param(interface)

        changes = []

        for iface in interfaces:
            state = self._get_param(iface, 'state')
            if state == 'present':
                changes += self.apply_present(iface)
            elif state == 'absent':
                changes += self.apply_absent(iface)
            else:
                raise ParameterError('The interface state is not one of [present|absent]')

        return changes if len(changes) > 0 else None

    def apply_present(self, interface):
        name = self._get_param(interface, 'name')
        iface_path = self.path % name
        changes = []

        try:
            iface_dmr = self.read_resource_dmr(iface_path, recursive=True)
            fc = dict(
                (k, v) for (k, v) in iteritems(interface) if k in self.INTERFACE_PARAMS)
            a_changes = self._sync_attributes(parent_node=iface_dmr,
                                              parent_path=iface_path,
                                              target_state=fc,
                                              allowable_attributes=self.INTERFACE_PARAMS)
            if len(a_changes) > 0:
                changes.append({'interface': name, 'action': 'update', 'changes': a_changes})
        except NotFoundError:
            iface_params = self.convert_to_dmr_params(interface, self.INTERFACE_PARAMS)
            self.cmd('%s:add(%s)' % (iface_path, iface_params))
            changes.append({'interface': name, 'action': 'add'})
        return changes

    def apply_absent(self, interface):
        name = self._get_param(interface, 'name')
        iface_path = self.path % name
        changes = []

        try:
            self.read_resource_dmr(iface_path)
            self.cmd('%s:remove()' % iface_path)
            changes.append({'interface': name, 'action': 'delete'})
        except NotFoundError:
            pass

        return changes

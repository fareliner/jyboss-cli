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


class SocketBindingModule(BaseJBossModule):
    BINDING_PARAMS = [
        'port',
        'interface'
    ]

    def __init__(self, context=None):
        super(SocketBindingModule, self).__init__(path='/socket-binding-group=%s/socket-binding=%s',
                                                  context=context)

    def __call__(self, binding_conf):

        binding_conf = self.unescape_keys(binding_conf)

        if 'name' not in binding_conf:
            raise ParameterError('provided socket binding name is null')

        if 'socket-binding-group-name' not in binding_conf:
            raise ParameterError('provided socket binding group name is null')

    def apply(self, socket_binding=None, **kwargs):

        socket_bindings = self._format_apply_param(socket_binding)

        changes = []

        for binding in socket_bindings:

            state = self._get_param(binding, 'state')

            if state not in ['present', 'absent']:
                raise ParameterError('socket binding state is not one of [present|absent]')

            if state == 'present':
                changes += self.apply_socket_binding_present(binding)
            elif state == 'absent':
                changes += self.apply_socket_binding_absent(binding)

        return None if len(changes) < 1 else changes

    def apply_socket_binding_present(self, binding):
        group_name = self._get_param(binding, 'socket-binding-group-name')
        name = self._get_param(binding, 'name')

        resource_path = self.path % (group_name, name)

        changes = []

        try:
            binding_dmr = self.read_resource_dmr(resource_path, True)
            fc = dict(
                (k, v) for (k, v) in iteritems(binding) if k in self.BINDING_PARAMS)
            a_changes = self._sync_attributes(parent_node=binding_dmr,
                                              parent_path=resource_path,
                                              target_state=fc,
                                              allowable_attributes=self.BINDING_PARAMS)
            if len(a_changes) > 0:
                changes.append({'socket-binding': name, 'socket-binding-group': group_name, 'action': 'update',
                                'changes': a_changes})

        except NotFoundError:
            binding_params = self.convert_to_dmr_params(binding, self.BINDING_PARAMS)

            self.cmd('%s:add(%s)' % (resource_path, binding_params))
            changes.append({'socket-binding': name, 'socket-binding-group': group_name, 'action': 'add',
                            'params': binding_params})

        return changes

    def apply_socket_binding_absent(self, binding):
        group_name = self._get_param(binding, 'socket-binding-group-name')
        name = self._get_param(binding, 'name')
        resource_path = self.path % (group_name, name)
        try:
            self.cmd('%s:remove' % resource_path)
            return [{'socket-binding': name, 'socket-binding-group': group_name, 'action': 'delete'}]
        except NotFoundError:
            return []

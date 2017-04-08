# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

import copy

from jyboss.exceptions import ParameterError, NotFoundError
from jyboss.command.core import BaseJBossModule
from jyboss.logging import debug

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


class JGroupsModule(BaseJBossModule):
    JGROUPS_PARAMS = [
        'default-channel',
        'default-stack'
    ]

    def __init__(self, context=None):
        super(JGroupsModule, self).__init__(path='/subsystem=jgroups', context=context)
        self.CONFIG_SUBMODULE = {
            'stack': JGroupsStackModule(self.context),
            'channel': JGroupsChannelModule(self.context)
        }

    def apply(self, jgroups=None, **kwargs):

        jgroups = self.unescape_keys(jgroups)

        if not isinstance(jgroups, dict):
            raise ParameterError('%s provided to %s is not an allowable type' % (jgroups, self.__class__.__name__))

        changes = []

        state = self._get_param(jgroups, 'state')
        if state not in ['present', 'absent']:
            raise ParameterError('The jgroups state is not one of [present|absent]')

        # first need to deal with jgroups submodule itself
        if state == 'present':
            changes += self.apply_present(jgroups)

        elif state == 'absent':
            changes += self.apply_absent()

        return None if len(changes) < 1 else changes

    def apply_present(self, jgroups):
        changes = []

        try:
            self.read_resource(self.path, recursive=True)
        except NotFoundError:
            self.cmd('%s:add()' % self.path)
            changes.append({'subsystem': 'jgroups', 'action': 'add'})

        for key in jgroups:
            if key in self.CONFIG_SUBMODULE:
                handler = self.CONFIG_SUBMODULE[key]
                subchanges = handler.apply(jgroups[key])
                if len(subchanges) > 0:
                    changes.append({
                        key: subchanges
                    })
            elif key in JGroupsModule.JGROUPS_PARAMS:
                # very simple hack to set or unset value
                jgroups_dmr = self.read_resource_dmr(self.path)
                fc = dict(
                    (k, v) for (k, v) in iteritems(jgroups) if k in self.JGROUPS_PARAMS
                )
                changes += self._sync_attributes(parent_node=jgroups_dmr, parent_path=self.path, target_state=fc,
                                                 allowable_attributes=self.JGROUPS_PARAMS)
            elif key in ['state']:
                pass
            else:
                raise ParameterError('%s cannot handle configuration %s' % (self.__class__.__name__, key))

        return changes

    def apply_absent(self):
        changes = []

        try:
            self.read_resource_dmr(self.path)
            self.cmd('%s:remove()' % self.path)
            changes.append({'subsystem': 'jgroups', 'action': 'delete'})
        except NotFoundError:
            pass

        return changes


class JGroupsStackModule(BaseJBossModule):
    STACK_PARAMS = [
        'transport',
        'protocol'
    ]

    TRANSPORT_PARAMS = [
        'shared',
        'rack',
        'socket-binding'
    ]

    PROTOCOL_PARAMS = [
        'socket-binding'
    ]

    def __init__(self, context=None):
        super(JGroupsStackModule, self).__init__(path='/subsystem=jgroups/stack=%s', context=context)

    def apply(self, stack=None, **kwargs):

        stack = self._format_apply_param(stack)

        changes = []

        for st in stack:
            state = self._get_param(st, 'state')
            if state not in ['present', 'absent']:
                raise ParameterError('The stack state is not one of [present|absent]')

            if state == 'present':
                changes += self.apply_present(st)
            elif state == 'absent':
                changes += self.apply_absent(st)

        return changes

    def apply_absent(self, stack):

        name = self._get_param(stack, 'name')
        try:
            self.cmd((self.path + ':remove()') % name)
            return [{'stack': name, 'action': 'delete'}]
        except NotFoundError:
            return []

    def apply_present(self, stack):
        name = self._get_param(stack, 'name')
        stack_path = self.path % name
        changes = []

        try:
            self.read_resource_dmr(stack_path, recursive=True)
        except NotFoundError:
            self.cmd('%s:add()' % stack_path)
            changes.append({'stack': name, 'action': 'add'})

        # now sync sub items
        for k, v in iteritems(stack):
            if k == 'transport':
                changes += self.sync_transport(name, v)
            elif k == 'protocol':
                changes += self.sync_protocols(name, v)
            elif k in ['name', 'state']:
                pass
            else:
                raise NotImplementedError('%s.apply(stack) does not understand how to apply %s sub configuration' % \
                                          (self.__class__.__name__, k))

        return changes

    def sync_transport(self, stack_name, transport):

        changes = []
        name = self._get_param(transport, 'type')
        transport_path = (self.path % stack_name) + ('/transport=%s' % name)

        # remove any transport that does not match the specified transport type in the new configuration
        tnames = self.ls((self.path % stack_name) + '/transport', silent=True)
        for tname in tnames:
            if tname not in ['TRANSPORT', name]:
                try:
                    self.cmd('%s:remove()' % transport_path)
                    changes.append({'transport': name, 'action': 'delete'})
                except NotFoundError:
                    pass

        # apply transport configuration
        try:
            transport_dmr = self.read_resource_dmr(transport_path)
            fc = dict(
                (k, v) for (k, v) in iteritems(transport) if k in self.TRANSPORT_PARAMS
            )
            a_changes = self._sync_attributes(parent_node=transport_dmr,
                                              parent_path=transport_path,
                                              target_state=fc,
                                              allowable_attributes=self.TRANSPORT_PARAMS)
            if len(a_changes) > 0:
                changes.append({'transport': name, 'action': 'update', 'changes': a_changes})
        except NotFoundError:
            tp = copy.deepcopy(transport)
            tp['type'] = name
            transport_params = self.convert_to_dmr_params(tp, self.TRANSPORT_PARAMS + ['type'])
            self.cmd('%s:add(%s)' % (transport_path, transport_params))
            changes.append({'transport': name, 'action': 'add', 'params': transport_params})

        return changes

    def sync_protocols(self, stack_name, protocols):
        """
        Synching protocols is a bit more complicated in jgroups as order of items is important. This method will check
        for ordered equality of the list of protocols and if equal will attempt to sync each item or if not equal will
        remove all and add them.
        :param stack_name: the name of the stack within the protocol
        :param protocols: the list of protocols to sync
        :return: any changes that have been applied in the process
        """
        changes = []

        if self._check_protocol_order(stack_name, protocols):
            # synch properties of each proto - can asume the order and quantity of protos is all good
            for new_proto in protocols:
                protocol_type = self._get_param(new_proto, 'type')
                old_proto = self.read_resource('{0}/protocol={1}'.format(self.path % stack_name, protocol_type))

                # FIXME sync all registered params

                # sync properties params
                # match all new to all old properties
                old_properties = old_proto.get('properties', {})
                for property in new_proto.get('properties', []):
                    p_k = property.get('name', None)
                    p_vn = property.get('value', None)
                    # first check is for a deliberate remove of a prop by setting new value to None
                    if p_vn is None:
                        if p_k in old_properties:
                            # remove it
                            self.cmd('{0}/protocol={1}/property={2}/:remove()' \
                                     .format(self.path % stack_name, protocol_type, p_k))
                            changes.append({
                                'protocol': protocol_type,
                                'property': p_k,
                                'action': 'delete'
                            })
                    # then we check if we need to compare both
                    elif p_k in old_properties:
                        # FIXME convert to comparable values
                        p_vo = old_properties.get(p_k)
                        # only a crappy hack atm
                        if isinstance(p_vo, dict) and p_vo.keys()[0] == 'EXPRESSION_VALUE':
                            p_vo = p_vo['EXPRESSION_VALUE']

                        if str(p_vo) != str(p_vn):
                            # update it
                            self.cmd('{0}/protocol={1}/property={2}/:add(value={3})' \
                                     .format(self.path % stack_name, protocol_type, p_k, p_vn))
                            changes.append({
                                'protocol': protocol_type,
                                'property': p_k,
                                'action': 'update',
                                'old_value': p_vo,
                                'new_value': p_vn
                            })
                    # lastly we may need to add if not exists
                    else:
                        # add it
                        self.cmd('{0}/protocol={1}/property={2}/:add(value={3})' \
                                 .format(self.path % stack_name, protocol_type, p_k, p_vn))
                        changes.append({
                            'protocol': protocol_type,
                            'property': p_k,
                            'action': 'add',
                            'new_value': p_vn
                        })

        else:
            # delete old protocols and add new set (we don't care about order here)
            old_protos = self.ls((self.path % stack_name) + '/protocol', silent=True)
            for old_proto in old_protos:
                self.cmd((self.path % stack_name) + ('/protocol=%s:remove()' % old_proto))
                changes.append({'protocol': old_proto, 'action': 'delete'})
            # add new set
            for new_proto in protocols:
                protocol_type = self._get_param(new_proto, 'type')
                proto_params = self.convert_to_dmr_params(new_proto, self.PROTOCOL_PARAMS + ['type'])
                self.cmd('{0}/protocol={1}:add({2})'.format(self.path % stack_name, protocol_type, proto_params))
                properties = new_proto.get('properties', [])
                for new_prop in properties:
                    p_k = new_prop.get('name')
                    p_v = new_prop.get('value')
                    if p_v is not None:
                        self.cmd('{0}/protocol={1}/property={2}/:add(value={3})' \
                                 .format(self.path % stack_name, protocol_type, p_k, p_v))
                changes.append({'protocol': protocol_type, 'action': 'add', 'parameters': proto_params,
                                'properties': properties})

        return changes

    def _check_protocol_order(self, stack_name, protocols):
        old_stack = self.read_resource_dmr(self.path % stack_name)
        if old_stack.has('protocol') and str(old_stack.get('protocol').type) != 'UNDEFINED':
            old_protos = [str(p) for p in old_stack.get('protocol').keys()]
        else:
            old_protos = []

        new_protos = [p.get('type') for p in protocols]

        equal = len(old_protos) > 0 and len(old_protos) == len(new_protos)

        while len(old_protos) > 0 and equal:
            if old_protos.pop() != new_protos.pop():
                equal = False

        return equal


class JGroupsChannelModule(BaseJBossModule):
    CHANNEL_PARAMS = [
        'address',
        'address-as-uuid',
        'cluster',
        'discard-own-messages',
        'num-tasks-in-timer',
        'num-timer-threads',
        'received-bytes',
        'received-messages',
        'sent-bytes',
        'sent-messages',
        'stack',
        'stats-enabled',
        'version',
        'view'
    ]

    def __init__(self, context=None):
        super(JGroupsChannelModule, self).__init__(path='/subsystem=jgroups/channel=%s', context=context)

    def apply(self, channel=None, **kwargs):

        channel = self._format_apply_param(channel)

        changes = []

        for ch in channel:
            state = self._get_param(ch, 'state')
            if state not in ['present', 'absent']:
                raise ParameterError('The channel state is not one of [present|absent]')

            if state == 'present':
                changes += self.apply_present(ch)
            elif state == 'absent':
                changes += self.apply_absent(ch)

        return changes

    def apply_absent(self, stack):

        name = self._get_param(stack, 'name')
        try:
            self.cmd((self.path + ':remove()') % name)
            return [{'channel': name, 'action': 'delete'}]
        except NotFoundError:
            return []

    def apply_present(self, channel):
        name = self._get_param(channel, 'name')
        channel_path = self.path % name
        changes = []

        try:
            channel_dmr = self.read_resource_dmr(channel_path, recursive=True)
            fc = dict(
                (k, v) for (k, v) in iteritems(channel) if k in self.CHANNEL_PARAMS)
            a_changes = self._sync_attributes(parent_node=channel_dmr,
                                              parent_path=channel_path,
                                              target_state=fc,
                                              allowable_attributes=self.CHANNEL_PARAMS)
            if len(a_changes) > 0:
                changes.append({'realm': name, 'action': 'update', 'changes': a_changes})

        except NotFoundError:
            channel_params = self.convert_to_dmr_params(channel, self.CHANNEL_PARAMS)
            self.cmd('%s:add(%s)' % (channel_path, channel_params))
            changes.append({'channel': name, 'action': 'add', 'params': channel_params})

        return changes

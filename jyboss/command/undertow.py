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

__metaclass__ = type


class UndertowCustomFilterModule(BaseJBossModule):
    DEFAULT_PRIORITY = 1

    FILTER_PARAMS = {'module', 'class-name'}

    FILTER_REF_PARAMS = {'priority'}

    def __init__(self):
        super(UndertowCustomFilterModule, self).__init__('/subsystem=undertow/configuration=filter')

    def __call__(self, filter_conf):
        if 'name' not in filter_conf:
            raise ParameterError('provided filter name is null')

    def apply(self, server_name=None, host_name=None, custom_filter=None, **kwargs):

        custom_filter = self.unescape_keys(custom_filter)

        changes = []

        if type(custom_filter) is dict:
            custom_filter = [custom_filter]
        elif type(custom_filter) is list:
            pass
        else:
            raise ParameterError(
                '%s provided to %s is not an allowable type' % (custom_filter, self.__class__.__name__))

        for filter_config in custom_filter:

            state = self._get_param(filter_config, 'state')

            if state not in ['present', 'absent']:
                raise ParameterError('filter state is not one of [present|absent]')

            name = self._get_param(filter_config, 'name')

            if state == 'present':
                changes += self.apply_filter_present(name, filter_config)
                changes += self.apply_filter_ref_present(server_name, host_name, name, filter_config)

            elif state == 'absent':
                changes += self.apply_filter_ref_absent(server_name, host_name, name)
                changes += self.apply_filter_absent(name)

        return None if len(changes) < 1 else changes

    def apply_filter_absent(self, name):
        changes = []
        # FIXME if 'WFLYCTL0216' not in failure:
        #     raise ProcessingError('failed to delete filter %s: %s' % (name, failure))
        try:
            self.cmd('%s/custom-filter=%s:remove()' % (self.path, name))
            changes.append({'filter': name, 'action': 'deleted'})
        except NotFoundError:
            pass

        return changes

    def apply_filter_ref_absent(self, server_name, host_name, name):
        changes = []
        try:
            self.cmd('/subsystem=undertow/server=%s/host=%s/filter-ref=%s:remove()' % (
                server_name, host_name, name))
            changes.append({'filter_ref': name, 'action': 'deleted'})
        except NotFoundError:
            pass

        return changes

    def apply_filter_present(self, name, filter_config):
        changes = []
        try:
            dmr_filter = self.read_resource_dmr('%s/custom-filter=%s' % (self.path, name))
            # reduce filter config to only allowable values
            fc = dict(
                (key, value) for (key, value) in filter_config.items() if key in self.FILTER_PARAMS)
            a_changes = self._sync_attributes(parent_node=dmr_filter,
                                              parent_path='%s/custom-filter=%s' % (self.path, name),
                                              target_state=fc,
                                              allowable_attributes=self.FILTER_PARAMS)
            if len(a_changes) > 0:
                changes.append({'filter': name, 'action': 'updated', 'changes': a_changes})
        except NotFoundError:
            # filter does not exist and we need to create it
            module = self._get_param(filter_config, 'module')
            class_name = self._get_param(filter_config, 'class-name')
            self.cmd('%s/custom-filter=%s:add(class-name=%s, module=%s)' % (self.path, name, class_name, module))
            changes.append({'filter': name, 'action': 'added'})

        return changes

    def apply_filter_ref_present(self, server_name, host_name, name, filter_config):
        changes = []
        filter_ref_path = '/subsystem=undertow/server=%s/host=%s/filter-ref=%s' % (server_name, host_name, name)
        try:
            dmr_filter_ref = self.read_resource_dmr(filter_ref_path)
            # reduce filter config to only allowable values
            fc = dict(
                (key, value) for (key, value) in filter_config.items() if key in self.FILTER_REF_PARAMS)

            a_changes = self._sync_attributes(parent_node=dmr_filter_ref,
                                              parent_path=filter_ref_path,
                                              target_state=fc,
                                              allowable_attributes=self.FILTER_REF_PARAMS,
                                              callback_handler=self._update_filter_ref_attribute)

            if len(a_changes) > 0:
                changes.append({'filter-ref': name, 'action': 'updated', 'changes': a_changes})

        except NotFoundError:
            # filter ref does not exist and we need to create it
            priority = filter_config.get('priority', None)
            if priority is None or priority == self.DEFAULT_PRIORITY:
                cmd = '/subsystem=undertow/server=%s/host=%s/filter-ref=%s:add' % (server_name, host_name, name)
            else:
                cmd = '/subsystem=undertow/server=%s/host=%s/filter-ref=%s:add(priority=%s)' % (
                    server_name, host_name, name, priority)

            self.cmd(cmd)
            changes.append({'filter-ref': name, 'action': 'added'})

        return changes

    def _update_filter_ref_attribute(self, parent_path=None, name=None, old_value=None, new_value=None):

        change = None

        if name == 'priority' and (old_value is None or old_value == self.DEFAULT_PRIORITY) and (
                        new_value is None or new_value == self.DEFAULT_PRIORITY):
            pass  # nothing to do priority is already set
        elif new_value is None and old_value is not None:
            self.cmd('%s:undefine-attribute(name=%s)' % (parent_path, name))

            change = {
                'attribute': name,
                'action': 'delete',
                'old_value': old_value
            }

        elif new_value is not None and new_value != old_value:
            self.cmd('%s:write-attribute(name=%s, value=%s)' % (parent_path, name, new_value))

            change = {
                'attribute': name,
                'action': 'update',
                'old_value': old_value,
                'new_value': new_value
            }

        return change

# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

from abc import ABCMeta, abstractmethod
from collections import defaultdict

from jyboss.exceptions import ParameterError, NotFoundError, ProcessingError
from jyboss.command.core import CommandHandler
from jyboss.logging import debug, info

try:
    # Python 2
    unicode
except NameError:
    # Python 3
    unicode = str


class AtrributeUpdateHandler(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def update(self, **kwargs):
        pass


class BaseJBossModule(CommandHandler):
    __metaclass__ = ABCMeta

    STATE_ABSENT = 'absent'
    STATE_PRESENT = 'present'

    def __init__(self, path):
        super(BaseJBossModule, self).__init__()
        self.path = path
        self.ARG_TYPE_DISPATCHER = {
            'UNDEFINED': self._cast_node_undefined,
            'INT': self._cast_node_int,
            'LONG': self._cast_node_long,
            'STRING': self._cast_node_string,
            'BOOLEAN': self._cast_node_boolean
        }

    @staticmethod
    def _cast_node_undefined(n, v):
        if n is None:
            v_a = None
        else:
            raise ParameterError('Node has a undefined type but contains some value: %r' % n)
        # we have no means to work out what type this target value is supposed to have so just regurgitate
        return v_a, v

    @staticmethod
    def _cast_node_int(n, v):
        v_a = None if n is None else n.asInt()
        v_t = None if v is None else int(v)
        return v_a, v_t

    @staticmethod
    def _cast_node_long(n, v):
        v_a = None if n is None else n.asLong()
        v_t = None if v is None else long(v)
        return v_a, v_t

    @staticmethod
    def _cast_node_string(n, v):
        v_a = None if n is None else n.asString()
        v_t = None if v is None else str(v)
        return v_a, v_t

    @staticmethod
    def _cast_node_boolean(n, v):
        v_a = None if n is None else n.asBoolean()
        v_t = None if v is None else str(bool(v)).lower()
        return v_a, v_t

    def _sync_attr(self, parent, target_state, callback_handler):
        """
        Synchronise the attributes of a configuration object with allowable list of args

        :param parent: the parent dmr node containing the attributes to sync
        :param target_state: the requested target state to sync the parent to
        :param callback_handler: callback handler that can process the attribute updates
        :return: changed and changes as list
        """

        if 'cb_args' not in callback_handler:
            raise ParameterError('Unable to find cb_args in callback_handler')

        if 'cb_fun' not in callback_handler or callback_handler['cb_fun'] is None:
            raise ParameterError('Unable to find cb_fun in callback_handler')

        cb_args = callback_handler['cb_args']

        r_changed = False
        r_changes = []

        # for k, v in supported.items():
        #     if k in chk_filter and v != chk_filter.get(k):
        #         self.cmd('%s/custom-filter=%s:write-attribute(name=%s, value=%s)' % (self.path, name, k, v))
        # r_changed = True
        # r_changes.append(
        #     {'filter': name, 'property': k, 'action': 'updated', 'old': chk_filter.get(k), 'new': v})

        if target_state is None:
            return r_changed, r_changes

        for k_t, v_t in target_state.items():
            # name_fix = k_t.find('_') > -1
            k_t_namefix = k_t.replace('_', '-')

            attr = parent.get(k_t_namefix)
            attr_type = 'UNDEFINED' if attr is None else str(attr.type)

            if attr_type not in self.ARG_TYPE_DISPATCHER:
                raise ParameterError('%s.sync_attr: synchronizing attribute %s of type %s is not supported' % (
                    self.__class__.__name__, k_t_namefix, attr_type))
            else:
                debug('%s.sync_attr: check param %s of type %s' % (self.__class__.__name__, k_t_namefix, attr_type))

            dp = self.ARG_TYPE_DISPATCHER[attr_type]
            v_a, v_t = dp(attr, v_t)
            if v_a != v_t:
                debug('%s.sync_attr: param %s of type %s needs updating old[%r] new[%r]' % (
                    self.__class__.__name__, k_t_namefix, attr_type, v_a, v_t))
                r_changed = True
                cb_args['key'] = k_t_namefix
                cb_args['value'] = v_t

            if r_changed:
                cb = callback_handler['cb_fun']
                cb(**cb_args)
                r_changes.append({'attr': k_t_namefix, 'action': 'deleted' if v_t is None else 'updated', 'value': v_t})

        return r_changed, r_changes

    def _get_param(self, obj, name):
        """
        extracts a parameter from the provided configuration object
        :param obj {dict} - the object to check
        :param name {str} - the name of the param to get
        :return {any} - whatever this param is set to
        """
        if obj is None:
            raise ParameterError('%s: configuration is null' % self.__class__.__name__)
        elif name not in obj:
            raise ParameterError('%s: no % s was provided' % (self.__class__.__name__, name))
        else:
            return obj[name]

    @abstractmethod
    def apply(self, **kwargs):
        """
        Method to call with the module configuration to apply the module specific actions.
         :param kwargs {dict} the full configuration set, each module is responsible for picking out
         the bits that it needs
         :return {bool, list} returns a change flag and a list of changes that have been applied
        """
        pass


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

        r_changed = False
        r_changes = []

        if type(custom_filter) is dict:
            # we assume its a single filter configuration that was passed
            # and not a list of filters
            custom_filter = [custom_filter]

        for filter_config in custom_filter:

            state = self._get_param(filter_config, 'state')

            if state not in ['present', 'absent']:
                raise ParameterError('filter state is not one of [present|absent]')

            name = self._get_param(filter_config, 'name')

            if state == 'present':
                f_changed, f_changes = self.apply_filter_present(name, filter_config)
                if f_changed:
                    r_changed = True
                    r_changes += f_changes

                # also check that the ref is added
                f_changed, f_changes = self.apply_filter_ref_present(server_name, host_name, name, filter_config)
                if f_changed:
                    r_changed = True
                    r_changes += f_changes

            elif state == 'absent':
                f_changed, f_changes = self.apply_filter_absent(server_name, host_name, name)
                if f_changed:
                    r_changed = True
                    r_changes += f_changes

        return r_changed, r_changes

    def apply_filter_absent(self, server_name, host_name, name):

        r_changed = False
        r_changes = []

        # FIXME if 'WFLYCTL0216' not in failure:
        #     raise ProcessingError('failed to delete filter %s: %s' % (name, failure))
        try:
            self.cmd('%s/custom-filter=%s:remove()' % (self.path, name))
            r_changed = True
            r_changes.append({'filter': name, 'action': 'deleted'})
        except NotFoundError:
            pass

        try:
            self.cmd('/subsystem=undertow/server=%s/host=%s/filter-ref=%s:remove()' % (
                server_name, host_name, name))
            r_changed = True
            r_changes.append({'filter_ref': name, 'action': 'deleted'})
        except NotFoundError:
            pass

        return r_changed, r_changes

    def apply_filter_present(self, name, filter_config):

        r_changed = False
        r_changes = []

        try:
            dmr_filter = self.dmr_cmd('%s/custom-filter=%s:read-resource()' % (self.path, name))
            # reduce filter config to only allowable values
            fc = dict(
                (key, value) for (key, value) in filter_config.items() if key.replace('_', '-') in self.FILTER_PARAMS)
            cb_handler = {
                'cb_args': {
                    'filter_name': name
                },
                'cb_fun': self._update_filter_attribute
            }
            a_changed, a_changes = self._sync_attr(dmr_filter, fc, cb_handler)

            if a_changed:
                r_changed = True
                r_changes.append({'filter': name, 'action': 'updated', 'changes': a_changes})

        except NotFoundError:
            # filter does not exist and we need to create it
            module = self._get_param(filter_config, 'module')
            class_name = self._get_param(filter_config, 'class_name')
            self.cmd('%s/custom-filter=%s:add(class-name=%s, module=%s)' % (self.path, name, class_name, module))
            r_changed = True
            r_changes.append({'filter': name, 'action': 'added'})

        return r_changed, r_changes

    def apply_filter_ref_present(self, server_name, host_name, name, filter_config):

        r_changed = False
        r_changes = []

        try:
            dmr_filter_ref = self.dmr_cmd('/subsystem=undertow/server=%s/host=%s/filter-ref=%s:read-resource' % (
                server_name, host_name, name))
            # reduce filter config to only allowable values
            fc = dict(
                (key, value) for (key, value) in filter_config.items() if
                key.replace('_', '-') in self.FILTER_REF_PARAMS)
            cb_handler = {
                'cb_args': {
                    'filter_ref_name': name,
                    'server_name': server_name,
                    'host_name': host_name
                },
                'cb_fun': self._update_filter_ref_attribute
            }
            a_changed, a_changes = self._sync_attr(dmr_filter_ref, fc, cb_handler)

            if a_changed:
                r_changed = True
                r_changes.append({'filter-ref': name, 'action': 'updated', 'changes': a_changes})

        except NotFoundError:
            # filter ref does not exist and we need to create it
            priority = filter_config.get('priority', None)
            if priority is None or priority == self.DEFAULT_PRIORITY:
                cmd = '/subsystem=undertow/server=%s/host=%s/filter-ref=%s:add' % (server_name, host_name, name)
            else:
                cmd = '/subsystem=undertow/server=%s/host=%s/filter-ref=%s:add(priority=%s)' % (server_name, host_name, name, priority)

            self.cmd(cmd)
            r_changed = True
            r_changes.append({'filter-ref': name, 'action': 'added'})

        return r_changed, r_changes

    def _update_filter_attribute(self, filter_name, key, value):
        if key not in self.FILTER_PARAMS:
            raise NotImplementedError('Setting custom filter attribute %s is not supported by this module.' % key)

        if value is None:
            self.cmd(
                '%s/custom-filter=%s:undefine-attribute(name=%s)' % (self.path, filter_name, key))
        else:
            self.cmd(
                '%s/custom-filter=%s:write-attribute(name=%s, value=%s)' % (self.path, filter_name, key, value))

    def _update_filter_ref_attribute(self, server_name, host_name, filter_ref_name, key, value):
        if key not in self.FILTER_REF_PARAMS:
            raise NotImplementedError('Setting filter-ref attribute %s is not supported by this module.' % key)

        if value is None or (key == 'priority' and value == self.DEFAULT_PRIORITY):
            cmd = '/subsystem=undertow/server=%s/host=%s/filter-ref=%s:undefine-attribute(name=%s)' % (
                server_name, host_name, filter_ref_name, key)
        else:
            cmd = '/subsystem=undertow/server=%s/host=%s/filter-ref=%s:write-attribute(name=%s, value=%s)' % (
                server_name, host_name, filter_ref_name, key, value)

        self.cmd(cmd)

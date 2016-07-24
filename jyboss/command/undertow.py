# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

from jyboss.exceptions import ParameterError, NotFoundError
from jyboss.command.core import BaseJBossModule

__metaclass__ = type

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


class UndertowCustomFilterModule(BaseJBossModule):
    DEFAULT_PRIORITY = 1

    FILTER_PARAMS = {'module', 'class-name'}

    FILTER_REF_PARAMS = {'priority'}

    def __init__(self, context=None):
        super(UndertowCustomFilterModule, self).__init__(path='/subsystem=undertow/configuration=filter',
                                                         context=context)

    def __call__(self, filter_conf):
        if 'name' not in filter_conf:
            raise ParameterError('provided filter name is null')

    def apply(self, server_name=None, host_name=None, custom_filter=None, **kwargs):

        custom_filter = self.unescape_keys(custom_filter)

        if server_name is None:
            if 'server_name' in kwargs:
                server_name = kwargs['server_name']
            else:
                raise ParameterError('The undertow custom-filter module requires a server_name argument')

        if host_name is None:
            if 'host_name' in kwargs:
                host_name = kwargs['host_name']
            else:
                raise ParameterError('The undertow custom-filter module requires a host_name argument')

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


class UndertowSocketBindingModule(BaseJBossModule):
    BINDING_PARAMS = {'port'}

    def __init__(self, context=None):
        super(UndertowSocketBindingModule, self).__init__(path='/socket-binding-group=%s/socket-binding=%s',
                                                          context=context)

    def __call__(self, binding_conf):
        binding_conf = self.unescape_keys(binding_conf)
        if 'name' not in binding_conf:
            raise ParameterError('provided socket binding name is null')

        if 'socket-binding-group-name' not in binding_conf:
            raise ParameterError('provided socket binding group name is null')

    def apply(self, socket_binding=None, **kwargs):

        socket_binding = self.unescape_keys(socket_binding)

        if isinstance(socket_binding, dict):
            socket_bindings = [socket_binding]
        elif isinstance(socket_binding, list):
            socket_bindings = socket_binding
        else:
            raise ParameterError(
                '%s.apply(undertow.socket-binding:%s): The socket binding configuration is not valid.' % (
                    self.__class__.__name__, type(socket_binding)))

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
                changes.append({'socket-binding': name, 'socket-binding-group': group_name, 'action': 'updated',
                                'changes': a_changes})

        except NotFoundError:
            binding_params = self.convert_to_dmr_params(binding, self.BINDING_PARAMS)

            self.cmd('%s:add(%s)' % (resource_path, binding_params))
            changes.append({'socket-binding': name, 'socket-binding-group': group_name, 'action': 'added',
                            'params': binding_params})

        return changes

    def apply_socket_binding_absent(self, binding):
        group_name = self._get_param(binding, 'socket-binding-group-name')
        name = self._get_param(binding, 'name')
        resource_path = self.path % (group_name, name)
        try:
            self.cmd('%s:remove' % resource_path)
            return [{'socket-binding': name, 'socket-binding-group': group_name, 'action': 'deleted'}]
        except NotFoundError:
            return []


class UndertowListenerModule(BaseJBossModule):
    AJP_LISTENER = 'ajp-listener'
    HTTP_LISTENER = 'http-listener'

    def __init__(self, listener_type, listener_params, context=None):
        super(UndertowListenerModule, self).__init__(path='/subsystem=undertow/server=%s/%s=%s', context=context)
        if listener_type not in [UndertowListenerModule.AJP_LISTENER, UndertowListenerModule.HTTP_LISTENER]:
            raise ParameterError("listener type %s is not one of [%s|%s]" % (
                listener_type, UndertowListenerModule.AJP_LISTENER, UndertowListenerModule.HTTP_LISTENER))
        self.listener_type = listener_type
        self.listener_params = listener_params

    def __call__(self, binding_conf):
        binding_conf = self.unescape_keys(binding_conf)
        if 'name' not in binding_conf:
            raise ParameterError('provided %s name is null' % self.listener_type)

    def apply(self, listener_config=None, server_name=None, **kwargs):

        if server_name is None:
            if 'server_name' in kwargs:
                server_name = kwargs['server_name']
            else:
                raise ParameterError('The undertow %s module requires a server_name argument' % self.listener_type)

        listener_config = self.unescape_keys(listener_config)

        if isinstance(listener_config, dict):
            listener_configs = [listener_config]
        elif isinstance(listener_config, list):
            listener_configs = listener_config
        else:
            raise ParameterError(
                '%s.apply(keycloak.realm:%s): The %s configuration is not valid.' % (
                    self.__class__.__name__, type(listener_config), self.listener_type))

        changes = []

        for listener in listener_configs:

            state = self._get_param(listener, 'state')

            if state not in ['present', 'absent']:
                raise ParameterError('%s state is not one of [present|absent]' % self.listener_type)

            if state == 'present':
                changes += self.apply_listener_present(server_name, listener)
            elif state == 'absent':
                changes += self.apply_listener_absent(server_name, listener)

        return None if len(changes) < 1 else changes

    def apply_listener_present(self, server_name, listener):

        name = self._get_param(listener, 'name')

        resource_path = self.path % (server_name, self.listener_type, name)

        changes = []

        try:
            listener_dmr = self.read_resource_dmr(resource_path, True)
            fc = dict(
                (k, v) for (k, v) in iteritems(listener) if k in self.listener_params)
            a_changes = self._sync_attributes(parent_node=listener_dmr,
                                              parent_path=resource_path,
                                              target_state=fc,
                                              allowable_attributes=self.listener_params)
            if len(a_changes) > 0:
                changes.append({self.listener_type: name, 'action': 'updated',
                                'changes': a_changes})

        except NotFoundError:
            listener_add_params = self.convert_to_dmr_params(listener, self.listener_params)

            self.cmd('%s:add(%s)' % (resource_path, listener_add_params))
            changes.append({self.listener_type: name, 'action': 'added',
                            'params': listener_add_params})

        return changes

    def apply_listener_absent(self, server_name, listener):

        name = self._get_param(listener, 'name')

        resource_path = self.path % (server_name, self.listener_type, name)

        try:
            self.cmd('%s:remove' % resource_path)
            return [{self.listener_type: name, 'action': 'deleted'}]
        except NotFoundError:
            return []


class UndertowAjpListenerModule(UndertowListenerModule):
    LISTENER_PARAMS = ["allow-encoded-slash",
                       "allow-equals-in-cookie-value",
                       "always-set-keep-alive",
                       "buffer-pipelined-data",
                       "buffer-pool",
                       "decode-url",
                       "disallowed-methods",
                       "enabled",
                       "max-buffered-request-size",
                       "max-connections",
                       "max-cookies",
                       "max-header-size",
                       "max-headers",
                       "max-parameters",
                       "max-post-size",
                       "no-request-timeout",
                       "read-timeout",
                       "receive-buffer",
                       "record-request-start-time",
                       "redirect-socket",
                       "request-parse-timeout",
                       "resolve-peer-address",
                       "proxy-address-forwarding",
                       "scheme",
                       "secure",
                       "send-buffer",
                       "socket-binding",
                       "tcp-backlog",
                       "tcp-keep-alive",
                       "url-charset",
                       "worker",
                       "write-timeout"]

    def __init__(self, context=None):
        super(UndertowAjpListenerModule, self).__init__(listener_type=UndertowListenerModule.AJP_LISTENER,
                                                        listener_params=UndertowAjpListenerModule.LISTENER_PARAMS,
                                                        context=context)

    def apply(self, ajp_listener=None, **kwargs):
        return super(UndertowAjpListenerModule, self).apply(ajp_listener, **kwargs)


class UndertowHttpListenerModule(UndertowListenerModule):
    LISTENER_PARAMS = ["allow-encoded-slash",
                       "allow-equals-in-cookie-value",
                       "always-set-keep-alive",
                       "buffer-pipelined-data",
                       "buffer-pool",
                       "decode-url",
                       "disallowed-methods",
                       "enabled",
                       "max-buffered-request-size",
                       "max-connections",
                       "max-cookies",
                       "max-header-size",
                       "max-headers",
                       "max-parameters",
                       "max-post-size",
                       "no-request-timeout",
                       "read-timeout",
                       "receive-buffer",
                       "record-request-start-time",
                       "redirect-socket",
                       "request-parse-timeout",
                       "resolve-peer-address",
                       "proxy-address-forwarding",
                       "scheme",
                       "secure",
                       "send-buffer",
                       "socket-binding",
                       "tcp-backlog",
                       "tcp-keep-alive",
                       "url-charset",
                       "worker",
                       "write-timeout"]

    def __init__(self, context=None):
        super(UndertowHttpListenerModule, self).__init__(listener_type=UndertowListenerModule.HTTP_LISTENER,
                                                         listener_params=UndertowAjpListenerModule.LISTENER_PARAMS,
                                                         context=context)

    def apply(self, http_listener=None, **kwargs):
        return super(UndertowHttpListenerModule, self).apply(http_listener, **kwargs)

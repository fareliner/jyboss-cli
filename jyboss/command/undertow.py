# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

from jyboss.exceptions import ParameterError, NotFoundError
from jyboss.command.core import BaseJBossModule
from jyboss.logging import debug

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


class UndertowModule(BaseJBossModule):
    def __init__(self, context=None):
        super(UndertowModule, self).__init__(path='/subsystem=undertow', context=context)

        self.UNDERTOW_PARAMS = {
            "server_name",
            "host_name"
        }

        self.CONFIG_SUBMODULE = {
            'filter_ref': UndertowFilterRefModule(self.context),
            'web_filter': UndertowFilterModule(self.context),
            'http_listener': UndertowHttpListenerModule(self.context),
            'ajp_listener': UndertowAjpListenerModule(self.context)
        }

    def apply(self, undertow=None, **kwargs):

        changes = []

        undertow_config = dict((k, v) for (k, v) in undertow.items() if k not in self.CONFIG_SUBMODULE)

        undertow_config.update(kwargs)

        for key in undertow.keys():
            if key in self.CONFIG_SUBMODULE:
                handler = self.CONFIG_SUBMODULE[key]
                subchanges = handler.apply(undertow[key], **undertow_config)
                if subchanges is not None:
                    changes.append({
                        key: subchanges
                    })
            elif key in self.UNDERTOW_PARAMS:
                pass
            else:
                raise ParameterError('%s cannot handle configuration %s' % (self.__class__.__name__, key))

        return None if len(changes) < 1 else changes


class UndertowFilterRefModule(BaseJBossModule):
    DEFAULT_PRIORITY = 1

    FILTER_REF_PARAMS = {'priority'}

    def __init__(self, context=None):
        super(UndertowFilterRefModule, self).__init__(path='/subsystem=undertow/server=%s/host=%s/filter-ref=%s',
                                                      context=context)

    def apply(self, filter_ref=None, server_name=None, host_name=None, **kwargs):

        filter_refs = self._format_apply_param(filter_ref)

        if server_name is None:
            if 'server_name' in kwargs:
                server_name = kwargs['server_name']
            else:
                raise ParameterError('The undertow filter-ref module requires a server_name argument')

        if host_name is None:
            if 'host_name' in kwargs:
                host_name = kwargs['host_name']
            else:
                raise ParameterError('The undertow filter-ref module requires a host_name argument')

        changes = []

        for fref in filter_refs:

            state = self._get_param(fref, 'state')

            if state not in ['present', 'absent']:
                raise ParameterError('filter state is not one of [present|absent]')

            name = self._get_param(fref, 'name')

            if state == 'present':
                changes += self.apply_filter_ref_present(server_name, host_name, name, fref)

            elif state == 'absent':
                changes += self.apply_filter_ref_absent(server_name, host_name, name)

        return None if len(changes) < 1 else changes

    def apply_filter_ref_absent(self, server_name, host_name, name):

        changes = []
        try:
            self.cmd(self.path % (server_name, host_name, name) + ':remove()')
            changes.append({'filter_ref': name, 'action': 'delete'})
        except NotFoundError:
            pass

        return changes

    def apply_filter_ref_present(self, server_name, host_name, name, filter_config):
        changes = []
        filter_ref_path = self.path % (server_name, host_name, name)
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
                changes.append({'filter-ref': name, 'action': 'update', 'changes': a_changes})

        except NotFoundError:
            # filter ref does not exist and we need to create it
            priority = filter_config.get('priority', None)
            if priority is None or priority == self.DEFAULT_PRIORITY:
                cmd = '/subsystem=undertow/server=%s/host=%s/filter-ref=%s:add' % (server_name, host_name, name)
            else:
                cmd = '/subsystem=undertow/server=%s/host=%s/filter-ref=%s:add(priority=%s)' % (
                    server_name, host_name, name, priority)

            self.cmd(cmd)
            changes.append({'filter-ref': name, 'action': 'add'})

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


class UndertowFilterModule(BaseJBossModule):
    """
    Module that can modify filters.

    web_filter:
        name: filter-name
        type: type of filter e.g. [custom-filter|response-header]
        state: [present|absent]
        prop_x: property by name from each of the filter type definitions

    """

    FILTER_PARAMS = {
        'custom-filter': [
            'module',
            'class-name'
        ],
        'response-header': [
            'header-name',
            'header-value'
        ]
    }

    def __init__(self, context=None):
        super(UndertowFilterModule, self).__init__(path='/subsystem=undertow/configuration=filter',
                                                   context=context)
        self.filter_ref_module = UndertowFilterRefModule(context)

    def apply(self, web_filter=None, **kwargs):

        if web_filter is None:
            raise ParameterError('filter must not be null')

        filters = self._format_apply_param(web_filter)

        changes = []

        for filter_config in filters:

            state = self._get_param(filter_config, 'state')

            if state not in ['present', 'absent']:
                raise ParameterError('filter state is not one of [present|absent]')

            if state == 'present':
                changes += self.apply_filter_present(filter_config)
                # the filter configuration carries enough information for us to also create the filter-ref element
                ref_change = self.filter_ref_module.apply(filter_config, **kwargs)
                if ref_change is not None:
                    changes += ref_change
            elif state == 'absent':
                # the filter configuration carries enough information for us to also remove the filter-ref element
                ref_change = self.filter_ref_module.apply(filter_config, **kwargs)
                if ref_change is not None:
                    changes += ref_change
                changes += self.apply_filter_absent(filter_config)

        return None if len(changes) < 1 else changes

    def apply_filter_absent(self, filter_config):
        filter_name = self._get_param(filter_config, 'name')
        filter_type = self._get_param(filter_config, 'type')
        changes = []
        # FIXME if 'WFLYCTL0216' not in failure:
        #     raise ProcessingError('failed to delete filter %s: %s' % (name, failure))
        try:
            self.cmd('%s/%s=%s:remove()' % (self.path, filter_type, filter_name))
            changes.append({'filter': filter_name, 'type': filter_type, 'action': 'delete'})
        except NotFoundError:
            pass

        return changes

    def apply_filter_present(self, filter_config):
        filter_name = self._get_param(filter_config, 'name')
        filter_type = self._get_param(filter_config, 'type')
        changes = []
        try:
            dmr_filter = self.read_resource_dmr('%s/%s=%s' % (self.path, filter_type, filter_name))
            # reduce filter config to only allowable values
            fc = dict(
                (key, value) for (key, value) in filter_config.items() if
                key in self.FILTER_PARAMS.get(filter_type, []))
            a_changes = self._sync_attributes(parent_node=dmr_filter,
                                              parent_path='%s/%s=%s' % (self.path, filter_type, filter_name),
                                              target_state=fc,
                                              allowable_attributes=self.FILTER_PARAMS.get(filter_type, []))

            if len(a_changes) > 0:
                changes.append({'filter': filter_name, 'type': filter_type, 'action': 'update', 'changes': a_changes})

        except NotFoundError:
            filter_params = self.convert_to_dmr_params(filter_config, self.FILTER_PARAMS.get(filter_type, []))
            self.cmd('%s/%s=%s:add(%s)' % (self.path, filter_type, filter_name, filter_params))
            changes.append({'filter': filter_name, 'type': filter_type, 'action': 'add', 'params': filter_params})

        return changes


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

        listener_configs = self._format_apply_param(listener_config)

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

        debug('%s:add(): %r' % (self.__class__.__name__, listener))
        debug('  >> allowed_params: %r' % self.listener_params)

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
                changes.append({self.listener_type: name, 'action': 'update',
                                'changes': a_changes})

        except NotFoundError:
            listener_add_params = self.convert_to_dmr_params(listener, self.listener_params)
            self.cmd('%s:add(%s)' % (resource_path, listener_add_params))
            changes.append({self.listener_type: name, 'action': 'add',
                            'params': listener_add_params})

        return changes

    def apply_listener_absent(self, server_name, listener):

        name = self._get_param(listener, 'name')

        resource_path = self.path % (server_name, self.listener_type, name)

        try:
            self.cmd('%s:remove' % resource_path)
            return [{self.listener_type: name, 'action': 'delete'}]
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

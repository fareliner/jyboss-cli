# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

from abc import ABCMeta

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


class InfinispanModule(BaseJBossModule):
    def __init__(self, context=None):
        super(InfinispanModule, self).__init__(path='/subsystem=infinispan', context=context)
        self.submodules = {
            'cache-container': CacheContainerModule(self.context)
        }

    def apply(self, infinispan=None, **kwargs):

        infinispan = self.unescape_keys(infinispan)

        if not isinstance(infinispan, dict):
            raise ParameterError('%s.apply(): No valid infinispan subsystem configuration provided: %r' % (
                self.__class__.__name__, infinispan))

        changes = []

        state = self._get_param(infinispan, 'state')
        if state not in ['present', 'absent']:
            raise ParameterError('The infinispan state is not one of [present|absent]')

        if state == 'present':
            changes += self.apply_present(infinispan)
        elif state == 'absent':
            changes += self.apply_absent()

        return changes if len(changes) > 0 else None

    def apply_present(self, infinispan):
        changes = []

        try:
            self.read_resource(self.path, recursive=False)
        except NotFoundError:
            self.cmd('%s:add()' % self.path)
            changes.append({'subsystem': 'infinispan', 'action': 'add'})

        for key in infinispan:
            # first check if a submodule handler exists for the key element
            if key in self.submodules:
                handler = self.submodules[key]
                handler_changes = handler.apply(infinispan[key])
                if len(handler_changes) > 0:
                    changes += handler_changes
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
            changes.append({'subsystem': 'infinispan', 'action': 'delete'})
        except NotFoundError:
            pass

        return changes


class CacheContainerModule(BaseJBossModule):
    CONTAINER_PARAMS = [
        'default',
        'aliases',
        'jndi-name',
        'default-cache',
        'module',
        'statistics-enabled'
    ]

    def __init__(self, context=None):
        super(CacheContainerModule, self).__init__(path='/subsystem=infinispan/cache-container=%s',
                                                   context=context)
        self.submodules = {
            'transport': TransportModule(self.context),
            'caches': CacheResolverDelegate(self.context)
        }

    def apply(self, containers=None, **kwargs):

        containers = self._format_apply_param(containers)

        changes = []

        for container in containers:
            state = self._get_param(container, 'state')
            if state not in ['present', 'absent']:
                raise ParameterError('The container state is not one of [present|absent]')

            if state == 'present':
                changes += self.apply_present(container)
            elif state == 'absent':
                changes += self.apply_absent(container)

        return changes

    def apply_absent(self, stack):

        name = self._get_param(stack, 'name')
        try:
            self.cmd((self.path + ':remove()') % name)
            return [{'cache-container': name, 'action': 'delete'}]
        except NotFoundError:
            return []

    def apply_present(self, container):
        container_name = self._get_param(container, 'name')
        container_path = self.path % container_name

        change = {
            'cache-container': container_name,
            'action': None,
            'changes': []
        }

        try:
            container_dmr = self.read_resource_dmr(container_path, recursive=True)
            fc = dict(
                (k, v) for (k, v) in iteritems(container) if k in self.CONTAINER_PARAMS)
            update_changes = self._sync_attributes(parent_node=container_dmr,
                                                   parent_path=container_path,
                                                   target_state=fc,
                                                   allowable_attributes=self.CONTAINER_PARAMS)
            if len(update_changes) > 0:
                change['action'] = 'update'
                change['changes'] += update_changes

        except NotFoundError:
            container_params = self.convert_to_dmr_params(container, self.CONTAINER_PARAMS)
            self.cmd('%s:add(%s)' % (container_path, container_params))
            change['action'] = 'add'
            if len(container_params) > 0:
                change['params'] = container_params

        # now apply all sub component handlers
        for key in container:
            if key in self.submodules:
                handler = self.submodules[key]
                modchanges = handler.apply(container_name, container[key])
                if len(modchanges) > 0:
                    if change['action'] is None:
                        change['action'] = 'update'
                    change['changes'] += modchanges
            elif key in ['state', 'name'] + CacheContainerModule.CONTAINER_PARAMS:
                pass  # not interested in these ones as they would have been processed above already
            else:
                raise ParameterError('%s cannot handle configuration %s' % (self.__class__.__name__, key))

        if len(change['changes']) < 1:
            change.pop('changes')

        return [] if change['action'] is None else [change]


class TransportModule(BaseJBossModule):
    TRANSPORT_PARAMS = [
        'channel',
        'stack',
        'cluster',
        'lock-timeout'
    ]

    def __init__(self, context=None):
        super(TransportModule, self).__init__(
            path='/subsystem=infinispan/cache-container=%s/transport=TRANSPORT',
            context=context)

    def apply(self, container_name, transport=None, **kwargs):

        changes = []

        state = self._get_param(transport, 'state')
        if state not in ['present', 'absent']:
            raise ParameterError('The container transport state is not one of [present|absent]')

        if state == 'present':
            changes += self.apply_present(container_name, transport)
        elif state == 'absent':
            changes += self.apply_absent(transport)

        return changes

    def apply_absent(self, container_name):

        try:
            self.cmd((self.path + ':remove()') % container_name)
            return [{'transport': 'TRANSPORT', 'action': 'delete'}]
        except NotFoundError:
            return []

    def apply_present(self, container_name, transport):
        transport_path = self.path % container_name
        change = {
            'transport': 'TRANSPORT',
            'action': None,
            'changes': []
        }

        try:
            transport_dmr = self.read_resource_dmr(transport_path, recursive=True)
            fc = dict(
                (k, v) for (k, v) in iteritems(transport) if k in self.TRANSPORT_PARAMS)
            a_changes = self._sync_attributes(parent_node=transport_dmr,
                                              parent_path=transport_path,
                                              target_state=fc,
                                              allowable_attributes=self.TRANSPORT_PARAMS)
            if len(a_changes) > 0:
                change['action'] = 'update'
                change['changes'] += a_changes

        except NotFoundError:
            transport_params = self.convert_to_dmr_params(transport, self.TRANSPORT_PARAMS)
            self.cmd('%s:add(%s)' % (transport_path, transport_params))
            change['action'] = 'add'
            if len(transport_params) > 0:
                change['params'] = transport_params

        if len(change['changes']) < 1:
            change.pop('changes')

        return [] if change['action'] is None else [change]


class CacheResolverDelegate(object):
    def __init__(self, context=None):
        self.submodules = {
            'local-cache': LocalCache(context),
            'replicated-cache': ReplicatedCache(context),
            'invalidation-cache': InvalidationCache(context),
            'distributed-cache': DistributedCache(context)
        }

    def apply(self, container_name, caches):

        changes = []

        for cache in caches:
            if 'type' not in cache:
                raise ParameterError('%s: cache type was not provided' % self.__class__.__name__)
            cache_type = cache['type']
            if cache_type in self.submodules:
                changes += self.submodules[cache_type].apply(container_name, cache)
            else:
                raise ParameterError(
                    '%s does not have a cache handler for type %s' % (self.__class__.__name__, cache_type))

        return changes


class Cache(BaseJBossModule):
    __metaclass__ = ABCMeta

    def __init__(self, context=None):
        super(Cache, self).__init__(path='/subsystem=infinispan/cache-container=%s/%s=%s', context=context)
        self.cache_params = [
            'jndi-name',
            'module',
            'statistics-enabled'
        ]

        self.cache_modules = {
            'locking': Component(component_type='locking',
                                 component_params=[
                                     'isolation',
                                     'striping',
                                     'acquire-timeout',
                                     'concurrency-level'
                                 ],
                                 context=context),
            'transaction': Component(component_type='transaction',
                                     component_params=[
                                         'mode',
                                         'stop-timeout',
                                         'locking'
                                     ],
                                     context=context),
            'eviction': Component(component_type='eviction',
                                  component_params=[
                                      'strategy',
                                      'max-entries'
                                  ],
                                  context=context),
            'expiration': Component(component_type='expiration',
                                    component_params=[
                                        'max-idle',
                                        'lifespan',
                                        'interval'
                                    ],
                                    context=context)
            # FIXME implement store cache submodules
            # store
            # file-store
            # string-keyed-jdbc-store
            # binary-keyed-jdbc-store
            # mixed-keyed-jdbc-store
            # remote-store
        }

    def apply(self, container_name, cache=None, **kwargs):
        changes = []
        state = self._get_param(cache, 'state')
        if state not in ['present', 'absent']:
            raise ParameterError('The cache state is not one of [present|absent]')

        if state == 'present':
            changes += self.apply_present(container_name, cache)
        elif state == 'absent':
            changes += self.apply_absent(container_name, cache)

        return changes

    def apply_absent(self, container_name, cache):
        cache_name = self._get_param(cache, 'name')
        cache_type = self._get_param(cache, 'type')
        try:
            self.cmd((self.path + ':remove()') % (container_name, cache_type, cache_name))
            return [{cache_type: cache_name, 'action': 'delete'}]
        except NotFoundError:
            return []

    def apply_present(self, container_name, cache):
        cache_name = self._get_param(cache, 'name')
        cache_type = self._get_param(cache, 'type')
        cache_path = self.path % (container_name, cache_type, cache_name)

        change = {
            cache_type: cache_name,
            'action': None,
            'changes': []
        }

        try:
            cache_dmr = self.read_resource_dmr(cache_path, recursive=True)
            fc = dict(
                (k, v) for (k, v) in iteritems(cache) if k in self.cache_params)
            attr_changes = self._sync_attributes(parent_node=cache_dmr,
                                                 parent_path=cache_path,
                                                 target_state=fc,
                                                 allowable_attributes=self.cache_params)
            if len(attr_changes) > 0:
                change['action'] = 'update'
                change['changes'] += attr_changes

        except NotFoundError:
            cache_params = self.convert_to_dmr_params(cache, self.cache_params)
            self.cmd('%s:add(%s)' % (cache_path, cache_params))
            change['action'] = 'add'
            if len(cache_params) > 0:
                change['params'] = cache_params

        # process all submodules
        for key in cache:
            if key in self.cache_modules:
                modchanges = self.cache_modules[key].apply(container_name=container_name, cache_type=cache_type,
                                                           cache_name=cache_name, config=cache[key])
                if len(modchanges) > 0:
                    change[key] = modchanges

            elif key in self.cache_params or key in ['state', 'name', 'type']:
                pass
            else:
                raise ParameterError(
                    '%s does not have a component handler for %s' % (self.__class__.__name__, key))

        if len(change['changes']) < 1:
            change.pop('changes')

        return [] if change['action'] is None else [change]


class ClusteredCache(Cache):
    __metaclass__ = ABCMeta

    def __init__(self, context=None):
        super(ClusteredCache, self).__init__(context=context)
        self.cache_params += [
            'mode',
            'queue-size',
            'queue-flush-interval',
            'remote-timeout'
        ]


class SharedStateCache(ClusteredCache):
    __metaclass__ = ABCMeta

    def __init__(self, context=None):
        super(SharedStateCache, self).__init__(context=context)
        self.cache_modules['partition-handling'] = Component(component_type='partition-handling',
                                                             component_params=['enabled'],
                                                             context=context)
        self.cache_modules['state-transfer'] = Component(component_type='state-transfer',
                                                         component_params=['timeout', 'chunk-size'],
                                                         context=context)
        # FIXME implement backup cache submodules
        # backups
        # backup-for


class LocalCache(Cache):
    def __init__(self, context=None):
        super(LocalCache, self).__init__(context=context)


class InvalidationCache(ClusteredCache):
    def __init__(self, context=None):
        super(InvalidationCache, self).__init__(context=context)


class ReplicatedCache(SharedStateCache):
    def __init__(self, context=None):
        super(ReplicatedCache, self).__init__(context=context)


class DistributedCache(SharedStateCache):
    def __init__(self, context=None):
        super(DistributedCache, self).__init__(context=context)
        self.cache_params += [
            'owners',
            'segments',
            'l1-lifespan',
            'capacity-factor',
            'consistent-hash-strategy'
        ]


class Component(BaseJBossModule):
    def __init__(self, component_type, component_params=None, context=None):
        super(Component, self).__init__(path='/subsystem=infinispan/cache-container=%s/%s=%s/component=%s',
                                        context=context)
        self.component_type = component_type
        self.component_params = component_params

    def apply(self, container_name, cache_type, cache_name, config=None, **kwargs):
        if config is None:
            return self.apply_absent(container_name, cache_type, cache_name)
        else:
            return self.apply_present(container_name, cache_type, cache_name, config)

    def apply_absent(self, container_name, cache_type, cache_name):
        try:
            self.cmd((self.path + ':remove()') % (container_name, cache_type, cache_name, self.component_type))
            return [{'component': self.component_type, 'action': 'delete'}]
        except NotFoundError:
            return []

    def apply_present(self, container_name, cache_type, cache_name, config):
        config_path = self.path % (container_name, cache_type, cache_name, self.component_type)
        change = {
            'component': self.component_type,
            'action': None,
            'changes': []
        }

        try:
            config_dmr = self.read_resource_dmr(config_path, recursive=True)
            fc = dict(
                (k, v) for (k, v) in iteritems(config) if k in self.component_params)
            attr_changes = self._sync_attributes(parent_node=config_dmr,
                                                 parent_path=config_path,
                                                 target_state=fc,
                                                 allowable_attributes=self.component_params)
            if len(attr_changes) > 0:
                change['action'] = 'update'
                change['changes'] += attr_changes

        except NotFoundError:
            config_params = self.convert_to_dmr_params(config, self.component_params)
            self.cmd('%s:add(%s)' % (config_path, config_params))
            change['action'] = 'add'
            if len(config_params) > 0:
                change['params'] = config_params

        if len(change['changes']) < 1:
            change.pop('changes')

        return [] if change['action'] is None else [change]

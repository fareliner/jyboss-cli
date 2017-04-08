# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

from jyboss.exceptions import ParameterError, CommandError
from jyboss.command.core import BaseJBossModule
from jyboss.logging import debug

from java.io import File

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


class ModuleModule(BaseJBossModule):
    MODULE_PARAMS = [
        {'name': 'name', 'type': 'str'},
        {'name': 'property', 'type': 'property'},
        {'name': 'enabled', 'type': 'list'}
    ]

    def __init__(self, context=None):
        super(ModuleModule, self).__init__(path='module ', context=context)

    def apply(self, module=None, **kwargs):

        modules = self._format_apply_param(module)

        changes = []

        for mod in modules:
            state = self._get_param(mod, 'state')

            if state not in ['present', 'absent']:
                raise ParameterError('The module state is not one of [present|absent]')

            if state == 'present':
                args = ['%s add' % self.path]
            elif state == 'absent':
                args = ['%s remove' % self.path]

            delim = mod.get('resource-delimiter', File.pathSeparatorChar)
            module_base = mod.get('module-base', 'system.layers.base')

            for k, v in mod.items():
                if k in ['name']:
                    args.append('--%s=%s.%s' % (k, module_base, v))
                elif k in ['slot', 'main-class', 'module-xml']:
                    args.append('--%s=%s' % (k, v))
                elif k in ['resources']:
                    if isinstance(v, list):
                        args.append('--%s=%s' % (k, delim.join(v)))
                    else:
                        args.append('--%s=%s' % (k, v))
                elif k in ['properties']:
                    if isinstance(v, dict):
                        args.append('--%s=%s' % (k, ','.join('%s=%s' % (name, value) for name, value in iteritems(v))))
                    else:
                        raise ParameterError('Format of %s parameter is invalid.' % k)

            try:
                cmd = ' '.join(args)
                debug('module: execute command %s' % cmd)
                self.cmd(cmd)
                changes.append(
                    {'module': self._get_param(mod, 'name'), 'action': 'add' if state == 'present' else 'delete'})
            except CommandError as ce:
                debug('module command error %r' % ce)
                self.debug_errm(ce)
                cause = getattr(ce, 'cause') if hasattr(ce, 'cause') else None
                msg = getattr(cause, 'message') if cause is not None and hasattr(cause, 'message') else ''
                if msg.find('already exists') != -1 or msg.find('Failed to locate module') != -1:
                    # ignore as nothing to do
                    debug('Ignoring module deploy error: %s' % msg)
                else:
                    raise ce
            except Exception as coe:
                debug('module other error %r' % coe)
                self.debug_errm(coe)
                raise coe

        return changes if len(changes) > 0 else None

    def debug_errm(self, err, level=0):
        msg = err.message if 'message' in err and err['message'] is not None else ''
        debug(msg.rjust(level + 1, '>'))
        if 'cause' in err and err['cause'] is not None:
            self.debug_errm(err.cause, level + 1)

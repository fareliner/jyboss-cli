# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

from jyboss.exceptions import NotFoundError
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


class DeploymentModule(BaseJBossModule):
    DEPLOYMENT_PARAMS = [
        'name',
        'enabled'
    ]

    def __init__(self, context=None):
        super(DeploymentModule, self).__init__(path='/deployment=%s', context=context)

    def apply(self, deployment=None, **kwargs):

        deployments = self._format_apply_param(deployment)

        changes = []

        for d in deployments:
            name = self._get_param(d, 'name')
            enabled = self._get_param(d, 'enabled')
            action = 'deploy' if enabled else 'undeploy'
            debug(self.__class__.__name__ + '.apply: ' + (self.path % name) + ':' + action)
            try:
                cur_depl = self.read_resource(self.path % name)
                if 'enabled' in cur_depl:
                    if cur_depl['enabled'] != enabled:
                        self.cmd((self.path % name) + ':' + action)
                        changes.append({'deployment': name, 'action': action})

            except NotFoundError:
                pass

        return changes if len(changes) > 0 else None

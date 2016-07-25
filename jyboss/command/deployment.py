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


class DeploymentModule(BaseJBossModule):
    DEPLOYMENT_PARAMS = [
        'name',
        'enabled'
    ]

    def __init__(self, context=None):
        super(DeploymentModule, self).__init__(path='/deployment=%s', context=context)

    def apply(self, deployments=None, **kwargs):

        deployments = self.unescape_keys(deployments)

        if type(deployments) is not dict:
            raise ParameterError('%s provided to %s is not an allowable type' % (deployments, self.__class__.__name__))

        changes = []

        for key in deployments.keys():
            if key == 'data-source':
                datasources = self._format_apply_param(datasources['data-source'])
                changes += self.apply_datasources(datasources)
            elif key == 'jdbc-driver':
                drivers = self._format_apply_param(datasources['jdbc-driver'])
                changes += self.apply_jdbc_drivers(drivers)

        if len(changes) > 0:
            changes = {
                'datasources': changes
            }
        else:
            changes = None

        return changes

    def apply_datasources(self, datasources):

        changes = []
        for ds in datasources:

            name = self._get_param(ds, 'name')

            state = self._get_param(ds, 'state')

            if state not in ['present', 'absent']:
                raise ParameterError('The datasource state is not one of [present|absent]')

            if state == 'present':
                changes += self.apply_datasource_present(name, ds)
            elif state == 'absent':
                changes += self.apply_datasource_absent(name)

        return changes

    def apply_datasource_absent(self, name):

        try:
            self.cmd('%s/data-source=%s:remove()' % (self.path, name))
            return [{'datasource': name, 'action': 'deleted'}]
        except NotFoundError:
            return []

    def apply_datasource_present(self, name, datasource):

        ds_path = '%s/data-source=%s' % (self.path, name)

        changes = []
        try:
            ds_dmr = self.read_resource_dmr(ds_path)
            # update datasource
            fc = dict(
                (k, v) for (k, v) in iteritems(datasource) if k in self.DATASOURCE_PARAMS)
            a_changes = self._sync_attributes(parent_node=ds_dmr,
                                              parent_path=ds_path,
                                              target_state=fc,
                                              allowable_attributes=self.DATASOURCE_PARAMS)
            if len(a_changes) > 0:
                changes.append({'datasource': name, 'action': 'updated', 'changes': a_changes})

        except NotFoundError:
            # create the datasource
            ds_params = self.convert_to_dmr_params(datasource, self.DATASOURCE_PARAMS)
            self.cmd('%s/data-source=%s:add(%s)' % (self.path, name, ds_params))
            changes.append({'datasource': name, 'action': 'added', 'params': ds_params})

        return changes

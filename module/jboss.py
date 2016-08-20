#! /usr/bin/env jython
# WANT_JSON

# Ansible Module

# Note: If you need to use env to discover where json is, in your inventory
# file set the ansible_jython_interpreter variable for the hosts you're
# running this module on ex:
#
# myhost ansible_jython_interpreter="/usr/bin/env jython"
DOCUMENTATION = '''
---
module: jboss
short_description: Manage jboss container via jboss-cli
'''

import sys

from jyboss import jyboss, embedded, standalone
from jyboss.command import *
from jyboss.logging import debug
from jyboss.ansible import AnsibleModule
from jyboss.command import escape_keys
from jyboss.exceptions import NotFoundError


def main():
    result = dict(changed=False)

    try:

        # region ansible boilerplate
        ansible = AnsibleModule(
            argument_spec=dict(
                jboss_home=dict(required=True),
                config_file=dict(required=False, type='str'),
                embedded_mode=dict(default=False, type='bool'),
                domain_mode=dict(default=False, type='bool'),
                server_name=dict(default='default-server', type='str'),
                host_name=dict(default='default-host', type='str'),
                reload=dict(default=False, type='bool'),
                collect_facts=dict(default=False, type='bool')
            ),
        )

        # set a jboss home if it is not passed in as either ENV variable or set as system property
        if 'jboss_home' in ansible.params:
            jyboss.jboss_home = ansible.params['jboss_home']
            debug('jboss_home set to %s' % jyboss.jboss_home)

        if 'config_file' in ansible.params:
            jyboss.config_file = ansible.params['config_file']
            debug('config_file set to %s' % jyboss.config_file)

        if ansible.params.get('domain_mode', False):
            debug('interact in domain mode')
        else:
            debug('interact in standalone mode')

        if ansible.params.get('embedded_mode', False):
            conn = embedded
            debug('embedded connect mode')
        else:
            conn = standalone
            debug('server connect mode')

        jyboss.interactive = False

        change_processor = ChangeObservable()
        # register all modules needed for processing, extensions not registered will simply be ignored
        change_processor.register(ExtensionModule(jyboss))
        change_processor.register(UndertowModule(jyboss))
        change_processor.register(SecurityModule(jyboss))
        change_processor.register(KeycloakModule(jyboss))
        change_processor.register(EEModule(jyboss))
        change_processor.register(ModuleModule(jyboss))
        change_processor.register(DatasourcesModule(jyboss))
        change_processor.register(DeploymentModule(jyboss))
        change_processor.register(ReloadCommandHandler(jyboss))
        # endregion

        with conn:
            if ansible.params.get('facts', False):
                debug('jyboss.ansible: collecting facts')
                facter = ansible.params['facts']
                fact_path = '/'
                fact_name = 'jboss'
                fact_recursive = True
                if isinstance(facter, dict):
                    if 'path' in facter:
                        fact_path = facter['path']
                    if 'name' in facter:
                        fact_name = facter['name']
                    if 'recursive' in facter:
                        fact_recursive = bool(facter['recursive'])
                try:
                    facts = cmd('%s:read-resource(recursive=%s)' % (fact_path, str(fact_recursive).lower()))
                    result.setdefault('ansible_facts', {})[fact_name] = escape_keys(facts)
                except NotFoundError:
                    pass

            changeset = change_processor.process_instructions(ansible.params)
            if changeset.pop('changed', False):
                result['changed'] = True
            for key in changeset:
                result[key] = changeset[key]

        ansible.exit_json(**result)
    except Exception as err:
        result['msg'] = err.message
        # result['failure_details'] = err
        result['invocation'] = ansible.params
        ansible.fail_json(**result)


if __name__ == '__main__':
    main()
    sys.exit(0)

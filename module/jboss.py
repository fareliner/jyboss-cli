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

from jyboss import jyboss, cmd, embedded, standalone, jyboss_undertow_filter, jyboss_extension
from jyboss.logging import debug
from jyboss.ansible import AnsibleModule
from jyboss.command import escape_keys


def main():
    global ansible

    ansible = AnsibleModule(
        argument_spec=dict(
            jboss_home=dict(required=True),
            config_file=dict(required=False, type='str'),
            embedded_mode=dict(default=False, type='bool'),
            domain_mode=dict(default=False, type='bool'),
            server_name=dict(default='default-server', type='str'),
            host_name=dict(default='default-host', type='str'),
            reload=dict(default=False, type='bool'),
            collect_facts=dict(default=False, type='bool'),
            socket_binding=dict(required=False),
            ajp_listener=dict(required=False),
            http_listener=dict(required=False),
            custom_filter=dict(required=False),
            jdbc_driver=dict(required=False),
            datasource=dict(required=False),
            deployment=dict(required=False),
            ee=dict(required=False)
        )
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

    jyboss.noninteractive()

    result = dict(changed=False)

    with conn:
        if ansible.params.get('facts', False):
            facts = cmd('/:read-resource(recursive=true)')
            result.setdefault('ansible_facts', {})['jboss'] = escape_keys(facts.get('response', None))

        if ansible.params.get('custom_filter', False):
            changes = jyboss_undertow_filter.apply(**ansible.params)
            if changes is not None:
                result['changed'] = True
                result.setdefault('changes', {})['custom_filter'] = changes

        if ansible.params.get('extension', False):
            changes = jyboss_extension.apply(**ansible.params)
            if changes is not None:
                result['changed'] = True
                result.setdefault('changes', {})['extension'] = changes

    ansible.exit_json(**result)


# if ctx.silent_streams is not None:
#     for line in ctx.silent_streams.out.lines:
#         info(line)
#
#     for line in ctx.silent_streams.err.lines:
#         info(line)


if __name__ == '__main__':
    main()
    sys.exit(0)

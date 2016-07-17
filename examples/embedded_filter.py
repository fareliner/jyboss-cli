#! /usr/bin/env jython
import sys

from collections import defaultdict

from jyboss import *
from jyboss.logging import debug
from jyboss.core.ansible import AnsibleModule

from jyboss.core import *


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

    if 'domain_mode' in ansible.params and ansible.params['domain_mode']:
        debug('interact in domain mode')
    else:
        debug('interact in standalone mode')

    if 'embedded_mode' in ansible.params and ansible.params['embedded_mode']:
        conn = embedded
        debug('embedded connect mode')
    else:
        conn = standalone
        debug('server connect mode')

    jyboss.noninteractive()

    result = dict(changed=False)

    with conn:
        if 'facts' in ansible.params and ansible.params['facts']:
            debug('collecting facts')
            result['ansible_facts'] = cmd('/:read-resource(recursive=true)')['response']
            # # restructure children
            # container_children = cmd('/:read-children-types')['response']
            # if isinstance(container_children, list):
            #     result['ansible_facts']['children'] = dict()
            #     for child_name in container_children:
            #         if child_name in result['ansible_facts']:
            #             result['ansible_facts']['children'] = result['ansible_facts'][child_name]
            #             result['ansible_facts'].pop(child_name, None)

            # container_children = cmd('/:read-children-types')['response']
            # if isinstance(container_children, list):
            #     result['ansible_facts']['children'] = dict()
            #     for child_name in container_children:
            #         child_values = cmd('/:read-children-names(child-type=%s)' % child_name)['response']
            #         for child_value in child_values:
            #             child = cmd('/%s=%s:read-resource(recursive=true)' % (child_name, child_value))['response']
            #             result['ansible_facts']['children'].setdefault(child_name, []).append(child)

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

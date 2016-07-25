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

    result = dict(changed=False)

    try:
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

            if ansible.params.get('extension', False):
                debug('jyboss.ansible: process extensions')
                handler = ExtensionModule(jyboss)
                changes = handler.apply(**ansible.params)
                if changes is not None:
                    result['changed'] = True
                    result.setdefault('changes', {})['extension'] = changes

            if ansible.params.get('security', False):
                debug('jyboss.ansible: process security')
                handler = SecurityModule(jyboss)
                changes = handler.apply(**ansible.params)
                if changes is not None:
                    result['changed'] = True
                    result.setdefault('changes', {})['security'] = changes

            if ansible.params.get('keycloak', False):
                debug('jyboss.ansible: process keycloak')
                handler = KeycloakModule(jyboss)
                changes = handler.apply(**ansible.params)
                if changes is not None:
                    result['changed'] = True
                    result.setdefault('changes', {})['keycloak'] = changes

            if ansible.params.get('undertow', False):
                undertow = ansible.params['undertow']
                if undertow.get('custom_filter', False):
                    debug('jyboss.ansible: process custom filters')
                    handler = UndertowCustomFilterModule(jyboss)
                    changes = handler.apply(custom_filter=undertow['custom_filter'], **ansible.params)
                    if changes is not None:
                        result['changed'] = True
                        result.setdefault('changes', {})['custom_filter'] = changes
                if undertow.get('socket_binding', False):
                    debug('jyboss.ansible: process socket bindings')
                    handler = UndertowSocketBindingModule(jyboss)
                    changes = handler.apply(socket_binding=undertow['socket_binding'], **ansible.params)
                    if changes is not None:
                        result['changed'] = True
                        result.setdefault('changes', {})['socket_binding'] = changes
                if undertow.get('http_listener', False):
                    debug('jyboss.ansible: process http listener')
                    handler = UndertowHttpListenerModule(jyboss)
                    changes = handler.apply(http_listener=undertow['http_listener'], **ansible.params)
                    if changes is not None:
                        result['changed'] = True
                        result.setdefault('changes', {})['http_listener'] = changes
                if undertow.get('ajp_listener', False):
                    debug('jyboss.ansible: process ajp listener')
                    handler = UndertowAjpListenerModule(jyboss)
                    changes = handler.apply(ajp_listener=undertow['ajp_listener'], **ansible.params)
                    if changes is not None:
                        result['changed'] = True
                        result.setdefault('changes', {})['ajp_listener'] = changes

            if ansible.params.get('ee', False):
                debug('jyboss.ansible: process ee')
                handler = EEModule(jyboss)
                changes = handler.apply(**ansible.params)
                if changes is not None:
                    result['changed'] = True
                    result.setdefault('changes', {})['ee'] = changes

            if ansible.params.get('module', False):
                debug('jyboss.ansible: process module')
                handler = ModuleModule(jyboss)
                changes = handler.apply(**ansible.params)
                if changes is not None:
                    result['changed'] = True
                    result.setdefault('changes', {})['module'] = changes

            if ansible.params.get('datasources', False):
                debug('jyboss.ansible: process datasources')
                handler = DatasourcesModule(jyboss)
                changes = handler.apply(**ansible.params)
                if changes is not None:
                    result['changed'] = True
                    result.setdefault('changes', {})['datasources'] = changes

            if ansible.params.get('deployment', False):
                debug('jyboss.ansible: process deployment')
                handler = DeploymentModule(jyboss)
                changes = handler.apply(**ansible.params)
                if changes is not None:
                    result['changed'] = True
                    result.setdefault('changes', {})['deployment'] = changes

            if ansible.params.get('reload', False):
                cmd('/:reload()')


        ansible.exit_json(**result)
    except Exception as err:
        result['msg'] = err.message
        # result['failure_details'] = err
        result['invocation'] = ansible.params
        ansible.fail_json(**result)


# if ctx.silent_streams is not None:
#     for line in ctx.silent_streams.out.lines:
#         info(line)
#
#     for line in ctx.silent_streams.err.lines:
#         info(line)


if __name__ == '__main__':
    main()
    sys.exit(0)

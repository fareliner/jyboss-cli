#! /usr/bin/env jython
import sys
from jyboss import *
from jyboss.core.ansible import AnsibleModule

from jyboss.core import *


def main():
    global ansible

    ansible = AnsibleModule(
        argument_spec=dict(
            jboss_home=dict(required=True),
            server_name=dict(default='default-server', type='str'),
            host_name=dict(default='default-host', type='str'),
            embedded=dict(default=False, type='bool'),
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

    ctx = JyBossCLI.instance()
    # set a jboss home if it is not passed in as either ENV variable or set as system property
    ctx.jboss_home = 'c:\\dev\\apps\\keycloak\\keycloak-1.9.8.Final'
    ctx.config_file = 'standalone-ha.xml'
    # ctx.noninteractive()

    with EmbeddedConnection():
        ls()


# if ctx.silent_streams is not None:
#     for line in ctx.silent_streams.out.lines:
#         info(line)
#
#     for line in ctx.silent_streams.err.lines:
#         info(line)

if __name__ == '__main__':
    main()
    sys.exit(0)

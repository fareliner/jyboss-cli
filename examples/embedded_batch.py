#! /usr/bin/env jython
from jyboss import *


def main():
    ctx = JyBossCLI.instance()
    # set a jboss home if it is not passed in as either ENV variable or set as system property
    ctx.jboss_home = 'c:\\dev\\apps\\keycloak\\keycloak-1.9.8.Final'
    ctx.config_file = 'standalone-ha.xml'

    ctx.noninteractive()
    EmbeddedConnection().connect()
    batch()
    batch_add_cmd('/subsystem=jgroups/stack=tcpping:add()')
    batch_add_cmd('/subsystem=jgroups/stack=tcpping/transport=TCP:add(type="TCP",socket-binding=jgroups-tcp)')
    batch_add_cmd('/subsystem=jgroups/stack=tcpping/protocol=TCPPING:add(type="TCPPING")')
    batch_add_cmd(
        '/subsystem=jgroups/stack=tcpping/protocol=TCPPING/property=initial_hosts/:add(value="localhost[7800]")')
    batch_add_cmd('/subsystem=jgroups/stack=tcpping/protocol=TCPPING/property=port_range/:add(value=0)')
    batch_add_cmd('/subsystem=jgroups/stack=tcpping/protocol=TCPPING/property=timeout/:add(value=3000)')
    batch_add_cmd('/subsystem=jgroups/stack=tcpping/protocol=TCPPING/property=num_initial_members/:add(value=1)')
    batch_add_cmd('/subsystem=jgroups/stack=tcpping/protocol=MERGE3:add(type="MERGE3")')
    batch_add_cmd('/subsystem=jgroups/stack=tcpping/protocol=FD_SOCK:add(type="FD_SOCK",socket-binding=jgroups-tcp-fd)')
    batch_add_cmd('/subsystem=jgroups/stack=tcpping/protocol=FD:add(type="FD")')
    batch_add_cmd('/subsystem=jgroups/stack=tcpping/protocol=VERIFY_SUSPECT:add(type="VERIFY_SUSPECT")')
    batch_add_cmd('/subsystem=jgroups/stack=tcpping/protocol=pbcast.NAKACK2:add(type="pbcast.NAKACK2")')
    batch_add_cmd('/subsystem=jgroups/stack=tcpping/protocol=UNICAST3:add(type="UNICAST3")')
    batch_add_cmd('/subsystem=jgroups/stack=tcpping/protocol=pbcast.STABLE:add(type="pbcast.STABLE")')
    batch_add_cmd('/subsystem=jgroups/stack=tcpping/protocol=pbcast.GMS:add(type="pbcast.GMS")')
    batch_add_cmd('/subsystem=jgroups/stack=tcpping/protocol=MFC:add(type="MFC")')
    batch_add_cmd('/subsystem=jgroups/stack=tcpping/protocol=FRAG2:add(type="FRAG2")')
    batch_add_cmd('/subsystem=jgroups/stack=tcpping/protocol=pbcast.STATE_TRANSFER:add(type="pbcast.STATE_TRANSFER")')
    batch_add_cmd('/subsystem=jgroups/stack=tcpping/protocol=pbcast.FLUSH:add(type="pbcast.FLUSH")')
    batch_result = batch_run()

    disconnect()


if __name__ == '__main__':
    main()

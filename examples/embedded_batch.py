#! /usr/bin/env jython
from jyboss import *
import simplejson as json


def main():
    # set a jboss home if it is not passed in as either ENV variable or set as system property
    jyboss.jboss_home = 'C:\\opt\\jboss\\wildfly-10.0.0.Final'
    jyboss.config_file = 'standalone.xml'
    jyboss.interactive = False

    jyboss.instance().jboss_home = 'C:\\opt\\jboss\\wildfly-10.0.0.Final'

    with embedded:
        cmd('/subsystem=jgroups/stack=tcpping:add()')
        batch.start()
        # batch.add_cmd('/subsystem=jgroups/stack=tcpping:add()')
        batch.add_cmd('/subsystem=jgroups/stack=tcpping/transport=TCP:add(type="TCP",socket-binding=jgroups-tcp)')
        batch.add_cmd('/subsystem=jgroups/stack=tcpping/protocol=TCPPING:add(type="TCPPING")')
        batch.add_cmd(
            '/subsystem=jgroups/stack=tcpping/protocol=TCPPING/property=initial_hosts/:add(value="localhost[7800]")')
        batch.add_cmd('/subsystem=jgroups/stack=tcpping/protocol=TCPPING/property=port_range/:add(value=0)')
        batch.add_cmd('/subsystem=jgroups/stack=tcpping/protocol=TCPPING/property=timeout/:add(value=3000)')
        batch.add_cmd('/subsystem=jgroups/stack=tcpping/protocol=TCPPING/property=num_initial_members/:add(value=1)')
        batch.add_cmd('/subsystem=jgroups/stack=tcpping/protocol=MERGE3:add(type="MERGE3")')
        batch.add_cmd('/subsystem=jgroups/stack=tcpping/protocol=FD_SOCK:add(type="FD_SOCK",socket-binding=jgroups-tcp-fd)')
        batch.add_cmd('/subsystem=jgroups/stack=tcpping/protocol=FD:add(type="FD")')
        batch.add_cmd('/subsystem=jgroups/stack=tcpping/protocol=VERIFY_SUSPECT:add(type="VERIFY_SUSPECT")')
        batch.add_cmd('/subsystem=jgroups/stack=tcpping/protocol=pbcast.NAKACK2:add(type="pbcast.NAKACK2")')
        batch.add_cmd('/subsystem=jgroups/stack=tcpping/protocol=UNICAST3:add(type="UNICAST3")')
        batch.add_cmd('/subsystem=jgroups/stack=tcpping/protocol=pbcast.STABLE:add(type="pbcast.STABLE")')
        batch.add_cmd('/subsystem=jgroups/stack=tcpping/protocol=pbcast.GMS:add(type="pbcast.GMS")')
        batch.add_cmd('/subsystem=jgroups/stack=tcpping/protocol=MFC:add(type="MFC")')
        batch.add_cmd('/subsystem=jgroups/stack=tcpping/protocol=FRAG2:add(type="FRAG2")')
        batch.add_cmd('/subsystem=jgroups/stack=tcpping/protocol=pbcast.STATE_TRANSFER:add(type="pbcast.STATE_TRANSFER")')
        batch.add_cmd('/subsystem=jgroups/stack=tcpping/protocol=pbcast.FLUSH:add(type="pbcast.FLUSH")')
        batch_result = batch.run()

        json.dumps(batch_result, indent=4)

if __name__ == '__main__':
    main()

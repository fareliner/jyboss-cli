#! /usr/bin/env jython
from jyboss import *

embedded.connect()
cd('/subsystem')
ls()

batch.start()
batch.add_cmd("ls")
# batch.add_cmd("if (outcome == success) /subsystem=modcluster:read-resource")
# batch.add_cmd("end-if")
batch.run()


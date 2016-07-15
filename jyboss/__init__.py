# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from jyboss.command import *
from jyboss.context import JyBossCLI, ServerConnection, EmbeddedConnection, EMBEDDED_MODE, CONNECTED_MODE

#
#
# Assemble a shell and wire the command handlers to the session
#
jyboss = JyBossCLI
connect = JyBossCLI.context().connect
disconnect = JyBossCLI.context().disconnect

_base = BasicCommandHandler()
_cmd = RawHandler()
_batch = BatchHandler()

# register command handler with session
JyBossCLI.context().register_handler(_base)
JyBossCLI.context().register_handler(_cmd)
JyBossCLI.context().register_handler(_batch)

# create shell alias
cd = _base.cd
ls = _base.ls
cmd = _cmd.cmd

batch = _batch.start
batch_reset = _batch.reset
batch_is_active = _batch.is_active
batch_add_cmd = _batch.add_cmd

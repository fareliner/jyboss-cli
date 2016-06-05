from .command import *
from .context import JyBossCLI, Connection, EMBEDDED_MODE, CONNECTED_MODE

#
#
# Assemble a shell and wire the command handlers to the session
#
jyboss = JyBossCLI
connect = JyBossCLI.context().connect
disconnect = JyBossCLI.context().disconnect

_base = BasicCommandHandler()
_cmd = RawHandler()

# register command handler with session
JyBossCLI.context().register_handler(_base)
JyBossCLI.context().register_handler(_cmd)

# create shell alias
cd = _base.cd
ls = _base.ls
cmd = _cmd.cmd

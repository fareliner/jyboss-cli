# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

from jyboss.context import JyBossCLI as _JyBossCLI
from jyboss.context import ServerConnection as _ServerConnection
from jyboss.context import EmbeddedConnection as _EmbeddedConnection

from jyboss.command.core import BasicCommandHandler as _BasicCommandHandler
from jyboss.command.core import RawHandler as _RawHandler
from jyboss.command.core import BatchHandler as _BatchHandler
from jyboss.command.undertow import UndertowCustomFilterModule as _UndertowCustomFilterModule

#
#
# Assemble a shell and wire the command handlers to the session
#

jyboss = _JyBossCLI.instance()
standalone = _ServerConnection(jyboss)
embedded = _EmbeddedConnection(jyboss)
# optional user will have to configure the jyboss context further, both connection
# classes will handle context as configuration holder

disconnect = jyboss.disconnect

# TODO refactor into a submodule but do not expose to module consumer
_base = _BasicCommandHandler()
_cmd = _RawHandler()
_batch = _BatchHandler()

undertow_filter = _UndertowCustomFilterModule()

# register command handler with session
jyboss.register_handler(_base)
jyboss.register_handler(_cmd)
jyboss.register_handler(_batch)
jyboss.register_handler(undertow_filter)

# create shell alias for core functions
cd = _base.cd
ls = _base.ls
cmd = _cmd.cmd

# create shell alias for batch mode
batch = _batch.start
batch_run = _batch.run
batch_reset = _batch.reset
batch_is_active = _batch.is_active
batch_add_cmd = _batch.add_cmd

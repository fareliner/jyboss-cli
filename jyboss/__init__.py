# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

from jyboss.context import JyBossContext, MODE_EMBEDDED, MODE_STANDALONE
from jyboss.context import ConnectionResource as _ConnectionResource
from jyboss.command import ls, cmd, cd, batch

#
# from jyboss.command import *

__metaclass__ = type

# make default context available to module user
jyboss = JyBossContext.instance()
standalone = _ConnectionResource(MODE_STANDALONE, jyboss)
embedded = _ConnectionResource(MODE_EMBEDDED, jyboss)
disconnect = jyboss.disconnect

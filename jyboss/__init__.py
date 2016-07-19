# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

from jyboss.context import JyBossCLI as _JyBossCLI
from jyboss.context import ServerConnection as _ServerConnection
from jyboss.context import EmbeddedConnection as _EmbeddedConnection

from jyboss.command import *

__metaclass__ = type

jyboss = _JyBossCLI.instance()
standalone = _ServerConnection(jyboss)
embedded = _EmbeddedConnection(jyboss)
disconnect = jyboss.disconnect

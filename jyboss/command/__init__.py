# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

from jyboss.context import JyBossCLI as _JyBossCLI

# care command handlers
from jyboss.command.core import escape_keys, unescape_keys, expression_deserializer
from jyboss.command.core import CommandHandler as _BasicCommandHandler
from jyboss.command.core import BatchHandler as _BatchHandler

# management specific handlers
from jyboss.command.undertow import UndertowCustomFilterModule as _UndertowCustomFilterModule
from jyboss.command.extension import ExtensionModule as _ExtensionModule
from jyboss.command.security import SecurityModule as _SecurityModule

__metaclass__ = type

try:
    # Python 2
    unicode
except NameError:
    # Python 3
    unicode = str

"""
This package contains command modules to configure jboss subsystems.
"""

_jyboss = _JyBossCLI.instance()

_base = _BasicCommandHandler()
_batch = _BatchHandler()

_jyboss.register_handler(_base)
_jyboss.register_handler(_batch)

# create shell alias for core functions
cd = _base.cd
ls = _base.ls
cmd = _base.cmd

# create shell alias for batch mode
batch = _batch.start
batch_run = _batch.run
batch_reset = _batch.reset
batch_is_active = _batch.is_active
batch_add_cmd = _batch.add_cmd

jyboss_undertow_filter = _UndertowCustomFilterModule()
_jyboss.register_handler(jyboss_undertow_filter)

jyboss_extension = _ExtensionModule()
_jyboss.register_handler(jyboss_extension)

jyboss_security = _SecurityModule()
_jyboss.register_handler(jyboss_security)
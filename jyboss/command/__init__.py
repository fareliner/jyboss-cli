# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

# care command handlers
from jyboss.command.core import escape_keys, unescape_keys, expression_deserializer
from jyboss.command.core import ReloadCommandHandler
from jyboss.command.core import ChangeObservable
from jyboss.command.core import CommandHandler as _BasicCommandHandler

# management specific handlers
from jyboss.command.undertow import UndertowModule
from jyboss.command.undertow import UndertowCustomFilterModule
from jyboss.command.undertow import UndertowSocketBindingModule
from jyboss.command.undertow import UndertowHttpListenerModule
from jyboss.command.undertow import UndertowAjpListenerModule
from jyboss.command.undertow import UndertowSocketBindingModule

from jyboss.command.extension import ExtensionModule
from jyboss.command.ee import EEModule
from jyboss.command.datasources import DatasourcesModule
from jyboss.command.module import ModuleModule
from jyboss.command.security import SecurityModule
from jyboss.command.keycloak import KeycloakModule
from jyboss.command.deployment import DeploymentModule
from jyboss.command.jgroups import JGroupsModule

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

_base = _BasicCommandHandler()
# create shell alias for core functions
cd = _base.cd
ls = _base.ls
cmd = _base.cmd

batch = _base

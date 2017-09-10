# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

# care command handlers
from .core import escape_keys, unescape_keys, expression_deserializer
from .core import ReloadCommandHandler, CliCmdHandler
from .core import ChangeObservable
from .core import CommandHandler as _BasicCommandHandler

# management specific handlers
from .undertow import UndertowModule
from .undertow import UndertowFilterRefModule
from .undertow import UndertowFilterModule
from .undertow import UndertowHttpListenerModule
from .undertow import UndertowAjpListenerModule

from .extension import ExtensionModule
from .ee import EEModule
from .datasources import DatasourcesModule
from .module import ModuleModule
from .security import SecurityModule
from .keycloak import KeycloakAdapterModule
from .keycloak import KeycloakServerModule
from .deployment import DeploymentModule
from .jgroups import JGroupsModule
from .infinispan import InfinispanModule
from .interface import InterfaceModule
from .binding import SocketBindingModule

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

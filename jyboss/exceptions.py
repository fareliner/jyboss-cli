# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

import sys

__metaclass__ = type


class ConnectionError(Exception):
    """ A connection problem was encountered.
    """

    def __init__(self, cause):
        self.traceback = sys.exc_info()
        self.cause = cause
        super(ConnectionError, self).__init__(cause.message)


class ContextError(Exception):
    """ A problem with a context command is encountered.
    """

    def __init__(self, message, cause=None):
        self.traceback = sys.exc_info()
        self.cause = cause
        super(ContextError, self).__init__(message)


class OperationError(Exception):
    """ A problem with a cli command is encountered.
    """
    pass


class NotFoundError(Exception):
    """ A problem with a cli command is encountered.
    """
    pass


class DuplicateResourceError(Exception):
    """ The resource to be created already exists.
    """
    pass


class ParameterError(Exception):
    """
    error when a wrong parameter was supplied to the module
    """
    pass


class ProcessingError(Exception):
    """
    error processing a module request
    """
    pass


class CommandError(Exception):
    def __init__(self, message, cause=None):
        self.traceback = sys.exc_info()
        self.cause = cause
        super(CommandError, self).__init__(message)

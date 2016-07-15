class ConnectionError(Exception):
    """ A connection problem was encountered.
    """
    pass


class ContextError(Exception):
    """ A problem with a context command is encountered.
    """
    pass


class OperationError(Exception):
    """ A problem with a cli command is encountered.
    """
    pass


class NotFoundError(Exception):
    """ A problem with a cli command is encountered.
    """
    pass

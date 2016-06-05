import time
import traceback
import collections
import os
from abc import ABCMeta, abstractmethod

from .exceptions import ContextError, ConnectionError
from .logging import debug, SyslogOutputStream

from java.lang import IllegalStateException, IllegalArgumentException, System, ClassLoader, Thread
from java.io import PrintStream, File
from java.net import URL, URLClassLoader
from jarray import array

EMBEDDED_MODE = "embedded"
CONNECTED_MODE = "connected"

streams = collections.namedtuple('streams', ['out', 'err'])


# helper functions
def normalize_dirpath(dirpath):
    return dirpath[:-1] if dirpath[-1] == '/' or dirpath[-1] == '\\' else dirpath


def retry(exceptions=None, tries=None):
    if exceptions:
        exceptions = tuple(exceptions)

    def wrapper(fun):
        def retry_calls(*args, **kwargs):
            if tries:
                for _ in xrange(tries):
                    try:
                        fun(*args, **kwargs)
                    except exceptions:
                        pass
                    else:
                        break
            else:
                while True:
                    try:
                        fun(*args, **kwargs)
                    except exceptions:
                        pass
                    else:
                        break

        return retry_calls

    return wrapper


class Connection(object):
    """
    a cli object that can interact with jyboss
    """

    def __init__(self, controller_host=None, controller_port=None, admin_username=None, admin_password=None,
                 mode=CONNECTED_MODE, context=None):
        if context is None:
            self.context = JyBossCLI.context()
        else:
            self.context = context
        self._controller_host = controller_host
        self._controller_port = controller_port
        self._admin_username = admin_username
        self._admin_password = admin_password
        self.mode = mode
        self.jcli = None
        self._resource_managed = False

    def __enter__(self):
        self.connect()
        self._resource_managed = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        self._resource_managed = False
        return False

    @retry([ConnectionError], 4)
    def connect(self):
        if self._resource_managed:
            raise ContextError("this resource is already connected")

        # try to load the CLI from classpath
        try:
            # @formatter:off
            from org.jboss.as.cli.scriptsupport import CLI
            # @formatter:on
        except ImportError:
            # try to check the os environment JBOSS_HOME
            # if context has jboss_home defined take this else look at
            if self.context.jboss_home is None:
                self.context.jboss_home = os.environ.get("JBOSS_HOME")
            self.context.configure_classpath()

            # TODO try to check the context has jboss_home set
            try:
                # @formatter:off
                from org.jboss.as.cli.scriptsupport import CLI
                # @formatter:on
            except ImportError:
                raise ContextError(
                    "jboss cli libraries are not on the classpath, either start jython with jboss-cli-client.jar on the classpath, set JBOSS_HOME environment variable or create a context with a specific jboss_home path")

        debug("Session.connect: try to connect, current cli: %s" % self.jcli)
        jcli = CLI.newInstance()
        try:
            if self._controller_host is None or self._controller_port is None or self._admin_username is None or self._admin_password is None:
                jcli.connect()
            else:
                jcli.connect(self._controller_host, self._controller_port, self._admin_username, self._admin_password)
            debug("connected to server")
        except IllegalStateException as e:
            if e.message.startswith('Already connected to server'):
                debug("already connected to server")
            else:
                debug("connecting to server failed, retry in 2 seconds: %s" % e.message)
                try:  # cleanup and try again
                    jcli.disconnect()
                except:
                    pass
                time.sleep(2)
                raise e

        self.jcli = jcli
        # also need to make sure the session is propagated to all command handler
        self.context.observer.publish(self)

    def disconnect(self):
        debug("Session.disconnect: try to disconnect cli state %s" % self.jcli)
        if self.jcli is not None:
            try:
                self.jcli.disconnect()
            except:
                pass
            finally:
                self.jcli = None
                self.context.observer.publish(self)


class ExactTypeEqualityMixIn:
    def __init__(self):
        pass

    def __eq__(self, other):
        return other is not None and other.__class__ == self.__class__

    def __ne__(self, other):
        return not self.__eq__(other)


class ConnectionEventHandler(object, ExactTypeEqualityMixIn):
    __metaclass__ = ABCMeta

    @abstractmethod
    def handle(self, connection):
        pass


class ConnectionEventObserver(object):
    def __init__(self):
        """

        :rtype: object
        """
        self._handlers = []

    def register_handler(self, handler):
        """ Register a handler that will get notified when the session in context changes.
        :param handler: the handler to be notified
        :return: True if the handler was appended or False if the handler to be appended was already present
        """
        if not any(x == handler for x in self._handlers):
            self._handlers.append(handler)
            return True
        else:
            return False

    def handlers(self):
        return self._handlers

    def unregister_handler(self, handler):
        self._handlers.remove(handler)

    def publish(self, connection):
        """ This function will call handler.handle(connection) on every registered handler.
        :param connection: the connection that has changed
        :return: nothing
        """
        debug("%s.publish: update connection context" % self.__class__.__name__)
        for handler in self._handlers:
            handler.handle(connection)


class JyBossCLI(object):
    _CONTEXT = None

    def __init__(self, jboss_home=None, session_observer=None, interactive=True):
        if session_observer is None:
            self.observer = ConnectionEventObserver()
        else:
            self.observer = session_observer
        # add myself to the list of handlers so I can get updates
        # on what connection is in progress
        self.observer.register_handler(self)
        self.connection = None
        self.jboss_home = jboss_home
        self.original_streams = streams(System.out, System.err)
        self.silent_streams = None
        self._set_interactive(interactive)
        # TODO save original streams before nuking them

    @staticmethod
    def context(jboss_home=None, session_observer=None, interactive=True):
        if JyBossCLI._CONTEXT is None:
            JyBossCLI._CONTEXT = JyBossCLI(jboss_home=jboss_home, session_observer=session_observer,
                                           interactive=interactive)
        return JyBossCLI._CONTEXT

    def noninteractive(self):
        self._set_interactive(False)

    def isinteractive(self):
        self._set_interactive(True)

    def _set_interactive(self, interactive):
        # deactivate all handlers
        if not interactive:
            debug("disable default JVM output streams")
            if self.silent_streams is None:
                self.silent_streams = streams(SyslogOutputStream(), SyslogOutputStream(SyslogOutputStream.ERR))
            System.out.flush()
            System.err.flush()
            System.setOut(PrintStream(self.silent_streams.out, True))
            System.setErr(PrintStream(self.silent_streams.err, True))
        else:
            debug("enable default JVM output streams")
            System.out.flush()
            System.err.flush()
            System.setOut(self.original_streams.out)
            System.setErr(self.original_streams.err)

        self.interactive = interactive

    def configure_classpath(self):
        """
        jboss CLI does something dodgy and can't just append the cli.jar to the system path
        sys.path.append(jboss_home + "/bin/client/jboss-cli-client.jar")
        instead we are going to add a URL classloader into the loader hirarchy of
        the current thread context
        """
        if self.jboss_home is None:
            raise ContextError("jboss_home must be provided to the module context")

        jboss_home = File(normalize_dirpath(self.jboss_home))
        if not jboss_home.isDirectory():
            raise ContextError("jboss_home %s is not a directory or does not exist" % jboss_home)
        else:
            jars = array([], URL)
            jars.append(File(jboss_home, "/bin/client/jboss-cli-client.jar").toURL())
            jars.append(File(jboss_home, "/jboss-modules.jar").toURL())
            current_thread_classloader = Thread.currentThread().getContextClassLoader()
            updated_classloader = URLClassLoader(jars, current_thread_classloader)
            Thread.currentThread().setContextClassLoader(updated_classloader)

    def is_connected(self):
        """ Check if a context is connected
        :return: True if a connection is available, False otherwise
        """
        return self.connection is not None and self.connection.jcli is not None

    def register_handler(self, handler):
        """ Convinent method to register a handler with the context.
        :param handler: the handler to be registered
        :return: see ConnectionEventHandler
        """
        handler.interactive = self.interactive
        return self.observer.register_handler(handler)

    def unregister_handler(self, handler):
        """ Convinent method to the removal of a handler registration with the context.
        :param handler: the handler to be unregistered
        :return: nothing
        """
        return self.observer.unregister_handler(handler)

    def handle(self, connection):
        """ Context itself is a connection context handler to manage its own view of connection.
        :param connection: the connection
        :return:
        """
        self.connection = connection

    @staticmethod
    def connect(controller_host=None, controller_port=None, admin_username=None, admin_password=None,
                mode=CONNECTED_MODE):
        context = JyBossCLI.context()
        if context.is_connected():
            raise ContextError("session already in progress")
        else:
            connection = Connection(controller_host, controller_port, admin_username, admin_password, mode, context)
            connection.connect()

    def disconnect(self):
        if self.is_connected():
            self.connection.disconnect()
        else:
            raise ContextError("session already in progress")

# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

import time
from functools import wraps
import collections
import os
from abc import ABCMeta, abstractmethod
from synchronize import make_synchronized

from jyboss.exceptions import ContextError, ConnectionError
from jyboss.logging import debug, warn, SyslogOutputStream

from java.lang import IllegalStateException, IllegalArgumentException, System, ClassLoader, Thread
from java.io import PrintStream, File
from java.net import URL, URLClassLoader
from jarray import array

streams = collections.namedtuple('streams', ['out', 'err'])


# helper functions
def normalize_dirpath(dirpath):
    return dirpath[:-1] if dirpath[-1] == '/' or dirpath[-1] == '\\' else dirpath


def retry(exceptions=None, tries=None, delay=2, backoff=2):
    if exceptions:
        exceptions = tuple(exceptions)

    def wrapper(fun):

        @wraps(fun)
        def retry_calls(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return fun(*args, **kwargs)
                except exceptions as e:
                    wrapped = ''
                    if len(args) > 0:
                        wrapped = args[0].__class__.__name__
                    if fun is not None and hasattr(fun, 'func_name'):
                        wrapped = ''.join([wrapped, '.', getattr(fun, 'func_name')])
                    warn('%s: %s, Retrying in %d seconds...' % (wrapped, str(e), mdelay))
                    time.sleep(mdelay)
                    mtries -= 1
                    if backoff > 0:
                        mdelay *= backoff
            return fun(*args, **kwargs)

        return retry_calls  # decorator

    return wrapper


class ExactTypeEqualityMixIn:
    def __init__(self):
        pass

    def __eq__(self, other):
        return other is not None and other.__class__ == self.__class__

    def __ne__(self, other):
        return not self.__eq__(other)


class Connection(object):
    """
    abstract connection to a jboss server
    """

    __metaclass__ = ABCMeta

    def __init__(self, context=None):
        if context is None:
            self.context = JyBossCLI.instance()
        else:
            self.context = context
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

    @abstractmethod
    def _connect(self, cli):
        """Method documentation"""
        return

    @abstractmethod
    def get_mode(self):
        """Method documentation"""
        return

    def connect(self):
        if self._resource_managed:
            raise ContextError('%s.connect: this resource is already connected' % self.__class__.__name__)

        if self.jcli is not None:
            if self.jcli.is_connected():
                raise ContextError('%s.connect: this resource is already connected' % self.__class__.__name__)
            else:
                jcli = self.jcli
        else:
            jcli = self.context.get_jcli_instance()

        debug("%s.connect: try to connect, current cli: %s" % (self.__class__.__name__, jcli))
        try:
            self._connect(jcli)
            debug("%s.connect: connected to server" % self.__class__.__name__)
        except Exception as e:
            if e.message.startswith('Already connected to server'):
                debug('%s.connect: already connected to server' % self.__class__.__name__)
            else:
                try:  # cleanup and try again
                    jcli.disconnect()
                except:
                    pass
                raise e

        self.jcli = jcli
        # also need to make sure the session is propagated to all command handler
        self.context.observer.publish(self)

    def disconnect(self):
        debug("Session.disconnect: try to disconnect %s cli state %s" % (self.get_mode(), self.jcli))
        if self.jcli is not None:
            try:
                self.jcli.disconnect()
            except Exception as e:
                warn('failed to disconnect from %s server: %s' % (self.__class__.__name__, e.message))
                pass
            finally:
                self.jcli = None
                self.context.observer.publish(None)


class EmbeddedConnection(Connection):
    """
    a cli object that can start an embedded jboss
    """

    def __init__(self, context=None):
        super(EmbeddedConnection, self).__init__(context=context)

    def _connect(self, cli):
        cli.embedded(self.context.get_jboss_home(), self.context.config_file)

    def get_mode(self):
        return 'embedded'


class ServerConnection(Connection):
    """
    a cli object that can interact with jboss server
    """

    def __init__(self, protocol=None, controller_host=None, controller_port=None, admin_username=None,
                 admin_password=None,
                 context=None):
        super(ServerConnection, self).__init__(context=context)
        self._protocol = protocol
        self._controller_host = controller_host
        self._controller_port = controller_port
        self._admin_username = admin_username
        self._admin_password = admin_password

    @retry([ConnectionError], tries=4, backoff=2)
    def _connect(self, cli):
        try:
            cli.connect(protocol=self._protocol,
                        controller_host=self._controller_host,
                        controller_port=self._controller_port,
                        username=self._admin_username,
                        password=self._admin_password)
            debug('%s.connect: connected to server' % self.__class__.__name__)
        except IllegalStateException as e:
            if e.message.startswith('Already connected to server'):
                debug('%s.connect: already connected to server' % self.__class__.__name__)
            else:
                try:  # cleanup and try again
                    cli.disconnect()
                except:
                    pass
                raise ConnectionError(e)

    def get_mode(self):
        return 'standalone'


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
    _INSTANCE = None

    def __init__(self, jboss_home=None, config_file=None, session_observer=None, interactive=True):
        if session_observer is None:
            self.observer = ConnectionEventObserver()
        else:
            self.observer = session_observer
        # add myself to the list of handlers so I can get updates
        # on what connection is in progress
        self.observer.register_handler(self)
        self.connection = None
        self.jboss_home = jboss_home
        self.config_file = config_file if config_file is not None else 'standalone.xml'
        self.original_streams = streams(System.out, System.err)
        self.silent_streams = None
        self._set_interactive(interactive)
        # TODO save original streams before nuking them

    @staticmethod
    def instance(jboss_home=None, config_file=None, session_observer=None, interactive=True):
        if JyBossCLI._INSTANCE is None:
            JyBossCLI._INSTANCE = JyBossCLI(jboss_home=jboss_home, config_file=config_file,
                                            session_observer=session_observer,
                                            interactive=interactive)
        return JyBossCLI._INSTANCE

    def get_jcli_instance(self):

        try:
            # @formatter:off
            from org.jboss.logmanager import LogManager as JBossLogManager
            from org.jboss.as.cli import CommandContextFactory
            from org.jboss.as.cli import CliInitializationException
            from org.jboss.as.cli import CommandLineException
            # @formatter:on
        except ImportError:
            self.configure_classpath()
            try:
                # @formatter:off
                from org.jboss.logmanager import LogManager as JBossLogManager
                from org.jboss.as.cli import CommandContextFactory
                from org.jboss.as.cli import CliInitializationException
                from org.jboss.as.cli import CommandLineException
                # @formatter:on
            except ImportError:
                raise ContextError(
                    "jboss cli libraries are not on the classpath, either start jython with jboss-cli-client.jar on the classpath, set JBOSS_HOME environment variable or create a context with a specific jboss_home path")

        # if the log manager is JUL we need to hack it as it has been initialised prior we got a change to do so,
        # embedded mode will fail if this is not setup properly
        from java.util.logging import LogManager as JulLogManager
        logManager = JulLogManager.getLogManager()
        if type(logManager) is JulLogManager:
            # need to hack the JUL LogManager
            from java.lang.reflect import Modifier
            field = logManager.__class__.getDeclaredField("manager")
            field.setAccessible(True)
            modifiersField = field.__class__.getDeclaredField("modifiers")
            modifiersField.setAccessible(True)
            modifiersField.setInt(field, field.getModifiers() & ~Modifier.FINAL)
            field.set(None, JBossLogManager())

        # now it's safe to load the cli
        from .cli import Cli
        return Cli()

    def is_interactive(self):
        return self.interactive

    def noninteractive(self):
        self._set_interactive(False)
        return self

    def interactive(self):
        self._set_interactive(True)
        return self

    @make_synchronized
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

        # also write through to the actual cli command context
        if self.connection is not None and self.connection.jcli is not None:
            self.connection.jcli.set_silent(not interactive)

        self.interactive = interactive

    def get_jboss_home(self):
        # first check if the jboss home was passed in as java property
        if self.jboss_home is None:
            self.jboss_home = System.getProperty('jboss.home.dir')

        # if still nothing, try to check the os environment JBOSS_HOME
        if self.jboss_home is None:
            self.jboss_home = os.environ.get("JBOSS_HOME")

        return self.jboss_home

    def configure_classpath(self):
        """
        jboss CLI does something dodgy and can't just append the cli.jar to the system path
        sys.path.append(jboss_home + "/bin/client/jboss-cli-client.jar")
        instead we are going to add a URL classloader into the loader hirarchy of
        the current thread context
        """
        jboss_home_str = self.get_jboss_home()
        if jboss_home_str is None:
            raise ContextError("jboss_home must be provided to the module context")

        jboss_home = File(normalize_dirpath(jboss_home_str))
        if not jboss_home.isDirectory():
            raise ContextError("jboss_home %s is not a directory or does not exist" % jboss_home_str)
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
        return self.connection is not None and self.connection.jcli is not None and self.connection.jcli.is_connected()

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

    # TODO should remove this from context
    @staticmethod
    def connect(controller_host=None, controller_port=None, admin_username=None, admin_password=None):
        context = JyBossCLI.instance()
        if context.is_connected():
            raise ContextError("session already in progress")
        else:
            connection = ServerConnection(controller_host=controller_host, controller_port=controller_port,
                                          admin_username=admin_username, admin_password=admin_password, context=context)
            connection.connect()

    def disconnect(self):
        if self.is_connected():
            self.connection.disconnect()
        else:
            raise ContextError("no session in progress")

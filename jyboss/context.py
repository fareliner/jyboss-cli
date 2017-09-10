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

try:
    from java.lang import IllegalStateException, IllegalArgumentException, System, ClassLoader, Thread
    from java.io import PrintStream, File
    from java.net import URL, URLClassLoader
    from jarray import array
except ImportError as jpe:
    raise ContextError('Java packages are not available, please run this module with jython.', jpe)

# Python2 & 3 way to get NoneType
NoneType = type(None)

__metaclass__ = type

MODE_EMBEDDED = 'embedded'

MODE_STANDALONE = 'standalone'

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


class ConfigurationChangeHandler(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def configuration_changed(self, change_event):
        pass


class ConnectionResource(object):
    def __init__(self, mode, context=None):
        if mode is None:
            ContextError('%s cannot be created without a connection mode' % self.__class__.__name__)

        self.mode = mode

        if context is None:
            self.context = JyBossContext.instance()
        else:
            self.context = context

        self.connection = None  # type: Connection

    def __enter__(self):

        if self.mode == MODE_EMBEDDED:
            self.connection = EmbeddedConnection(self.context)
        elif self.mode == MODE_STANDALONE:
            self.connection = ServerConnection(self.context)

        self.connection.connect()

        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        connection = self.connection
        connection.disconnect()
        return False

    def connect(self):
        self.__enter__()

    def disconnect(self):
        self.__exit__(None, None, None)


class Connection(ConfigurationChangeHandler):
    """
    abstract connection to a jboss server
    """
    __metaclass__ = ABCMeta

    def __init__(self, context=None):
        if context is None:
            self.context = JyBossContext.instance()
        else:
            self.context = context
        # need to register to receive change notifications from the context so we can detect if a connection is in progress
        self.context.register_change_handler(self)
        self.context.connection = self
        self.jcli = None

    @abstractmethod
    def _connect(self, cli):
        """Method documentation"""
        return

    @abstractmethod
    def get_mode(self):
        """Method documentation"""
        return

    def connect(self):

        # now we are interested in context change events
        self.context.register_change_handler(self)

        if self.jcli is None:
            jcli = self.context.create_cli()
        else:
            if self.jcli.is_connected():
                raise ContextError('%s.connect: this resource is already connected' % self.__class__.__name__)
            else:
                jcli = self.jcli

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
                self.context.unregister_change_handler(self)

    def configuration_changed(self, change):
        if 'interactive' in change and self.jcli is not None:
            debug('%s handled: %r' % (self.__class__.__name__, change))
            # TODO self.jcli.silent = change['interactive']['new_value']


class EmbeddedConnection(Connection):
    """
    a cli object that can start an embedded jboss
    """

    def __init__(self, context=None):
        super(EmbeddedConnection, self).__init__(context=context)

    def _connect(self, cli):
        config_file = self.context.config_file if self.context.config_file is not None else 'standalone.xml'

        cli.embedded(self.context.get_jboss_home(), config_file)

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


class ConfigurationChangeObserver(object):
    def __init__(self):
        self.test = None
        self._handlers = []

    def register(self, handler):
        """ Register a handler that will get notified when the configuration in context changes.
        :param handler: the handler to be notified
        :return: True if the handler was appended or False if the handler to be appended was already present
        """
        if not isinstance(handler, ConfigurationChangeHandler):
            raise ContextError('Cannot register handler of type %r' % type(handler))
        elif not any(x == handler for x in self._handlers):
            self._handlers.append(handler)
            return True
        else:
            return False

    def handlers(self):
        return self._handlers

    def unregister(self, handler):
        self._handlers.remove(handler)

    def publish(self, change):
        """ This function will call handler.handle(connection) on every registered handler.
        :param change: the change
        :return: nothing
        """
        debug('%s.publish: %r' % (self.__class__.__name__, change))
        for handler in self._handlers:
            handler.configuration_changed(change)


class JyBossContext(ConfigurationChangeHandler):
    """
    The JyBoss context which manages the bootstrapping of the cli and connection in flight
    """
    _DEFAULT_INSTANCE = None

    _CliType = None

    _EXCLUDE_FROM_OBSERVATION = [
        'change_observer',
        'original_streams',
        'silent_streams',
        '_jboss_home_classpath'
    ]

    def __init__(self, jboss_home=None, config_file=None, interactive=True):
        self.jboss_home = jboss_home
        self.config_file = config_file
        self.original_streams = streams(System.out, System.err)
        self.silent_streams = None
        self.interactive = interactive
        self.connection = None
        # TODO save original streams before nuking them
        self._jboss_home_classpath = None
        # add myself to the list of handlers so context can handle some of the updates to itself
        change_observer = ConfigurationChangeObserver()
        change_observer.register(self)
        self.change_observer = change_observer

    def __setattr__(self, name, value):
        """
        The context item will have a little magic so we can set properties and still be able to notify the change
        handlers to make adjustments should they need to.
        :param name: the name of the context parameter that is changed
        :param value: the value it is changed to
        :return:
        """
        if name not in self._EXCLUDE_FROM_OBSERVATION \
                and name in self.__dict__ \
                and hasattr(self, 'change_observer'):
            old_value = self.__dict__[name]
            if old_value != value:
                self.change_observer.publish({name: {'old_value': old_value, 'new_value': value}})

        super(JyBossContext, self).__setattr__(name, value)

    @staticmethod
    def instance():

        if JyBossContext._DEFAULT_INSTANCE is None:
            JyBossContext._DEFAULT_INSTANCE = JyBossContext()

        return JyBossContext._DEFAULT_INSTANCE

    def create_cli(self):
        # make sure we only ever load this once
        if JyBossContext._CliType is None:
            JyBossContext._CliType = self._load_cli()

        return JyBossContext._CliType()

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

        # FIXME boadcast configuration change to connection managers

        if self.connection is not None and self.connection.jcli is not None:
            self.connection.jcli.set_silent(not interactive)

    def get_jboss_home(self):

        jboss_home = self.jboss_home

        # first check if the jboss home was passed in as java property
        if jboss_home is None:
            jboss_home = System.getProperty('jboss.home.dir')

        # if still nothing, try to check the os environment JBOSS_HOME
        if jboss_home is None:
            jboss_home = os.environ.get("JBOSS_HOME")

        if jboss_home is None:
            raise ContextError("jboss_home must be provided to the module context")

        # preserver for later
        self.jboss_home = jboss_home

        return jboss_home

    def is_connected(self):
        """ Check if a context is connected
        :return: True if a connection is available, False otherwise
        """
        return self.connection is not None and self.connection.jcli is not None and self.connection.jcli.is_connected()

    def disconnect(self):
        if self.is_connected():
            self.connection.disconnect()
        else:
            raise ContextError("no session in progress")

    def _load_cli(self):
        try:
            # @formatter:off
            # noinspection PyUnresolvedReferences
            from org.jboss.logmanager import LogManager as JBossLogManager
            from org.jboss.as.cli import CommandContextFactory
            from org.jboss.as.cli import CliInitializationException
            from org.jboss.as.cli import CommandLineException
            # @formatter:on
        except ImportError:
            self._configure_classpath()
            try:
                # @formatter:off
                # noinspection PyUnresolvedReferences
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
        try:
            from java.util.logging import LogManager as JulLogManager
            from java.lang.reflect import Modifier
        except ImportError as jpe:
            raise ContextError('Java packages are not available, please run this module with jython.', jpe)

        logManager = JulLogManager.getLogManager()
        if type(logManager) is JulLogManager:
            # need to hack the JUL LogManager
            field = logManager.__class__.getDeclaredField("manager")
            field.setAccessible(True)
            modifiersField = field.__class__.getDeclaredField("modifiers")
            modifiersField.setAccessible(True)
            modifiersField.setInt(field, field.getModifiers() & ~Modifier.FINAL)
            field.set(None, JBossLogManager())

        # now it's safe to load the cli
        from .cli import Cli as _Cli
        return _Cli

    def _configure_classpath(self):
        """
        jboss CLI does something dodgy and can't just append the cli.jar to the system path
        sys.path.append(jboss_home + "/bin/client/jboss-cli-client.jar")
        instead we are going to add a URL classloader into the loader hierarchy of
        the current thread context
        """
        jboss_home_str = self.get_jboss_home()

        jboss_home = File(normalize_dirpath(jboss_home_str))
        if not jboss_home.isDirectory():
            raise ContextError("jboss_home %s is not a directory or does not exist" % jboss_home_str)

        jars = array([], URL)
        jars.append(File(jboss_home, "/bin/client/jboss-cli-client.jar").toURL())
        jars.append(File(jboss_home, "/jboss-modules.jar").toURL())
        current_thread_classloader = Thread.currentThread().getContextClassLoader()
        updated_classloader = URLClassLoader(jars, current_thread_classloader)
        Thread.currentThread().setContextClassLoader(updated_classloader)

        self._jboss_home_classpath = jboss_home_str

    def register_change_handler(self, handler):
        self.change_observer.register(handler)

    def unregister_change_handler(self, handler):
        self.change_observer.unregister(handler)

    def configuration_changed(self, change_event):
        if 'interactive' in change_event and 'new_value' in change_event['interactive']:
            self._set_interactive(bool(change_event['interactive']['new_value']))

# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

from jyboss.exceptions import ContextError, CommandError

try:
    from java.lang import System, IllegalStateException, IllegalArgumentException
    from java.io import IOException
    from java.net import URI, URISyntaxException
except ImportError as jpe:
    raise ContextError('Java packages are not available, please run this module with jython.', jpe)

try:
    # @formatter:off
    # noinspection PyUnresolvedReferences
    from org.jboss.as.cli import CliInitializationException, CommandContext, CommandContextFactory, CommandFormatException, CommandLineException
    from org.jboss.as.cli.impl import CommandContextConfiguration
    from org.jboss.dmr import ModelNode
    # @formatter:on
except ImportError as jbe:
    raise ContextError(
        'The jboss client library is not present on the python path. Please configure the context classpath (se jyboss documentation).',
        jbe)


class Cli(object):
    """
    a replacement for the jboss scripting cli, which does not support embedded mode and has a few
    other quirks including a private constructor
    """

    def __init__(self):
        self.ctx = None

    @staticmethod
    def instance():
        return Cli()

    def is_silent(self):
        return False if self.ctx is None else self.ctx.isSilent()

    def set_silent(self, flag=True):
        if self.ctx is not None:
            self.ctx.setSilent(flag)

    def is_connected(self):
        return False if self.ctx is None else not self.ctx.isTerminated()

    def check_already_connected(self):
        if self.ctx is not None:
            raise IllegalStateException("Already connected to server.")

    def check_not_connected(self):
        if self.ctx is None:
            raise IllegalStateException("Not connected to server.")
        if self.ctx.isTerminated():
            raise IllegalStateException("Session is terminated.")

    def get_command_context(self):
        return self.ctx

    @staticmethod
    def _construct_uri(protocol, host, port):
        try:
            uri = URI(protocol, None, host, port, None, None, None)
            return uri.toString().substring(2) if protocol is None else uri.toString()
        except URISyntaxException as e:
            raise IllegalStateException("Unable to construct URI.", e)

    def embedded(self, jboss_home, server_config=None):
        self.check_already_connected()
        try:
            self.ctx = CommandContextFactory.getInstance().newCommandContext()
            # TODO factor this out into the instantiation
            # apparently needed in the embedded cli for module loading
            System.setProperty("jboss.home.dir", jboss_home)
            # --std-out=echo
            self.ctx.handle(
                "embed-server --jboss-home=" + jboss_home + " --server-config=" + server_config)
        except CliInitializationException as e:
            raise IllegalStateException("Unable to initialize command context.", e)
        except CommandLineException as ce:
            raise IllegalStateException("Unable to connect to controller.", ce)

    def connect(self):
        self.check_already_connected()
        try:
            self.ctx = CommandContextFactory.getInstance().newCommandContext()
            self.ctx.connectController()
        except CliInitializationException as ie:
            raise IllegalStateException("Unable to initialize command context.", ie)
        except CommandLineException as ce:
            raise IllegalStateException("Unable to connect to controller.", ce)

    def connect(self, protocol=None, controller_host=None, controller_port=None, username=None, password=None,
                client_bind_address=None):
        self.check_already_connected()
        try:

            builder = CommandContextConfiguration.Builder()

            if controller_host is not None and controller_port is not None:
                builder.setController(self._construct_uri(protocol, controller_host, controller_port))

            if controller_port is not None:
                builder.setController(controller_port)

            if username is not None:
                builder.setUsername(username)

            if password is not None:
                builder.setPassword(password)

            if client_bind_address is not None:
                builder.setClientBindAddress(client_bind_address)

            self.ctx = CommandContextFactory.getInstance().newCommandContext(builder.build())
            self.ctx.connectController()

        except CliInitializationException as ie:
            raise IllegalStateException("Unable to initialize command context.", ie)
        except CommandLineException as ce:
            raise IllegalStateException("Unable to connect to controller.", ce)

    def disconnect(self):
        try:
            self.check_not_connected()
            self.ctx.terminateSession()
        finally:
            self.ctx = None

    def cmd(self, cli_command):
        self.check_not_connected()
        try:
            request = self.ctx.buildRequest(cli_command)
            response = self.ctx.getModelControllerClient().execute(request)
            return Result(cli_command, request=request, response=response)
        except CommandFormatException as cfe:
            try:
                self.ctx.handle(cli_command)
                return Result(cli_command, exit_code=self.ctx.getExitCode())
            except CommandLineException as cle:
                raise CommandError("Error handling command: %s" % cli_command, cle)
        except IOException as ioe:
            raise IllegalStateException("Unable to send command " + cli_command + " to server.", ioe)

    def batch_start(self):
        self.check_not_connected()
        try:
            bm = self.ctx.getBatchManager()
            if not bm.isBatchActive():
                bm.activateNewBatch()
        except Exception as e:
            raise IllegalStateException("Failed to start batch.", e)

    def batch_reset(self):
        self.check_not_connected()
        try:
            bm = self.ctx.getBatchManager()
            if bm.isBatchActive():
                bm.discardActiveBatch()

        except Exception as e:
            raise IllegalStateException("Failed to reset batch.", e)

    def batch_is_active(self):
        self.check_not_connected()
        try:
            bm = self.ctx.getBatchManager()
            return bm.isBatchActive()
        except Exception as e:
            raise IllegalStateException("Failed to test if batch is active.", e)

    def batch_add_cmd(self, batch_command):
        self.check_not_connected()
        try:
            cmd = self.ctx.toBatchedCommand(batch_command)
            bm = self.ctx.getBatchManager()

            batch = bm.getActiveBatch()
            batch.add(cmd)

        except Exception as e:
            raise IllegalStateException("Failed to add %s to batch command." % batch_command, e)


class Result(object):
    def __init__(self, cli_command=None, request=None, response=None, exit_code=None):
        self.cliCommand = cli_command
        self.request = request
        self.response = response
        if exit_code is None:
            self.is_success = response is not None and response.get("outcome").asString() == u'success'
            self.is_local_command = False
        else:
            self.is_success = True if exit_code == 0 else False
            self.is_local_command = True

    def getRequest(self):
        return self.request

    def getResponse(self):
        return self.response

    def isSuccess(self):
        return self.is_success

# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

import unittest
import os
import sys
import tempfile
import shutil
from functools import wraps
import yaml
import simplejson as json

from jyboss.context import ConnectionResource, JyBossContext, MODE_STANDALONE, MODE_EMBEDDED
from jyboss.exceptions import ParameterError

try:
    import ConfigParser as configparser
except ImportError:
    import configparser

try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path

__metaclass__ = type

# Unfortunately xmlunittest does not work with Jython so next best thing is to use XMLUnit.
# adding XMLUnit jars to the classpath so we don't have to muck about installing anything into
# the standard jython home or some weird classpath
test_lib_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
for list_file in os.listdir(test_lib_dir):
    if list_file.endswith(".jar"):
        extra_jar = os.path.join(test_lib_dir, list_file)
        sys.path.append(extra_jar)


def jboss_context(jboss_home=None, config_file=None, mode=MODE_EMBEDDED, interactive=True):
    """
    Test method annotation to configure the jyboss runtime context.
    :param jboss_home: The path to the JBOSS application server to use for the test execution
    :param config_file: The configuration file to copy to the sever home, if none supplied default/standalone.xml
           is used.
    :param mode: The context mode can be embedded, standalone or in future domain
    :param interactive: Flag if the test should be executed interactively logging data to the stdout/stderr.
    :return: Functional wrapper of the test function with a configured test context.
    """

    def wrapper(fun):

        @wraps(fun)
        def configure_test(*args, **kwargs):
            # set configuration context on the test base class
            if args is not None and len(args) > 0 and isinstance(args[0], JBossTest):
                test = args[0]
                # test the jboss home configuration following this precedence order
                # 1. jboss_home configured on the test itself
                # 2. jboss_home configured in the jboss-test.properties file in the tests folder
                # 3. TODO JBOSS_HOME environment environment variable set
                _jboss_home = jboss_home
                if _jboss_home is None:
                    # find a file in the root dir
                    _jboss_home = test.read_test_configuration('jboss.home')

                if _jboss_home is None:
                    raise Exception(
                        'No jboss_home defined. Please either supply a valid jboss server location to the setup or configure it in the jboss-test.properties file.')

                # determine which server configuration file to use for the test
                _config_file = 'standalone.xml' if config_file is None else config_file

                # lets look for the file in the test specific config location first then in the default location
                _server_config_path = Path(test.test_dir, 'configurations', test.__class__.__name__, _config_file)
                if not _server_config_path.is_file():
                    _server_config_path = Path(test.test_dir, 'configurations', 'default', _config_file)
                    if not _server_config_path.is_file():
                        raise Exception('Configuration file %s is missing in the tests directory.' % config_file)

                # create connection context
                test.context = JyBossContext.instance()

                test.context.jboss_home = _jboss_home
                # every test will use a separate configuration file so we can go back and inspect actions
                test.context.config_file = fun.__name__ + ".xml"
                test.context.interactive = interactive

                if mode in [MODE_EMBEDDED, MODE_STANDALONE]:
                    test.mode = mode
                    # copy / override the test config file
                    test.src_config_path = str(_server_config_path)
                    test.dst_config_path = str(
                        Path(_jboss_home, 'standalone', 'configuration', test.context.config_file))
                    shutil.copy2(test.src_config_path, test.dst_config_path)
                else:
                    raise NotImplemented('Testing in %s mode is not supported.' % mode)

                # add a connection object to the method
                test.connection = ConnectionResource(mode=mode, context=test.context)

            return fun(*args, **kwargs)

        return configure_test  # decorator

    return wrapper


class YamlLoaderMixIn(object):
    def __init__(self):
        self.test_dir = None
        self._testMethodName = None
        super(YamlLoaderMixIn, self).__init__()

    def load_yaml(self, yaml_file_path=None):
        """
        Load the YAML configuration that corresponds to the test method executed.

        :param yaml_file_path: The path of the yaml configuration file, if not defined, the loader will look for a file
                               /tests/configuration/<TextClassName>/<test_method_name>.yaml.

        :return: the content of the YAML file
        """
        if yaml_file_path is None and self._testMethodName is not None:
            yaml_file_path = os.path.join(self.test_dir, 'configurations', self.__class__.__name__,
                                          '%s.yml' % self._testMethodName)
        else:
            raise ParameterError('A valid YAML file path needs to be provided to the loader.')

        with open(yaml_file_path, 'r') as f:
            return yaml.load(f)

    def trans(self, yaml_file):
        src = os.path.join(self.test_dir, 'configurations', yaml_file)
        with open(src, 'r') as f:
            try:
                conf = yaml.load(f)
                new_file, _ = tempfile.mkstemp()
                json.dump(conf, new_file, indent=4)
                return new_file
            except yaml.YAMLError as exc:
                print(exc)


class ConfigurationReaderMixIn(object):
    def __init__(self):
        self.prop_file_name = None
        self.test_dir = None
        super(ConfigurationReaderMixIn, self).__init__()

    # noinspection PyBroadException
    def read_test_configuration(self, property_name):
        """
        A test can specify a properties file to use which is resolved in this function.

        :param property_name: the name of the property to read from the file

        :return: the configuration content of the property file
        """
        prop_file_name = self.prop_file_name if self.prop_file_name is not None else 'jboss-test.properties'
        conf_file = os.path.join(self.test_dir, prop_file_name)
        config = configparser.ConfigParser()
        try:
            config.read(conf_file)
        except:
            return None

        try:
            # FIXME get unit test name and check if there is a section
            return config.get('TODO', property_name)
        except (configparser.NoOptionError, configparser.NoSectionError):
            try:
                return config.get('default', property_name)
            except (configparser.NoOptionError, configparser.NoSectionError):
                return None


class JBossTest(unittest.TestCase, ConfigurationReaderMixIn, YamlLoaderMixIn):
    """
    A base test class that will provide support to run jboss integration tests.
    """

    # noinspection PyPep8Naming
    def __init__(self, methodName='runTest'):
        super(JBossTest, self).__init__(methodName)
        # defaults
        self.mode = None
        # type: JyBossContext
        self.context = None
        self.connection = None
        self.prop_file_name = None
        self.src_config_path = None
        self.dst_config_path = None
        self.config_dir = None
        self.test_dir = os.path.dirname(__file__)

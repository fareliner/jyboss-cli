# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

import unittest
import os
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

__metaclass__ = type


def jboss_context(jboss_home=None, config_file=None, mode=MODE_EMBEDDED, interactive=True):
    def wrapper(fun):

        @wraps(fun)
        def configure_test(*args, **kwargs):
            # set context
            if args is not None and len(args) > 0 and isinstance(args[0], JBossTest):
                test = args[0]
                # test the jboss home configuration
                _jboss_home = jboss_home
                if _jboss_home is None:
                    # find a file in the root dir
                    _jboss_home = test.read_test_configuration('jboss.home')

                if _jboss_home is None:
                    raise Exception(
                        'No jboss_home defined. Please either supply a valid jboss server location to the setup or configure it in the jboss-test.properties file.')

                # default the config file
                if config_file is None:
                    _config_dir = 'default'
                    _config_file = 'standalone.xml'
                else:
                    _config_dir = test.__class__.__name__
                    _config_file = config_file

                # create connection context
                test.context = JyBossContext.instance()

                test.context.jboss_home = _jboss_home
                test.context.config_file = _config_file
                test.context.interactive = interactive

                if mode in [MODE_EMBEDDED, MODE_STANDALONE]:
                    test.mode = mode
                    # copy / override the test config file
                    test.src_config_path = os.path.join(test.test_dir, 'configurations', _config_dir, _config_file)
                    test.dst_config_path = os.path.join(_jboss_home, 'standalone', 'configuration', _config_file)
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

from . import *

from jyboss import ls


class TestJBossTestParent(JBossTest):
    def setUp(self):
        print('run %s:%s' % (self.__class__.__name__, self._testMethodName))
        super(JBossTest, self).setUp()

    @jboss_context(config_file='config-test-01.xml', mode=MODE_EMBEDDED, interactive=False)
    def test_custom_server_configuration(self):
        with self.connection:
            data = ls('/subsystem')
            self.assertIsNotNone(data)
            self.assertTrue('datasources' in data)
            self.assertTrue('undertow' not in data)

    @jboss_context(mode=MODE_EMBEDDED, interactive=False)
    def test_default_server_configuration(self):
        with self.connection:
            data = ls('/subsystem')
            self.assertIsNotNone(data)
            self.assertTrue('datasources' in data)
            self.assertTrue('undertow' in data)

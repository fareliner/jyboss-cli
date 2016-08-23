import unittest
import re

from jyboss.command import escape_keys, unescape_keys


class TestExpressionDetection(unittest.TestCase):
    def setUp(self):
        self.expression_matcher = re.compile('^[\'\"]?(?:expression\s*[\'\"]?)?(\$\{.*\})[\'\"]*$')

    def test_unquoted_detect(self):
        m = self.expression_matcher.match('${jboss.standalone.cluster.port:7900}')
        self.assertIsNotNone(m)
        self.assertEqual(1, len(m.groups()))
        self.assertEqual('${jboss.standalone.cluster.port:7900}', m.group(1))

    def test_single_quote_detect(self):
        m = self.expression_matcher.match("'${jboss.standalone.cluster.port:7900}'")
        self.assertIsNotNone(m)
        self.assertEqual(1, len(m.groups()))
        self.assertEqual('${jboss.standalone.cluster.port:7900}', m.group(1))

    def test_double_quote_detect(self):
        m = self.expression_matcher.match('"${jboss.standalone.cluster.port:7900}"')
        self.assertIsNotNone(m)
        self.assertEqual(1, len(m.groups()))
        self.assertEqual('${jboss.standalone.cluster.port:7900}', m.group(1))

    def test_prefix_undoubled_detect(self):
        m = self.expression_matcher.match('expression "${jboss.standalone.cluster.port:7900}"')
        self.assertIsNotNone(m)
        self.assertEqual(1, len(m.groups()))
        self.assertEqual('${jboss.standalone.cluster.port:7900}', m.group(1))

    def test_prefix_double_quote_detect(self):
        m = self.expression_matcher.match('\"expression \'${jboss.standalone.cluster.port:7900}\'\"')
        self.assertIsNotNone(m)
        self.assertEqual(1, len(m.groups()))
        self.assertEqual('${jboss.standalone.cluster.port:7900}', m.group(1))

    def test_prefix_single_quote_detect(self):
        m = self.expression_matcher.match('\'expression "${jboss.standalone.cluster.port:7900}"\'')
        self.assertIsNotNone(m)
        self.assertEqual(1, len(m.groups()))
        self.assertEqual('${jboss.standalone.cluster.port:7900}', m.group(1))

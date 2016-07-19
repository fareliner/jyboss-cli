import unittest

from jyboss.command import escape_keys, unescape_keys


class TestUnescape(unittest.TestCase):
    def setUp(self):
        self.complex_data = {
            'sub1.test': {
                'sub2_test': {
                    'sub3.test': [
                        {
                            'sub4_test': {
                                'sub5.test': 'test.dont_touch'
                            }
                        }, ['test._me', 'me']
                    ]
                }

            }
        }

    def test_unescape_key_nested(self):
        result = unescape_keys(self.complex_data)
        self.assertIn('sub1.test', result)
        self.assertIn('sub2-test', result['sub1.test'])
        self.assertIn('sub3.test', result['sub1.test']['sub2-test'])
        self.assertIsInstance(result['sub1.test']['sub2-test']['sub3.test'][0], dict)
        self.assertIn('sub4-test', result['sub1.test']['sub2-test']['sub3.test'][0])
        self.assertIn('sub5.test', result['sub1.test']['sub2-test']['sub3.test'][0]['sub4-test'])
        self.assertEquals('test.dont_touch', result['sub1.test']['sub2-test']['sub3.test'][0]['sub4-test']['sub5.test'])

    def test_unescape_key_null(self):
        result = unescape_keys(None)
        self.assertIsNone(result)


class TestEscape(unittest.TestCase):
    def setUp(self):
        self.complex_data = {
            'sub1.test': {
                'sub2-test': {
                    'sub3.test': [
                        {
                            'sub4-test': {
                                'sub5.test': 'test.-dont_touch'
                            }
                        }, ['test.-me', 'me']
                    ]
                }

            }
        }

    def test_escape_key_nested(self):
        result = escape_keys(self.complex_data)
        self.assertIn('sub1.test', result)
        self.assertIn('sub2_test', result['sub1.test'])
        self.assertIn('sub3.test', result['sub1.test']['sub2_test'])
        self.assertIsInstance(result['sub1.test']['sub2_test']['sub3.test'][0], dict)
        self.assertIn('sub4_test', result['sub1.test']['sub2_test']['sub3.test'][0])
        self.assertIn('sub5.test', result['sub1.test']['sub2_test']['sub3.test'][0]['sub4_test'])
        self.assertEquals('test.-dont_touch',
                          result['sub1.test']['sub2_test']['sub3.test'][0]['sub4_test']['sub5.test'])

    def test_unescape_key_null(self):
        result = escape_keys(None)
        self.assertIsNone(result)

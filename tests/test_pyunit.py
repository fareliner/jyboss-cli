import unittest

import pytest


class TestContainer(object):

    def test_with_container(self):
        print("testing")

    def test_fail_container(self):
        print("testing")
        assert hasattr(self, 'connection')

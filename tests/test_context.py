import unittest

from jyboss.context import JyBossCLI, ConnectionEventHandler, ConnectionEventObserver


class TestContextHandler(ConnectionEventHandler):
    def __init__(self):
        self.connection = None

    def handle(self, connection):
        self.connection = connection


class TestConnection(object):
    pass


class TestContext(unittest.TestCase):
    def test_handler_added(self):
        observer = ConnectionEventObserver()
        self.assertIsNotNone(observer._handlers)
        self.assertEqual(len(observer._handlers), 0)
        observer.register_handler(TestContextHandler())
        self.assertEqual(len(observer._handlers), 1)

    def test_same_handler_added_twise(self):
        observer = ConnectionEventObserver()
        h1 = TestContextHandler()
        observer.register_handler(h1)
        self.assertEqual(len(observer._handlers), 1)
        h2 = TestContextHandler()
        observer.register_handler(h2)
        self.assertEqual(len(observer._handlers), 1)

    def test_remove_handler(self):
        observer = ConnectionEventObserver()
        h1 = TestContextHandler()
        observer.register_handler(h1)
        self.assertEqual(len(observer._handlers), 1)
        observer.unregister_handler(h1)
        self.assertEqual(len(observer._handlers), 0)

    def test_oontext_initilises(self):
        ctx = JyBossCLI()
        self.assertIsNotNone(ctx.observer)

    def test_handler_invoked(self):
        ctx = JyBossCLI()
        handler = TestContextHandler()
        ctx.observer.register_handler(handler)
        self.assertIsNone(handler.connection)
        ctx.observer.publish(TestConnection())
        self.assertIsNotNone(handler.connection)
        self.assertIsInstance(handler.connection, TestConnection)

    def test_context_has_session(self):
        ctx = JyBossCLI()
        self.assertIsNone(ctx.connection)
        ctx.observer.publish(TestConnection())
        self.assertIsNotNone(ctx.connection)
        self.assertIsInstance(ctx.connection, TestConnection)

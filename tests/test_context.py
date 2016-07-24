import unittest

from jyboss.context import JyBossContext, ConfigurationChangeHandler, ConfigurationChangeObserver


class TestContextHandler(ConfigurationChangeHandler):
    def __init__(self):
        self.changes = []

    def configuration_changed(self, change_event):
        self.changes.append(change_event)


class TestContext(unittest.TestCase):
    def test_handler_added(self):
        observer = ConfigurationChangeObserver()
        self.assertIsNotNone(observer._handlers)
        self.assertEqual(len(observer._handlers), 0)
        observer.register(TestContextHandler())
        self.assertEqual(len(observer._handlers), 1)

    def test_adding_multiple_handlers(self):
        observer = ConfigurationChangeObserver()
        h1 = TestContextHandler()
        observer.register(h1)
        self.assertEqual(len(observer._handlers), 1)
        h2 = TestContextHandler()
        observer.register(h2)
        self.assertEqual(len(observer._handlers), 2)

    def test_remove_handler(self):
        observer = ConfigurationChangeObserver()
        h1 = TestContextHandler()
        observer.register(h1)
        self.assertEqual(len(observer._handlers), 1)
        observer.unregister(h1)
        self.assertEqual(len(observer._handlers), 0)

    def test_oontext_initilises(self):
        ctx = JyBossContext()
        self.assertIsNotNone(ctx.change_observer)

    def test_handler_invoked(self):
        ctx = JyBossContext()
        handler = TestContextHandler()
        ctx.register_change_handler(handler)

        ctx.change_observer.publish('change1')
        self.assertEqual(1, len(handler.changes))
        self.assertEqual('change1', handler.changes[0])

    def test_context_jboss_home_change_published(self):
        ctx = JyBossContext()
        handler1 = TestContextHandler()
        ctx.register_change_handler(handler1)
        ctx.jboss_home = 'test_dir'
        self.assertEqual(1, len(handler1.changes))
        self.assertTrue('jboss_home' in handler1.changes[0])
        self.assertTrue('old_value' in handler1.changes[0]['jboss_home'])
        self.assertTrue('new_value' in handler1.changes[0]['jboss_home'])
        self.assertIsNone(handler1.changes[0]['jboss_home']['old_value'])
        self.assertEqual('test_dir', handler1.changes[0]['jboss_home']['new_value'])

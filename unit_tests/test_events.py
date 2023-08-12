import unittest

from events.event_dispatcher import EventDispatcher, Event


class TestEvents(unittest.IsolatedAsyncioTestCase):
    async def test_add_listener_before_event_creation(self):
        event_dispatcher = EventDispatcher()
        event_dispatcher.start()

        listener_one_responses = []

        def listener_one(event: Event):
            listener_one_responses.append("success")

        event_dispatcher.add_listener("test", listener_one)
        event_dispatcher.trigger(Event("test", "Test_Type"))

        await event_dispatcher.close()

        self.assertEqual(["success"], listener_one_responses)


if __name__ == '__main__':
    unittest.main()

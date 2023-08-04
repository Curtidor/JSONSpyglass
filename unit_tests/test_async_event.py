import asyncio
import unittest

from events.event_dispatcher import EventDispatcher, Event, Priority


class TestAsyncEvent(unittest.IsolatedAsyncioTestCase):
    async def test_busy_async_event(self):
        """
        Test the EventDispatcher's ability to handle busy async listeners.

        This test verifies that the EventDispatcher can correctly handle multiple asynchronous
        event listeners attached to the same event, even when some listeners are busy with time-consuming tasks.
        We simulate a busy listener using asyncio.sleep(1) and make sure that other listeners still get executed.
        """
        # Initialize empty lists to store results from event listeners
        listener_one_results = []
        listener_two_results = []

        async def listener_one():
            # Simulate some asynchronous work by waiting for 1 second
            await asyncio.sleep(1)
            listener_one_results.append("success")

        async def listener_two():
            listener_two_results.append("success")

        event_dispatcher = EventDispatcher()

        # Add both listeners to the same event ("test") in the EventDispatcher
        event_dispatcher.add_listener("test", listener_one)
        event_dispatcher.add_listener("test", listener_two)

        # Trigger the event twice asynchronously using async_trigger
        await asyncio.gather(
            event_dispatcher.async_trigger(Event("test", "test_type")),
            event_dispatcher.async_trigger(Event("test", "test_type"))
        )

        # Assert that listener_one has been called only once (due to the 1-second delay),
        # and listener_two has been called twice (once for each event trigger).
        self.assertEqual(listener_one_results, ["success"])
        self.assertEqual(listener_two_results, ["success", "success"])

    async def test_max_responders_and_priority(self):
        """
        Test the behavior of max_responders and listener priority.

        This test verifies that the EventDispatcher correctly handles the max_responders parameter and listener priorities.
        We define two asynchronous listeners, each appending a success message to their respective result lists.
        The first listener (listener_one) has a higher priority than the second listener (listener_two).
        We add both listeners to the same event ("test") in the EventDispatcher with a max_responders value of 1.
        """
        # Initialize empty lists to store results from event listeners
        listener_one_results = []
        listener_two_results = []

        # Define two asynchronous event listeners (listener_one and listener_two)
        async def listener_one():
            listener_one_results.append("success")

        async def listener_two():
            listener_two_results.append("success")

        # Create an instance of the EventDispatcher
        event_dispatcher = EventDispatcher()

        # Add both listeners to the same event ("test") in the EventDispatcher with specified priorities
        event_dispatcher.add_listener("test", listener_one, priority=Priority.HIGH)
        event_dispatcher.add_listener("test", listener_two, priority=Priority.NORMAL)

        # Trigger the event asynchronously with max_responders=1
        await event_dispatcher.async_trigger(Event("test", "test_type", max_responders=1))

        # Assert that only the highest priority listener (listener_one) has been called
        # and the second listener (listener_two) has not been executed due to max_responders=1
        self.assertEqual(listener_one_results, ["success"])
        self.assertEqual(listener_two_results, [])


if __name__ == "__main__":
    unittest.main()

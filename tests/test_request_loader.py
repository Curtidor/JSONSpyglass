import asyncio
import unittest

from typing import Any, Callable
from unittest.mock import patch, Mock, AsyncMock

from loaders.response_loader.response_loader import ResponseLoader
from models.requires import Requires


class TestRequestLoader(unittest.IsolatedAsyncioTestCase):

    @staticmethod
    def patch_playwright():
        def decorator(test_func):
            @patch('playwright.async_api.Page.goto', new_callable=AsyncMock)
            @patch('playwright.async_api.Page.content', new_callable=AsyncMock)
            @patch('scraping.page_manager.BrowserManager.get_page', new_callable=AsyncMock)
            def wrapper(mock_get_page, mock_content, mock_goto, *args, **kwargs):
                return test_func(mock_get_page, mock_content, mock_goto, *args, **kwargs)

            return wrapper

        return decorator

    @patch('httpx.AsyncClient.get')
    async def test_non_rendering_requests(self, mock_get):
        mock_response = Mock()
        mock_response.text = '<html>some_random_text</html>'
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        dispatcher = Mock()
        r_loader = ResponseLoader(dispatcher, None, render=False)

        urls = {f'https://example.com/{n}' for n in range(6)}
        results = await r_loader.load_responses(urls)

        for url, result in results.items():
            self.assertEqual(result.html, '<html>some_random_text</html>')
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.url, url)
            self.assertTrue(url.startswith('https'))

    @patch('httpx.AsyncClient.get')
    async def test_non_rendering_request(self, mock_get):
        mock_response = Mock()
        mock_response.text = '<html>some_random_text</html>'
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        dispatcher = Mock()
        r_loader = ResponseLoader(dispatcher, None, render=False)

        url = 'https://example.com'
        result = await r_loader.get_response(url)

        self.assertEqual(result.html, '<html>some_random_text</html>')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.url, url)
        self.assertTrue(url.startswith('https'))

    @patch_playwright()
    async def test_get_rendered_responses(self, mock_get_page, mock_content, mock_goto):  # noqa
        mock_page = AsyncMock()
        mock_get_page.return_value = mock_page

        mock_goto = AsyncMock()
        mock_content = AsyncMock()

        mock_goto.return_value = AsyncMock(status=200)
        mock_content.return_value = '<html></html>'

        mock_page.goto = mock_goto
        mock_page.content = mock_content

        mock_wait_for_page_states = AsyncMock()
        mock_wait_for_page_events = AsyncMock()
        mock_collect_clickable_null_hrefs = AsyncMock(return_value=[])

        with patch.object(ResponseLoader, '_wait_for_page_states', mock_wait_for_page_states), \
                patch.object(ResponseLoader, '_wait_for_page_events', mock_wait_for_page_events), \
                patch.object(ResponseLoader, '_collect_clickable_null_hrefs', mock_collect_clickable_null_hrefs):
            dispatcher = Mock()
            r_loader = ResponseLoader(dispatcher, None, render=True)

            urls = {f'https://example.com{n}' for n in range(6)}

            results = await r_loader.load_responses(urls)

            for url, result in results.items():
                mock_get_page.assert_called_once()
                mock_goto.assert_called_once_with(url, timeout=30 * 1000)
                mock_content.assert_called()
                self.assertEqual(result.html, '<html></html>')
                self.assertEqual(result.status_code, 200)

    @patch_playwright()
    async def test_get_rendered_response(self, mock_get_page, mock_content, mock_goto):  # noqa
        mock_page = AsyncMock()
        mock_get_page.return_value = mock_page

        mock_goto = AsyncMock()
        mock_content = AsyncMock()

        mock_goto.return_value = AsyncMock(status=200)
        mock_content.return_value = '<html></html>'

        mock_page.goto = mock_goto
        mock_page.content = mock_content

        # mock other methods called within get_rendered_response
        mock_wait_for_page_states = AsyncMock()
        mock_wait_for_page_events = AsyncMock()
        mock_collect_clickable_null_hrefs = AsyncMock(return_value=[])

        # replace the actual methods with mocks
        with patch.object(ResponseLoader, '_wait_for_page_states', mock_wait_for_page_states), \
                patch.object(ResponseLoader, '_wait_for_page_events', mock_wait_for_page_events), \
                patch.object(ResponseLoader, '_collect_clickable_null_hrefs', mock_collect_clickable_null_hrefs):
            dispatcher = Mock()
            r_loader = ResponseLoader(dispatcher, None)

            url = 'https://example.com'
            result = await r_loader.get_rendered_response(url)

            mock_get_page.assert_called_once()
            mock_goto.assert_called_once_with(url, timeout=30 * 1000)
            mock_content.assert_called()
            self.assertEqual(result.html, '<html></html>')
            self.assertEqual(result.status_code, 200)

    @patch_playwright()
    async def test_get_rendered_with_event(self, mock_get_page, mock_content, mock_goto):  # noqa

        event_count = 0

        def page_on(event: str, callback: Callable[..., Any]):  # noqa
            callback()
            nonlocal event_count
            event_count += 1

        mock_page = AsyncMock()
        mock_get_page.return_value = mock_page

        mock_goto.return_value = AsyncMock(status=200)
        mock_content.return_value = '<html></html>'

        mock_page.goto = mock_goto
        mock_page.content = mock_content
        mock_page.on = page_on

        mock_wait_for_page_states = AsyncMock()
        mock_collect_clickable_null_hrefs = AsyncMock(return_value=[])

        with patch.object(ResponseLoader, '_wait_for_page_states', mock_wait_for_page_states), \
                patch.object(ResponseLoader, '_collect_clickable_null_hrefs', mock_collect_clickable_null_hrefs):
            events = {'test_event', 'another_test_event'}
            dispatcher = Mock()

            r_loader = ResponseLoader(dispatcher, Requires(events=events))

            url = 'https://example.com'
            result = await r_loader.get_rendered_response(url)

            mock_get_page.assert_called_once()
            mock_goto.assert_called_once_with(url, timeout=30 * 1000)
            mock_content.assert_called()
            self.assertEqual(result.html, '<html></html>')
            self.assertEqual(result.status_code, 200)
            self.assertEqual(event_count, 2)

    @patch_playwright()
    async def test_get_rendered_with_states(self, mock_get_page, mock_content, mock_goto):  # noqa

        total_load_states = 0

        async def wait_for_load_state(state, timeout):  # noqa
            await asyncio.sleep(0.2)
            nonlocal total_load_states
            total_load_states += 1

        mock_page = AsyncMock()
        mock_get_page.return_value = mock_page

        mock_goto.return_value = AsyncMock(status=200)
        mock_content.return_value = '<html></html>'

        mock_page.goto = mock_goto
        mock_page.content = mock_content
        mock_page.wait_for_load_state = wait_for_load_state

        mock_wait_for_page_events = AsyncMock()
        mock_collect_clickable_null_hrefs = AsyncMock(return_value=[])

        with patch.object(ResponseLoader, '_wait_for_page_events', mock_wait_for_page_events), \
                patch.object(ResponseLoader, '_collect_clickable_null_hrefs', mock_collect_clickable_null_hrefs):
            dispatcher = Mock()

            r_loader = ResponseLoader(dispatcher, Requires(states={"domcontentloaded", "load", "networkidle"}))

            url = 'https://example.com'
            result = await r_loader.get_rendered_response(url)

            mock_get_page.assert_called_once()
            mock_goto.assert_called_once_with(url, timeout=30 * 1000)
            mock_content.assert_called()
            self.assertEqual(result.html, '<html></html>')
            self.assertEqual(result.status_code, 200)
            self.assertEqual(total_load_states, 3)


if __name__ == '__main__':
    unittest.main()

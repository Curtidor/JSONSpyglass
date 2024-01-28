import asyncio
import unittest

from playwright.async_api import async_playwright


class Request(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.p = await async_playwright().start()
        self.browser = await self.p.chromium.launch(headless=True)

    async def asyncTearDown(self) -> None:
        await self.browser.close()
        await self.p.stop()

    async def test_listen_request_page_non_ajax(self):
        page = await self.browser.new_page()

        await page.goto('https://www.google.com/')
        event = asyncio.Event()

        async def callback():
            event.set()

        page.on('requestfinished', callback)

        had_timeout = False
        try:
            await asyncio.wait_for(event.wait(), 15)
        except asyncio.TimeoutError:
            had_timeout = True

        page.remove_listener('requestfinished', callback)

        await page.close()
        self.assertFalse(had_timeout)

    async def test_listen_request_page_ajax(self):
        page = await self.browser.new_page()
        await page.goto('https://www.scrapethissite.com/pages/ajax-javascript/#2014')

        had_timeout = False
        try:
            await asyncio.wait_for(page.wait_for_load_state('networkidle'), 15)
        except asyncio.TimeoutError:
            had_timeout = True

        html = await page.content()
        print(html)
        await page.close()

        self.assertFalse(had_timeout)


if __name__ == '__main__':
    unittest.main()

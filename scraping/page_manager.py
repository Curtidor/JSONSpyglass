from asyncio import Queue, Lock
from typing import Set
from playwright.async_api import Browser, async_playwright, Page


class PagePool:
    _pool: Queue = Queue()
    _max_size = 5  # Set a reasonable maximum pool size
    _lock = Lock()

    @classmethod
    def get_pool(cls) -> Queue:
        return cls._pool

    @classmethod
    def t_active_pages(cls) -> int:
        return cls._pool.qsize()

    @classmethod
    async def populate_pool(cls, total_items) -> None:
        async with cls._lock:
            # Ensure we don't exceed the maximum pool size
            total_items = min(total_items, cls._max_size)

            for _ in range(total_items):
                page = await BrowserManager.create_new_page()
                cls._pool.put_nowait(page)

    @classmethod
    async def get_page(cls) -> Page:
        async with cls._lock:
            # if not cls._pool.empty():
            return await cls._pool.get()

    # return await BrowserManager.create_new_page()

    @classmethod
    async def put_page_back(cls, page: Page) -> bool:
        """
        Put a page back into the pool for reuse or close it if the pool is full.

        Args:
            page (Page): The Page object to put back into the pool or close.

        Returns:
            bool: `True` if the page was put back into the pool, `False` if pool is full and was not put back.

        Example usage:
            To put a page back into the pool:
            ```
            if await ResponseLoader.put_page_back(page_to_put_back):
                print("Page was put back into the pool.")
            else:
                print("Page was not put back due to the pool being full.")
            ```

        """
        async with cls._lock:
            if page is None:
                return False

            # Check if the pool is full
            if cls.is_full():
                return False

            # Prepare the page for reuse
            await page.context.clear_cookies()
            await page.context.clear_permissions()

            await cls._pool.put(page)

            return True

    @classmethod
    def set_pool_size(cls, pool_size: int) -> None:
        cls._max_size = pool_size

    @classmethod
    def is_full(cls) -> bool:
        return cls._pool.qsize() >= cls._max_size


class BrowserManager:
    _browser: Browser = None
    _all_pages: Set[Page] = set()
    _lock: Lock = Lock()

    @classmethod
    async def initialize(cls, is_rendering: bool = False):
        if cls._browser is None and is_rendering:
            cls._browser = await cls.get_browser()
            await PagePool.populate_pool(5)

    @classmethod
    def remove_from_active_pages(cls, page: Page) -> None:
        if page in cls._all_pages:
            cls._all_pages.remove(page)

    @classmethod
    async def create_new_page(cls) -> Page:
        browser = await cls.get_browser()
        page = await browser.new_page()

        cls._all_pages.add(page)
        return page

    @classmethod
    async def clean_up_pages(cls):
        pages_in_pool = set()
        pool = PagePool.get_pool()

        # Collect pages currently in the pool
        while not pool.empty():
            pages_in_pool.add(pool.get_nowait())

        for page in cls._all_pages:
            if page not in pages_in_pool:
                # Close pages that are not in the pool
                await page.close()
            else:
                # Return pages to the pool
                pool.put_nowait(page)

    @classmethod
    async def get_browser(cls, headless: bool = False) -> Browser:
        if cls._browser is None:
            p = await async_playwright().start()
            cls._browser = await p.chromium.launch(headless=headless)
        return cls._browser

    @classmethod
    async def close(cls):
        for page in cls._all_pages:
            await page.close()
        cls._all_pages.clear()

        if cls._browser:
            await cls._browser.close()

    @classmethod
    async def close_page(cls, page: Page, feed_into_pool: bool = False) -> None:
        """
        Close a page or return it to the pool based on the `feed_into_pool` parameter.

        Args:
            page (Page): The Page object to close or return to the pool.
            feed_into_pool (bool): If `True`, the page will be returned to the pool if possible.
                                   If `False`, the page will be closed.

        Returns:
            None

       Note:
            If `feed_into_pool` is `True` and the page is successfully returned to the pool,
            it will **not** be removed from the active pages set.

            If `feed_into_pool` is `True` and the page cannot be put back in the pool,
            it will be removed from the active pages set and closed.

            If `feed_into_pool` is `False`, the page will always be closed and removed from the active pages set.


        Example usage:
            To close a page:
            ```
            await ResponseLoader.close_page(page_to_close)
            ```

            To return a page to the pool:
            ```
            await ResponseLoader.close_page(page_to_return, feed_into_pool=True)
            ```

            To close a page without returning it to the pool:
            ```
            await ResponseLoader.close_page(page_to_close, feed_into_pool=False)
            ```

        """
        async with cls._lock:
            if feed_into_pool and not PagePool.is_full():
                if await PagePool.put_page_back(page):
                    print("RETURN SUCCESS:", page)
                    cls.remove_from_active_pages(page)
            elif not feed_into_pool:
                print("CLOSING PAGE:", page)
                cls.remove_from_active_pages(page)
                await page.close()
            elif PagePool.is_full():
                print("FULL POOL")
                cls.remove_from_active_pages(page)
                await page.close()

    @staticmethod
    async def get_page() -> Page:
        return await PagePool.get_page()

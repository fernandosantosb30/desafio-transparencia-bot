from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


class BrowserPool:
    """Limits the number of concurrent Playwright browser jobs."""

    def __init__(self, max_concurrency: int = 5):
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be positive")
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def run(self, task_factory: Callable[[], Awaitable[T]]) -> T:
        async with self._semaphore:
            return await task_factory()

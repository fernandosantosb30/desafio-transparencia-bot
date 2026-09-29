import asyncio

import pytest

from app.core.config import Settings, settings
from app.services.browser_pool import BrowserPool
from app.services.scraper import TransparenciaScraper
from app.utils.errors import SearchTimeoutError


async def test_concurrency_limit_and_release_after_error():
    pool = BrowserPool(2)
    active = peak = 0

    async def job():
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        try:
            await asyncio.sleep(0.02)
        finally:
            active -= 1

    await asyncio.gather(*(pool.run(job) for _ in range(6)))
    assert peak == 2

    async def fail():
        raise RuntimeError("test")

    with pytest.raises(RuntimeError):
        await pool.run(fail)
    await asyncio.wait_for(pool.run(job), 1)


async def test_total_deadline_includes_queue(monkeypatch):
    pool = BrowserPool(1)
    entered = asyncio.Event()

    async def hold():
        entered.set()
        await asyncio.Event().wait()

    task = asyncio.create_task(pool.run(hold))
    await entered.wait()
    monkeypatch.setattr(settings, "REQUEST_TIMEOUT_SECONDS", 0.05)
    try:
        with pytest.raises(SearchTimeoutError):
            await TransparenciaScraper(pool).consultar("Maria")
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


def test_invalid_capacity():
    with pytest.raises(ValueError):
        BrowserPool(0)
    with pytest.raises(ValueError):
        Settings(MAX_CONCURRENT_REQUESTS=0)

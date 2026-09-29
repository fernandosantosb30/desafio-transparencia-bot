from __future__ import annotations

import base64
from typing import Any


async def page_to_base64(page: Any) -> str:
    screenshot = await page.screenshot(full_page=True)
    return base64.b64encode(screenshot).decode("utf-8")

import asyncio
import random
from playwright.async_api import Page

from config import MIN_DELAY, MAX_DELAY


async def human_delay(min_s: float = MIN_DELAY, max_s: float = MAX_DELAY):
    await asyncio.sleep(random.uniform(min_s, max_s))


async def human_mouse_move(page: Page, x: int, y: int):
    steps = random.randint(10, 20)
    start_x = random.randint(100, 900)
    start_y = random.randint(100, 600)
    for i in range(steps + 1):
        t = i / steps
        cx = random.randint(min(start_x, x), max(start_x, x))
        cy = random.randint(min(start_y, y), max(start_y, y))
        bx = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * cx + t ** 2 * x
        by = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * cy + t ** 2 * y
        await page.mouse.move(bx, by)
        await asyncio.sleep(random.uniform(0.01, 0.02))


async def reading_delay(text: str):
    """Wait proportional to message length - simulates reading."""
    chars = len(text)
    base = chars / random.uniform(180, 280)
    thinking = random.uniform(1.0, 3.5)
    await asyncio.sleep(base + thinking)


async def human_scroll(page: Page):
    scroll_up = random.randint(200, 500)
    await page.mouse.wheel(0, -scroll_up)
    await human_delay(0.5, 1.2)
    await page.mouse.wheel(0, scroll_up)
    await human_delay(0.3, 0.8)


async def js_click(page: Page, selector: str, timeout: int = 5000) -> bool:
    """Click element via JavaScript - avoids visibility issues."""
    try:
        el = await page.wait_for_selector(selector, timeout=timeout)
        if el:
            await page.evaluate("el => el.click()", el)
            return True
    except Exception:
        pass
    return False


async def type_into(page: Page, selector: str, text: str):
    """Focus element and type character by character."""
    el = await page.query_selector(selector)
    if el:
        await page.evaluate("el => el.click()", el)
        await asyncio.sleep(0.2)
        for char in text:
            await page.keyboard.type(char)
            await asyncio.sleep(random.uniform(0.04, 0.12))


# JavaScript snippet used to detect outgoing messages by background color
OUTGOING_COLOR_JS = """el => {
    let node = el;
    for (let i = 0; i < 10; i++) {
        node = node.parentElement;
        if (!node) break;
        if (node.getAttribute && node.getAttribute('role') === 'presentation') {
            const bg = window.getComputedStyle(node).backgroundColor;
            if (!bg || bg === 'transparent' || bg === 'rgba(0, 0, 0, 0)') continue;
            const parts = bg.replace("rgba(","").replace("rgb(","").replace(")","").split(",");
            if (parts && parts.length >= 3) {
                const r = parseInt(parts[0]);
                const g = parseInt(parts[1]);
                const b = parseInt(parts[2]);
                const isGrey = Math.abs(r - 240) < 15 && Math.abs(g - 240) < 15 && Math.abs(b - 240) < 15;
                return !isGrey;
            }
        }
    }
    return false;
}"""

from playwright.async_api import Page
from browser.actions import js_click, human_delay
from logger import log


async def accept_cookies(page: Page):
    for selector in [
        '[aria-label="Allow all cookies"]',
        'button:has-text("Allow all cookies")',
        'button:has-text("Accept all")',
        'button:has-text("Accept")',
        'button[data-cookiebanner="accept_button"]',
        '[data-testid="cookie-policy-manage-dialog-accept-button"]',
    ]:
        if await js_click(page, selector, timeout=3000):
            await human_delay(0.8, 1.5)
            log.info("[BROWSER] Cookies acceptate.")
            return


async def dismiss_popups(page: Page):
    """Dismiss notifications, save login, and other blocking popups."""
    for selector in [
        'button:has-text("Not Now")',
        'button:has-text("Not now")',
        'button:has-text("Maybe Later")',
        'button._a9--._ap36._a9_1',
        '[aria-label="Close"]',
    ]:
        await js_click(page, selector, timeout=2000)


async def dismiss_ig_connect_prompt(page: Page):
    """Dismiss Instagram Connect/Log in prompt."""
    for selector in [
        '[aria-label="Log in"]',
        '[aria-label="Connect"]',
        'button:has-text("Log in")',
    ]:
        if await js_click(page, selector, timeout=3000):
            await human_delay(0.8, 1.5)
            log.info("[IG] Prompt Connect inchis.")
            return


async def handle_fb_pin(page: Page):
    """Handle Facebook e2ee PIN prompt - PIN is 123456."""
    try:
        pin_input = await page.wait_for_selector('[aria-label="PIN"]', timeout=5000)
        if pin_input:
            log.info("[FB] PIN prompt detectat, introduc PIN-ul...")
            await page.evaluate("el => { el.focus(); el.click(); }", pin_input)
            await page.keyboard.type("123456")
            await page.keyboard.press("Enter")
            from browser.actions import human_delay as hd
            await hd(0.8, 1.5)
            log.info("[FB] PIN introdus.")
    except Exception:
        pass
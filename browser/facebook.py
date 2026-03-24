import asyncio
import random
import urllib.parse
from playwright.async_api import Page, BrowserContext

from config import FB_EMAIL, FB_PASSWORD, BROWSER_TIMEOUT, CONTEXT_MESSAGE_LIMIT
from browser.actions import human_delay, human_mouse_move, human_scroll, reading_delay, js_click, type_into, OUTGOING_COLOR_JS
from browser.popups import accept_cookies, dismiss_popups, handle_fb_pin
from logger import log

FB_SESSION_PATH = "session_fb.json"


def is_fb_login_page(url: str) -> bool:
    return (
        "facebook.com/login" in url
        or "facebook.com/?next=" in url
        or ("facebook.com" in url and "login" in url)
    )


async def is_fb_login_shown(page: Page) -> bool:
    """Detect Facebook login form even when URL does not change."""
    if is_fb_login_page(page.url):
        return True
    for selector in [
        'div:has-text("You must log in to continue")',
        'div:has-text("Log Into Facebook")',
        '#loginbutton',
        'input[name="email"]',
    ]:
        try:
            el = await page.query_selector(selector)
            if el:
                return True
        except Exception:
            pass
    return False


async def do_facebook_login(page: Page):
    log.info("[FB] Navighez la pagina de login...")
    await page.goto("https://www.facebook.com/login.php")
    await page.wait_for_load_state("domcontentloaded")
    await human_delay(1.5, 2.5)

    if await js_click(page, '[aria-label="Use another profile"]', timeout=4000):
        log.info("[FB] Use another profile apasat.")
        await page.wait_for_load_state("domcontentloaded")
        await human_delay(1, 1.5)

    log.info("[FB] Astept campul de email...")
    await page.wait_for_selector('input[name="email"]', timeout=15000)
    await human_delay(0.5, 1)

    await accept_cookies(page)
    await human_delay(0.5, 1)

    log.info("[FB] Completez credentiale...")
    await page.focus('input[type="text"][name="email"]')
    await asyncio.sleep(0.3)
    for char in FB_EMAIL:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.04, 0.12))
    await human_delay(0.4, 0.8)

    await page.focus('input[type="password"][name="pass"]')
    await asyncio.sleep(0.3)
    for char in FB_PASSWORD:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.04, 0.12))
    await human_delay(0.4, 0.8)

    log.info("[FB] Apas login...")
    if not await js_click(page, '#loginbutton', timeout=5000):
        if not await js_click(page, '[name="login"]', timeout=3000):
            await page.keyboard.press("Enter")

    await page.wait_for_load_state("domcontentloaded")
    await human_delay(1.5, 3)
    log.info(f"[FB] Login realizat. URL: {page.url}")


class FacebookBrowser:
    def __init__(self, context: BrowserContext):
        self.context = context

    async def ensure_logged_in(self, page: Page):
        await human_delay(0.8, 1.5)
        log.info(f"[FB] URL curent: {page.url}")
        if await is_fb_login_shown(page):
            log.info("[FB] Login necesar, reautentificare...")
            await do_facebook_login(page)
            await self.context.storage_state(path=FB_SESSION_PATH)
            log.info("[FB] Sesiune re-salvata.")
        else:
            log.info("[FB] Sesiune valida.")
            await dismiss_popups(page)

    async def get_conversation(self, profile_id: str) -> list[dict]:
        page = await self.context.new_page()
        page.set_default_timeout(BROWSER_TIMEOUT)

        url_e2ee = f"https://www.facebook.com/messages/e2ee/t/{profile_id}"
        url_regular = f"https://www.facebook.com/messages/t/{profile_id}"

        log.info(f"[FB] Deschid conversatia {profile_id}...")
        await page.goto(url_e2ee)
        await page.wait_for_load_state("domcontentloaded")
        await human_delay(1.5, 2.5)

        await self.ensure_logged_in(page)

        if "facebook.com/messages" not in page.url:
            log.info("[FB] Incerc URL regular...")
            await page.goto(url_regular)
            await page.wait_for_load_state("domcontentloaded")
            await human_delay(1.5, 2)

        log.info(f"[FB] URL conversatie: {page.url}")

        await handle_fb_pin(page)
        await dismiss_popups(page)
        await human_delay(0.8, 1.5)
        await human_scroll(page)

        messages = []
        try:
            all_bubbles = await page.query_selector_all('div[role="presentation"] span[dir="auto"]')

            filtered = []
            for b in all_bubbles:
                in_date_break = await b.evaluate("""el => {
                    let node = el;
                    while (node) {
                        const scope = node.getAttribute && node.getAttribute('data-scope');
                        const hidden = node.getAttribute && node.getAttribute('aria-hidden');
                        if (scope === 'date_break' || hidden === 'true') return true;
                        node = node.parentElement;
                    }
                    return false;
                }""")
                if not in_date_break:
                    filtered.append(b)

            for bubble in filtered[-CONTEXT_MESSAGE_LIMIT:]:
                text = (await bubble.inner_text()).strip()
                if not text:
                    continue
                is_outgoing = await bubble.evaluate(OUTGOING_COLOR_JS)
                role = "CHATBOT" if is_outgoing else "USER"
                messages.append({"role": role, "message": text})

            log.info(f"[FB] {len(messages)} mesaje extrase.")
        except Exception as e:
            log.error(f"[FB] Eroare la extragere mesaje: {e}")

        await page.close()
        return messages

    async def send_message(self, profile_id: str, text: str, last_incoming: str = ""):
        page = await self.context.new_page()
        page.set_default_timeout(BROWSER_TIMEOUT)

        url_e2ee = f"https://www.facebook.com/messages/e2ee/t/{profile_id}"
        url_regular = f"https://www.facebook.com/messages/t/{profile_id}"

        log.info(f"[FB] Deschid conversatia pentru trimitere {profile_id}...")
        await page.goto(url_e2ee)
        await page.wait_for_load_state("domcontentloaded")
        await human_delay(1.5, 2.5)

        await self.ensure_logged_in(page)

        if "facebook.com/messages" not in page.url:
            await page.goto(url_regular)
            await page.wait_for_load_state("domcontentloaded")
            await human_delay(1.5, 2)

        await handle_fb_pin(page)
        await dismiss_popups(page)
        await human_delay(0.8, 1.2)

        if last_incoming:
            await reading_delay(last_incoming)
        else:
            await human_delay(1.5, 3)

        try:
            input_box = await page.wait_for_selector(
                '[aria-placeholder="Aa"], [aria-label="Message"], [role="textbox"]',
                timeout=10000,
            )
            box = await input_box.bounding_box()
            if box:
                await human_mouse_move(page, int(box["x"] + box["width"] / 2), int(box["y"] + box["height"] / 2))
            await input_box.click()
            await human_delay(0.3, 0.8)
            for char in text:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.04, 0.12))
            await human_delay(0.3, 0.8)
            await page.keyboard.press("Enter")
            await human_delay(0.8, 1.5)
            log.info(f"[FB] Mesaj trimis catre {profile_id}")
        except Exception as e:
            log.error(f"[FB] Eroare la trimitere: {e}")
        finally:
            await page.close()
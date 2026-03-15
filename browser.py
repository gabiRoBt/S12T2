import asyncio
import random
import os
import urllib.parse
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from config import (
    FB_EMAIL, FB_PASSWORD,
    IG_USERNAME, IG_PASSWORD,
    HEADLESS, BROWSER_TIMEOUT,
    CONTEXT_MESSAGE_LIMIT,
    MIN_DELAY, MAX_DELAY,
)

FB_SESSION_PATH = "session_fb.json"
IG_SESSION_PATH = "session_ig.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def human_delay(min_s: float = MIN_DELAY, max_s: float = MAX_DELAY):
    await asyncio.sleep(random.uniform(min_s, max_s))


async def human_mouse_move(page: Page, x: int, y: int):
    steps = random.randint(15, 25)
    start_x = random.randint(100, 900)
    start_y = random.randint(100, 600)
    for i in range(steps + 1):
        t = i / steps
        cx = random.randint(min(start_x, x), max(start_x, x))
        cy = random.randint(min(start_y, y), max(start_y, y))
        bx = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * cx + t ** 2 * x
        by = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * cy + t ** 2 * y
        await page.mouse.move(bx, by)
        await asyncio.sleep(random.uniform(0.01, 0.03))


async def reading_delay(text: str):
    chars = len(text)
    base = chars / random.uniform(150, 250)
    thinking = random.uniform(1.5, 5.0)
    await asyncio.sleep(base + thinking)


async def human_scroll(page: Page):
    scroll_up = random.randint(200, 500)
    await page.mouse.wheel(0, -scroll_up)
    await human_delay(0.8, 1.5)
    await page.mouse.wheel(0, scroll_up)
    await human_delay(0.5, 1.0)


async def js_click(page: Page, selector: str, timeout: int = 5000) -> bool:
    """Find element and click via JavaScript - avoids visibility issues."""
    try:
        el = await page.wait_for_selector(selector, timeout=timeout)
        if el:
            await page.evaluate("el => el.click()", el)
            print(f"[BROWSER] JS click: {selector}")
            return True
    except Exception:
        pass
    return False


async def type_into(page: Page, selector: str, text: str):
    """Click element and type text character by character."""
    el = await page.query_selector(selector)
    if el:
        await el.click()
        for char in text:
            await page.keyboard.type(char)
            await asyncio.sleep(random.uniform(0.05, 0.15))


# ---------------------------------------------------------------------------
# Popup helpers
# ---------------------------------------------------------------------------

async def _accept_cookies(page: Page):
    print("[BROWSER] Caut banner cookies...")
    for selector in [
        'button:has-text("Allow all cookies")',
        'button:has-text("Accept all")',
        'button:has-text("Accept")',
        'button[data-cookiebanner="accept_button"]',
        '[data-testid="cookie-policy-manage-dialog-accept-button"]',
        '[data-testid="accept-btn"]',
    ]:
        if await js_click(page, selector, timeout=3000):
            await human_delay(1, 2)
            return
    print("[BROWSER] Niciun banner cookies gasit.")


async def _dismiss_popups(page: Page):
    """Dismiss any blocking popup - notifications, save login, etc."""
    for selector in [
        'button:has-text("Not Now")',
        'button:has-text("Not now")',
        'button:has-text("Maybe Later")',
        'button._a9--._ap36._a9_1',
        '[aria-label="Close"]',
    ]:
        await js_click(page, selector, timeout=2000)


async def _dismiss_connect_prompt(page: Page):
    """Dismiss Instagram Connect prompt."""
    for selector in [
        '[aria-label="Log in"]',
        '[aria-label="Connect"]',
        'button:has-text("Log in")',
    ]:
        if await js_click(page, selector, timeout=3000):
            await human_delay(1, 2)
            print(f"[IG] Prompt Connect inchis.")
            return


# ---------------------------------------------------------------------------
# Login flows
# ---------------------------------------------------------------------------

async def _do_facebook_login(page: Page):
    print("[FB] Logare in curs...")
    await _accept_cookies(page)
    await human_delay(1, 2)

    print("[FB] Astept campul de email...")
    await page.wait_for_selector('#email', timeout=15000)
    await type_into(page, '#email', FB_EMAIL)
    await human_delay(0.5, 1.2)
    await type_into(page, '#pass', FB_PASSWORD)
    await human_delay(0.5, 1.2)

    print("[FB] Apas login...")
    if not await js_click(page, '[name="login"]', timeout=5000):
        await page.keyboard.press("Enter")

    print("[FB] Astept redirectionare...")
    await page.wait_for_load_state("domcontentloaded")
    await human_delay(2, 4)
    print("[FB] Login realizat.")


async def _do_instagram_login(page: Page):
    print("[IG] Logare in curs...")
    await _accept_cookies(page)
    await _dismiss_connect_prompt(page)
    await human_delay(1, 2)

    print("[IG] Astept campul de username...")
    await page.wait_for_selector('input[name="username"], input[name="email"]', timeout=15000)
    await type_into(page, 'input[name="username"], input[name="email"]', IG_USERNAME)
    await human_delay(0.5, 1.2)

    print("[IG] Completez parola...")
    await type_into(page, 'input[name="password"], input[name="pass"]', IG_PASSWORD)
    await human_delay(0.5, 1.2)

    print("[IG] Apas login cu Enter...")
    await page.keyboard.press("Enter")

    print("[IG] Astept redirectionare...")
    await page.wait_for_load_state("domcontentloaded")
    await human_delay(2, 3)

    # Handle onetap / save login info page
    if "onetap" in page.url or "save-login" in page.url:
        print("[IG] Pagina Save login info - o sar...")
        if not await js_click(page, 'button:has-text("Not Now")', timeout=4000):
            raw_next = page.url.split("next=")[-1].split("&")[0]
            next_url = urllib.parse.unquote(raw_next)
            if next_url and "instagram.com" in next_url:
                print(f"[IG] Navighez direct la: {next_url}")
                await page.goto(next_url)
                await page.wait_for_load_state("domcontentloaded")
                await human_delay(1, 2)

    # Dismiss notifications popup and any other popups
    await human_delay(1, 2)
    await _dismiss_popups(page)
    await human_delay(1, 2)

    print("[IG] Login realizat.")


# ---------------------------------------------------------------------------
# Login page detection
# ---------------------------------------------------------------------------

def _is_fb_login_page(url: str) -> bool:
    return "facebook.com/login" in url or "facebook.com/?next=" in url


def _is_ig_login_page(url: str) -> bool:
    return "instagram.com/accounts/login" in url or "instagram.com/?next=" in url


# ---------------------------------------------------------------------------
# Browser session
# ---------------------------------------------------------------------------

class BrowserSession:
    def __init__(self):
        self.playwright = None
        self.browser: Browser | None = None
        self.fb_context: BrowserContext | None = None
        self.ig_context: BrowserContext | None = None

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=HEADLESS,
            args=["--disable-blink-features=AutomationControlled"],
        )

    async def stop(self):
        if self.fb_context:
            await self.fb_context.storage_state(path=FB_SESSION_PATH)
            print(f"[FB] Sesiune salvata.")
        if self.ig_context:
            await self.ig_context.storage_state(path=IG_SESSION_PATH)
            print(f"[IG] Sesiune salvata.")
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def _new_context(self, session_path: str | None = None) -> BrowserContext:
        kwargs = dict(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        if session_path and os.path.exists(session_path):
            kwargs["storage_state"] = session_path
            print(f"[BROWSER] Sesiune incarcata din {session_path}")
        return await self.browser.new_context(**kwargs)

    # ------------------------------------------------------------------
    # Facebook
    # ------------------------------------------------------------------

    async def login_facebook(self):
        self.fb_context = await self._new_context(FB_SESSION_PATH)
        page = await self.fb_context.new_page()
        page.set_default_timeout(BROWSER_TIMEOUT)

        await page.goto("https://www.facebook.com/")
        await page.wait_for_load_state("domcontentloaded")
        await human_delay(2, 3)

        if await page.query_selector('#email') is None:
            print("[FB] Deja logat via sesiune salvata.")
            await page.close()
            return

        await _do_facebook_login(page)
        await self.fb_context.storage_state(path=FB_SESSION_PATH)
        print("[FB] Sesiune salvata dupa login.")
        await page.close()

    async def _fb_ensure_logged_in(self, page: Page):
        await human_delay(1, 2)
        print(f"[FB] URL curent: {page.url}")
        if _is_fb_login_page(page.url):
            print("[FB] Redirectat la login, reautentificare...")
            await _do_facebook_login(page)
            await self.fb_context.storage_state(path=FB_SESSION_PATH)
            print("[FB] Sesiune re-salvata.")
        else:
            print("[FB] Sesiune valida.")

    async def get_facebook_conversation(self, profile_id: str) -> list[dict]:
        page = await self.fb_context.new_page()
        page.set_default_timeout(BROWSER_TIMEOUT)

        url = f"https://www.facebook.com/messages/t/{profile_id}"
        print(f"[FB] Deschid conversatia {profile_id}...")
        await page.goto(url)
        await page.wait_for_load_state("domcontentloaded")

        await self._fb_ensure_logged_in(page)

        if "facebook.com/messages/t/" not in page.url:
            print("[FB] Renavighez la conversatie...")
            await page.goto(url)
            await page.wait_for_load_state("domcontentloaded")
            await human_delay(2, 3)

        await human_scroll(page)

        messages = []
        try:
            rows = await page.query_selector_all('[data-scope="messages_table"] [class*="message"]')
            for row in rows[-CONTEXT_MESSAGE_LIMIT:]:
                text = (await row.inner_text()).strip()
                if not text:
                    continue
                is_outgoing = await row.evaluate(
                    "el => el.closest('[class*=\"outgoing\"]') !== null"
                )
                role = "CHATBOT" if is_outgoing else "USER"
                messages.append({"role": role, "message": text})
            print(f"[FB] {len(messages)} mesaje extrase.")
        except Exception as e:
            print(f"[FB] Eroare la extragere mesaje: {e}")

        await page.close()
        return messages

    async def send_facebook_message(self, profile_id: str, text: str, last_incoming: str = ""):
        page = await self.fb_context.new_page()
        page.set_default_timeout(BROWSER_TIMEOUT)

        url = f"https://www.facebook.com/messages/t/{profile_id}"
        print(f"[FB] Deschid conversatia pentru trimitere {profile_id}...")
        await page.goto(url)
        await page.wait_for_load_state("domcontentloaded")

        await self._fb_ensure_logged_in(page)

        if "facebook.com/messages/t/" not in page.url:
            await page.goto(url)
            await page.wait_for_load_state("domcontentloaded")
            await human_delay(2, 3)

        if last_incoming:
            await reading_delay(last_incoming)
        else:
            await human_delay(2, 5)

        try:
            input_box = await page.wait_for_selector('[aria-label="Message"]', timeout=10000)
            box = await input_box.bounding_box()
            if box:
                await human_mouse_move(page, int(box['x'] + box['width'] / 2), int(box['y'] + box['height'] / 2))
            await input_box.click()
            await human_delay(0.5, 1)
            for char in text:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.04, 0.15))
            await human_delay(0.5, 1.5)
            await page.keyboard.press("Enter")
            await human_delay(1, 2)
            print(f"[FB] Mesaj trimis catre {profile_id}")
        except Exception as e:
            print(f"[FB] Eroare la trimitere: {e}")
        finally:
            await page.close()

    # ------------------------------------------------------------------
    # Instagram
    # ------------------------------------------------------------------

    async def login_instagram(self):
        self.ig_context = await self._new_context(IG_SESSION_PATH)
        page = await self.ig_context.new_page()
        page.set_default_timeout(BROWSER_TIMEOUT)

        await page.goto("https://www.instagram.com/accounts/login/")
        await page.wait_for_load_state("domcontentloaded")
        await human_delay(2, 3)

        if await page.query_selector('input[name="username"], input[name="email"]') is None:
            print("[IG] Deja logat via sesiune salvata.")
            await page.close()
            return

        await _do_instagram_login(page)

        # Save session AFTER all popups dismissed so preferences are stored
        await self.ig_context.storage_state(path=IG_SESSION_PATH)
        print("[IG] Sesiune salvata dupa login si dismiss popups.")
        await page.close()

    async def _ig_ensure_logged_in(self, page: Page):
        await human_delay(1, 2)
        print(f"[IG] URL curent: {page.url}")
        if _is_ig_login_page(page.url):
            print("[IG] Redirectat la login, reautentificare...")
            await _do_instagram_login(page)
            await self.ig_context.storage_state(path=IG_SESSION_PATH)
            print("[IG] Sesiune re-salvata.")
        else:
            print("[IG] Sesiune valida.")

    async def get_instagram_conversation(self, profile_id: str) -> list[dict]:
        page = await self.ig_context.new_page()
        page.set_default_timeout(BROWSER_TIMEOUT)

        url = f"https://www.instagram.com/direct/t/{profile_id}/"
        print(f"[IG] Deschid conversatia {profile_id}...")
        await page.goto(url)
        await page.wait_for_load_state("domcontentloaded")
        await human_delay(2, 3)

        await self._ig_ensure_logged_in(page)

        if "instagram.com/direct/t/" not in page.url:
            print("[IG] Renavighez la conversatie...")
            await page.goto(url)
            await page.wait_for_load_state("domcontentloaded")
            await human_delay(2, 3)

        # Dismiss any popup before reading
        await _dismiss_popups(page)
        await human_delay(1, 2)

        await human_scroll(page)

        messages = []
        try:
            bubbles = await page.query_selector_all('div[role="presentation"] div[dir="auto"]')
            print(f"[IG] Gasit {len(bubbles)} bule de mesaje.")
            for bubble in bubbles[-CONTEXT_MESSAGE_LIMIT:]:
                text = (await bubble.inner_text()).strip()
                if not text:
                    continue
                is_outgoing = await bubble.evaluate(
                    """el => {
                        let node = el;
                        for (let i = 0; i < 10; i++) {
                            node = node.parentElement;
                            if (!node) break;
                            const bg = window.getComputedStyle(node).backgroundColor;
                            if (!bg || bg === 'transparent' || bg === 'rgba(0, 0, 0, 0)') continue;

                            const parts = bg.replace("rgba(","").replace("rgb(","").replace(")","").split(",");
                            if (parts && parts.length >= 3) {
                                const r = parseInt(parts[0]);
                                const g = parseInt(parts[1]);
                                const b = parseInt(parts[2]);
                                // Grey = incoming (r, g, b close to each other and not too bright)
                                const isGrey = Math.abs(r - g) < 20 && Math.abs(g - b) < 20 && Math.abs(r - b) < 20;
                                if (isGrey) return false;
                                // Any non-grey color with actual value = outgoing
                                if (r + g + b > 30) return true;
                            }
                        }
                        return false;
                    }"""
                )
                role = "CHATBOT" if is_outgoing else "USER"
                messages.append({"role": role, "message": text})
                print(f"[IG] [{role}]: {text}")
            print(f"[IG] {len(messages)} mesaje extrase.")
        except Exception as e:
            print(f"[IG] Eroare la extragere mesaje: {e}")

        await page.close()
        return messages

    async def send_instagram_message(self, profile_id: str, text: str, last_incoming: str = ""):
        page = await self.ig_context.new_page()
        page.set_default_timeout(BROWSER_TIMEOUT)

        url = f"https://www.instagram.com/direct/t/{profile_id}/"
        print(f"[IG] Deschid conversatia pentru trimitere {profile_id}...")
        await page.goto(url)
        await page.wait_for_load_state("domcontentloaded")
        await human_delay(2, 3)

        await self._ig_ensure_logged_in(page)

        if "instagram.com/direct/t/" not in page.url:
            await page.goto(url)
            await page.wait_for_load_state("domcontentloaded")
            await human_delay(2, 3)

        await _dismiss_popups(page)
        await human_delay(1, 2)

        if last_incoming:
            await reading_delay(last_incoming)
        else:
            await human_delay(2, 5)

        try:
            input_box = await page.wait_for_selector(
                '[aria-placeholder="Message..."], [aria-label="Message"], [placeholder="Message..."]',
                timeout=10000,
            )
            box = await input_box.bounding_box()
            if box:
                await human_mouse_move(page, int(box['x'] + box['width'] / 2), int(box['y'] + box['height'] / 2))
            await input_box.click()
            await human_delay(0.5, 1)
            for char in text:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.04, 0.15))
            await human_delay(0.5, 1.5)
            await page.keyboard.press("Enter")
            await human_delay(1, 2)
            print(f"[IG] Mesaj trimis catre {profile_id}")
        except Exception as e:
            print(f"[IG] Eroare la trimitere: {e}")
        finally:
            await page.close()
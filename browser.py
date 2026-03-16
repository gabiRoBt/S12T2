from logger import log
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
            return True
    except Exception:
        pass
    return False


async def type_into(page: Page, selector: str, text: str):
    """Click element via JS and type text character by character."""
    el = await page.query_selector(selector)
    if el:
        await page.evaluate("el => el.click()", el)
        await asyncio.sleep(0.3)
        for char in text:
            await page.keyboard.type(char)
            await asyncio.sleep(random.uniform(0.05, 0.15))


def _is_grey(r: int, g: int, b: int) -> bool:
    return abs(r - g) < 20 and abs(g - b) < 20 and abs(r - b) < 20


OUTGOING_COLOR_JS = """el => {
    // Find the div[role="presentation"] parent which has the bubble background
    let node = el;
    for (let i = 0; i < 15; i++) {
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
                // Incoming = grey rgb(240, 240, 240) with tolerance 15
                const isGrey = Math.abs(r - 240) < 15 && Math.abs(g - 240) < 15 && Math.abs(b - 240) < 15;
                return !isGrey;
            }
        }
    }
    return false;
}"""


# ---------------------------------------------------------------------------
# Popup helpers
# ---------------------------------------------------------------------------

async def _handle_fb_pin(page: Page):
    """Handle Facebook e2ee PIN prompt if present."""
    try:
        pin_input = await page.wait_for_selector('[aria-label="PIN"]', timeout=5000)
        if pin_input:
            log.info("[FB] PIN prompt detectat, introduc PIN-ul imediat...")
            await page.evaluate("el => { el.focus(); el.click(); }", pin_input)
            await asyncio.sleep(0.1)
            await page.keyboard.type("123456")
            await asyncio.sleep(0.2)
            await page.keyboard.press("Enter")
            await asyncio.sleep(1)
            log.info("[FB] PIN introdus.")
    except Exception:
        pass


async def _accept_cookies(page: Page):
    log.info("[BROWSER] Caut banner cookies...")
    for selector in [
        '[aria-label="Allow all cookies"]',
        'button:has-text("Allow all cookies")',
        'button:has-text("Permite toate modulele cookie")',
        'button:has-text("Accept all")',
        'button:has-text("Accept")',
        'button[data-cookiebanner="accept_button"]',
        '[data-testid="cookie-policy-manage-dialog-accept-button"]',
        '[data-testid="accept-btn"]',
    ]:
        if await js_click(page, selector, timeout=3000):
            await human_delay(1, 2)
            log.info("[BROWSER] Cookies acceptate.")
            return
    log.info("[BROWSER] Niciun banner cookies gasit.")


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
            log.info("[IG] Prompt Connect inchis.")
            return


# ---------------------------------------------------------------------------
# Login flows
# ---------------------------------------------------------------------------

async def _do_facebook_login(page: Page):
    log.info("[FB] Navighez la pagina de login...")
    await page.goto("https://www.facebook.com/login.php")
    await page.wait_for_load_state("domcontentloaded")
    await human_delay(2, 3)

    # Click "Use another profile" if present
    if await js_click(page, '[aria-label="Use another profile"]', timeout=4000):
        log.info("[FB] Use another profile apasat.")
        await page.wait_for_load_state("domcontentloaded")
        await human_delay(1, 2)

    log.info("[FB] Astept campul de email...")
    await page.wait_for_selector('input[name="email"]', timeout=15000)
    await human_delay(0.5, 1)

    # Accept cookies after page loaded
    await _accept_cookies(page)
    await human_delay(0.5, 1)

    log.info("[FB] Completez email...")
    await page.focus('input[type="text"][name="email"]')
    await asyncio.sleep(0.3)
    for char in FB_EMAIL:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.05, 0.15))
    await human_delay(0.5, 1.2)

    log.info("[FB] Completez parola...")
    await page.focus('input[type="password"][name="pass"]')
    await asyncio.sleep(0.3)
    for char in FB_PASSWORD:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.05, 0.15))
    await human_delay(0.5, 1.2)

    log.info("[FB] Apas login...")
    if not await js_click(page, '#loginbutton', timeout=5000):
        if not await js_click(page, '[name="login"]', timeout=3000):
            await page.keyboard.press("Enter")

    log.info("[FB] Astept redirectionare dupa login...")
    await page.wait_for_load_state("domcontentloaded")
    await human_delay(5, 8)
    log.info(f"[FB] Dupa login URL: {page.url}")
    log.info("[FB] Astept 15 secunde ca sa poti vedea pagina...")
    await asyncio.sleep(15)
    log.info(f"[FB] Continuez. URL final: {page.url}")


async def _do_instagram_login(page: Page):
    log.info("[IG] Logare in curs...")
    await _accept_cookies(page)
    await _dismiss_connect_prompt(page)
    await human_delay(1, 2)

    log.info("[IG] Astept campul de username...")
    await page.wait_for_selector('input[name="username"], input[name="email"]', timeout=15000)
    await type_into(page, 'input[name="username"], input[name="email"]', IG_USERNAME)
    await human_delay(0.5, 1.2)

    log.info("[IG] Completez parola...")
    await type_into(page, 'input[name="password"], input[name="pass"]', IG_PASSWORD)
    await human_delay(0.5, 1.2)

    log.info("[IG] Apas login cu Enter...")
    await page.keyboard.press("Enter")

    log.info("[IG] Astept redirectionare...")
    await page.wait_for_load_state("domcontentloaded")
    await human_delay(2, 3)

    # Handle onetap / save login info page
    if "onetap" in page.url or "save-login" in page.url:
        log.info("[IG] Pagina Save login info - o sar...")
        if not await js_click(page, 'button:has-text("Not Now")', timeout=4000):
            raw_next = page.url.split("next=")[-1].split("&")[0]
            next_url = urllib.parse.unquote(raw_next)
            if next_url and "instagram.com" in next_url:
                log.info(f"[IG] Navighez direct la: {next_url}")
                await page.goto(next_url)
                await page.wait_for_load_state("domcontentloaded")
                await human_delay(1, 2)

    await human_delay(1, 2)
    await _dismiss_popups(page)
    await human_delay(1, 2)
    log.info("[IG] Login realizat.")


# ---------------------------------------------------------------------------
# Login page detection
# ---------------------------------------------------------------------------

def _is_fb_login_page(url: str) -> bool:
    return "facebook.com/login" in url or "facebook.com/?next=" in url


async def _is_fb_login_shown(page) -> bool:
    """Detect Facebook login form even when URL does not change."""
    if _is_fb_login_page(page.url):
        return True
    if "facebook.com" in page.url and ("login" in page.url or "login_attempt" in page.url):
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
                log.info(f"[FB] Login form detectat cu: {selector}")
                return True
        except Exception:
            pass
    return False


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
        # Save sessions before closing
        if self.fb_context:
            try:
                await self.fb_context.storage_state(path=FB_SESSION_PATH)
                log.info("[FB] Sesiune salvata.")
            except Exception:
                pass
        if self.ig_context:
            try:
                await self.ig_context.storage_state(path=IG_SESSION_PATH)
                log.info("[IG] Sesiune salvata.")
            except Exception:
                pass
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception:
                pass

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
            log.info(f"[BROWSER] Sesiune incarcata din {session_path}")
        return await self.browser.new_context(**kwargs)

    # ------------------------------------------------------------------
    # Facebook
    # ------------------------------------------------------------------

    async def login_facebook(self):
        self.fb_context = await self._new_context(FB_SESSION_PATH)
        log.info("[FB] Context creat, sesiunea va fi verificata la prima conversatie.")

    async def _fb_ensure_logged_in(self, page: Page):
        await human_delay(1, 2)
        log.info(f"[FB] URL curent: {page.url}")
        if await _is_fb_login_shown(page):
            log.info("[FB] Login form detectat, reautentificare...")
            await _do_facebook_login(page)
            await self.fb_context.storage_state(path=FB_SESSION_PATH)
            log.info("[FB] Sesiune re-salvata.")
        else:
            log.info("[FB] Sesiune valida.")
            await _dismiss_popups(page)

    async def get_facebook_conversation(self, profile_id: str) -> list[dict]:
        page = await self.fb_context.new_page()
        page.set_default_timeout(BROWSER_TIMEOUT)

        # Try e2ee first, fallback to regular
        url_e2ee = f"https://www.facebook.com/messages/e2ee/t/{profile_id}"
        url_regular = f"https://www.facebook.com/messages/t/{profile_id}"

        log.info(f"[FB] Deschid conversatia {profile_id}...")
        await page.goto(url_e2ee)
        await page.wait_for_load_state("domcontentloaded")
        await human_delay(2, 3)

        await self._fb_ensure_logged_in(page)

        # If e2ee redirected away from messages, try regular
        if "facebook.com/messages" not in page.url:
            log.info("[FB] e2ee nu a functionat, incerc URL regular...")
            await page.goto(url_regular)
            await page.wait_for_load_state("domcontentloaded")
            await human_delay(2, 3)

        # If still not on messages, re-login and try again
        if "facebook.com/messages" not in page.url:
            log.info("[FB] Renavighez dupa login...")
            await page.goto(url_e2ee)
            await page.wait_for_load_state("domcontentloaded")
            await human_delay(2, 3)

        log.info(f"[FB] URL conversatie: {page.url}")

        await _handle_fb_pin(page)
        await _dismiss_popups(page)
        await human_delay(1, 2)

        await human_scroll(page)

        messages = []
        try:
            # Get all spans with dir=auto inside presentation bubbles
            all_bubbles = await page.query_selector_all('div[role="presentation"] span[dir="auto"]')

            # Filter out timestamps - spans inside date_break or aria-hidden
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
            bubbles = filtered
            for bubble in bubbles[-CONTEXT_MESSAGE_LIMIT:]:
                text = (await bubble.inner_text()).strip()
                if not text:
                    continue
                is_outgoing = await bubble.evaluate(OUTGOING_COLOR_JS)
                role = "CHATBOT" if is_outgoing else "USER"
                messages.append({"role": role, "message": text})
            log.info(f"[FB] {len(messages)} mesaje extrase.")
        except Exception as e:
            log.info(f"[FB] Eroare la extragere mesaje: {e}")

        await page.close()
        return messages

    async def send_facebook_message(self, profile_id: str, text: str, last_incoming: str = ""):
        page = await self.fb_context.new_page()
        page.set_default_timeout(BROWSER_TIMEOUT)

        url_e2ee = f"https://www.facebook.com/messages/e2ee/t/{profile_id}"
        url_regular = f"https://www.facebook.com/messages/t/{profile_id}"

        log.info(f"[FB] Deschid conversatia pentru trimitere {profile_id}...")
        await page.goto(url_e2ee)
        await page.wait_for_load_state("domcontentloaded")
        await human_delay(2, 3)

        await self._fb_ensure_logged_in(page)

        if "facebook.com/messages" not in page.url:
            log.info("[FB] e2ee nu a functionat, incerc URL regular...")
            await page.goto(url_regular)
            await page.wait_for_load_state("domcontentloaded")
            await human_delay(2, 3)

        log.info(f"[FB] URL conversatie: {page.url}")

        await _dismiss_popups(page)
        await human_delay(1, 2)

        if last_incoming:
            await reading_delay(last_incoming)
        else:
            await human_delay(2, 5)

        try:
            input_box = await page.wait_for_selector(
                '[aria-placeholder="Aa"], [aria-label="Message"], [role="textbox"]',
                timeout=10000,
            )
            box = await input_box.bounding_box()
            if box:
                await human_mouse_move(page, int(box["x"] + box["width"] / 2), int(box["y"] + box["height"] / 2))
            await input_box.click()
            await human_delay(0.5, 1)
            for char in text:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.04, 0.15))
            await human_delay(0.5, 1.5)
            await page.keyboard.press("Enter")
            await human_delay(1, 2)
            log.info(f"[FB] Mesaj trimis catre {profile_id}")
        except Exception as e:
            log.info(f"[FB] Eroare la trimitere: {e}")
        finally:
            await page.close()

    # ------------------------------------------------------------------
    # Instagram
    # ------------------------------------------------------------------

    async def login_instagram(self):
        self.ig_context = await self._new_context(IG_SESSION_PATH)
        log.info("[IG] Context creat, sesiunea va fi verificata la prima conversatie.")

    async def _ig_ensure_logged_in(self, page: Page):
        await human_delay(1, 2)
        log.info(f"[IG] URL curent: {page.url}")
        if _is_ig_login_page(page.url):
            log.info("[IG] Redirectat la login, reautentificare...")
            await _do_instagram_login(page)
            await self.ig_context.storage_state(path=IG_SESSION_PATH)
            log.info("[IG] Sesiune re-salvata.")
        else:
            log.info("[IG] Sesiune valida.")

    async def get_instagram_conversation(self, profile_id: str) -> list[dict]:
        page = await self.ig_context.new_page()
        page.set_default_timeout(BROWSER_TIMEOUT)

        url = f"https://www.instagram.com/direct/t/{profile_id}/"
        log.info(f"[IG] Deschid conversatia {profile_id}...")
        await page.goto(url)
        await page.wait_for_load_state("domcontentloaded")
        await human_delay(2, 3)

        await self._ig_ensure_logged_in(page)

        if "instagram.com/direct/t/" not in page.url:
            log.info("[IG] Renavighez la conversatie...")
            await page.goto(url)
            await page.wait_for_load_state("domcontentloaded")
            await human_delay(2, 3)

        await _dismiss_popups(page)
        await human_delay(1, 2)
        await human_scroll(page)

        messages = []
        try:
            bubbles = await page.query_selector_all('div[role="presentation"] div[dir="auto"]')
            for bubble in bubbles[-CONTEXT_MESSAGE_LIMIT:]:
                text = (await bubble.inner_text()).strip()
                if not text:
                    continue
                is_outgoing = await bubble.evaluate(OUTGOING_COLOR_JS)
                role = "CHATBOT" if is_outgoing else "USER"
                messages.append({"role": role, "message": text})
            log.info(f"[IG] {len(messages)} mesaje extrase.")
        except Exception as e:
            log.info(f"[IG] Eroare la extragere mesaje: {e}")

        await page.close()
        return messages

    async def send_instagram_message(self, profile_id: str, text: str, last_incoming: str = ""):
        page = await self.ig_context.new_page()
        page.set_default_timeout(BROWSER_TIMEOUT)

        url = f"https://www.instagram.com/direct/t/{profile_id}/"
        log.info(f"[IG] Deschid conversatia pentru trimitere {profile_id}...")
        await page.goto(url)
        await page.wait_for_load_state("domcontentloaded")
        await human_delay(2, 3)

        await self._ig_ensure_logged_in(page)

        if "instagram.com/direct/t/" not in page.url:
            log.info("[IG] Renavighez la conversatie...")
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
                await human_mouse_move(page, int(box["x"] + box["width"] / 2), int(box["y"] + box["height"] / 2))
            await input_box.click()
            await human_delay(0.5, 1)
            for char in text:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.04, 0.15))
            await human_delay(0.5, 1.5)
            await page.keyboard.press("Enter")
            await human_delay(1, 2)
            log.info(f"[IG] Mesaj trimis catre {profile_id}")
        except Exception as e:
            log.info(f"[IG] Eroare la trimitere: {e}")
        finally:
            await page.close()
import asyncio
import random
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from config import (
    FB_EMAIL, FB_PASSWORD,
    IG_USERNAME, IG_PASSWORD,
    HEADLESS, BROWSER_TIMEOUT,
    CONTEXT_MESSAGE_LIMIT,
    MIN_DELAY, MAX_DELAY,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def human_delay(min_s: float = MIN_DELAY, max_s: float = MAX_DELAY):
    """Wait a random amount of time to simulate human behavior."""
    await asyncio.sleep(random.uniform(min_s, max_s))


async def human_type(page: Page, selector: str, text: str):
    """Type text character by character with random delays."""
    await page.click(selector)
    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.05, 0.18))


# ---------------------------------------------------------------------------
# Browser session management
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
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def _new_context(self) -> BrowserContext:
        return await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="ro-RO",
        )

    # ------------------------------------------------------------------
    # Facebook
    # ------------------------------------------------------------------

    async def login_facebook(self):
        self.fb_context = await self._new_context()
        page = await self.fb_context.new_page()
        page.set_default_timeout(BROWSER_TIMEOUT)

        await page.goto("https://www.facebook.com/")
        await human_delay(2, 3)

        await human_type(page, '#email', FB_EMAIL)
        await human_delay(0.5, 1)
        await human_type(page, '#pass', FB_PASSWORD)
        await human_delay(0.5, 1)
        await page.click('[name="login"]')
        await page.wait_for_load_state("networkidle")
        await human_delay(2, 4)
        await page.close()
        print("[FB] Login successful")

    async def get_facebook_conversation(self, profile_id: str) -> list[dict]:
        """
        Open a Facebook Messenger conversation by profile ID and extract messages.
        Returns list of dicts: {"role": "USER"|"CHATBOT", "message": "..."}
        """
        page = await self.fb_context.new_page()
        page.set_default_timeout(BROWSER_TIMEOUT)

        url = f"https://www.facebook.com/messages/t/{profile_id}"
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        await human_delay(2, 3)

        messages = []
        try:
            # Each message row has a data-scope attribute
            rows = await page.query_selector_all('[data-scope="messages_table"] [class*="message"]')
            for row in rows[-CONTEXT_MESSAGE_LIMIT:]:
                text = (await row.inner_text()).strip()
                if not text:
                    continue
                # Outgoing messages have a different alignment class
                is_outgoing = await row.evaluate(
                    "el => el.closest('[class*=\"outgoing\"]') !== null"
                )
                role = "CHATBOT" if is_outgoing else "USER"
                messages.append({"role": role, "message": text})
        except Exception as e:
            print(f"[FB] Could not extract messages for {profile_id}: {e}")

        await page.close()
        return messages

    async def send_facebook_message(self, profile_id: str, text: str):
        """Type and send a message in a Facebook Messenger conversation."""
        page = await self.fb_context.new_page()
        page.set_default_timeout(BROWSER_TIMEOUT)

        url = f"https://www.facebook.com/messages/t/{profile_id}"
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        await human_delay(2, 3)

        try:
            input_box = await page.wait_for_selector('[aria-label="Message"]', timeout=10000)
            await input_box.click()
            await human_delay(0.5, 1)
            for char in text:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.04, 0.15))
            await human_delay(0.5, 1.5)
            await page.keyboard.press("Enter")
            await human_delay(1, 2)
            print(f"[FB] Message sent to {profile_id}")
        except Exception as e:
            print(f"[FB] Could not send message to {profile_id}: {e}")
        finally:
            await page.close()

    # ------------------------------------------------------------------
    # Instagram
    # ------------------------------------------------------------------

    async def login_instagram(self):
        self.ig_context = await self._new_context()
        page = await self.ig_context.new_page()
        page.set_default_timeout(BROWSER_TIMEOUT)

        await page.goto("https://www.instagram.com/accounts/login/")
        await human_delay(2, 3)

        await human_type(page, '[name="username"]', IG_USERNAME)
        await human_delay(0.5, 1)
        await human_type(page, '[name="password"]', IG_PASSWORD)
        await human_delay(0.5, 1)
        await page.click('[type="submit"]')
        await page.wait_for_load_state("networkidle")
        await human_delay(3, 5)

        # Dismiss "Save your login info?" popup if present
        try:
            await page.click('text=Not Now', timeout=5000)
        except Exception:
            pass

        await page.close()
        print("[IG] Login successful")

    async def get_instagram_conversation(self, profile_id: str) -> list[dict]:
        """
        Open an Instagram DM conversation by profile ID and extract messages.
        """
        page = await self.ig_context.new_page()
        page.set_default_timeout(BROWSER_TIMEOUT)

        url = f"https://www.instagram.com/direct/t/{profile_id}/"
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        await human_delay(2, 3)

        messages = []
        try:
            rows = await page.query_selector_all('[role="listitem"]')
            for row in rows[-CONTEXT_MESSAGE_LIMIT:]:
                text = (await row.inner_text()).strip()
                if not text:
                    continue
                is_outgoing = await row.evaluate(
                    "el => el.querySelector('[class*=\"own\"]') !== null || "
                    "el.style.alignSelf === 'flex-end'"
                )
                role = "CHATBOT" if is_outgoing else "USER"
                messages.append({"role": role, "message": text})
        except Exception as e:
            print(f"[IG] Could not extract messages for {profile_id}: {e}")

        await page.close()
        return messages

    async def send_instagram_message(self, profile_id: str, text: str):
        """Type and send a message in an Instagram DM conversation."""
        page = await self.ig_context.new_page()
        page.set_default_timeout(BROWSER_TIMEOUT)

        url = f"https://www.instagram.com/direct/t/{profile_id}/"
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        await human_delay(2, 3)

        try:
            input_box = await page.wait_for_selector(
                '[aria-label="Message"], [placeholder="Message..."]',
                timeout=10000,
            )
            await input_box.click()
            await human_delay(0.5, 1)
            for char in text:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.04, 0.15))
            await human_delay(0.5, 1.5)
            await page.keyboard.press("Enter")
            await human_delay(1, 2)
            print(f"[IG] Message sent to {profile_id}")
        except Exception as e:
            print(f"[IG] Could not send message to {profile_id}: {e}")
        finally:
            await page.close()

import asyncio
import random
import urllib.parse
from playwright.async_api import Page, BrowserContext

from config import IG_USERNAME, IG_PASSWORD, BROWSER_TIMEOUT, CONTEXT_MESSAGE_LIMIT
from browser.actions import human_delay, human_mouse_move, human_scroll, reading_delay, js_click, type_into, OUTGOING_COLOR_JS
from browser.popups import accept_cookies, dismiss_popups, dismiss_ig_connect_prompt
from logger import log

IG_SESSION_PATH = "session_ig.json"


def is_ig_login_page(url: str) -> bool:
    return (
        "instagram.com/accounts/login" in url
        or "instagram.com/?next=" in url
    )


async def do_instagram_login(page: Page):
    log.info("[IG] Logare in curs...")
    await accept_cookies(page)
    await dismiss_ig_connect_prompt(page)
    await human_delay(0.8, 1.5)

    log.info("[IG] Astept campul de username...")
    await page.wait_for_selector('input[name="username"], input[name="email"]', timeout=15000)
    await type_into(page, 'input[name="username"], input[name="email"]', IG_USERNAME)
    await human_delay(0.4, 0.8)

    log.info("[IG] Completez parola...")
    await type_into(page, 'input[name="password"], input[name="pass"]', IG_PASSWORD)
    await human_delay(0.4, 0.8)

    log.info("[IG] Apas login...")
    await page.keyboard.press("Enter")
    await page.wait_for_load_state("domcontentloaded")
    await human_delay(1.5, 2.5)

    if "onetap" in page.url or "save-login" in page.url:
        log.info("[IG] Pagina Save login info - o sar...")
        if not await js_click(page, 'button:has-text("Not Now")', timeout=4000):
            raw_next = page.url.split("next=")[-1].split("&")[0]
            next_url = urllib.parse.unquote(raw_next)
            if next_url and "instagram.com" in next_url:
                log.info(f"[IG] Navighez direct la: {next_url}")
                await page.goto(next_url)
                await page.wait_for_load_state("domcontentloaded")
                await human_delay(1, 1.5)

    await human_delay(0.8, 1.5)
    await dismiss_popups(page)
    await human_delay(0.8, 1.5)
    log.info("[IG] Login realizat.")


class InstagramBrowser:
    def __init__(self, context: BrowserContext):
        self.context = context

    async def ensure_logged_in(self, page: Page):
        await human_delay(0.8, 1.5)
        log.info(f"[IG] URL curent: {page.url}")
        if is_ig_login_page(page.url):
            log.info("[IG] Login necesar, reautentificare...")
            await do_instagram_login(page)
            await self.context.storage_state(path=IG_SESSION_PATH)
            log.info("[IG] Sesiune re-salvata.")
        else:
            log.info("[IG] Sesiune valida.")

    async def get_conversation(self, profile_id: str) -> list[dict]:
        page = await self.context.new_page()
        page.set_default_timeout(BROWSER_TIMEOUT)

        url = f"https://www.instagram.com/direct/t/{profile_id}/"
        log.info(f"[IG] Deschid conversatia {profile_id}...")
        await page.goto(url)
        await page.wait_for_load_state("domcontentloaded")
        await human_delay(1.5, 2.5)

        await self.ensure_logged_in(page)

        if "instagram.com/direct/t/" not in page.url:
            log.info("[IG] Renavighez la conversatie...")
            await page.goto(url)
            await page.wait_for_load_state("domcontentloaded")
            await human_delay(1.5, 2)

        await dismiss_popups(page)
        await human_delay(0.8, 1.2)
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
            log.error(f"[IG] Eroare la extragere mesaje: {e}")

        await page.close()
        return messages

    async def send_message(self, profile_id: str, text: str, last_incoming: str = ""):
        page = await self.context.new_page()
        page.set_default_timeout(BROWSER_TIMEOUT)

        url = f"https://www.instagram.com/direct/t/{profile_id}/"
        log.info(f"[IG] Deschid conversatia pentru trimitere {profile_id}...")
        await page.goto(url)
        await page.wait_for_load_state("domcontentloaded")
        await human_delay(1.5, 2.5)

        await self.ensure_logged_in(page)

        if "instagram.com/direct/t/" not in page.url:
            await page.goto(url)
            await page.wait_for_load_state("domcontentloaded")
            await human_delay(1.5, 2)

        await dismiss_popups(page)
        await human_delay(0.8, 1.2)

        if last_incoming:
            await reading_delay(last_incoming)
        else:
            await human_delay(1.5, 3)

        try:
            input_box = await page.wait_for_selector(
                '[aria-placeholder="Message..."], [aria-label="Message"], [placeholder="Message..."]',
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
            log.info(f"[IG] Mesaj trimis catre {profile_id}")
        except Exception as e:
            log.error(f"[IG] Eroare la trimitere: {e}")
        finally:
            await page.close()
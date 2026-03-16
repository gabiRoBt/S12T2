import os
from playwright.async_api import async_playwright, Browser, BrowserContext

from config import HEADLESS
from browser.facebook import FacebookBrowser, FB_SESSION_PATH
from browser.instagram import InstagramBrowser, IG_SESSION_PATH
from logger import log


class BrowserSession:
    def __init__(self):
        self.playwright = None
        self.browser: Browser | None = None
        self._fb_context: BrowserContext | None = None
        self._ig_context: BrowserContext | None = None
        self.facebook: FacebookBrowser | None = None
        self.instagram: InstagramBrowser | None = None

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=HEADLESS,
            args=["--disable-blink-features=AutomationControlled"],
        )
        log.info("[BROWSER] Browser pornit.")

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

    async def init_facebook(self):
        if self.facebook is None:
            self._fb_context = await self._new_context(FB_SESSION_PATH)
            self.facebook = FacebookBrowser(self._fb_context)
            log.info("[FB] Context Facebook creat.")

    async def init_instagram(self):
        if self.instagram is None:
            self._ig_context = await self._new_context(IG_SESSION_PATH)
            self.instagram = InstagramBrowser(self._ig_context)
            log.info("[IG] Context Instagram creat.")

    async def stop(self):
        if self._fb_context:
            try:
                await self._fb_context.storage_state(path=FB_SESSION_PATH)
                log.info("[FB] Sesiune salvata.")
            except Exception:
                pass
        if self._ig_context:
            try:
                await self._ig_context.storage_state(path=IG_SESSION_PATH)
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
        log.info("[BROWSER] Browser inchis.")

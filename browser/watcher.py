import asyncio
from playwright.async_api import Page, BrowserContext
from browser.actions import human_delay
from browser.popups import accept_cookies, dismiss_popups, handle_fb_pin
from logger import log

FB_INBOX_URL = "https://www.facebook.com/messages/"
IG_INBOX_URL = "https://www.instagram.com/direct/inbox/"

# Polling approach checking computed styles instead of fragile classes
FB_OBSERVER_JS = """(callback) => {
    let reported = new Set();
    const check = () => {
        const links = document.querySelectorAll('a[href*="/t/"]');
        links.forEach(link => {
            const href = link.href;
            if (!href.includes('facebook.com/messages/t/') && !href.includes('facebook.com/messages/e2ee/t/')) return;
            
            const parts = href.split('/t/');
            if (parts.length < 2) return;
            const convId = parts[1].split('/')[0].split('?')[0];

            // Check for unread indicators (blue dot or aria-label)
            const hasUnread = Array.from(link.querySelectorAll('*')).some(el => {
                const aria = el.getAttribute('aria-label');
                if (aria && aria.toLowerCase().includes('unread')) return true;
                
                const style = window.getComputedStyle(el);
                const isBlue = style.backgroundColor === 'rgb(8, 102, 255)' || style.backgroundColor === 'rgb(0, 132, 255)';
                const isSmall = parseInt(style.width) > 0 && parseInt(style.width) <= 16;
                const isCircle = style.borderRadius === '50%';
                return isBlue && isSmall && isCircle;
            });

            if (hasUnread) {
                if (!reported.has(convId)) {
                    reported.add(convId);
                    console.log('[WATCHER-FB] Unread detected:', convId);
                    callback({ platform: 'facebook', id: convId });
                }
            }
        });
    };
    setInterval(check, 3000);
    check();
}"""

IG_OBSERVER_JS = """(callback) => {
    let reported = new Set();
    const check = () => {
        const links = document.querySelectorAll('a[href^="/direct/t/"]');
        links.forEach(link => {
            const href = link.href;
            const parts = href.split('/direct/t/');
            if (parts.length < 2) return;
            const convId = parts[1].split('/')[0].split('?')[0];

            // Check for unread indicators (blue dot or bold text)
            const hasUnread = Array.from(link.querySelectorAll('*')).some(el => {
                const aria = el.getAttribute('aria-label');
                if (aria && aria.toLowerCase().includes('unread')) return true;

                const style = window.getComputedStyle(el);
                const isBlue = style.backgroundColor === 'rgb(0, 149, 246)' || style.backgroundColor === 'rgb(0, 100, 224)';
                const isSmall = parseInt(style.width) > 0 && parseInt(style.width) <= 15;
                const isCircle = style.borderRadius === '50%';
                
                const fw = style.fontWeight;
                const isBold = fw === '600' || fw === '700' || fw === 'bold';

                return (isBlue && isSmall && isCircle) || isBold;
            });

            if (hasUnread) {
                if (!reported.has(convId)) {
                    reported.add(convId);
                    console.log('[WATCHER-IG] Unread detected:', convId);
                    callback({ platform: 'instagram', id: convId });
                }
            }
        });
    };
    setInterval(check, 3000);
    check();
}"""


class InboxWatcher:
    def __init__(self):
        self.fb_page: Page | None = None
        self.ig_page: Page | None = None
        self._pending: asyncio.Queue = asyncio.Queue()

    async def start_facebook(self, context: BrowserContext, fb_browser):
        self.fb_page = await context.new_page()
        log.info("[WATCHER] Opening Facebook inbox...")
        await self.fb_page.goto(FB_INBOX_URL)
        await self.fb_page.wait_for_load_state("domcontentloaded")
        await human_delay(2, 3)

        # Login if needed
        await fb_browser.ensure_logged_in(self.fb_page)

        # Handle PIN
        await handle_fb_pin(self.fb_page)

        # Dismiss popups
        await dismiss_popups(self.fb_page)
        await human_delay(1, 2)

        # Navigate back to inbox if redirected
        if "facebook.com/messages" not in self.fb_page.url:
            await self.fb_page.goto(FB_INBOX_URL)
            await self.fb_page.wait_for_load_state("domcontentloaded")
            await human_delay(1, 2)

        await self.fb_page.expose_function("on_fb_message", self._on_new_message)
        await self.fb_page.evaluate(f"({FB_OBSERVER_JS})(window.on_fb_message)")
        log.info("[WATCHER] Facebook observer active.")

    async def start_instagram(self, context: BrowserContext, ig_browser):
        self.ig_page = await context.new_page()
        log.info("[WATCHER] Opening Instagram inbox...")
        await self.ig_page.goto(IG_INBOX_URL)
        await self.ig_page.wait_for_load_state("domcontentloaded")
        await human_delay(2, 3)

        # Login if needed
        await ig_browser.ensure_logged_in(self.ig_page)

        # Accept cookies
        await accept_cookies(self.ig_page)

        # Dismiss popups
        await dismiss_popups(self.ig_page)
        await human_delay(1, 2)

        # Navigate back to inbox if redirected
        if "instagram.com/direct/inbox" not in self.ig_page.url:
            await self.ig_page.goto(IG_INBOX_URL)
            await self.ig_page.wait_for_load_state("domcontentloaded")
            await human_delay(1, 2)

        await self.ig_page.expose_function("on_ig_message", self._on_new_message)
        await self.ig_page.evaluate(f"({IG_OBSERVER_JS})(window.on_ig_message)")
        log.info("[WATCHER] Instagram observer active.")

    async def _on_new_message(self, data: dict):
        platform = data.get("platform")
        conv_id = data.get("id")
        log.info(f"[WATCHER] New message detected - {platform} | {conv_id}")
        await self._pending.put({"platform": platform, "id": conv_id})

    async def next_event(self) -> dict:
        return await self._pending.get()

    async def stop(self):
        for page in [self.fb_page, self.ig_page]:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
        log.info("[WATCHER] Watcher stopped.")
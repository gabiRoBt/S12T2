import asyncio
from playwright.async_api import Page, BrowserContext
from browser.actions import human_delay
from browser.popups import accept_cookies, dismiss_popups, handle_fb_pin
from logger import log

FB_INBOX_URL = "https://www.facebook.com/messages/"
IG_INBOX_URL = "https://www.instagram.com/direct/inbox/"

FB_OBSERVER_JS = """(callback) => {
    let reported = new Set();

    const check = () => {
        const items = document.querySelectorAll('[role="button"][tabindex="-1"]');
        items.forEach(item => {
            const hasDot = item.querySelector('[data-visualcompletion="ignore"]');
            const nameEl = item.querySelector('[dir="auto"]');
            if (!hasDot || !nameEl) return;

            const name = nameEl.innerText.trim();
            if (!name) return;

            const link = item.closest('a') || item.querySelector('a');
            const href = link ? link.href : '';
            const parts = href.split('/t/');
            const convId = parts.length > 1 ? parts[1].split('/')[0].split('?')[0] : name;

            const key = convId + ':' + name;
            if (reported.has(key)) return;
            reported.add(key);
            console.log('[WATCHER-FB] Unread detected:', convId);
            callback({ platform: 'facebook', id: convId, name: name });
        });
    };

    check();
    new MutationObserver(check).observe(document.body, { childList: true, subtree: true });
    setInterval(() => { reported.clear(); check(); }, 15000);
}"""

IG_OBSERVER_JS = """(callback) => {
    let reported = new Set();

    const check = () => {
        const all = document.querySelectorAll('[data-visualcompletion="ignore"]');
        all.forEach(el => {
            if (el.innerText.trim() !== 'Unread') return;
            let node = el;
            for (let i = 0; i < 15; i++) {
                node = node.parentElement;
                if (!node) break;
                const links = node.querySelectorAll('a');
                for (const link of links) {
                    if (!link.href.includes('/direct/t/')) continue;
                    const parts = link.href.split('/direct/t/');
                    const convId = parts.length > 1 ? parts[1].split('/')[0].split('?')[0] : null;
                    if (!convId || reported.has(convId)) continue;
                    reported.add(convId);
                    console.log('[WATCHER-IG] Unread detected:', convId);
                    callback({ platform: 'instagram', id: convId });
                    return;
                }
            }
        });
    };

    check();
    new MutationObserver(check).observe(document.body, { childList: true, subtree: true });
    setInterval(() => { reported.clear(); check(); }, 15000);
}"""


class InboxWatcher:
    def __init__(self):
        self.fb_page: Page | None = None
        self.ig_page: Page | None = None
        self._pending: asyncio.Queue = asyncio.Queue()

    async def start_facebook(self, context: BrowserContext, fb_browser):
        self.fb_page = await context.new_page()
        log.info("[WATCHER] Deschid Facebook inbox...")
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
        log.info("[WATCHER] Facebook observer activ.")

    async def start_instagram(self, context: BrowserContext, ig_browser):
        self.ig_page = await context.new_page()
        log.info("[WATCHER] Deschid Instagram inbox...")
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
        log.info("[WATCHER] Instagram observer activ.")

    async def _on_new_message(self, data: dict):
        platform = data.get("platform")
        conv_id = data.get("id")
        log.info(f"[WATCHER] Mesaj nou detectat - {platform} | {conv_id}")
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
        log.info("[WATCHER] Watcher oprit.")
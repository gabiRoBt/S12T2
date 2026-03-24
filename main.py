import asyncio
from bot import create_bot
from core.runner import cleanup
from config import DISCORD_TOKEN
from logger import log
from browser.actions import js_click, human_delay


async def main():
    bot = create_bot()
    try:
        log.info("[MAIN] Pornesc botul...")
        await bot.start(DISCORD_TOKEN)
    except KeyboardInterrupt:
        pass
    finally:
        log.info("[MAIN] Oprire detectata, curatenie...")
        await cleanup()
        if not bot.is_closed():
            await bot.close()
        log.info("[MAIN] Inchis corect.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

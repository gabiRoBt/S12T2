from logger import log
import asyncio
import discord
from bot import create_bot
from runner import cleanup


async def main():
    bot = create_bot()

    try:
        from config import DISCORD_TOKEN
        log.info("[MAIN] Pornesc botul...")
        await bot.start(DISCORD_TOKEN)
    except KeyboardInterrupt:
        pass
    finally:
        log.info("\n[MAIN] Oprire detectata, curatenie...")
        await cleanup()
        if not bot.is_closed():
            await bot.close()
        log.info("[MAIN] Inchis corect.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
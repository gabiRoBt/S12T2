import asyncio
import signal
from bot import start_bot
from runner import cleanup


def handle_shutdown(signum, frame):
    print("\n[MAIN] Shutdown signal received. Cleaning up...")
    asyncio.get_event_loop().run_until_complete(cleanup())
    exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    print("[MAIN] Starting chatbot automation...")
    start_bot()

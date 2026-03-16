import asyncio
import random
from datetime import datetime
from logger import log

# Format: (start_hour, end_hour, probability)
SCHEDULE = [
    (0,  7,  0.0),
    (7,  9,  0.3),
    (9,  12, 0.8),
    (12, 14, 0.6),
    (14, 18, 0.9),
    (18, 20, 0.7),
    (20, 23, 0.95),
    (23, 24, 0.4),
]

# Delay per slot (min_minutes, max_minutes)
RESPONSE_DELAY = {
    (0,  7):  (0,   0),
    (7,  9):  (15,  60),
    (9,  12): (2,   15),
    (12, 14): (5,   30),
    (14, 18): (1,   12),
    (18, 20): (3,   20),
    (20, 23): (1,   8),
    (23, 24): (8,   45),
}

ALWAYS_ONLINE_DELAY = (5, 45)


def _get_probability(hour: int) -> float:
    for start, end, prob in SCHEDULE:
        if start <= hour < end:
            return prob
    return 0.5


def should_respond(always_online: bool = False) -> bool:
    if always_online:
        return True
    return random.random() < _get_probability(datetime.now().hour)


async def activity_delay(always_online: bool = False):
    hour = datetime.now().hour

    if always_online:
        delay = random.uniform(ALWAYS_ONLINE_DELAY[0], ALWAYS_ONLINE_DELAY[1])
        log.info(f"[ACTIVITY] Mod always online - raspund in {delay:.0f}s")
        await asyncio.sleep(delay)
        return

    for (start, end), (min_m, max_m) in RESPONSE_DELAY.items():
        if start <= hour < end:
            if min_m == 0 and max_m == 0:
                return
            delay = random.uniform(min_m * 60, max_m * 60)
            minutes = int(delay // 60)
            seconds = int(delay % 60)
            if minutes > 0:
                log.info(f"[ACTIVITY] Raspund in {minutes}min {seconds}s (ora {hour}:xx)")
            else:
                log.info(f"[ACTIVITY] Raspund in {seconds}s (ora {hour}:xx)")
            await asyncio.sleep(delay)
            log.info("[ACTIVITY] Trimit raspunsul acum.")
            return

    await asyncio.sleep(random.uniform(60, 240))

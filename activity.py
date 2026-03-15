import random
from datetime import datetime


# Format: (start_hour, end_hour, probability_of_responding)
SCHEDULE = [
    (0,  7,  0.0),   # Noaptea - doarme, nu raspunde niciodata
    (7,  9,  0.3),   # Dimineata devreme - probabil inca doarme sau e grabit
    (9,  12, 0.8),   # Dimineata - activ
    (12, 14, 0.6),   # Pranz - probabil mananca
    (14, 18, 0.9),   # Dupa-amiaza - foarte activ
    (18, 20, 0.7),   # Seara devreme - probabil ocupat
    (20, 23, 0.95),  # Seara - cel mai activ, sta pe telefon
    (23, 24, 0.4),   # Tarziu noaptea - pe cale sa adoarma
]

# Delay per time slot (min_minutes, max_minutes)
RESPONSE_DELAY = {
    (0,  7):  (0,   0),
    (7,  9):  (20,  90),
    (9,  12): (2,   20),
    (12, 14): (5,   40),
    (14, 18): (1,   15),
    (18, 20): (5,   30),
    (20, 23): (1,   10),
    (23, 24): (10,  60),
}

# Always online mode - delay between 5 and 60 seconds only
ALWAYS_ONLINE_DELAY = (5, 60)


def _get_slot(hour: int) -> tuple:
    for start, end, prob in SCHEDULE:
        if start <= hour < end:
            return (start, end, prob)
    return (0, 24, 0.5)


def should_respond(always_online: bool = False) -> bool:
    if always_online:
        return True
    hour = datetime.now().hour
    _, _, probability = _get_slot(hour)
    return random.random() < probability


async def activity_delay(always_online: bool = False):
    import asyncio
    hour = datetime.now().hour

    if always_online:
        delay_seconds = random.uniform(
            ALWAYS_ONLINE_DELAY[0],
            ALWAYS_ONLINE_DELAY[1],
        )
        print(f"[ACTIVITY] Mod always online - raspund in {delay_seconds:.0f}s")
        await asyncio.sleep(delay_seconds)
        return

    for (start, end), (min_m, max_m) in RESPONSE_DELAY.items():
        if start <= hour < end:
            if min_m == 0 and max_m == 0:
                return
            delay_seconds = random.uniform(min_m * 60, max_m * 60)
            respond_at = datetime.now().replace(microsecond=0)
            minutes = int(delay_seconds // 60)
            seconds = int(delay_seconds % 60)

            if minutes > 0:
                print(f"[ACTIVITY] Raspund in {minutes}min {seconds}s (ora {hour}:xx)")
            else:
                print(f"[ACTIVITY] Raspund in {seconds}s (ora {hour}:xx)")

            await asyncio.sleep(delay_seconds)
            print(f"[ACTIVITY] Trimit raspunsul acum.")
            return

    await asyncio.sleep(random.uniform(60, 300))
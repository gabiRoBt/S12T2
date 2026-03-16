import discord
from core.cohere_client import generate_reply, extract_profile_data
from core.profile_db import get_profile, update_profile, profile_to_context, init_db
from logger import log

# Active demo sessions: { user_id: { "personality": str, "history": [...] } }
demo_sessions: dict[int, dict] = {}


async def handle_dm_message(message: discord.Message):
    """Process a DM message if the user has an active demo session."""
    user_id = message.author.id
    if user_id not in demo_sessions:
        return

    session = demo_sessions[user_id]
    personality = session["personality"]
    history = session["history"]

    history.append({"role": "USER", "message": message.content})

    profile = get_profile(f"demo_{user_id}", "demo")
    profile_context = profile_to_context(profile)

    async with message.channel.typing():
        reply = await generate_reply(history, personality_key=personality, profile_context=profile_context)
        new_data = await extract_profile_data(history)
        if new_data:
            update_profile(f"demo_{user_id}", "demo", new_data)

    if reply:
        history.append({"role": "CHATBOT", "message": reply})
        await message.channel.send(reply)
    else:
        await message.channel.send("*(eroare la generarea raspunsului)*")


def start_session(user_id: int, personality: str):
    demo_sessions[user_id] = {"personality": personality, "history": []}
    log.info(f"[DEMO] Sesiune pornita pentru user {user_id} cu personalitatea {personality}")


def stop_session(user_id: int) -> bool:
    if user_id in demo_sessions:
        demo_sessions.pop(user_id)
        log.info(f"[DEMO] Sesiune oprita pentru user {user_id}")
        return True
    return False


def has_session(user_id: int) -> bool:
    return user_id in demo_sessions

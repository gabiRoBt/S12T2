import httpx
from config import COHERE_API_KEY, COHERE_MODEL
from personalities import get_personality


COHERE_URL = "https://api.cohere.ai/v1/chat"


async def generate_reply(
    conversation_history: list[dict],
    personality_key: str = "iubita",
) -> str:
    """
    Send conversation history to Cohere and get a reply.

    conversation_history format:
        [{"role": "USER", "message": "..."}, {"role": "CHATBOT", "message": "..."}, ...]
    """
    personality = get_personality(personality_key)
    system_prompt = personality["prompt"]

    if not conversation_history:
        return ""

    # Last message is the one we need to reply to
    last_message = conversation_history[-1]["message"]
    chat_history = conversation_history[:-1]

    payload = {
        "model": COHERE_MODEL,
        "message": last_message,
        "chat_history": chat_history,
        "preamble": system_prompt,
        "temperature": 0.8,
    }

    headers = {
        "Authorization": f"Bearer {COHERE_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(COHERE_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("text", "").strip()

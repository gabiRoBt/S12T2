import json
import httpx
from config import COHERE_API_KEY, COHERE_MODEL
from personalities import get_personality
from logger import log

COHERE_URL = "https://api.cohere.ai/v1/chat"

EXTRACT_PROMPT = """
You are an information extraction system.
Analyze the conversation below and extract ONLY information the USER explicitly mentioned about themselves.
Return ONLY valid JSON, no extra text, no markdown, no explanations.

Possible fields (include only if explicitly mentioned):
- nume (name)
- varsta (age)
- oras (city)
- job
- relatii (relationship status)
- interese (hobbies, interests)
- familie (family members)
- stare (emotional state)

If no new information found, return: {}

Example valid output:
{"nume": "Andrei", "oras": "Cluj", "job": "programmer"}
"""


async def generate_reply(
    conversation_history: list[dict],
    personality_key: str = "iubita",
    profile_context: str = "",
) -> str:
    personality = get_personality(personality_key)
    system_prompt = personality["prompt"]

    if profile_context:
        system_prompt = f"{system_prompt}\n\n{profile_context}"

    if not conversation_history:
        return ""

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


async def extract_profile_data(conversation_history: list[dict]) -> dict:
    if not conversation_history:
        return {}

    convo_text = "\n".join(
        [f"{msg['role']}: {msg['message']}" for msg in conversation_history]
    )

    payload = {
        "model": COHERE_MODEL,
        "message": f"Conversation:\n{convo_text}",
        "preamble": EXTRACT_PROMPT,
        "temperature": 0.1,
    }

    headers = {
        "Authorization": f"Bearer {COHERE_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(COHERE_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            raw = data.get("text", "").strip()

        raw = raw.replace("```json", "").replace("```", "").strip()
        extracted = json.loads(raw)
        if isinstance(extracted, dict):
            return extracted
    except Exception as e:
        log.warning(f"[COHERE] Profile extraction failed: {e}")

    return {}

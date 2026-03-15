import json
import httpx
from config import COHERE_API_KEY, COHERE_MODEL
from personalities import get_personality


COHERE_URL = "https://api.cohere.ai/v1/chat"

EXTRACT_PROMPT = """
Esti un sistem de extragere a informatiilor. 
Analizeaza conversatia de mai jos si extrage DOAR informatiile pe care persoana (USER) le-a mentionat explicit despre ea insasi.
Returneaza DOAR un JSON valid, fara text suplimentar, fara markdown, fara explicatii.

Campuri posibile (include-le doar daca sunt mentionate explicit):
- nume
- varsta
- oras
- job
- relatii (are iubit/iubita, casatorit, singur etc.)
- interese (hobby-uri, pasiuni)
- familie (frati, parinti, copii)
- stare (cum se simte emotional)

Daca nu gasesti nicio informatie noua, returneaza: {}

Exemplu output valid:
{"nume": "Andrei", "oras": "Cluj", "job": "programator"}
"""


async def generate_reply(
    conversation_history: list[dict],
    personality_key: str = "iubita",
    profile_context: str = "",
) -> str:
    """
    Send conversation history to Cohere and get a reply.

    conversation_history format:
        [{"role": "USER", "message": "..."}, {"role": "CHATBOT", "message": "..."}, ...]
    """
    personality = get_personality(personality_key)
    system_prompt = personality["prompt"]

    # Inject profile context into preamble if available
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
    """
    Send conversation to Cohere and extract profile information.
    Returns a dict with any found fields, or empty dict if nothing found.
    """
    if not conversation_history:
        return {}

    # Format conversation as plain text for extraction
    convo_text = "\n".join(
        [f"{msg['role']}: {msg['message']}" for msg in conversation_history]
    )

    payload = {
        "model": COHERE_MODEL,
        "message": f"Conversatie:\n{convo_text}",
        "preamble": EXTRACT_PROMPT,
        "temperature": 0.1,  # Low temperature for consistent JSON output
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

        # Clean up in case model adds markdown fences
        raw = raw.replace("```json", "").replace("```", "").strip()

        extracted = json.loads(raw)
        if isinstance(extracted, dict):
            return extracted

    except Exception as e:
        print(f"[COHERE] Profile extraction failed: {e}")

    return {}
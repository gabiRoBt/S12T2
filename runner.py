import asyncio
from browser import BrowserSession
from cohere_client import generate_reply
from config import FB_EMAIL, FB_PASSWORD, IG_USERNAME, IG_PASSWORD


# Shared browser session across all accounts in a single run
_session: BrowserSession | None = None


async def _get_session() -> BrowserSession:
    global _session
    if _session is None:
        _session = BrowserSession()
        await _session.start()

        if FB_EMAIL and FB_PASSWORD:
            try:
                await _session.login_facebook()
            except Exception as e:
                print(f"[RUNNER] Facebook login failed: {e}")

        if IG_USERNAME and IG_PASSWORD:
            try:
                await _session.login_instagram()
            except Exception as e:
                print(f"[RUNNER] Instagram login failed: {e}")

    return _session


async def _process_account(session: BrowserSession, account: dict) -> dict:
    """
    Process a single account:
    1. Read conversation
    2. Generate reply via Cohere
    3. Send reply
    """
    platform = account["platform"].lower()
    account_id = account["id"]
    personality = account.get("personality", "iubita")

    result = {"id": account_id, "platform": platform, "success": False, "detail": ""}

    try:
        # 1. Read conversation
        if platform == "facebook":
            history = await session.get_facebook_conversation(account_id)
        elif platform == "instagram":
            history = await session.get_instagram_conversation(account_id)
        else:
            result["detail"] = f"Platform necunoscuta: {platform}"
            return result

        if not history:
            result["detail"] = "Nu am gasit mesaje in conversatie."
            return result

        # Only process if the last message is from the other person
        if history[-1]["role"] == "CHATBOT":
            result["success"] = True
            result["detail"] = "Ultimul mesaj este al nostru, asteptam raspuns."
            return result

        # 2. Generate reply
        reply = await generate_reply(history, personality_key=personality)
        if not reply:
            result["detail"] = "Cohere nu a returnat un raspuns."
            return result

        # 3. Send reply
        if platform == "facebook":
            await session.send_facebook_message(account_id, reply)
        elif platform == "instagram":
            await session.send_instagram_message(account_id, reply)

        result["success"] = True
        result["detail"] = f"Trimis: {reply[:60]}..."

    except Exception as e:
        result["detail"] = str(e)

    return result


async def run_all_accounts(accounts: list[dict]) -> list[dict]:
    """
    Run the bot for all provided accounts sequentially.
    Sequential (not parallel) to avoid detection.
    """
    session = await _get_session()
    results = []

    for account in accounts:
        print(f"[RUNNER] Processing {account['platform']} | {account['id']} | {account.get('personality')}")
        result = await _process_account(session, account)
        results.append(result)
        # Small pause between accounts
        await asyncio.sleep(2)

    return results


async def cleanup():
    """Call this when shutting down to close the browser."""
    global _session
    if _session:
        await _session.stop()
        _session = None

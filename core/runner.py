import asyncio
import random
from browser.session import BrowserSession
from core.cohere_client import generate_reply, extract_profile_data
from core.profile_db import get_profile, update_profile, profile_to_context
from core.activity import should_respond, activity_delay
from logger import log

_session: BrowserSession | None = None


async def _get_session(platform: str) -> BrowserSession:
    global _session
    if _session is None:
        _session = BrowserSession()
        await _session.start()

    if platform == "facebook":
        await _session.init_facebook()
    elif platform == "instagram":
        await _session.init_instagram()

    return _session


async def _process_account(session: BrowserSession, account: dict, always_online: bool = False) -> dict:
    platform = account["platform"].lower()
    account_id = account["id"]
    personality = account.get("personality", "iubita")

    result = {"id": account_id, "platform": platform, "success": False, "detail": ""}

    try:
        if not should_respond(always_online=always_online):
            log.info(f"[RUNNER] {account_id} - in afara programului, skip.")
            result["success"] = True
            result["detail"] = "In afara programului de activitate."
            return result

        log.info(f"[RUNNER] {account_id} - citesc conversatia...")
        if platform == "facebook":
            history = await session.facebook.get_conversation(account_id)
        elif platform == "instagram":
            history = await session.instagram.get_conversation(account_id)
        else:
            result["detail"] = f"Platform necunoscuta: {platform}"
            return result

        if not history:
            log.info(f"[RUNNER] {account_id} - niciun mesaj gasit.")
            result["detail"] = "Nu am gasit mesaje in conversatie."
            return result

        if history[-1]["role"] == "CHATBOT":
            log.info(f"[RUNNER] {account_id} - ultimul mesaj e al nostru, asteptam raspuns.")
            result["success"] = True
            result["detail"] = "Ultimul mesaj este al nostru."
            return result

        profile = get_profile(account_id, platform)
        profile_context = profile_to_context(profile)

        last_incoming = history[-1]["message"]
        log.info(f"[RUNNER] {account_id} - mesaj primit: \"{last_incoming[:60]}\"")

        await activity_delay(always_online=always_online)

        log.info(f"[RUNNER] {account_id} - generez raspunsul...")
        reply = await generate_reply(history, personality_key=personality, profile_context=profile_context)
        if not reply:
            result["detail"] = "Cohere nu a returnat un raspuns."
            return result

        log.info(f"[RUNNER] {account_id} - trimit: \"{reply[:60]}\"")

        if platform == "facebook":
            await session.facebook.send_message(account_id, reply, last_incoming=last_incoming)
        elif platform == "instagram":
            await session.instagram.send_message(account_id, reply, last_incoming=last_incoming)

        log.info(f"[RUNNER] {account_id} - mesaj trimis cu succes.")

        new_data = await extract_profile_data(history)
        if new_data:
            update_profile(account_id, platform, new_data)

        result["success"] = True
        result["detail"] = f"Trimis: {reply[:60]}..."

    except Exception as e:
        log.error(f"[RUNNER] {account_id} - eroare: {e}")
        result["detail"] = str(e)

    return result


async def run_all_accounts(accounts: list[dict], always_online: bool = False) -> list[dict]:
    results = []
    mode = "ALWAYS ONLINE" if always_online else "NORMAL"
    log.info(f"[RUNNER] Pornesc procesarea a {len(accounts)} conturi - mod {mode}")

    for account in accounts:
        log.info(f"[RUNNER] --- {account['platform'].upper()} | {account['id']} | {account.get('personality')} ---")
        session = await _get_session(platform=account["platform"])
        result = await _process_account(session, account, always_online=always_online)
        results.append(result)
        await asyncio.sleep(random.uniform(2, 5))

    log.info("[RUNNER] Procesare completa.")
    return results


async def auto_watch_loop(accounts: list[dict], always_online: bool = True):
    """
    Start inbox watchers and process new messages as they arrive.
    Runs indefinitely until cancelled.
    accounts: list of dicts with id, platform, personality
    """
    # Build a lookup: platform+id -> personality
    account_map = {
        f"{acc['platform']}:{acc['id']}": acc.get("personality", "iubita")
        for acc in accounts
    }

    # Initialize sessions for all needed platforms
    platforms = set(acc["platform"] for acc in accounts)
    for platform in platforms:
        session = await _get_session(platform)

    await _session.start_watching()
    log.info("[WATCHER] Auto-watch pornit. Ascult pentru mesaje noi...")

    while True:
        event = await _session.watcher.next_event()
        platform = event["platform"]
        conv_id = event["id"]

        key = f"{platform}:{conv_id}"
        personality = account_map.get(key, "iubita")

        account = {"id": conv_id, "platform": platform, "personality": personality}
        log.info(f"[WATCHER] Procesez {platform} | {conv_id} | {personality}")

        session = await _get_session(platform)
        await _process_account(session, account, always_online=always_online)


async def cleanup():
    global _session
    if _session:
        await _session.stop()
        _session = None
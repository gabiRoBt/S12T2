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
            log.info(f"[RUNNER] {account_id} - outside schedule, skip.")
            result["success"] = True
            result["detail"] = "Outside activity schedule."
            return result

        log.info(f"[RUNNER] {account_id} - reading conversation...")
        if platform == "facebook":
            history = await session.facebook.get_conversation(account_id)
        elif platform == "instagram":
            history = await session.instagram.get_conversation(account_id)
        else:
            result["detail"] = f"Unknown platform: {platform}"
            return result

        if not history:
            log.info(f"[RUNNER] {account_id} - no messages found.")
            result["detail"] = "No messages found in conversation."
            return result

        if history[-1]["role"] == "CHATBOT":
            log.info(f"[RUNNER] {account_id} - last message is ours, waiting for reply.")
            result["success"] = True
            result["detail"] = "Last message is ours."
            return result

        profile = get_profile(account_id, platform)
        profile_context = profile_to_context(profile)

        last_incoming = history[-1]["message"]
        log.info(f"[RUNNER] {account_id} - received message: \"{last_incoming[:60]}\"")

        await activity_delay(always_online=always_online)

        log.info(f"[RUNNER] {account_id} - generating reply...")
        reply = await generate_reply(history, personality_key=personality, profile_context=profile_context)
        if not reply:
            result["detail"] = "Cohere did not return a response."
            return result

        log.info(f"[RUNNER] {account_id} - sending: \"{reply[:60]}\"")

        if platform == "facebook":
            await session.facebook.send_message(account_id, reply, last_incoming=last_incoming)
        elif platform == "instagram":
            await session.instagram.send_message(account_id, reply, last_incoming=last_incoming)

        log.info(f"[RUNNER] {account_id} - message sent successfully.")

        new_data = await extract_profile_data(history)
        if new_data:
            update_profile(account_id, platform, new_data)

        result["success"] = True
        result["detail"] = f"Sent: {reply[:60]}..."

    except Exception as e:
        log.error(f"[RUNNER] {account_id} - error: {e}")
        result["detail"] = str(e)

    return result

async def run_all_accounts(accounts: list[dict], always_online: bool = False) -> list[dict]:
    """Processes a specific list of accounts sequentially."""
    results = []
    mode = "ALWAYS ONLINE" if always_online else "NORMAL"
    log.info(f"[RUNNER] Starting processing for {len(accounts)} accounts - mode {mode}")

    for account in accounts:
        log.info(f"[RUNNER] --- {account['platform'].upper()} | {account['id']} | {account.get('personality')} ---")
        session = await _get_session(platform=account["platform"])
        result = await _process_account(session, account, always_online=always_online)
        results.append(result)
        await asyncio.sleep(random.uniform(2, 5))

    log.info("[RUNNER] Processing complete.")
    return results

async def auto_watch_loop(always_online: bool = True):
    """
    Start inbox watchers and process new messages as they arrive globally.
    """
    global _session
    
    # Initialize sessions for both platforms
    await _get_session("facebook")
    await _get_session("instagram")

    await _session.start_watching()
    log.info("[WATCHER] Auto-watch started. Listening for new messages...")

    while True:
        event = await _session.watcher.next_event()
        platform = event["platform"]
        conv_id = event["id"]

        # Default personality for incoming unknown IDs
        personality = "iubita"

        account = {"id": conv_id, "platform": platform, "personality": personality}
        log.info(f"[WATCHER] Processing {platform} | {conv_id} | {personality}")

        session = await _get_session(platform)
        await _process_account(session, account, always_online=always_online)

async def cleanup():
    global _session
    if _session:
        await _session.stop()
        _session = None
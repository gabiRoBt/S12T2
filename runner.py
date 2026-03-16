from logger import log
import asyncio
import random
from browser import BrowserSession
from cohere_client import generate_reply, extract_profile_data
from profile_db import get_profile, update_profile, profile_to_context
from activity import should_respond, activity_delay
from config import FB_EMAIL, FB_PASSWORD, IG_USERNAME, IG_PASSWORD


_session: BrowserSession | None = None


async def _get_session(platform: str = "facebook") -> BrowserSession:
    global _session
    if _session is None:
        _session = BrowserSession()
        await _session.start()

    if platform == "facebook" and _session.fb_context is None:
        if FB_EMAIL and FB_PASSWORD:
            try:
                log.info("[RUNNER] Pornesc sesiunea Facebook...")
                await _session.login_facebook()
            except Exception as e:
                log.info(f"[RUNNER] Facebook login failed: {e}")
        else:
            log.info("[RUNNER] FB_EMAIL sau FB_PASSWORD lipsa din .env, skip Facebook.")

    elif platform == "instagram" and _session.ig_context is None:
        if IG_USERNAME and IG_PASSWORD:
            try:
                log.info("[RUNNER] Pornesc sesiunea Instagram...")
                await _session.login_instagram()
            except Exception as e:
                log.info(f"[RUNNER] Instagram login failed: {e}")
        else:
            log.info("[RUNNER] IG_USERNAME sau IG_PASSWORD lipsa din .env, skip Instagram.")

    return _session


async def _process_account(current_session: BrowserSession, account: dict, always_online: bool = False) -> dict:
    platform = account["platform"].lower()
    account_id = account["id"]
    personality = account.get("personality", "iubita")

    result = {"id": account_id, "platform": platform, "success": False, "detail": ""}

    try:
        # 1. Check activity schedule
        if not should_respond(always_online=always_online):
            log.info(f"[RUNNER] {account_id} - in afara programului, skip.")
            result["success"] = True
            result["detail"] = "In afara programului de activitate, skip."
            return result

        # 2. Read conversation
        log.info(f"[RUNNER] {account_id} - citesc conversatia...")
        if platform == "facebook":
            history = await current_session.get_facebook_conversation(account_id)
        elif platform == "instagram":
            history = await current_session.get_instagram_conversation(account_id)
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
            result["detail"] = "Ultimul mesaj este al nostru, asteptam raspuns."
            return result

        # 3. Load profile
        profile = get_profile(account_id, platform)
        profile_context = profile_to_context(profile)
        if profile_context:
            log.info(f"[RUNNER] {account_id} - profil incarcat: {list(profile.keys())}")

        # 4. Wait before responding
        last_incoming = history[-1]["message"]
        log.info(f"[RUNNER] {account_id} - mesaj primit: \"{last_incoming[:50]}\"")
        await activity_delay(always_online=always_online)

        # 5. Generate reply
        log.info(f"[RUNNER] {account_id} - generez raspunsul...")
        reply = await generate_reply(
            history,
            personality_key=personality,
            profile_context=profile_context,
        )
        if not reply:
            result["detail"] = "Cohere nu a returnat un raspuns."
            return result

        log.info(f"[RUNNER] {account_id} - trimit: \"{reply[:60]}\"")

        # 6. Send reply
        if platform == "facebook":
            await current_session.send_facebook_message(account_id, reply, last_incoming=last_incoming)
        elif platform == "instagram":
            await current_session.send_instagram_message(account_id, reply, last_incoming=last_incoming)

        log.info(f"[RUNNER] {account_id} - mesaj trimis cu succes.")

        # 7. Extract and save profile data
        new_data = await extract_profile_data(history)
        if new_data:
            update_profile(account_id, platform, new_data)
            log.info(f"[RUNNER] {account_id} - profil actualizat: {new_data}")

        result["success"] = True
        result["detail"] = f"Trimis: {reply[:60]}..."

    except Exception as e:
        log.info(f"[RUNNER] {account_id} - eroare: {e}")
        result["detail"] = str(e)

    return result


async def run_all_accounts(accounts: list[dict], always_online: bool = False) -> list[dict]:
    results = []

    mode = "ALWAYS ONLINE" if always_online else "NORMAL"
    log.info(f"[RUNNER] Pornesc procesarea a {len(accounts)} conturi - mod {mode}")

    for account in accounts:
        log.info(f"[RUNNER] --- {account['platform'].upper()} | {account['id']} | {account.get('personality')} ---")
        current_session = await _get_session(platform=account["platform"])
        result = await _process_account(current_session, account, always_online=always_online)
        results.append(result)
        await asyncio.sleep(random.uniform(3, 8))

    log.info(f"[RUNNER] Procesare completa.")
    return results


async def cleanup():
    global _session
    if _session:
        await _session.stop()
        _session = None
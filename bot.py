from logger import log
import discord
from discord.ext import commands
from discord import app_commands

from config import (
    DISCORD_TOKEN,
    DISCORD_GUILD_ID,
    CHANNEL_FACEBOOK_IDS,
    CHANNEL_INSTAGRAM_IDS,
)
from personalities import list_personalities, get_personality
from runner import run_all_accounts
from cohere_client import generate_reply, extract_profile_data
from profile_db import get_profile, update_profile, profile_to_context, init_db


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
guild = discord.Object(id=DISCORD_GUILD_ID)

# demo_sessions stores active demo conversations per user
# { user_id: { "personality": str, "history": [...] } }
demo_sessions: dict[int, dict] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def read_ids_from_channel(guild_obj: discord.Guild, channel_name: str) -> list[dict]:
    channel = discord.utils.get(guild_obj.text_channels, name=channel_name)
    if not channel:
        return []

    entries = []
    platform = "facebook" if channel_name == CHANNEL_FACEBOOK_IDS else "instagram"

    async for message in channel.history(limit=100):
        for line in message.content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            account_id = parts[0]
            personality = parts[1] if len(parts) > 1 else "iubita"
            entries.append({
                "id": account_id,
                "platform": platform,
                "personality": personality,
            })

    return entries


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

@bot.event
async def on_ready():
    init_db()
    await bot.tree.sync(guild=guild)
    log.info(f"[BOT] Logged in as {bot.user} | Guild: {DISCORD_GUILD_ID}")


@bot.event
async def on_message(message: discord.Message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Only handle DMs
    if not isinstance(message.channel, discord.DMChannel):
        await bot.process_commands(message)
        return

    user_id = message.author.id

    # Check if this user has an active demo session
    if user_id not in demo_sessions:
        await bot.process_commands(message)
        return

    session = demo_sessions[user_id]
    personality = session["personality"]
    history = session["history"]

    # Add user message to history
    history.append({"role": "USER", "message": message.content})

    # Load profile for demo user
    profile = get_profile(f"demo_{user_id}", "demo")
    profile_context = profile_to_context(profile)

    async with message.channel.typing():
        reply = await generate_reply(
            history,
            personality_key=personality,
            profile_context=profile_context,
        )

        # Extract and save profile info
        new_data = await extract_profile_data(history)
        if new_data:
            update_profile(f"demo_{user_id}", "demo", new_data)

    if reply:
        history.append({"role": "CHATBOT", "message": reply})
        await message.channel.send(reply)
    else:
        await message.channel.send("*(eroare la generarea raspunsului)*")

    await bot.process_commands(message)


# ---------------------------------------------------------------------------
# Slash commands
# ---------------------------------------------------------------------------

@bot.tree.command(
    name="run",
    description="Porneste botul pentru toate conturile din canale.",
    guild=guild,
)
async def run_command(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    guild_obj = bot.get_guild(DISCORD_GUILD_ID)
    fb_accounts = await read_ids_from_channel(guild_obj, CHANNEL_FACEBOOK_IDS)
    ig_accounts = await read_ids_from_channel(guild_obj, CHANNEL_INSTAGRAM_IDS)
    all_accounts = fb_accounts + ig_accounts

    if not all_accounts:
        await interaction.followup.send(
            "Nu am gasit niciun cont in canale. "
            f"Adauga ID-uri in `#{CHANNEL_FACEBOOK_IDS}` sau `#{CHANNEL_INSTAGRAM_IDS}`."
        )
        return

    summary_lines = [f"**Conturi gasite:** {len(all_accounts)}"]
    for acc in all_accounts:
        summary_lines.append(f"- [{acc['platform'].upper()}] `{acc['id']}` | _{acc['personality']}_")

    summary_lines.append("\nPornesc procesarea...")
    await interaction.followup.send("\n".join(summary_lines))

    results = await run_all_accounts(all_accounts)

    result_lines = ["\n**Rezultate:**"]
    for r in results:
        status = "OK" if r["success"] else "EROARE"
        result_lines.append(f"- `{r['id']}` [{r['platform']}] -> {status}: {r['detail']}")

    await interaction.followup.send("\n".join(result_lines))


@bot.tree.command(
    name="personalitati",
    description="Afiseaza lista de personalitati disponibile.",
    guild=guild,
)
async def personalitati_command(interaction: discord.Interaction):
    names = list_personalities()
    lines = ["**Personalitati disponibile:**"]
    for name in names:
        lines.append(f"- `{name}`")
    lines.append("\nFoloseste formatul `<id> | <personalitate>` in canale.")
    await interaction.response.send_message("\n".join(lines))


@bot.tree.command(
    name="test",
    description="Testeaza un singur cont.",
    guild=guild,
)
@app_commands.describe(
    platform="facebook sau instagram",
    account_id="ID-ul contului",
    personality="Personalitatea de folosit (default: iubita)",
)
async def test_command(
    interaction: discord.Interaction,
    platform: str,
    account_id: str,
    personality: str = "iubita",
):
    await interaction.response.defer(thinking=True)

    accounts = [{"id": account_id, "platform": platform, "personality": personality}]
    results = await run_all_accounts(accounts)

    r = results[0]
    status = "OK" if r["success"] else "EROARE"
    await interaction.followup.send(
        f"[{platform.upper()}] `{account_id}` | _{personality}_ -> **{status}**: {r['detail']}"
    )


@bot.tree.command(
    name="alwaysonline",
    description="Ruleaza botul in mod always online - raspunde in sub 1 minut.",
    guild=guild,
)
async def alwaysonline_command(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    guild_obj = bot.get_guild(DISCORD_GUILD_ID)
    fb_accounts = await read_ids_from_channel(guild_obj, CHANNEL_FACEBOOK_IDS)
    ig_accounts = await read_ids_from_channel(guild_obj, CHANNEL_INSTAGRAM_IDS)
    all_accounts = fb_accounts + ig_accounts

    if not all_accounts:
        await interaction.followup.send(
            "Nu am gasit niciun cont in canale. "
            f"Adauga ID-uri in `#{CHANNEL_FACEBOOK_IDS}` sau `#{CHANNEL_INSTAGRAM_IDS}`."
        )
        return

    summary_lines = [f"**[ALWAYS ONLINE] Conturi gasite:** {len(all_accounts)}"]
    for acc in all_accounts:
        summary_lines.append(f"- [{acc['platform'].upper()}] `{acc['id']}` | _{acc['personality']}_")

    summary_lines.append("\nMod always online activ - raspund in sub 1 minut...")
    await interaction.followup.send("\n".join(summary_lines))

    results = await run_all_accounts(all_accounts, always_online=True)

    result_lines = ["\n**Rezultate:**"]
    for r in results:
        status = "OK" if r["success"] else "EROARE"
        result_lines.append(f"- `{r['id']}` [{r['platform']}] -> {status}: {r['detail']}")

    await interaction.followup.send("\n".join(result_lines))


@bot.tree.command(
    name="demo",
    description="Porneste o conversatie de test in DM cu botul.",
    guild=guild,
)
@app_commands.describe(
    personality="Personalitatea de folosit (default: iubita)",
)
async def demo_command(
    interaction: discord.Interaction,
    personality: str = "iubita",
):
    user_id = interaction.user.id
    p = get_personality(personality)

    # Start or reset session
    demo_sessions[user_id] = {
        "personality": personality,
        "history": [],
    }

    await interaction.response.send_message(
        f"Sesiune demo pornita cu personalitatea **{p['name']}**.\n"
        f"Ti-am trimis un DM — scrie acolo pentru a conversa.\n"
        f"Foloseste `/stopdemo` pentru a opri.",
        ephemeral=True,
    )

    # Send opening message in DM
    dm = await interaction.user.create_dm()
    await dm.send(
        f"Salut! Sunt **{p['name']}**. Scrie-mi orice, sunt aici! 👋\n"
        f"*(demo activ — `/stoptdemo` pentru a opri)*"
    )


@bot.tree.command(
    name="stoptdemo",
    description="Opreste sesiunea demo activa.",
    guild=guild,
)
async def stopdemo_command(interaction: discord.Interaction):
    user_id = interaction.user.id

    if user_id in demo_sessions:
        demo_sessions.pop(user_id)
        await interaction.response.send_message(
            "Sesiune demo oprita. Profilul tau de test a fost salvat in DB.",
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            "Nu ai nicio sesiune demo activa.",
            ephemeral=True,
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def create_bot() -> commands.Bot:
    """Return the bot instance for use with asyncio.run in main.py."""
    return bot
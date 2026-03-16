import discord
from discord import app_commands
from discord.ext import commands

from config import DISCORD_GUILD_ID, CHANNEL_FACEBOOK_IDS, CHANNEL_INSTAGRAM_IDS
from personalities import list_personalities, get_personality
from core.runner import run_all_accounts
from bot.helpers import read_ids_from_channel
from bot import demo as demo_module
from core.profile_db import init_db
from logger import log

guild = discord.Object(id=DISCORD_GUILD_ID)


def setup(bot: commands.Bot):
    """Register all slash commands and events on the bot."""

    @bot.event
    async def on_ready():
        init_db()
        await bot.tree.sync(guild=guild)
        log.info(f"[BOT] Logat ca {bot.user} | Guild: {DISCORD_GUILD_ID}")

    @bot.event
    async def on_message(message: discord.Message):
        if message.author == bot.user:
            return
        if isinstance(message.channel, discord.DMChannel):
            await demo_module.handle_dm_message(message)
        await bot.process_commands(message)

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
                f"Nu am gasit niciun cont. Adauga ID-uri in `#{CHANNEL_FACEBOOK_IDS}` sau `#{CHANNEL_INSTAGRAM_IDS}`."
            )
            return

        lines = [f"**Conturi gasite:** {len(all_accounts)}"]
        for acc in all_accounts:
            lines.append(f"- [{acc['platform'].upper()}] `{acc['id']}` | _{acc['personality']}_")
        lines.append("\nPornesc procesarea...")
        await interaction.followup.send("\n".join(lines))

        results = await run_all_accounts(all_accounts)
        result_lines = ["\n**Rezultate:**"]
        for r in results:
            status = "OK" if r["success"] else "EROARE"
            result_lines.append(f"- `{r['id']}` [{r['platform']}] -> {status}: {r['detail']}")
        await interaction.followup.send("\n".join(result_lines))

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
            await interaction.followup.send("Nu am gasit niciun cont in canale.")
            return

        lines = [f"**[ALWAYS ONLINE] Conturi gasite:** {len(all_accounts)}"]
        for acc in all_accounts:
            lines.append(f"- [{acc['platform'].upper()}] `{acc['id']}` | _{acc['personality']}_")
        lines.append("\nMod always online activ - raspund in sub 1 minut...")
        await interaction.followup.send("\n".join(lines))

        results = await run_all_accounts(all_accounts, always_online=True)
        result_lines = ["\n**Rezultate:**"]
        for r in results:
            status = "OK" if r["success"] else "EROARE"
            result_lines.append(f"- `{r['id']}` [{r['platform']}] -> {status}: {r['detail']}")
        await interaction.followup.send("\n".join(result_lines))

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
        results = await run_all_accounts(
            [{"id": account_id, "platform": platform, "personality": personality}]
        )
        r = results[0]
        status = "OK" if r["success"] else "EROARE"
        await interaction.followup.send(
            f"[{platform.upper()}] `{account_id}` | _{personality}_ -> **{status}**: {r['detail']}"
        )

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
        name="demo",
        description="Porneste o conversatie de test in DM cu botul.",
        guild=guild,
    )
    @app_commands.describe(personality="Personalitatea de folosit (default: iubita)")
    async def demo_command(interaction: discord.Interaction, personality: str = "iubita"):
        user_id = interaction.user.id
        p = get_personality(personality)
        demo_module.start_session(user_id, personality)

        await interaction.response.send_message(
            f"Sesiune demo pornita cu personalitatea **{p['name']}**.\n"
            "Ti-am trimis un DM - scrie acolo pentru a conversa.\n"
            "Foloseste `/stopdemo` pentru a opri.",
            ephemeral=True,
        )
        dm = await interaction.user.create_dm()
        await dm.send(f"Salut! Sunt **{p['name']}**. Scrie-mi orice! 👋")

    @bot.tree.command(
        name="stopdemo",
        description="Opreste sesiunea demo activa.",
        guild=guild,
    )
    async def stopdemo_command(interaction: discord.Interaction):
        if demo_module.stop_session(interaction.user.id):
            await interaction.response.send_message(
                "Sesiune demo oprita. Profilul tau de test a fost salvat.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "Nu ai nicio sesiune demo activa.",
                ephemeral=True,
            )

import asyncio
import discord
from discord import app_commands
from discord.ext import commands

from config import DISCORD_GUILD_ID, CHANNEL_FACEBOOK_IDS, CHANNEL_INSTAGRAM_IDS
from personalities import list_personalities, get_personality
from core.runner import run_all_accounts, auto_watch_loop
from bot.channel_reader import read_ids_from_channel
from bot import demo as demo_module
from core.profile_db import init_db
from logger import log

guild = discord.Object(id=DISCORD_GUILD_ID)

_watch_task: asyncio.Task | None = None


def setup(bot: commands.Bot):
    """Register all slash commands and events on the bot."""

    @bot.event
    async def on_ready():
        init_db()
        await bot.tree.sync(guild=guild)
        log.info(f"[BOT] Logged in as {bot.user} | Guild: {DISCORD_GUILD_ID}")

    @bot.event
    async def on_message(message: discord.Message):
        if message.author == bot.user:
            return
        if isinstance(message.channel, discord.DMChannel):
            await demo_module.handle_dm_message(message)
        await bot.process_commands(message)

    @bot.tree.command(
        name="slowreader",
        description="Starts the bot for all accounts found in the pending channels.",
        guild=guild,
    )
    async def slowreader_command(interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        guild_obj = bot.get_guild(DISCORD_GUILD_ID)
        fb_accounts = await read_ids_from_channel(guild_obj, CHANNEL_FACEBOOK_IDS)
        ig_accounts = await read_ids_from_channel(guild_obj, CHANNEL_INSTAGRAM_IDS)
        all_accounts = fb_accounts + ig_accounts

        if not all_accounts:
            await interaction.followup.send(
                f"No accounts found. Please add IDs in `#{CHANNEL_FACEBOOK_IDS}` or `#{CHANNEL_INSTAGRAM_IDS}`."
            )
            return

        lines = [f"**Accounts found:** {len(all_accounts)}"]
        for acc in all_accounts:
            lines.append(f"- [{acc['platform'].upper()}] `{acc['id']}` | _{acc['personality']}_")
        lines.append("\nStarting processing...")
        await interaction.followup.send("\n".join(lines))

        results = await run_all_accounts(all_accounts)
        result_lines = ["\n**Results:**"]
        for r in results:
            status = "OK" if r["success"] else "ERROR"
            result_lines.append(f"- `{r['id']}` [{r['platform']}] -> {status}: {r['detail']}")
        await interaction.followup.send("\n".join(result_lines))

    @bot.tree.command(
        name="alwaysonline",
        description="Runs the bot in always online mode - replies in under 1 minute.",
        guild=guild,
    )
    async def alwaysonline_command(interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        guild_obj = bot.get_guild(DISCORD_GUILD_ID)
        fb_accounts = await read_ids_from_channel(guild_obj, CHANNEL_FACEBOOK_IDS)
        ig_accounts = await read_ids_from_channel(guild_obj, CHANNEL_INSTAGRAM_IDS)
        all_accounts = fb_accounts + ig_accounts

        if not all_accounts:
            await interaction.followup.send("No accounts found in channels.")
            return

        lines = [f"**[ALWAYS ONLINE] Accounts found:** {len(all_accounts)}"]
        for acc in all_accounts:
            lines.append(f"- [{acc['platform'].upper()}] `{acc['id']}` | _{acc['personality']}_")
        lines.append("\nAlways online mode active - replying in under 1 minute...")
        await interaction.followup.send("\n".join(lines))

        results = await run_all_accounts(all_accounts, always_online=True)
        result_lines = ["\n**Results:**"]
        for r in results:
            status = "OK" if r["success"] else "ERROR"
            result_lines.append(f"- `{r['id']}` [{r['platform']}] -> {status}: {r['detail']}")
        await interaction.followup.send("\n".join(result_lines))

    @bot.tree.command(
        name="test",
        description="Tests a single specific account.",
        guild=guild,
    )
    @app_commands.describe(
        platform="facebook or instagram",
        account_id="The account ID",
        personality="The personality to use (default: iubita)",
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
        status = "OK" if r["success"] else "ERROR"
        await interaction.followup.send(
            f"[{platform.upper()}] `{account_id}` | _{personality}_ -> **{status}**: {r['detail']}"
        )

    @bot.tree.command(
        name="personalities",
        description="Displays the list of available personalities.",
        guild=guild,
    )
    async def personalities_command(interaction: discord.Interaction):
        names = list_personalities()
        lines = ["**Available personalities:**"]
        for name in names:
            lines.append(f"- `{name}`")
        lines.append("\nUse the format `<id> | <personality>` in the target channels.")
        await interaction.response.send_message("\n".join(lines))

    @bot.tree.command(
        name="demo",
        description="Starts a test conversation in DM with the bot.",
        guild=guild,
    )
    @app_commands.describe(personality="The personality to use (default: iubita)")
    async def demo_command(interaction: discord.Interaction, personality: str = "iubita"):
        user_id = interaction.user.id
        p = get_personality(personality)
        demo_module.start_session(user_id, personality)

        await interaction.response.send_message(
            f"Demo session started using the **{p['name']}** personality.\n"
            "I sent you a DM - write there to start the conversation.\n"
            "Use `/stopdemo` to stop.",
            ephemeral=True,
        )
        dm = await interaction.user.create_dm()
        await dm.send(f"Hi! I'm **{p['name']}**. Text me anything! 👋")

    @bot.tree.command(
        name="run",
        description="Starts the global auto-listening mode - replies instantly to new messages.",
        guild=guild,
    )
    @app_commands.describe(
        mod="alwaysonline = replies instantly | normal = respects the activity schedule"
    )
    @app_commands.choices(mod=[
        app_commands.Choice(name="alwaysonline", value="alwaysonline"),
        app_commands.Choice(name="normal", value="normal"),
    ])
    async def run_command(interaction: discord.Interaction, mod: str = "alwaysonline"):
        await interaction.response.defer(thinking=True)
        always_online = mod == "alwaysonline"
        mod_label = "Always Online" if always_online else "Normal (Respects schedule)"

        await interaction.followup.send(
            f"**Global Watch mode started.**\n"
            f"Mode: **{mod_label}**\n"
            "I will automatically reply to any new messages."
        )
        async def run_watch():
            try:
                await auto_watch_loop(always_online=always_online)
            except Exception as e:
                log.error(f"[WATCH] Error in watch loop: {e}")
                import traceback
                log.error(traceback.format_exc())

        global _watch_task
        _watch_task = asyncio.create_task(run_watch())

    @bot.tree.command(
        name="stop",
        description="Stops the auto-listening mode.",
        guild=guild,
    )
    async def stop_command(interaction: discord.Interaction):
        global _watch_task
        if _watch_task and not _watch_task.done():
            _watch_task.cancel()
            _watch_task = None
            from core.runner import cleanup
            await cleanup()
            await interaction.response.send_message("Watch mode stopped.", ephemeral=True)
        else:
            await interaction.response.send_message("There is no active watch mode.", ephemeral=True)

    @bot.tree.command(
        name="stopdemo",
        description="Stops the active demo session.",
        guild=guild,
    )
    async def stopdemo_command(interaction: discord.Interaction):
        if demo_module.stop_session(interaction.user.id):
            await interaction.response.send_message(
                "Demo session stopped. Your test profile was saved.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "You do not have any active demo session.",
                ephemeral=True,
            )
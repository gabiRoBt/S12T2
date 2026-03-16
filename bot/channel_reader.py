import discord
from config import CHANNEL_FACEBOOK_IDS, CHANNEL_INSTAGRAM_IDS


async def read_ids_from_channel(guild: discord.Guild, channel_name: str) -> list[dict]:
    """
    Read account IDs from a Discord channel.

    Format per line:
        <id> | <personality>
        <id>               <- uses default personality
    Lines starting with # are ignored.
    """
    channel = discord.utils.get(guild.text_channels, name=channel_name)
    if not channel:
        return []

    platform = "facebook" if channel_name == CHANNEL_FACEBOOK_IDS else "instagram"
    entries = []

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

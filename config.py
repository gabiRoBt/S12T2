import os
from dotenv import load_dotenv

load_dotenv()

# Discord
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DISCORD_GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))

# Channel names on the Discord server
CHANNEL_FACEBOOK_IDS = os.getenv("CHANNEL_FACEBOOK_IDS", "facebook-ids")
CHANNEL_INSTAGRAM_IDS = os.getenv("CHANNEL_INSTAGRAM_IDS", "instagram-ids")
CHANNEL_COMMANDS = os.getenv("CHANNEL_COMMANDS", "comenzi")

# Cohere
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")
COHERE_MODEL = os.getenv("COHERE_MODEL", "command-r-plus")

# Facebook / Instagram credentials
FB_EMAIL = os.getenv("FB_EMAIL", "")
FB_PASSWORD = os.getenv("FB_PASSWORD", "")

IG_USERNAME = os.getenv("IG_USERNAME", "")
IG_PASSWORD = os.getenv("IG_PASSWORD", "")

# Browser settings
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
BROWSER_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "30000"))  # ms

# How many messages to read from a conversation as context
CONTEXT_MESSAGE_LIMIT = int(os.getenv("CONTEXT_MESSAGE_LIMIT", "10"))

# Delay between actions to simulate human behavior (seconds)
MIN_DELAY = float(os.getenv("MIN_DELAY", "1.5"))
MAX_DELAY = float(os.getenv("MAX_DELAY", "4.0"))

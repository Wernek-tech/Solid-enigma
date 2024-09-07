import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from cogs.music import Music
from utils.ffmpeg_checker import check_ffmpeg

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Check if FFMPEG is installed
check_ffmpeg()

# Set up bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

# Initialize the bot
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot is ready and logged in as {bot.user}")

    # Sync commands for all guilds
    try:
        synced = await bot.tree.sync()  # Sync all commands
        print(f"Synced {len(synced)} command(s) globally.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

async def main():
    async with bot:
        await bot.add_cog(Music(bot))
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())

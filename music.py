import discord
from discord.ext import commands
import yt_dlp
import logging
import imageio_ffmpeg as ffmpeg
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('music_bot')

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.music_queue = []
        self.is_playing = False
        self.current_song = None
        self.voice_client = None

    async def join_voice_channel(self, interaction):
        if interaction.user.voice is None:
            await interaction.response.send_message("You are not in a voice channel!", ephemeral=True)
            return False

        voice_channel = interaction.user.voice.channel
        try:
            if self.voice_client is None:
                self.voice_client = await voice_channel.connect()
            elif self.voice_client.channel != voice_channel:
                await self.voice_client.move_to(voice_channel)
            return True
        except Exception as e:
            logger.error(f"Error joining voice channel: {e}")
            await interaction.response.send_message("Failed to join the voice channel. Please try again.", ephemeral=True)
            return False

    async def search_song(self, query):
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'default_search': 'auto'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await self.bot.loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))
            if 'entries' in info:
                return info['entries'][0]['url']
            return None

    @discord.app_commands.command(name="play", description="Play a song from a YouTube URL or search for a song by name")
    async def play_slash(self, interaction: discord.Interaction, query: str):
        if not await self.join_voice_channel(interaction):
            return

        try:
            url_pattern = re.compile(r'https?://\S+')
            if re.match(url_pattern, query):
                url = query
            else:
                url = await self.search_song(query)
                if url is None:
                    await interaction.response.send_message("No results found for the given query.", ephemeral=True)
                    return

            self.music_queue.append(url)
            await interaction.response.send_message(f"Added to the queue!")

            if not self.is_playing:
                await self.play_next_song()
        except Exception as e:
            logger.error(f"Error in play slash command: {e}")
            await interaction.response.send_message("An error occurred while trying to play the song. Please try again.", ephemeral=True)

    async def play_next_song(self):
        if not self.music_queue:
            self.is_playing = False
            self.current_song = None
            return

        self.is_playing = True
        url = self.music_queue.pop(0)
        self.current_song = url

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
            'restrictfilenames': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'auto',
            'source_address': '0.0.0.0'
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Extracting info for URL: {url}")
                info = await self.bot.loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
                url2 = info['url']
                logger.info(f"Extracted audio URL: {url2}")

                ffmpeg_path = ffmpeg.get_ffmpeg_exe()
                source = await discord.FFmpegOpusAudio.from_probe(url2, method='fallback', executable=ffmpeg_path)

                def after_playing(error):
                    if error:
                        logger.error(f"Error occurred while playing: {error}")
                    self.bot.loop.create_task(self.play_next_song())

                self.voice_client.play(source, after=after_playing)
                logger.info(f"Now playing: {url}")

        except Exception as e:
            logger.error(f"An error occurred while trying to play the song: {e}")
            self.is_playing = False
            self.current_song = None
            await self.play_next_song()

    @commands.command(name="skip", description="Skip the current song")
    async def skip(self, ctx):
        if not self.is_playing:
            await ctx.send("No song is currently playing.")
            return

        self.voice_client.stop()
        await ctx.send("Skipped the current song.")

    @commands.command(name="queue", description="Show the current music queue")
    async def queue(self, ctx):
        if not self.music_queue and not self.current_song:
            await ctx.send("The queue is empty.")
            return

        queue_list = "Current queue:\n"
        if self.current_song:
            queue_list += f"Now playing: {self.current_song}\n"
        for i, song in enumerate(self.music_queue, start=1):
            queue_list += f"{i}. {song}\n"

        await ctx.send(queue_list)

    @commands.command(name="leave", description="Leave the voice channel")
    async def leave(self, ctx):
        if self.voice_client and self.voice_client.is_connected():
            await self.voice_client.disconnect()
            self.voice_client = None
            self.is_playing = False
            self.current_song = None
            self.music_queue.clear()
            await ctx.send("Left the voice channel and cleared the queue.")
        else:
            await ctx.send("I'm not in a voice channel.")

async def setup(bot):
    await bot.add_cog(Music(bot))
    await bot.tree.sync()  # Sync commands with Discord

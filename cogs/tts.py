import re
import discord
from discord.ext import commands
import os
from gtts import gTTS
import collections

class TtsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = collections.deque([])

    @commands.command()
    async def tts(self, ctx, *, text):
        await self.speak(ctx, text, "com")

    @commands.command()
    async def ttsie(self, ctx, *, text):
        await self.speak(ctx, text, "ie")

    @commands.command()
    async def ttsuk(self, ctx, *, text):
        await self.speak(ctx, text, "co.uk")

    @commands.command()
    async def ttsau(self, ctx, *, text):
        await self.speak(ctx, text, "com.au")
     
    async def speak(self, ctx, text, domain):
        if ctx.channel.name == "no-mic":
            if ctx.author.voice is None:
                await ctx.send("Please join a voice channel.")
                return
            filename = f"{ctx.message.id}.mp3"
            voice = ctx.voice_client
            if not voice:
                await ctx.author.voice.channel.connect()
                voice = ctx.voice_client
            text = re.sub(r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>","",text)
            to_speak = f"{ctx.author.display_name} says: {text}"
            tts = gTTS(text=to_speak, lang="en", tld=domain)
            tts.save(filename)
            self.queue.append(filename)
            self.play(voice)

    def play(self, voice):
        if voice.is_playing():
            return
        next_tts = self.queue.popleft()
        voice.play(discord.FFmpegPCMAudio(next_tts))
        while voice.is_playing():
            continue
        else:
            os.remove(next_tts)
            if len(self.queue) > 0:
                self.play(voice)

    @tts.error
    async def _tts_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Please provide some text to speak")
        else:
            print(error)

async def setup(bot):
    await bot.add_cog(TtsCog(bot))

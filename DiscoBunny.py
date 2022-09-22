import discord
import checks
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
import aiosqlite
import sqlite3
from settings import Settings
import aiohttp
from discoutils import get_cogs
import membership

load_dotenv()

description = "Bot for RabbitHole, random Bunny, etc."
TOKEN = os.getenv("TOKEN")

async def get_prefix(_bot, msg):
    prefix =  await _bot.settings.get("prefix")
    return commands.when_mentioned_or(prefix)(_bot, msg)

class Disco(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def setup_hook(self):
        self.db = await aiosqlite.connect(os.getenv("DB"))
        self.db.row_factory = sqlite3.Row
        self.settings = Settings(self.db)
        self.session = aiohttp.ClientSession()
        member_view = await self.settings.get("member_view")
        self.add_view(membership.GetMemberInfo(), message_id=int(member_view))
        extensions = get_cogs()
        for extension in extensions:
            await self.load_extension(extension)
        await self.load_extension('jishaku')

    async def on_ready(self):
        print('Logged in as')
        print(bot.user.name)
        print(bot.user.id)
        print('------')

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            row = await self.db.execute("select text from commands where name = ?", (ctx.invoked_with,))
            command = await row.fetchone()
            if command:
                return await ctx.send(command["text"])
            else:
                raise error
        else:
            raise error 
bot = Disco(command_prefix=get_prefix, description=description, intents=discord.Intents.all(), help=commands.DefaultHelpCommand())#, application_id=961325151021043802)
bot.run(TOKEN)

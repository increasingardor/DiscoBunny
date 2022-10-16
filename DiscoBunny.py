import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import aiosqlite
import sqlite3
from settings import Settings
import aiohttp
from discoutils import get_cogs
import membership

# Load environment variables
load_dotenv()

#set description and get Discord API bot token
description = "Bot for RabbitHole, random Bunny, etc."
TOKEN = os.getenv("TOKEN")

# Pull prefix from database, make bot respond when mentioned
async def get_prefix(_bot, msg):
    prefix =  _bot.settings.prefix#await _bot.settings.get("prefix")
    return commands.when_mentioned_or(prefix)(_bot, msg)

# Custom bot class
class Disco(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # Pre-launch setup in async frame: connects to settings database,
    # sets up persistent views, loads cogs
    async def setup_hook(self):
        self.db = await aiosqlite.connect("bunny.db")#os.getenv("DB"))
        self.db.row_factory = sqlite3.Row
        sets = await self.db.execute("select * from settings")
        settings = await sets.fetchall()
        self.settings = Settings(settings)#self.db)
        self.session = aiohttp.ClientSession()
        member_view = self.settings.member_view#await self.settings.get("member_view")
        self.add_view(membership.GetMemberInfo(), message_id=int(member_view))
        extensions = get_cogs()
        for extension in extensions:
            await self.load_extension(extension)
        await self.load_extension('jishaku')

    # Prints to logger once connected to Discord
    async def on_ready(self):
        print('Logged in as')
        print(bot.user.name)
        print(bot.user.id)
        print('------')

    # If a command isn't found it checks the database to see if there is a
    # custom command with that name.
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            row = await self.db.execute("select text from commands where name = ?", (ctx.invoked_with,))
            command = await row.fetchone()
            if command:
                if ctx.message.reference:
                    return await ctx.message.reference.resolved.reply(command["text"])
                else:
                    return await ctx.reply(command["text"])
            else:
                raise error
        else:
            raise error

# Defines bot variable, runs bot
bot = Disco(command_prefix=get_prefix, description=description, intents=discord.Intents.all(), help=commands.DefaultHelpCommand())

bot.run(TOKEN)

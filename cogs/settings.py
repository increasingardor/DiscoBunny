import discord
from discord.ext import commands
import os
import dotenv
import checks
from datetime import datetime
import pytz
import aiosqlite

# Manage settings for bot

class SettingsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
       
    @commands.group()
    @checks.is_mod()
    async def settings(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Please use a subcommand. Use `!help settings` for a list.")

    @settings.command()
    @checks.is_mod()
    async def add(self, ctx, key, *, value):
        key = key.lower()
        keys = self.bot.settings.keys
        if key in keys:
            await ctx.send(f"Setting {key.lower()} already exists. Please use `!settings update` to update a key.")
        else:
            async with aiosqlite.connect("bunny.db") as db:
                await db.execute("insert into settings (name, value, created_by, created_date) values (?, ?, ?, ?)", (key, value, ctx.author.display_name, datetime.now(pytz.timezone("US/Central"))))
                await db.commit()
                self.bot.settings.__setattr__(key, value)
            await ctx.send(f"Setting `{key}` set to `{value}`.")

    @add.error
    async def add_error(self, ctx, error):
        if isinstance(error, checks.MissingRoleInList):
            message = "You don't have permission to do that."
        else:
            message = f"ERROR: {type(error).__name__} - {error}"
        await ctx.send(message)

    @settings.command()
    @checks.is_mod()
    async def set(self, ctx, key, *, value):
        key = key.lower()
        keys = [k for k, v in self.bot.settings.__dict__.items()]#await self.bot.settings.keys()
        self.bot.settings.__setattr__(key, value)
        if key in keys:
            async with aiosqlite.connect("bunny.db") as db:
                await db.execute("update settings set value = ? where name = ?", (value, key))
                await db.commit()
            #await self.bot.settings.set(key, value)
        else:
            async with aiosqlite.connect("bunny.db") as db:
                await db.execute("insert into settings (name, value) values (? , ?)", (key, value))
                await db.commit()
        await ctx.send(f"Setting `{key}` set to `{value}`.")

    @settings.command()
    @checks.is_mod()
    async def get(self, ctx, key):
        key = key.lower()
        keys = self.bot.settings.__dict__.keys()#await self.bot.settings.keys()
        if key in keys:
            value = self.bot.settings.__dict__[key]#await self.bot.settings.get(key)
            await ctx.send(f"{key} = {value}")
        else:
            await ctx.send(f"Setting {key} does not exist. Please use `!settings add` to add a key.")

async def setup(bot):
    await bot.add_cog(SettingsCog(bot))

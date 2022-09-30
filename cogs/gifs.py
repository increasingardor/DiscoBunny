import traceback
import discord
from discord.ext import commands
import checks
import requests
import urllib.parse
import os
import dotenv
import validators
from datetime import datetime
import asyncio
import typing
import aiohttp
from io import BytesIO
import pprint

class Gifs(commands.Cog):
    """Commands to manage and retrieve GIFs."""

    def __init__(self, bot):
        self.bot = bot
        dotenv.load_dotenv(dotenv.find_dotenv())
        self.gif_cooldowns = {}

    @commands.group(invoke_without_command=True, aliases=["g"])
    async def gif(self, ctx, *, gif_name):
        """Get a gif from the database

        Retrieves one gif from the database. This gif will be masked with a spoiler in #general or any channel not marked NSFW.
        """
        if ctx.invoked_subcommand is None:
            if (not ctx.author.name in self.gif_cooldowns 
                    or (datetime.now() - self.gif_cooldowns[ctx.author.name]).seconds > int(await self.bot.settings.get("gif_cooldown")) 
                    or ctx.author.top_role >= discord.utils.get(ctx.guild.roles, name=await self.bot.settings.get("mod_role"))):
                payload = {'name': gif_name.lower()}
                async with self.bot.session.get("https://counter.heyitsjustbunny.com/get_gif", params=payload) as r:
                    data = await r.json()
                if data["url"] == "Gif does not exist!":
                    ctx.command.reset_cooldown(ctx)
                    await ctx.send("We don't have a GIF by that name.")
                else:
                    self.gif_cooldowns[ctx.author.name] = datetime.now()
                    sender = ctx.message.reference.resolved.reply if ctx.message.reference is not None else ctx.send
                    if data['nsfw'].lower() == "true" and (ctx.channel.id == 940258352775192639 or not ctx.channel.is_nsfw()):
                        msg = f"||{data['url']} ||"
                    else:
                        msg = f"{data['url']}"
                    await sender(msg)
            else:
                await ctx.send("You're doing that too frequently. Please wait a minute before doing that again.")

    @gif.error
    async def gif_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            message = f"You must provide a GIF name when making a request."
        elif isinstance(error, commands.CommandOnCooldown):
            message = "You're doing that too much. Please wait a minute before doing that again."
        else:
            message = "We encountered an error. Sorry about that."
            traceback.print_tb(error.traceback)
        await ctx.send(message)

    @gif.command(name="add")
    @checks.is_level_5("GIF Master")
    async def gif_add(self, ctx, *, text):
        """Add a new gif to the database.
        
        Usage: !gif <name> <url> [nsfw]

        Add one gif with a name and URL to the database. The nsfw parameter is optional; gifs default to nsfw if no value is provided. Values accepted for the nsfw parameter are "nsfw", "true", "sfw", and "false". Must be Level 5 or higher to use.
        """
        if (ctx.channel.name.find("bot-commands") > -1 
                or ctx.channel.name.find("bots-commands") > -1 
                or ctx.author.top_role >= discord.utils.get(ctx.guild.roles, name=await self.bot.settings.get("mod_role"))):
            parsed = text.split()
            if parsed[0].lower() in ["add", "update", "delete", "list"]:
                return await ctx.send("GIF names cannot begin with `add`, `update`, `delete`, or `list`.")
            last = parsed.pop()
            if last.lower() == "sfw" or last.lower() == "false":
                gif_url = parsed.pop()
                nsfw = False
            else:
                if last.lower() == "nsfw" or last.lower() == "true":
                    gif_url = parsed.pop()
                else:
                    gif_url = last
                nsfw = True
            gif_name = " ".join(parsed)
            if not validators.url(gif_url):
                await ctx.send(f"`{gif_url}` is not a valid URL. Make sure you're using the correct order: `!gif add gif-name gif-url [nsfw]`.")
            else:
                payload = {"name":gif_name.lower(), "url": urllib.parse.quote(gif_url, safe=''), "nsfw": nsfw}
                async with self.bot.session.post(f"https://counter.heyitsjustbunny.com/add_gif?name={gif_name.lower()}&url={urllib.parse.quote(gif_url, safe='')}&nsfw={nsfw}") as r:#?name={gif_name.lower()}&url={urllib.parse.quote(gif_url, safe='')}&nsfw={nsfw}") as r:
                    data = await r.json()
                if data["response"] == "Gif already exists!":
                    await ctx.send(f"A GIF with the name `{gif_name.lower()}` already exists. Try a different name!")
                else:
                    await ctx.send(f"GIF added by {ctx.author.display_name}!\nName: `{gif_name.lower()}`\nURL: `{gif_url}`\n{gif_url}\nNSFW: `{nsfw}`")
        else:
            await ctx.send("That can only be done in a bot command channel.")

    @gif_add.error
    async def gif_add_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            message = "You must be at least Level 5 to do that. If you are and still cannot do that, please contact a mod."
        elif isinstance(error, checks.CreepError):
            message = "No. Creep."
        elif isinstance(error, commands.NoPrivateMessage):
            message = "You can't use that in a DM. Why would you send a bot a GIF, anyway?"
        elif isinstance(error, commands.MissingRequiredArgument):
            message = "You must provide a GIF name and a URL to add a GIF: `!gif <name> <url>`"
        await ctx.send(message)


    @gif.command(name="update")
    @checks.is_level_5("GIF Master")
    async def gif_update(self, ctx, *, text):
        """Update an existing gif in the database.

        Usage: !gif update <name> <url> [nsfw]

        Primarily used to fix an incorrect URL, or to change the nsfw status of a gif. Gif names cannot be changed with this command. The nsfw parameter is optional; if left off, gifs default to nsfw. Values accepted for nsfw are "nsfw", "true", "sfw", and "false".
        """
        parsed = text.split()
        last = parsed.pop()
        if last.lower() == "sfw" or last.lower() == "false":
            gif_url = parsed.pop()
            nsfw = False
        else:
            if last.lower() == "nsfw" or last.lower() == "true":
                gif_url = parsed.pop()
            nsfw = True
        gif_name = " ".join(parsed)
        if not validators.url(gif_url):
            await ctx.send(f"`{gif_url}` is not a valid URL. Make sure you're using the correct order: `!gif add gif-name gif-url`.")
        else:
            async with self.bot.session.post(f"https://counter.heyitsjustbunny.com/add_gif?name={gif_name}&url={urllib.parse.quote(gif_url, safe='')}&nsfw={nsfw}&update=true") as r:
                data = await r.json()
            if data["response"] == "Gif updated!":
                await ctx.send(f"GIF updated!\nName: `{gif_name}`\nNew URL: `{gif_url}`\n{gif_url}")
            else:
                await ctx.send("There was a problem updating that GIF. Maybe we couldn't find one with the name, or some other problem occurred. Please try again.")

    @gif.command(name="delete", brief="Delete a GIF from the database.", help="!gif delete gif-name will delete that named GIF from the database.")
    @checks.is_level_5("GIF Master")
    async def gif_delete(self, ctx, *, gif_name):
        """Delete a gif from the database.

        Deletes one gif from the database. Will prompt for confirmation to make sure it is deleting the correct gif.
        """

        def check_yes(msg):
            return (msg.content.lower() == "y" or msg.content.lower() == "yes") and msg.author.id == ctx.author.id
       
        gif_name = gif_name.lower()
        payload = {'name': gif_name}
        async with self.bot.session.get(f"https://counter.heyitsjustbunny.com/get_gif", params=payload) as check:
            data = await check.json()
        if data["url"] == "Gif does not exist!":
            await ctx.send("We don't have a GIF by that name.")
        else:
            await ctx.send(f"Name: `{gif_name}`\nURL: `{data['url']}`\n{data['url']}")
            await ctx.send(f"Are you sure you want to delete GIF `{gif_name}? y/n")
            try:
                msg = await self.bot.wait_for("message", check=check_yes, timeout=15.0)
            except asyncio.TimeoutError:
                await ctx.send(f"Since you didn't respond yes, the GIF has not been deleted.")
            else:
                await self.bot.session.post(f"https://counter.heyitsjustbunny.com/delete_gif?name={gif_name}")
                await ctx.send(f"GIF {gif_name} deleted!")

    @gif.command(name="list")
    async def gif_list(self, ctx):
        """Get link to list of all gifs.

        A link to the website containing searchable list of all gifs.
        """
        await ctx.send("https://heyitsjustbunny.com/discobunny.html")

    @commands.command()
    async def welcome(self, ctx, members: commands.Greedy[discord.Member]):
        """A welcome gif.

        Displays a welcome gif to greet new members. Optionally you can provide a username or username mention, and the bot will mention them in its post, to tag them.
        """
        if len(members) > 0:
            mentions = " ".join([member.mention for member in members])
            await ctx.send(mentions, file=discord.File(fp="BunnyWelcome.gif", filename="BunnyWelcome.gif"))
            await ctx.message.delete()
        else:
            url = "https://cdn.discordapp.com/attachments/940258352775192639/961029709787975720/BunnyWelcome.gif"
            await ctx.send(url)

async def setup(bot):
    await bot.add_cog(Gifs(bot))

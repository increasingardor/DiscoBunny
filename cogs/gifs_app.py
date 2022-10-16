from code import interact
from dis import disco
import typing
import discord
from discord.ext import commands
from discord import app_commands
from discord.app_commands import Choice
import checks
import urllib.parse
import dotenv
import validators
from datetime import datetime
import asyncio

class GifsApp(commands.Cog):
    """Commands to manage and retrieve GIFs."""

    def __init__(self, bot):
        self.bot = bot
        dotenv.load_dotenv(dotenv.find_dotenv())
        self.gif_cooldowns = {}

    gifs = app_commands.Group(name="gifs", description="gif commands")

    #@commands.group(invoke_without_command=True, aliases=["g"])
    @gifs.command(name="get")
    @app_commands.describe(gif_name="the name of the gif to retrieve")
    async def gif_get(self, interaction: discord.Interaction, gif_name: str):
        """Get a gif from the database

        Retrieves one gif from the database. This gif will be masked with a spoiler in #general or any channel not marked NSFW.
        """
        if (not interaction.user.name in self.gif_cooldowns 
                or (datetime.now() - self.gif_cooldowns[interaction.user.name]).seconds > int(await self.bot.settings.gif_cooldown)#get("gif_cooldown")) 
                or interaction.user.top_role >= discord.utils.get(interaction.guild.roles, name=await self.bot.settings.mod_role)):#get("mod_role"))):
            payload = {'name': gif_name.lower()}
            async with self.bot.session.get("https://counter.heyitsjustbunny.com/get_gif", params=payload) as r:
                data = await r.json()
            if data["url"] == "Gif does not exist!":
                await interaction.response.send_message("We don't have a GIF by that name.", ephemeral=True)
            else:
                self.gif_cooldowns[interaction.user.name] = datetime.now()
                if data['nsfw'].lower() == "true" and (interaction.channel.id == 940258352775192639 or (not isinstance(interaction.channel, discord.DMChannel) and not interaction.channel.is_nsfw())):
                    msg = f"||{data['url']} ||"
                else:
                    msg = f"{data['url']}"
                await interaction.response.send_message(msg)
        else:
            await interaction.response.send_message("You're doing that too frequently. Please wait a minute before doing that again.")

    # @gif.error
    # async def gif_error(self, ctx, error):
    #     if isinstance(error, commands.MissingRequiredArgument):
    #         message = f"You must provide a GIF name when making a request."
    #     elif isinstance(error, commands.CommandOnCooldown):
    #         message = "You're doing that too much. Please wait a minute before doing that again."
    #     else:
    #         message = "We encountered an error. Sorry about that."
    #         traceback.print_tb(error.traceback)
    #     await ctx.send(message)

    @gifs.command(name="add")
    @checks.app_is_level_5("GIF Master")
    @app_commands.describe(name="the new gif name", url="the URL to the new GIF", nsfw="whether the new GIF is NSFW")
    @app_commands.choices(nsfw=[Choice(name="nsfw", value=1), Choice(name="sfw", value=0)])
    async def gif_add(self, interaction: discord.Interaction, name: str, url: str, nsfw: Choice[int]=1):
        """Add a new gif to the database.
        
        Usage: !gif <name> <url> [nsfw]

        Add one gif with a name and URL to the database. The nsfw parameter is optional; gifs default to nsfw if no value is provided. Values accepted for the nsfw parameter are "nsfw", "true", "sfw", and "false". Must be Level 5 or higher to use.
        """
        if (interaction.channel.name.find("bot-commands") > -1 
                or interaction.channel.name.find("bots-commands") > -1 
                or interaction.user.top_role >= discord.utils.get(interaction.guild.roles, name=await self.bot.settings.mod_role)):#get("mod_role"))):
            parsed = name.split()
            if parsed[0].lower() in ["add", "update", "delete", "list"]:
                return await interaction.response.send_message("GIF names cannot begin with `add`, `update`, `delete`, or `list`.", ephemeral=True)
            if not validators.url(url):
                await interaction.response.send_message(f"`{url}` is not a valid URL.", ephemeral=True)
            else:
                payload = {"name":name.lower(), "url": urllib.parse.quote(url, safe=''), "nsfw": nsfw}
                async with self.bot.session.post(f"https://counter.heyitsjustbunny.com/add_gif?name={name.lower()}&url={urllib.parse.quote(url, safe='')}&nsfw={bool(nsfw)}") as r:#?name={gif_name.lower()}&url={urllib.parse.quote(gif_url, safe='')}&nsfw={nsfw}") as r:
                    data = await r.json()
                if data["response"] == "Gif already exists!":
                    await interaction.response.send_message(f"A GIF with the name `{name.lower()}` already exists. Try a different name!", ephemeral=True)
                else:
                    await interaction.response.send_message(f"GIF added by {interaction.user.display_name}!\nName: `{name.lower()}`\nURL: `{url}`\n{url}\nNSFW: `{nsfw.name}`")
        else:
            await interaction.response.send_message("That can only be done in a bot command channel.", ephemeral=True)

    @gif_add.error
    async def gif_add_error(self, interaction, error):
        if isinstance(error, commands.CheckFailure):
            message = "You must be at least Level 5 to do that. If you are and still cannot do that, please contact a mod."
        elif isinstance(error, checks.CreepError):
            message = "No. Creep."
        elif isinstance(error, commands.NoPrivateMessage):
            message = "You can't use that in a DM. Why would you send a bot a GIF, anyway?"
        elif isinstance(error, commands.MissingRequiredArgument):
            message = "You must provide a GIF name and a URL to add a GIF: `!gif <name> <url>`"
        await interaction.response.send_message(message, ephemeral=True)


    @gifs.command(name="update")
    @checks.is_level_5("GIF Master")
    @app_commands.choices(nsfw=[Choice(name="nsfw", value=1), Choice(name="sfw", value=0)])
    async def gif_update(self, interaction: discord.Interaction, name: str, url: str, nsfw: Choice[int]=1):
        """Update an existing gif in the database.

        Usage: !gif update <name> <url> [nsfw]

        Primarily used to fix an incorrect URL, or to change the nsfw status of a gif. Gif names cannot be changed with this command. The nsfw parameter is optional; if left off, gifs default to nsfw. Values accepted for nsfw are "nsfw", "true", "sfw", and "false".
        """

        if not validators.url(url):
            await interaction.response.send_message(f"`{url}` is not a valid URL.", ephemeral=True)
        else:
            async with self.bot.session.post(f"https://counter.heyitsjustbunny.com/add_gif?name={name}&url={urllib.parse.quote(url, safe='')}&nsfw={bool(nsfw)}&update=true") as r:
                data = await r.json()
            if data["response"] == "Gif updated!":
                await interaction.response.send_message(f"GIF updated!\nName: `{name}`\nNew URL: `{url}`\n{url}")
            else:
                await interaction.response.send_message("There was a problem updating that GIF. Maybe we couldn't find one with the name, or some other problem occurred. Please try again.")

    @gifs.command(name="delete")
    @checks.app_is_level_5()
    @app_commands.describe(name="the GIF to delete")
    async def gif_delete(self, interaction: discord.Interaction, name: str):
        """Delete a gif from the database.

        Deletes one gif from the database. Will prompt for confirmation to make sure it is deleting the correct gif.
        """

        def check_yes(msg):
            return (msg.content.lower() == "y" or msg.content.lower() == "yes") and msg.author.id == interaction.user.id
       
        name = name.lower()
        payload = {'name': name}
        async with self.bot.session.get(f"https://counter.heyitsjustbunny.com/get_gif", params=payload) as check:
            data = await check.json()
        if data["url"] == "Gif does not exist!":
            await interaction.response.send_message("We don't have a GIF by that name.")
        else:
            view = DeleteGif(name)
            await interaction.response.send_message(f"Name: `{name}`\nURL: `{data['url']}`\n{data['url']}", view=view, ephemeral=True)
            view.message = await interaction.original_response()
            #await interaction.followup.send(f"Are you sure you want to delete GIF `{name}? y/n", ephemeral=True)
            # try:
            #     msg = await self.bot.wait_for("message", check=check_yes, timeout=15.0)
            # except asyncio.TimeoutError:
            #     await interaction.followup.send(f"Since you didn't respond yes, the GIF has not been deleted.")
            # else:
            #     await self.bot.session.post(f"https://counter.heyitsjustbunny.com/delete_gif?name={name}")
            #     await interaction.followup.send(f"GIF {name} deleted!", ephemeral=True)

    @gif_delete.error
    async def delete_error(self, interaction, error):
        print(error)
        if isinstance(error, app_commands.CheckFailure):
            message = "You must be at least Level 5 to do that. If you are and still cannot do that, please contact a mod."
            await interaction.response.send_message(message, ephemeral=True)
        else:
            raise error

    @gifs.command(name="list")
    async def gif_list(self, interaction: discord.Interaction):
        """Get link to list of all gifs.

        A link to the website containing searchable list of all gifs.
        """
        await interaction.response.send_message("https://heyitsjustbunny.com/discobunny.html", ephemeral=True)

    # @commands.command()
    # async def welcome(self, ctx, members: commands.Greedy[discord.Member]):
    #     """A welcome gif.

    #     Displays a welcome gif to greet new members. Optionally you can provide a username or username mention, and the bot will mention them in its post, to tag them.
    #     """
    #     if len(members) > 0:
    #         mentions = " ".join([member.mention for member in members])
    #         await ctx.send(mentions, file=discord.File(fp="BunnyWelcome.gif", filename="BunnyWelcome.gif"))
    #         await ctx.message.delete()
    #     else:
    #         url = "https://cdn.discordapp.com/attachments/940258352775192639/961029709787975720/BunnyWelcome.gif"
    #         await ctx.send(url)

class DeleteGif(discord.ui.View):
    def __init__(self, gif, *, timeout: typing.Optional[float] = 180):
        super().__init__(timeout=timeout)
        self.gif = gif

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def delete_gif(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.client.session.post(f"https://counter.heyitsjustbunny.com/delete_gif?name={self.gif}")
        await self.message.edit(view=None)
        await interaction.response.send_message(f"GIF {self.gif} deleted!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(GifsApp(bot))

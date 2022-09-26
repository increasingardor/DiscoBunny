from discord.ext import commands
import discord
import checks
import sqlite3
import dotenv
import re
import asyncio
from datetime import datetime
import pytz

class CustomCommands(commands.Cog):
    """Commands to manage custom text commands."""

    def __init__(self, bot):
        self.bot = bot
        dotenv.load_dotenv(dotenv.find_dotenv())
        self.tz = pytz.timezone("US/Central")

    @commands.group(name="custom", hidden=True)
    async def custom_command(self, ctx):
        if ctx.invoked_subcommand is None and ctx.author.top_role > discord.utils.get(ctx.guild.roles, name=await self.bot.settings.get("mod_role")):
            return await ctx.send("Please use a subcommand.")

    @custom_command.command(name="add")
    @checks.is_mod()
    async def custom_add(self, ctx, name, *, text):
        """
        Add a custom command.

        Add one custom text command. Command names may not contain spaces.
        """

        command_name = name.lower()
        if command_name in [command.name for command in self.bot.commands]:
            msg = f"We already have a command named {name}. Command not added."
        elif re.search(" +", command_name):
            msg = "Command names may not contain spaces."
        else:
            await self.bot.db.execute("insert into commands (name, text, created_by, created_date) values (?, ?, ?, ?)", (command_name, text, ctx.author.display_name, datetime.now(self.tz)))
            await self.bot.db.commit()
            msg = f"New custom text command added by {ctx.author.display_name}!\nCommand: !{command_name}\nText:\n```\n{text}\n```"
        await ctx.send(msg)

    @custom_add.error
    async def custom_add_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            if isinstance(error.original, sqlite3.IntegrityError):
                return await ctx.send(f"We already have a command named {ctx.args[2]}. Command not added.")

        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(f"Please provide a {error.param} for the command to add. Command not added.")
        else:
            await ctx.send("We encountered an unexpected error. Sorry about that.")
            raise error

    @custom_command.command("get")
    @checks.is_mod()
    async def custom_get(self, ctx, name):
        """
        Get information on a command.

        Display a command, its text, who created it and when, and who last modified it and when, if available.
        """

        command_name = name.lower()
        row = await self.bot.db.execute("select name, text, created_by, created_date, modified_by, modified_date from commands where name = ?", (command_name,))
        result = row.fetchone()
        if result:
            command_name, text, created_by, created_date, modified_by, modified_date = result
            embed = discord.Embed(title=f"Command: {command_name}", color=2447966)
            embed.description = text
            embed.add_field(name="Created By", value=created_by, inline=True).add_field(name="Created Date", value=f"<t:{int(datetime.fromisoformat(created_date).timestamp())}:f>", inline=True)
            if modified_by is not None:
                embed.add_field(name="\u200b", value="\u200b").add_field(name="Last Modified By", value=modified_by, inline=True).add_field(name="Last Modified Date", value=f"<t:{int(datetime.fromisoformat(modified_date).timestamp())}:f>", inline=True)
            return await ctx.send(embed=embed)
        else:
            return await ctx.send(f"Command `{command_name}` not found.")

    @custom_command.command(name="update")
    @checks.is_mod()
    async def custom_update(self, ctx, name, *, text):
        """
        Update the text for a custom command.

        Update the text that will be posted for one custom command in the database.
        """

        command_name = name.lower()
        row = await self.bot.db.execute("select name, text from commands where name = ?", (command_name,))
        result = await row.fetchone()
        if result:
            await self.bot.db.execute("update commands set text = ?, modified_by = ?, modified_date = ? where name = ?", (text, ctx.author.display_name, datetime.now(self.tz), command_name))
            await self.bot.db.commit()
            return await ctx.send(f"Custom text command updated by {ctx.author.display_name}!\nCommand: `!{command_name}`\n```\n{text}\n```")
        else:
            return await ctx.send(f"Command `{command_name}` not found.")

    @custom_update.error
    async def custom_update_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(f"Please provide a {error.param} for the command to be updated. Command not updated.")
        else:
            await ctx.send("We encountered an unexpected error. Sorry about that.")
            raise error

    @custom_command.command(name="rename")
    @checks.is_mod()
    async def custom_rename(self, ctx, old_name, new_name):
        """
        Rename a custom command.

        Rename one custom command in the database. Names may not contain spaces.
        """

        if re.search(" +", new_name):
            return await ctx.send("Command names may not contain spaces. Command not renamed.")
        old_command_name = old_name.lower()
        new_command_name = new_name.lower()
        if new_command_name in [command.name for command in self.bot.commands]:
            return await ctx.send(f"We already have a command named {new_command_name}. Command not renamed.")
        result = await self.bot.db.execute("select command_id from commands where name = ?", (old_command_name,))
        old_command = await result.fetchone()
        if old_command:
            await self.bot.db.execute("update commands set name = ? where command_id = ?", (new_command_name, old_command["command_id"]))
            await self.bot.db.commit()
            return await ctx.send(f"Command `{old_command_name}` renamed to `{new_command_name}`.")
        else:
            await ctx.send(f"Command `{old_command_name}` not found. Command not renamed.")

    @custom_rename.error
    async def custom_rename_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            if isinstance(error.original, sqlite3.IntegrityError):
                msg = f"We already have a command named `{ctx.args[3]}`. Command not renamed."
            else:
                msg = "We encountered an unexpected error. Sorry about that."
        else:
            msg = "We encountered an unexpected error. Sorry about that."
        await ctx.send(msg)

    @custom_command.command(name="delete", ignore_extra=False)
    @checks.is_mod()
    async def custom_delete(self, ctx, name):
        """
        Delete a custom command.

        Delete one custom command from the database.
        """

        def is_author(msg):
            return msg.author.id == ctx.author.id and msg.channel == ctx.channel

        def is_yes(msg_content):
            return msg_content.lower() == "y" or msg_content.lower() == "yes"

        def is_no(msg_content):
            return msg_content.lower() == "n" or msg_content.lower() == "no"

        command_name = name.lower()
        if re.search(" +", command_name):
            return await ctx.send("Command names do not contain spaces.")
        row = await self.bot.db.execute("select command_id, name, text from commands where name = ?", (command_name,))
        result = await row.fetchone()
        if result:
            result_id, result_name, result_text = result
            await ctx.send(f"Command name: `{result_name}`\nCommand text:\n```\n{result_text}\n```\nAre you sure you want to delete this command? (y/n)")
            try:
                msg = await self.bot.wait_for("message", check=is_author, timeout=15)
            except asyncio.TimeoutError:
                await ctx.send("No valid response received. Command not deleted.")
            else:
                if is_yes(msg.content):
                    await self.bot.db.execute("delete from commands where command_id = ?", (result_id,))
                    await self.bot.db.commit()
                    return await ctx.send(f"Command `{command_name}` has been deleted.")
                elif is_no(msg.content):
                    await ctx.send("Command not deleted.")
        else:
            await ctx.send(f"No command named {command_name} found.")

    @custom_delete.error
    async def custom_delete_error(self, ctx, error):
        if isinstance(error, commands.TooManyArguments):
            return await ctx.send("Not a valid command name. Command names do not include spaces.")
        else:
            await ctx.send("We encountered an unexpected error. Sorry about that.")
            raise error

    @custom_command.command(name="list")
    async def custom_list(self, ctx):
        """
        Get list of custom commands.

        Retrieves list of all custom text commands.
        """
        result = await self.bot.db.execute("select name from commands")
        commands = await result.fetchall()
        names = [command[0].ljust(20) for command in commands]
        for index, name in enumerate(names):
            names[index] = f"{name.ljust(20)}\n" if (index + 1) %2 == 0 else f"{name.ljust(20)}"
        await ctx.send(f"Custom Commands```{''.join(names)}```")

async def setup(bot):
    await bot.add_cog(CustomCommands(bot))

import asyncio
import datetime
import re
import checks
import discord
import pytz
from discord.ext import commands

# Rudimentary spam filter to delete spam links and invites

class Spam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_message")
    async def domains(self, message):
        # Compares message content against domains in the spam filter. Deletes if in the filter and alerts mods.
        if isinstance(message.channel, discord.TextChannel) and message.guild.id == 940258352775192636 and not message.author.bot and message.author.top_role < discord.utils.get(message.guild.roles, name=self.bot.settings.mod_role):#get("mod_role")):
            result = await self.bot.db.execute("select domain from spam")
            rows = await result.fetchall()
            for row in rows:
                if re.search(re.escape(row["domain"]), message.content):
                    await message.delete()
                    channel = message.guild.get_channel(940301083098632272)
                    await channel.send(f"<@&941023769244352562> Message from {message.author.mention} deleted in {message.channel.mention} as possible spam. See message in <#954403280103018526>.")

    @commands.group()
    @checks.is_mod()
    async def spam(self, ctx):
        if ctx.invoked_subcommand is None:
            pass

    # Lists current spam domains
    @spam.command(name="list")
    @checks.is_mod()
    async def list_spam(self, ctx):
        result = await self.bot.db.execute("select domain from spam")
        rows = await result.fetchall()
        domains = [row["domain"] for row in rows]
        for index, domain in enumerate(domains):
            domains[index] = f"{domain.ljust(20)}\n" if (index + 1) % 2 == 0 else f"{domain.ljust(20)}"
        await ctx.send(f"Blacklisted Domains```{''.join(domains)}```")


    # Add domain to spam list
    @spam.command(name="add")
    @checks.is_mod()
    async def add_spam(self, ctx, domain):
        tz = pytz.timezone("US/Central")
        now = datetime.datetime.now(tz)
        await self.bot.db.execute("insert into spam (domain, created_by, created_date) values (?, ?, ?)", (domain, ctx.author.display_name, now))
        await self.bot.db.commit()
        await ctx.send(f"`{domain}` added to spam list.")

    # Update a domain in spam list
    @spam.command(name="update")
    @checks.is_mod()
    async def update_spam(self, ctx, old_value, new_value):
        await self.bot.db.execute("update spam set domain = ? where domain = ?", (new_value, old_value))
        await self.bot.db.commit()
        await ctx.send(f"`{old_value}` updated to `{new_value}`")

    # Delete a domain from spam list
    @spam.command(name="delete")
    @checks.is_mod()
    async def delete_spam(self, ctx, domain):
        def is_author(msg):
            return msg.author.id == ctx.author.id and msg.channel == ctx.channel

        def is_yes(msg_content):
            return msg_content.lower() == "y" or msg_content.lower() == "yes"

        def is_no(msg_content):
            return msg_content.lower() == "n" or msg_content.lower() == "no"
        result = await self.bot.db.execute("select spam_id, domain from spam where domain = ?", (domain,))
        row = await result.fetchone()
        if row:
            spam_id, name = row
            await ctx.send(f"Delete `{name}` from spam filter? (y/n)")
            try:
                msg = await self.bot.wait_for("message", check=is_author, timeout=15)
            except asyncio.TimeoutError:
                await ctx.send("No valid response received. Domain not deleted.")
            else:
                if is_yes(msg.content):
                    await self.bot.db.execute("delete from spam where domain = ?", (domain,))
                    await self.bot.db.commit()
                    return await ctx.send(f"`{domain}` removed from spam filter.")
                elif is_no(msg.content):
                    await ctx.send("Domain not deleted.")
        else:
            await ctx.send(f"Domain `{domain}` not found")

async def setup(bot):
    await bot.add_cog(Spam(bot))

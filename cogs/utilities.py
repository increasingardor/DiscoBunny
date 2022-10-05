from pydoc import describe
import typing
import discord
from discord.ext import commands
from discord import app_commands
import pytz
import checks
import datetime

# Not currently working

class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Supposed to make accessing logs for bots easier, not currently working
    @commands.command()
    @checks.is_mod()
    async def log(self, ctx, module, time="today"):
        disco = ["d", "disco", "discobunny"]
        bunnit = ["b", "bunnit", "bunnitbot", "reddit"]
        module_lower = module.lower()
        if module_lower in disco:
            cmd = "discobunny"
        elif module_lower in bunnit:
            cmd = "bunnitbot"
        else:
            return await ctx.send("That is not a valid module name.")
        jsk_sh = self.bot.get_command("jishaku sh")
        await ctx.invoke(jsk_sh, argument=f"journalctl -u {module_lower} -S {time}")

    @commands.hybrid_command(description="Bunny's Twitch!")
    async def twitch(self, ctx: commands.Context, member: typing.Optional[discord.Member]):
        """
        Bunny's Twitch!

        Link to Bunny's Twitch.
        """
        now = datetime.datetime.now(tz=pytz.timezone("US/Central"))
        day = now.weekday()
        if day <= 1:
            next_day = 1 - day
        elif day <= 3:
            next_day = 3 - day
        else:
            next_day = 8 - day
        next_date = now.replace(hour=19, minute=0, second=0) + datetime.timedelta(days=next_day)
        stamp = int(next_date.timestamp())
        if ctx.message.reference:
            reply_to = ctx.message.reference.resolved
        else:
            reply_to = ctx
        greet = f"{member.mention} " if member else ""
        msg = f"{greet}Come see Bunny stream! Twice a week at <t:{stamp}:t>. Come see her scream her head off playing horror games, chilling in casual games, or just chatting.\n\nThe next stream is <t:{stamp}>. See her at https://twitch.tv/heyitsjustbunny" 
        await reply_to.reply(msg)

async def setup(bot):
    await bot.add_cog(Utilities(bot))

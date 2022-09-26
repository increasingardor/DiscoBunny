import discord
from discord.ext import commands
import checks

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

async def setup(bot):
    await bot.add_cog(Utilities(bot))

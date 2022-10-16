from pydoc import describe
import typing
import discord
from discord.ext import commands
import pytz
import checks
import datetime

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
        msg = f"{greet}Come see Bunny stream! Twice a week at <t:{stamp}:t>. Come see her scream her head off playing horror games, chilling in casual games, or just chatting.\n\nThe next stream is <t:{stamp}>. Come check her out!"
        view = StreamingRole()
        
        await reply_to.reply(msg, view=view)

    @commands.hybrid_command()
    async def about(self, ctx):
        embed = discord.Embed(color=discord.Color.blue(), title="About DiscoBunny")
        embed.description = "DiscoBunny is a custom bot written by Ardor specifically for The Rabbit Hole."
        embed.add_field(name="Version", value="2.1", inline=False)
        embed.add_field(name="Language", value="Python 3.9", inline=True)
        embed.add_field(name="Discord Library", value="[discord.py 2.0.1](https://discordpy.readthedocs.io/en/latest/)", inline=True)
        embed.add_field(name="Text to Speech", value="[gTTS](https://gtts.readthedocs.io/en/latest/)", inline=True)
        embed.add_field(name="Reddit", value="[asyncpraw](https://asyncpraw.readthedocs.io/en/stable/)", inline=True)
        embed.add_field(name="Database", value="[aiosqlite](https://aiosqlite.omnilib.dev/en/latest/)", inline=True)
        embed.add_field(name="GIF Database", value="DynamoDB", inline=True)
        embed.add_field(name="HTTP", value="[aiohttp](https://docs.aiohttp.org/en/stable/)")
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)

class StreamingRole(discord.ui.View):
    def __init__(self):
        super().__init__()
        url_button = discord.ui.Button(label="Bunny's Twitch!", style=discord.ButtonStyle.link, url="https://twitch.tv/heyitsjustbunny")
        self.add_item(url_button)
    
    @discord.ui.button(label="Get notified when Bunny streams!", style=discord.ButtonStyle.blurple)
    async def add_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.client.guilds[0]
        role = guild.get_role(976526774332694529)
        member = guild.get_member(interaction.user.id)
        await member.add_roles(role)
        await interaction.response.send_message(f"You have been given the {role.name} role! You will be notified in Discord when Bunny starts streaming.\n\nIf you want to remove this role, you can do so in <#940307355495727104>.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Utilities(bot))

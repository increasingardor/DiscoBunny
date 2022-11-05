from discord.ext import commands
import checks
import traceback

# Commands to load and unload other cogs/extensions
# This way we can work on just a single module and then reload it without impacting the rest of the bot

class ControlCogsCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
    
    # Loads a cog/extension - `cog` parameter must be a dot-separated path, e.g. cogs.gifs
    @commands.command(name='load', hidden=True)
    @checks.is_mod()
    async def ext_load(self, ctx, *, cog: str):
        """Command which Loads a Module.
        Remember to use dot path. e.g: cogs.owner"""

        try:
            await self.bot.load_extension(cog)
        except Exception as e:
            await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
            # traceback.print_exc()
            print(e)
        else:
            await ctx.send(f'`{cog}` loaded successfully.')
            print(f"Loaded cog {cog}")

    # Unloads cog/extension
    @commands.command(name='unload', hidden=True)
    @checks.is_mod()
    async def ext_unload(self, ctx, *, cog: str):
        """Command which Unloads a Module.
        Remember to use dot path. e.g: cogs.owner"""

        try:
            await self.bot.unload_extension(cog)
        except Exception as e:
            await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
        else:
            await ctx.send('**`SUCCESS`**')

    # Reloads a cog/extension
    @commands.command(name='reload', hidden=True)
    @checks.is_mod()
    async def ext_reload(self, ctx, *, cog: str):
        """Command which Reloads a Module.
        Remember to use dot path. e.g: cogs.owner"""

        try:
            await self.bot.unload_extension(cog)
            await self.bot.load_extension(cog)
        except Exception as e:
            await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
        else:
            await ctx.send('**`SUCCESS`**')

    # Sync any application commands / slash commands
    @commands.command()
    @checks.is_mod()
    async def sync(self, ctx):
        await self.bot.tree.sync()
        return await ctx.reply("Commands synced")

    # Gets list of current loaded extensions
    @commands.command(name='extensions', hidden=True)
    @checks.is_mod()
    async def ext_get(self, ctx):
        cogs_list = "**Current Loaded Extensions**\n"
        try:
            for cog in self.bot.extensions:
                cogs_list = cogs_list + f"{cog}\n"
        except Exception as e:
            await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
        else:
            await ctx.send(cogs_list)

async def setup(bot):
    await bot.add_cog(ControlCogsCog(bot))

import discord
from discord.ext import commands
import checks
import dotenv
import os

class EmojiCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        dotenv.load_dotenv(dotenv.find_dotenv())

    @commands.group()
    async def emoji(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Please use a subcommand")

    @emoji.command("add")
    @checks.has_role_in_list(os.getenv("MOD_ROLES"))
    async def add(self, ctx, emoji_name, roles: commands.Greedy[discord.Role], *, reason=None):
        attachments = ctx.message.attachments
        error_msg = []
        if discord.utils.get(ctx.guild.emojis, name=emoji_name) is not None:
            error_msg.append("An emoji by that name already exists on the server. Did you mean to edit?")
        if not attachments:
            error_msg.append("Please attach an image to use as the emoji.")
        elif len(attachments) > 1:
            error_msg.append("Please only attach one image.")
        if len(error_msg) > 0:
            await ctx.send(" ".join(error_msg))
        else:
            for attachment in ctx.message.attachments:
                if not attachment.content_type.endswith(("jpeg", "gif", "png")):
                    await ctx.send("Only GIF, JPEG, or PNG files may be used as emoji.")
                else:
                    img = await attachment.read()
                    emoji = await ctx.guild.create_custom_emoji(name=emoji_name, image=img, roles=roles, reason=reason)
                    role_names = []
                    if not roles:
                        role_names = ["Everyone"]
                    else:
                        role_names = [role.name for role in roles]
                    msg = f"Emoji {emoji} {emoji.name} added, with access for:\n"
                    msg += "\n".join(role_names)
                    await ctx.send(msg)

    @add.error
    async def _add_error(self, ctx, error):
        await ctx.send(f"{type(error).__name__}: {error}")

    @emoji.command()
    @checks.has_role_in_list(os.getenv("MOD_ROLES"))
    async def edit(self, ctx, emoji: discord.Emoji, roles: commands.Greedy[discord.Role], *, reason="No reason provided"):
        role_names = []
        if not roles:
            role_names = ["Everyone"]
        else:
            role_names = [role.name for role in roles]
        await emoji.edit(name=emoji.name, roles=roles, reason=reason)
        msg = f"Emoji {emoji} {emoji.name} edited, with access for:\n"
        msg += "\n".join(role_names)
        await ctx.send(msg)

    @edit.error
    async def _edit_error(self, ctx, error):
        if isinstance(error, commands.EmojiNotFound):
            await ctx.send("An emoji by that name was not found on the server.")

    @emoji.command()
    @checks.has_role_in_list(os.getenv("MOD_ROLES"))
    async def get(self, ctx, emoji: discord.Emoji):
        if not emoji.roles:
            role_list = ["Everyone"]
        else:
            role_list = [role.name for role in emoji.roles]
        roles = "\n".join(role_list)
        await ctx.send(f"{emoji}")
        await ctx.send(f"{emoji.name} available to:\n{roles}")

async def setup(bot):
    await bot.add_cog(EmojiCog(bot))

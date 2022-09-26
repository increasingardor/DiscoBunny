import discord
from discord.ext import commands
import checks

class Memberships(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Watches for removal of one of the membership roles and alerts in special channel 
    # to let mods know membership has ended. Originally for MEE6 membership, 
    # now watching for automatic removal by MEE6 at end of enrollment period and adding 
    # role back for additional month.
    @commands.Cog.listener("on_member_update")
    async def leave_membership(self, before, after):
        flr = before.guild.get_role(1009880250823491625)
        cc = before.guild.get_role(1009880071139491860)
        bh = before.guild.get_role(1009879837667762196)
        tiers = [flr, cc, bh]
        was_member = [tier for tier in tiers if tier in before.roles]
        if was_member:
            still_member = [tier for tier in tiers if tier in after.roles]
            if not still_member:
                channel = before.guild.get_channel(1016392838310809651)
                embed = discord.Embed(color=discord.Color.red(), title="Membership Ended")
                embed.set_author(name=before.display_name, icon_url=before.display_avatar.url)
                embed.add_field(name="Tier", value=was_member[0].name)
                manage = int(await self.bot.settings.get("manage_membership_roles"))
                if manage == 1:
                    await before.add_roles(was_member[0])
                    embed.description = f"Added role {was_member[0].name} back to member."
                await channel.send(embed=embed)

    # Turns the automatic add-back of roles on or off
    @commands.hybrid_group(name="manage-roles", invoke_without_command=True)
    @checks.is_mod()
    async def manage_roles(self, ctx):
        if not ctx.invoked_subcommand:
            return await ctx.reply("Please use `on` or `off` subcommand")

    @manage_roles.command(name="on")
    @checks.is_mod()
    async def manage_roles_on(self, ctx):
        await self.bot.settings.set("manage_membership_roles", True)
        return await ctx.reply("Disco will now manage membership roles.")

    @manage_roles.command(name="off")
    @checks.is_mod()
    async def manage_roles_off(self, ctx):
        await self.bot.settings.set("manage_membership_roles", False)
        return await ctx.reply("Disco is no longer managing membership roles.")

    # Add or remove FLR role
    @commands.hybrid_command()
    @checks.is_mod()
    async def flr(self, ctx, member: discord.Member):
        flr = ctx.guild.get_role(1009880250823491625)
        action = await self._manage_roles(flr, member)
        await ctx.reply(action)

    # Add or remove CC role
    @commands.hybrid_command()
    @checks.is_mod()
    async def cc(self, ctx, member: discord.Member):
        cc = ctx.guild.get_role(1009880071139491860)
        action = await self._manage_roles(cc, member)
        await ctx.reply(action)


    # Add or remove BH role
    @commands.hybrid_command()
    @checks.is_mod()
    async def bh(self, ctx, member: discord.Member):
        bh = ctx.guild.get_role(1009879837667762196)
        action = await self._manage_roles(bh, member)
        await ctx.reply(action)

    @flr.error
    async def flr_error(self, ctx, error):
        if isinstance(error, commands.MemberNotFound):
            return await ctx.reply(f"No member named {error.argument} was found in the server.")
        elif isinstance(error, commands.MissingRequiredArgument):
            return await ctx.reply("You must provide a member to add or remove this role from.")
        else:
            await ctx.reply(f"Unknown error encountered.")
            raise error


    @cc.error
    async def cc_error(self, ctx, error):
        if isinstance(error, commands.MemberNotFound):
            return await ctx.reply(f"No member named {error.argument} was found in the server.")
        elif isinstance(error, commands.MissingRequiredArgument):
            return await ctx.reply("You must provide a member to add or remove this role from.")
        else:
            await ctx.reply(f"Unknown error encountered.")
            raise error

    @bh.error
    async def bh_error(self, ctx, error):
        if isinstance(error, commands.MemberNotFound):
            return await ctx.reply(f"No member named {error.argument} was found in the server.")
        elif isinstance(error, commands.MissingRequiredArgument):
            return await ctx.reply("You must provide a member to add or remove this role from.")
        else:
            await ctx.reply(f"Unknown error encountered.")
            raise error

    # Actual function that adds/removes roles, called by other commands
    async def _manage_roles(self, role, member):
        if role in member.roles:
            manage = int(await self.bot.settings.get("manage_membership_roles"))
            if manage == 1:
                await self.bot.settings.set("manage_membership_roles", False)
                await member.remove_roles(role)
                await self.bot.settings.set("manage_membership_roles", True)
            else:
                await member.remove_roles(role)
            return f"{role.name} removed from {member.display_name}."
        else:
            await member.add_roles(role)
            return f"{role.name} added to {member.display_name}."

async def setup(bot):
    await bot.add_cog(Memberships(bot))

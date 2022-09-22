import discord
from discord.ext import commands


class CreepError(commands.CommandError):
    pass

class MissingRoleInList(commands.CommandError):
    pass

def is_level_5(role=None):
    def predicate(ctx):
        if ctx.author.id == 310957860551000082:
            return True
        top_role = ctx.author.top_role
        guild_roles = ctx.guild.roles
        creep = discord.utils.get(guild_roles, name="Creep")
        member_roles = ctx.author.roles
        level4 = discord.utils.get(guild_roles, name="Level 4")
        if creep in member_roles:
            raise CreepError()
        elif not role:
            return top_role > level4
        else:
            passed_role = discord.utils.get(guild_roles, name=role)
            return top_role > level4 or passed_role in member_roles
    return commands.check(predicate)

def is_level_10(role=None):
    def predicate(ctx):
        if ctx.author.id == 310957860551000082:
            return True
        top_role = ctx.author.top_role
        guild_roles = ctx.guild.roles
        creep = discord.utils.get(guild_roles, name="Creep")
        member_roles = ctx.author.roles
        level9 = discord.utils.get(guild_roles, name="Level 9")
        if creep in member_roles:
            raise CreepError()
        elif not rolee:
            return top_role > level9
        else:
            passed_role = discord.utils.get(guild_roles, name=role)
            return top_role > level9 or passed_role in member_roles
    return commands.check(predicate)

def level_check(level, role=None):
    def predicate(ctx):
        if ctx.author.id == 310957860551000082:
            return True
        top_role = ctx.author.top_role
        guild_roles = ctx.guild.roles
        creep = discord.utils.get(guild_roles, name="Creep")
        member_roles = ctx.author.roles
        level_role = discord.utils.get(guild_roles, name=f"Level {level}")
        if creep in member_roles:
            raise CreepError()
        elif not role:
            return top_role > level_role
        else:
            passed_role = discord.utils.get(guild_roles, name=role)
            return top_role > level_role or passed_role in member_roles
    return commands.check(predicate)

def has_role_in_list(roles):
    def predicate(ctx):
        if ctx.author.id == 310957860551000082:
            return True
        allowed_roles = []
        for role in roles.split(","):
            allowed_roles.append(role.strip())
        if not len([role for role in ctx.author.roles if role.name in allowed_roles]):
           raise MissingRoleInList()
        else:
            return True
    return commands.check(predicate)

def is_mod():
    def predicate(ctx):
        return ctx.author.id == 310957860551000082 or ctx.author.top_role >= discord.utils.get(ctx.guild.roles, name="Moderator")

    return commands.check(predicate)

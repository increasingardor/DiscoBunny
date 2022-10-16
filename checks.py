import discord
from discord.ext import commands

# Various Checks
# In discord.py a check is a function run before a command to determine if it should be run. 
# Checks for permissions, channels, etc.

# Just an error we raise if a user has the Creep role
class CreepError(commands.CommandError):
    pass

# An error we raise if user doesn't have a role in a provided list
class MissingRoleInList(commands.CommandError):
    pass

# Checks is user is Level 5 or higher or has an override role
def is_level_5(role=None):
    def predicate(ctx):
        # This checks to see if it's me; lets me run commands in DMs for testing
        if ctx.author.id == 310957860551000082:
            return True
        guild = ctx.bot.guilds[0]
        author = guild.get_member(ctx.author.id)
        # Member's top role
        top_role = author.top_role
        # All roles in the server
        guild_roles = guild.roles
        # The creep role
        creep = discord.utils.get(guild_roles, name="Creep")
        # All of member's roles
        member_roles = author.roles
        # The Level 4 role
        level4 = discord.utils.get(guild_roles, name="Level 4")
        # Raise error if has Creep role
        if creep in member_roles:
            raise CreepError()
        elif not role:
            return top_role > level4
        else:
            # The override role
            passed_role = discord.utils.get(guild_roles, name=role)
            return top_role > level4 or passed_role in member_roles
    return commands.check(predicate)

# Same as above, but Level 10
def is_level_10(role=None):
    def predicate(ctx):
        if ctx.author.id == 310957860551000082:
            return True
        guild = ctx.bot.guilds[0]
        author = guild.get_member(ctx.author.id)
        top_role = author.top_role
        guild_roles = guild.roles
        creep = discord.utils.get(guild_roles, name="Creep")
        member_roles = author.roles
        level9 = discord.utils.get(guild_roles, name="Level 9")
        if creep in member_roles:
            raise CreepError()
        elif not role:
            return top_role > level9
        else:
            passed_role = discord.utils.get(guild_roles, name=role)
            return top_role > level9 or passed_role in member_roles
    return commands.check(predicate)

# A check for any level number or an override role; not yet implemented in any module
def level_check(level, role=None):
    def predicate(ctx):
        if ctx.author.id == 310957860551000082:
            return True
        guild = ctx.bot.guilds[0]
        author = guild.get_member(ctx.author.id)
        top_role = author.top_role
        guild_roles = guild.roles
        creep = discord.utils.get(guild_roles, name="Creep")
        member_roles = author.roles
        level_role = discord.utils.get(guild_roles, name=f"Level {level}")
        if creep in member_roles:
            raise CreepError()
        elif not role:
            return top_role > level_role
        else:
            passed_role = discord.utils.get(guild_roles, name=role)
            return top_role > level_role or passed_role in member_roles
    return commands.check(predicate)

# Checks to see if user has any of the roles in a provided list
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

# Checks to see if member is me (for use in DMs) or has Mod role or higher.
def is_mod():
    def predicate(ctx):
        return ctx.author.id == 310957860551000082 or ctx.author.top_role >= discord.utils.get(ctx.guild.roles, name=ctx.bot.settings.mod_role)#"Moderator")

    return commands.check(predicate)

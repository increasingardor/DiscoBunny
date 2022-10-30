import random
import discord
from discord.ext import commands
from discord import app_commands
import typing
from pprint import pprint
import aiosqlite
import datetime
import pytz
import random
from jishaku.paginators import PaginatorEmbedInterface
from requests import delete

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.conversing = []
        self.add_message_menu = app_commands.ContextMenu(name="Add to PastBunny", callback=self.menu_add)
        self.bot.tree.add_command(self.add_message_menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.add_message_menu)

    @commands.group(invoke_without_command=True)
    async def drink(self, ctx, *, name: typing.Optional[str]=None):
        """
        Get a drink from the cocktail API.

        Retrieve a random drink from the cocktail API or a specific drink if a name is provided (and no subcommand is used).
        """

        if ctx.invoked_subcommand is None:
            async def random_drink():
                async with self.bot.session.get("https://www.thecocktaildb.com/api/json/v1/1/random.php") as data:
                    return await data.json()
            if name is None:
                api_data = await random_drink()
            else:
                params = { "s": name }
                async with self.bot.session.get("https://www.thecocktaildb.com/api/json/v1/1/search.php", params=params) as data:
                    api_data = await data.json()
            if api_data["drinks"] is None:
                await ctx.send("No drink found with that search term getting random drink.")
                api_data = await random_drink()
            drink = Drink(api_data["drinks"][0])
            embed = self.drink_embed(drink)
            await ctx.send(embed=embed)
    
    def drink_embed(self, drink):
        embed = discord.Embed(color=discord.Color.from_str("#ffffff"), title=drink.name)
        embed.set_thumbnail(url=drink.image)
        embed.description = f"**Glass:** {drink.glass}\n**Ingredients**\n" + "\n".join([f"{k} {v}" for k, v in drink.ingredients.items()]) + f"\n\n{drink.instructions}"
        return embed

    @drink.command(aliases=["i"])
    async def ingredient(self, ctx, *, ingredient):
        """
        Get drinks by ingredient
        
        Search for a list of drinks by a provided ingredient, paginated
        """
        if ingredient is None or ingredient == "":
            return await ctx.send("Please provide an ingredient")
        params = { "i": ingredient }
        async with self.bot.session.get("https://www.thecocktaildb.com/api/json/v1/1/filter.php", params=params) as data:
            pprint(await data.text())
            if await data.text() == "":
                return await ctx.send("No ingredient found for that term.")
            api_data = await data.json()
        drinks = [drink["strDrink"] for drink in api_data["drinks"]]
        paginator = commands.Paginator(max_size=200)
        for drink in drinks:
            paginator.add_line(drink)
        interface = PaginatorEmbedInterface(ctx.bot, paginator, author=ctx.author)
        await interface.send_to(ctx)

    @commands.hybrid_group(name="converse", fallback="on")
    async def converse(self, ctx: commands.Context):
        """
        Turn on conversing with PastBunny
        """
        if not self.bot.conversing:
            self.bot.add_listener(self.converse_listener, "on_message")
        elif ctx.author.id in self.bot.conversing:
            return await ctx.reply("You are already conversing with PastBunny!", ephemeral=True)

        self.bot.conversing.append(ctx.author.id)
        await ctx.reply("You are now conversing with PastBunny!")

    @converse.command(name="off")
    async def converse_off(self, ctx: commands.Context):
        """
        Turn off conversing with PastBunny
        """
        self.bot.conversing.remove(ctx.author.id)
        await ctx.reply("You are no longer conversing with PastBunny.")
        if not self.bot.conversing:
            self.bot.remove_listener(self.converse_listener, "on_message")

    @converse.command(name="add")
    async def converse_add(self, ctx: commands.Context, message: discord.Message=commands.parameter(description="the URL of the message you want to add")):
        """
        Add a new message to the PastBunny database
        """
        jump = discord.ui.View().add_item(discord.ui.Button(label="Back to Message", style=discord.ButtonStyle.link, url=message.jump_url))
        if message.author.id != 940257449502466138:
            return await ctx.send(f"Only messages from Bunny may be added. It's Past**Bunny**, not Past**{message.author.display_name}**.", ephemeral=True)

        async with aiosqlite.connect("bunny.db") as db:
            try:
                await db.execute("insert into past_bunny (message, content, created_by, created_date) values (?, ?, ?, ?)", (message.jump_url, message.clean_content, ctx.author.id, datetime.datetime.now(pytz.timezone("US/Central"))))
                await db.commit()
            except aiosqlite.IntegrityError:
                return await ctx.reply(f"That message has already been added.", ephemeral=True)
            await ctx.reply("Message added!", ephemeral=True, view=jump)

    async def menu_add(self, interaction: discord.Interaction, message: discord.Message=commands.parameter(description="the URL of the message you want to add")):
        """
        Add a new message to the PastBunny database
        """
        jump = discord.ui.View().add_item(discord.ui.Button(label="Back to Message", style=discord.ButtonStyle.link, url=message.jump_url))
        if message.author.id != 940257449502466138:
            return await interaction.response.send_message(f"Only messages from Bunny may be added. It's Past**Bunny**, not Past**{message.author.display_name}**.", ephemeral=True, view=jump)

        async with aiosqlite.connect("bunny.db") as db:
            try:
                await db.execute("insert into past_bunny (message, content, created_by, created_date) values (?, ?, ?, ?)", (message.jump_url, message.clean_content, interaction.user.id, datetime.datetime.now(pytz.timezone("US/Central"))))
                await db.commit()
            except aiosqlite.IntegrityError: # message URLs are unique in the db
                return await interaction.response.send_message(f"That message has already been added.", ephemeral=True, view=jump)
        await interaction.response.send_message("Message added!", ephemeral=True, view=jump)

    async def converse_listener(self, message):
        if message.author.id in self.bot.conversing:
            async with aiosqlite.connect("bunny.db") as db:
                db.row_factory = aiosqlite.Row
                result = await db.execute("select message, content from past_bunny")
                responses = await result.fetchall()
            reply = random.choice(responses)
            view = ConverseEnd(message.author.id, reply["message"])
            msg = await message.reply(reply["content"], view=view)
            view.msg = msg
    
    @converse.command(name="list")
    async def converse_list(self, ctx, public: typing.Literal["true", "false"]="false"):
        """
        List of PastBunny messages
        """
        ephemeral = False if public == "true" else True
        async with aiosqlite.connect("bunny.db") as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("select * from past_bunny")
            messages = await cursor.fetchall()
            embeds = [PastBunnyMessage(self.bot, message) for message in messages]
            view = BunnyMessagesList(embeds)
            embed = embeds[0].embed
        msg = await ctx.reply(embed=embed, view=view, ephemeral=ephemeral)
        view.msg = msg

    @commands.hybrid_command(name="sylvia")
    async def sylvia(self, ctx: commands.Context):
        """
        Get a Sylvia Plath Quote
        """
        params = { "api": "2255", "apisecret": self.bot.settings.sylvia_key }
        async with self.bot.session.get("https://generatorfun.com/consumeapi.php", params=params) as data:
            response = await data.text()
            quote = response.split("-")[0].replace('\"', "").replace("\\", "").strip()
        embed = discord.Embed(description=quote, color=discord.Color.red())
        embed.set_author(name="Sylvia Plath", url="https://en.wikipedia.org/wiki/Sylvia_Plath")
        embed.set_thumbnail(url="https://cdn.britannica.com/67/19067-050-843F2405/Sylvia-Plath.jpg")
        await ctx.reply(embed=embed)


    @commands.Cog.listener(name="on_member_update")
    async def rules_accepted(self, before: discord.Member, after: discord.Member):
        rules_role = before.guild.get_role(945922913423482891)
        channel = after.guild.get_channel(940258352775192639)
        had_role = [role for role in before.roles if role is rules_role]
        has_role = [role for role in after.roles if role is rules_role]
        if not had_role and has_role:
            view = WelcomeView(after)
            view.msg = await channel.send(f"{after.display_name} has accepted the rules!", view=view)

class WelcomeView(discord.ui.View):
    def __init__(self, member: discord.Member):
        self.member = member
        super().__init__(timeout=3600)

    def on_timeout(self):
        self.welcome_button.disabled = True
        self.msg.edit(content=self.msg.content, view=self)

    @discord.ui.button(label="Say hi!", style=discord.ButtonStyle.green)
    async def welcome_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        stickers = [
            "bunny_hole_hi",
            "bunny_phone_hi",
            "bunny_seductive_wink_hi",
            "bunny_wink_hi",
            "BunnyWelcome",
            "kawaii-hi",
            "miss_bunny",
            "peach",
            "tree_hi",
            "wumpus"
        ]
        greetings = [
            f"{interaction.user.mention} says hello to {self.member.mention}",
            f"{self.member.mention} greetings from {interaction.user.mention}",
            f"{self.member.mention} you've been waved at by {interaction.user.mention}",
            f"{self.member.mention} welcome from {interaction.user.mention}",
            f"{interaction.user.mention} cheers for {self.member.mention}",
            f"{interaction.user.mention} greets {self.member.mention} with a hug"
        ]
        image = f"{random.choice(stickers)}.gif"
        greeting = random.choice(greetings)
        await interaction.response.send_message(greeting, file=discord.File(fp=f"images/{image}", filename=f"{image}"))
            

class BunnyMessagesList(discord.ui.View):
    def __init__(self, embeds):
        super().__init__()
        self.embeds = embeds
        self.page = 1
        self.max = len(embeds)
        self.msg_id = embeds[self.page - 1].id
        self.remove_item(self.confirm_delete).remove_item(self.cancel_delete)

    async def on_timeout(self):
        await self.msg.delete()

    @discord.ui.button(label="<<", style=discord.ButtonStyle.danger, custom_id="first", disabled=True)
    async def first(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = 1
        button.disabled = True
        self.prev.disabled = True
        self.next.disabled = False
        self.last.disabled = False
        self.current.label = self.page
        self.msg_id = self.embeds[self.page - 1].id
        await interaction.response.edit_message(embed=self.embeds[self.page - 1].embed, view=self)

    @discord.ui.button(label="<", style=discord.ButtonStyle.blurple, custom_id="prev", disabled=True)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = self.page - 1
        self.current.label = self.page
        if self.page == 1:
            button.disabled = True
            self.first.disabled = True
        self.next.disabled = False
        self.last.disabled = False
        self.msg_id = self.embeds[self.page - 1].id
        await interaction.response.edit_message(embed=self.embeds[self.page - 1].embed, view=self)

    @discord.ui.button(label="1", style=discord.ButtonStyle.gray, custom_id="current")
    async def current(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PageSelectModal(self))

    @discord.ui.button(label=">", style=discord.ButtonStyle.blurple, custom_id="next")
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = self.page + 1
        self.current.label = self.page
        if self.page == self.max:
            button.disabled = True
            self.last.disabled = True
        self.first.disabled = False
        self.prev.disabled = False
        self.msg_id = self.embeds[self.page - 1].id
        await interaction.response.edit_message(embed=self.embeds[self.page - 1].embed, view=self)

    @discord.ui.button(label=">>", style=discord.ButtonStyle.danger, custom_id="last")
    async def last(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = self.max
        self.current.label = self.page
        button.disabled = True
        self.next.disabled = True
        self.first.disabled = False
        self.prev.disabled = False
        self.msg_id = self.embeds[self.page - 1].id
        await interaction.response.edit_message(embed=self.embeds[self.page - 1].embed, view=self)

    @discord.ui.button(label="Delete Message", style=discord.ButtonStyle.gray)
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        mod_role = discord.utils.get(interaction.guild.roles, name=interaction.client.settings.mod_role)
        if [role for role in interaction.user.roles if role >= mod_role]:
            self.delete_id = self.msg_id
            self.remove_item(self.delete).add_item(self.confirm_delete).remove_item(self.close).add_item(self.cancel_delete).add_item(self.close)
            await interaction.response.edit_message(embed=self.embeds[self.page - 1].embed, view=self)
        else:
            await interaction.response.send_message("Only a mod can do that.", ephemeral=True)

    @discord.ui.button(label="Confirm Delete", style=discord.ButtonStyle.danger)
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        mod_role = discord.utils.get(interaction.guild.roles, name=interaction.client.settings.mod_role)
        if [role for role in interaction.user.roles if role >= mod_role]:
            jump = discord.ui.View().add_item(discord.ui.Button(label="Back to Message", style=discord.ButtonStyle.link, url=self.embeds[self.page - 1].url))
            async with aiosqlite.connect("bunny.db") as db:
                await db.execute("delete from past_bunny where past_bunny_id = ?", (self.delete_id,))
                await db.commit()
            self.embeds.remove(self.embeds[self.page - 1])
            if self.page == self.max:
                self.page = self.page - 1
                self.current.label = self.page
            self.max = self.max - 1
            self.remove_item(self.confirm_delete).remove_item(self.cancel_delete).remove_item(self.close).add_item(self.delete).add_item(self.close)
            await interaction.response.edit_message(embed=self.embeds[self.page - 1].embed, view=self)
            await interaction.followup.send("Message deleted.", ephemeral=True, view=jump)
        else:
            await interaction.response.send_message("Only a mod can do that.", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.primary)
    async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        mod_role = discord.utils.get(interaction.guild.roles, name=interaction.client.settings.mod_role)
        if [role for role in interaction.user.roles if role >= mod_role]:
            self.remove_item(self.confirm_delete).remove_item(self.cancel_delete).remove_item(self.close).add_item(self.delete).add_item(self.close)
            await interaction.response.edit_message(embed=self.embeds[self.page - 1].embed, view=self)
        else:
            await interaction.response.send_message("Only a mod can do that.", ephemeral=True)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.gray)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.msg.delete()

class PastBunnyMessage:
    def __init__(self, bot, message):
        # self.bot = bot
        self.url = message["message"]
        self.content = message["content"]
        self.created_by = bot.guilds[0].get_member(int(message["created_by"]))
        self.id = message["past_bunny_id"]
        embed = discord.Embed(title="PastBunny Message", color=discord.Color.blue())
        embed.description = self.content
        embed.add_field(name="Jump Link", value=f"[Original Message]({self.url})")
        embed.add_field(name="Added by", value=self.created_by.mention)
        self.embed = embed

class ConverseEnd(discord.ui.View):
    def __init__(self, user, url):
        self.user = user
        self.url = url
        super().__init__()
        self.remove_item(self.remove_chat).remove_item(self.remove_db).remove_item(self.cancel_delete)
        self.add_item(self.get_jump())

    def get_jump(self):
        return discord.ui.Button(label="🐇", style=discord.ButtonStyle.link, url=self.url)

    @discord.ui.button(label="🛑", style=discord.ButtonStyle.gray)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        mod_role = discord.utils.get(interaction.guild.roles, name=interaction.client.settings.mod_role)
        if not interaction.user.id == self.user and not [role for role in interaction.user.roles if role >= mod_role]:
            return await interaction.response.send_message("You cannot stop someone else from talking to PastBunny.")
        interaction.client.conversing.remove(interaction.user.id)
        await interaction.response.send_message(f"{interaction.user.display_name} is no longer conversing with PastBunny.")
        if not interaction.client.conversing:
            fun = interaction.client.get_cog("Fun")
            interaction.client.remove_listener(fun.converse_listener, "on_message")

    @discord.ui.button(label="🗑️", style=discord.ButtonStyle.danger)
    async def remove(self, interaction: discord.Interaction, button: discord.ui.Button):
        mod_role = discord.utils.get(interaction.guild.roles, name=interaction.client.settings.mod_role)
        if [role for role in interaction.user.roles if role >= mod_role]:
            self.clear_items().add_item(self.remove_chat).add_item(self.remove_db)
            await interaction.response.edit_message(content=interaction.message.content, view=self)
        elif interaction.user.id == self.user:
            await self.delete_chat(interaction)
        else:
            await interaction.response.send_message("You cannot do that.", ephemeral=True)

    @discord.ui.button(label="Remove from Chat", style=discord.ButtonStyle.primary)
    async def remove_chat(self, interaction: discord.Interaction, button: discord.ui.Button):
        mod_role = discord.utils.get(interaction.guild.roles, name=interaction.client.settings.mod_role)
        if [role for role in interaction.user.roles if role >= mod_role]:
            await self.delete_chat(interaction)

    @discord.ui.button(label="Remove from Chat and DB", style=discord.ButtonStyle.danger)
    async def remove_db(self, interaction: discord.Interaction, button: discord.ui.Button):
        mod_role = discord.utils.get(interaction.guild.roles, name=interaction.client.settings.mod_role)
        if [role for role in interaction.user.roles if role >= mod_role]:
            await self.msg.delete()
            await interaction.response.send_message("Deleting response and entry in database", ephemeral=True)
            async with aiosqlite.connect("bunny.db") as db:
                await db.execute("delete from past_bunny where message = ?", (self.url,))
                await db.commit()
            self.clear_items().add_item(self.stop).add_item(self.remove).add_item(self.get_jump())
            await interaction.edit_original_response(content="Entry deleted from database and message removed from chat.", view=discord.ui.View().add_item(self.get_jump()))

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.green)
    async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        mod_role = discord.utils.get(interaction.guild.roles, name=interaction.client.settings.mod_role)
        if [role for role in interaction.user.roles if role >= mod_role]:
            self.clear_items().add_item(self.stop).add_item(self.remove).add_item(self.get_jump())

    async def delete_chat(self, interaction: discord.Interaction):
        await self.msg.delete()
        await interaction.response.send_message("Response deleted.", ephemeral=True)

class PageSelectModal(discord.ui.Modal, title="Jump to Page"):
    def __init__(self, view):
        self.view = view
        self.page.label = f"Page 1-{self.view.max}"
        super().__init__()    
        
    page = discord.ui.TextInput(label=f"", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if int(self.page.value) > self.view.max:
            raise commands.BadArgument
        else:
            self.view.page = int(self.page.value)
            self.view.current.label = self.view.page
            if self.view.page == self.view.max:
                self.view.last.disabled = True
                self.view.next.disabled = True
            if self.view.page == 1:
                self.view.first.disabled = True
                self.view.prev.disabled = True
            else:
                self.view.last.disabled = False
                self.view.next.disabled = False
                self.view.prev.disabled = False
                self.view.first.disabled = False
            await interaction.response.edit_message(embed=self.view.embeds[self.view.page - 1].embed, view=self.view)

    async def on_error(self, interaction: discord.Interaction, error):
        if isinstance(error, commands.BadArgument):
            await interaction.response.send_message(f"Page Number must be between 1 and {self.view.max}.", ephemeral=True)
        else:
            print(error)
            await interaction.response.send_message("An unknown error occurred.", ephemeral=True)

class Drink():
    def __init__(self, json):
        self.name = json["strDrink"]
        self.glass = json["strGlass"]
        self.instructions = json["strInstructions"]
        self.ingredients = {}
        for x in range(14):
            index = f"strIngredient{x+1}"
            if json[index] is not None:
                measure = json[f"strMeasure{x+1}"] if json[f"strMeasure{x+1}"] is not None else ""
                self.ingredients[f"{json[index]}"] = measure
        self.image = json["strDrinkThumb"]


async def setup(bot):
    await bot.add_cog(Fun(bot))

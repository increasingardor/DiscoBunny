import datetime
import discord
from discord import app_commands
from discord.ext import commands
import zoneinfo

class EmbedsCreator(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.edit_embed_menu = app_commands.ContextMenu(name="Edit Embed", callback=self.edit_embed)
        self.bot.tree.add_command(self.edit_embed_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.edit_embed_menu)
        return await super().cog_unload()

    @app_commands.command(name="embed")
    @app_commands.default_permissions(manage_messages=True)
    async def create_embed(self, interaction: discord.Interaction, channel: discord.TextChannel):
        embed = discord.Embed(title="Title Here", color=discord.Color.blue(), description="Description and text here")
        view = DraftEmbed()
        view.add_item(view.jump)
        view.channel = channel
        view.remove_item(view.edit)
        await interaction.response.send_message(f"**Drafting Embed for {channel.mention}**", embed=embed, view=view, ephemeral=True)
        view.msg: discord.Message = await interaction.original_response()

    @app_commands.default_permissions(manage_messages=True)
    async def edit_embed(self, interaction: discord.Interaction, message: discord.Message):
        if message.author.id is not interaction.client.user.id:
            await interaction.response.send_message("Only embeds from DiscoBunny may be edited.", ephemeral=True)
        else:
            view = DraftEmbed()
            view.existing = message
            embed = message.embeds[0]
            if embed.fields:
                view.fields.options = []
                for index, field in enumerate(embed.fields):
                    view.fields.add_option(label=field.name, value=index)
                view.fields.disabled = False
            view.remove_item(view.publish)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            view.msg = await interaction.original_response()
    
class TestView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=10)

    @discord.ui.button(label="test")
    async def view_test_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

class DraftEmbed(discord.ui.View):
    def __init__(self):
        super().__init__()
        
    jump = discord.ui.Button(label="Color Codes", url="https://www.color-hex.com/", row=1)

    @discord.ui.button(label="Authored by Bunny", style=discord.ButtonStyle.primary)
    async def author_bunny(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.change_author(interaction, 940257449502466138)
        await interaction.response.edit_message(content=self.msg.content, embed=self.msg.embeds[0], view=self)

    @discord.ui.button(label="Authored by Me", style=discord.ButtonStyle.primary)
    async def author_me(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.change_author(interaction, interaction.user.id)
        await interaction.response.edit_message(content=self.msg.content, embed=self.msg.embeds[0], view=self)

    def change_author(self, interaction: discord.Interaction, user: int=0):
        author = interaction.client.guilds[0].get_member(user)
        self.msg.embeds[0].set_author(name=author.display_name, icon_url=author.display_avatar.url)

    @discord.ui.button(label="Embed Contents", style=discord.ButtonStyle.green, emoji="🪧", row=1)
    async def contents(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalContents(self))

    @discord.ui.button(label="Images", style=discord.ButtonStyle.green, emoji="🖼️", row=1)
    async def images(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalImages(self))

    @discord.ui.button(label="Footer", style=discord.ButtonStyle.green, emoji="👣", row=1)
    async def footer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalFooter(self))

    @discord.ui.button(label="Random Color", style=discord.ButtonStyle.green, emoji="🎨")
    async def random_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.msg.embeds[0].color = discord.Color.random()
        await interaction.response.edit_message(embed=self.msg.embeds[0], view=self)

    @discord.ui.select(placeholder="Fields", disabled=True, options=[discord.SelectOption(label="Field 1", value="1")], row=2)
    async def fields(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_field = select.values[0]
        for option in select.options:
            if option.value == select.values[0]:
                option.default = True
            else:
                option.default = False
        await interaction.response.edit_message(embed=self.msg.embeds[0], view=self)

    @discord.ui.button(label="Add Field", style=discord.ButtonStyle.gray, emoji="➕", row=3)
    async def add_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalFieldAdd(self))

    @discord.ui.button(label="Edit Field", style=discord.ButtonStyle.gray, emoji="📝", disabled=True, row=3)
    async def edit_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalFieldEdit(self))

    @discord.ui.button(label="Remove Field", style=discord.ButtonStyle.gray, emoji="➖", disabled=True, row=3)
    async def remove_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.msg.embeds[0].remove_field(int(self.fields.values[0]))
        self.fields.options = []
        if not self.msg.embeds[0].fields:
            self.toggle_fields()
            self.fields.add_option(label="Field 1", value="0")
        else:
            for index, field in enumerate(self.msg.embeds[0].fields):
                self.fields.add_option(label=field.name, value=index)
        await interaction.response.edit_message(embed=self.msg.embeds[0], view=self)

    def toggle_fields(self):
        self.fields.disabled = not self.fields.disabled
        self.edit_field.disabled = not self.edit_field.disabled
        self.remove_field.disabled = not self.remove_field.disabled

    @discord.ui.button(label="Publish!", style=discord.ButtonStyle.danger, row=4)
    async def publish(self, interaction: discord.Interaction, button: discord.ui.Button):
        msg = await self.channel.send(embed=self.msg.embeds[0])
        jump = discord.ui.Button(label="Jump to Embed", url=msg.jump_url)
        view = discord.ui.View()
        view.add_item(jump)
        await interaction.response.send_message("Embed Published!", view=view, ephemeral=True)

    @discord.ui.button(label="Publish Edit", style=discord.ButtonStyle.danger, row=4)
    async def edit(self, interaction: discord.Interaction, button: discord.ui.Button):
        msg = await self.existing.edit(embed=self.msg.embeds[0])
        jump = discord.ui.Button(label="Jump to Embed", url=msg.jump_url)
        view = discord.ui.View()
        view.add_item(jump)
        await interaction.response.send_message("Embed Published!", view=view, ephemeral=True)

#     @app_commands.command(name="test")
#     async def test(self, inter: discord.Interaction):
#         view = TestView()
#         view.msg = inter.original_response()
#         await inter.response.send_message(view=view)
    

#     @commands.Cog.listener('on_interaction')
#     async def on_inter(self, inter: discord.Interaction):
#         print(f"Interaction triggered")
#         if inter.type == discord.InteractionType.component:
#             print(f"Component triggered")
#             msg = await inter.original_response()
#             x = await msg.view.wait()
#             print(x)

# class TestView(discord.ui.View):
#     def __init__(self):
#         super().__init__(timeout=10)

#     @discord.ui.button(label="test")
#     async def test(self, inter: discord.Interaction, button: discord.ui.Button):
#         await inter.response.send_message("This was a test")

class ModalContents(discord.ui.Modal, title="Modal Contents"):
    def __init__(self, view: discord.ui.View):
        self.view = view
        self.title_field.default = self.view.msg.embeds[0].title
        self.url_field.default = self.view.msg.embeds[0].url
        self.description_field.default = self.view.msg.embeds[0].description
        print(hex(self.view.msg.embeds[0].color.value))
        color = hex(self.view.msg.embeds[0].color.value)
        self.color_field.default = f"#{color[2:].zfill(6)}"
        super().__init__()

    title_field = discord.ui.TextInput(label="Title")
    url_field = discord.ui.TextInput(label="Title URL", required=False)
    color_field = discord.ui.TextInput(label="Hexadecimal Color")
    description_field = discord.ui.TextInput(label="Description", style=discord.TextStyle.long)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.msg.embeds[0].title = self.title_field.value
        self.view.msg.embeds[0].url = self.url_field.value
        self.view.msg.embeds[0].description = self.description_field.value
        self.view.msg.embeds[0].color = discord.Color.from_str(self.color_field.value)
        await interaction.response.edit_message(embed=self.view.msg.embeds[0], view=self.view)

    async def on_error(self, interaction: discord.Interaction, error):
        print(error)
        pass

class ModalImages(discord.ui.Modal, title="Images"):
    def __init__(self, view: discord.ui.View):
        self.view = view
        self.image_field.default = self.view.msg.embeds[0].image.url
        self.thumb_field.default = self.view.msg.embeds[0].thumbnail.url
        super().__init__()

    image_field = discord.ui.TextInput(label="Image URL", required=False)
    thumb_field = discord.ui.TextInput(label="Thumbnail URL", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.msg.embeds[0].set_image(url=self.image_field.value)
        self.view.msg.embeds[0].set_thumbnail(url=self.thumb_field.value)
        await interaction.response.edit_message(embed=self.view.msg.embeds[0], view=self.view)

class ModalFooter(discord.ui.Modal, title="Footer"):
    def __init__(self, view: discord.ui.View):
        self.view = view
        self.text_field.default = self.view.msg.embeds[0].footer.text
        self.icon_url_field.default = self.view.msg.embeds[0].footer.icon_url
        if self.view.msg.embeds[0].timestamp is not None:
            self.timestamp_field.default = self.view.msg.embeds[0].timestamp.strftime("%m/%d/%Y")
        super().__init__()

    text_field = discord.ui.TextInput(label="Text", required=False)
    icon_url_field = discord.ui.TextInput(label="Icon URL", required=False)
    timestamp_field = discord.ui.TextInput(label="Timestamp", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.msg.embeds[0].set_footer(text=self.text_field.value, icon_url=self.icon_url_field.value)
        dateparts = [int(num) for num in self.timestamp_field.value.split("/")]
        date = datetime.datetime(month=dateparts[0], day=dateparts[1], year=dateparts[2], tzinfo=zoneinfo.ZoneInfo("US/Central"))
        self.view.msg.embeds[0].timestamp = date
        await interaction.response.edit_message(embed=self.view.msg.embeds[0], view=self.view)

class ModalFieldAdd(discord.ui.Modal, title="Add Field"):
    def __init__(self, view: discord.ui.View):
        self.view = view
        self.inline_field.default = "False"
        super().__init__()

    name_field = discord.ui.TextInput(label="Field Name", required=False)
    value_field = discord.ui.TextInput(label="Field Value", required=False)
    inline_field = discord.ui.TextInput(label="Inline (true/false)", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        inline = True if self.inline_field.value.lower() == "true" else False
        self.view.msg.embeds[0].add_field(name=self.name_field.value, value=self.value_field.value, inline=inline)
        if self.view.fields.options[0].label == "Field 1":
            self.view.fields.options.pop()
            self.view.toggle_fields()
        self.view.fields.add_option(label=self.name_field.value, value=len(self.view.fields.options))
        await interaction.response.edit_message(embed=self.view.msg.embeds[0], view=self.view)

class ModalFieldEdit(discord.ui.Modal, title="Edit Field"):
    def __init__(self, view: discord.ui.View):
        self.view = view
        self.index = int(self.view.fields.values[0])
        field = self.view.msg.embeds[0].fields[self.index]
        self.name_field.default = field.name
        self.value_field.default = field.value
        self.inline_field.default = str(field.inline)
        super().__init__()

    name_field = discord.ui.TextInput(label="Field Name", required=False)
    value_field = discord.ui.TextInput(label="Field Value", required=False)
    inline_field = discord.ui.TextInput(label="Inline (true/false)", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        inline = True if self.inline_field.value.lower() == "true" else False
        self.view.msg.embeds[0].set_field_at(self.index, name=self.name_field.value, value = self.value_field.value, inline = inline)
        self.view.fields.options[self.index].label = self.name_field.value
        await interaction.response.edit_message(embed=self.view.msg.embeds[0], view=self.view)

async def setup(bot: commands.Bot):
    await bot.add_cog(EmbedsCreator(bot))
import datetime
import random
import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands

@app_commands.default_permissions(moderate_members=True)
class Giveaway(commands.GroupCog, name="giveaway"):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="start")
    @app_commands.describe(channel="Channel to publish giveaway in")
    async def start_giveaway(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """
        Start a new giveaway
        """
        await interaction.response.send_modal(GiveawayCreateModal(channel))

    @app_commands.command(name="winner")
    @app_commands.describe(giveaway_id="The id of the giveaway to pick a winner in", channel="The channel to publish the winner in")
    async def get_winner(self, interaction: discord.Interaction, giveaway_id: int, channel: discord.TextChannel):
        """
        Pick a winner in a giveaway
        """
        winner_data = await winner_select(giveaway_id)
        winner = interaction.guild.get_member(winner_data["user_id"])
        view = WinnerSelectView(giveaway_id, winner, channel)
        await interaction.response.send_message(f"The winner is {winner.mention}! Publish, or pick new winner?", view=view, ephemeral=True)

    @app_commands.command(name="end")
    @app_commands.describe(giveaway_id="The ID of the giveaway to end")
    async def end_giveaway(self, interaction: discord.Interaction, giveaway_id: int):
        """
        End a giveaway
        """
        async with aiosqlite.connect("bunny.db") as db:
            db.row_factory = aiosqlite.Row
            winners_data = await db.execute("select * from giveaway_entries where giveaway_id = ? and won = 1", (giveaway_id,))
            winners = await winners_data.fetchall()
            if winners:
                data = await db.execute("update giveaways set ended = 1 where giveaway_id = ? returning name", (giveaway_id,))
                giveaway = await data.fetchone()
                await db.commit()
                await interaction.response.send_message(f"{giveaway['name']} ended.", ephemeral=True)
            else:
                await interaction.response.send_message(f"This giveaway has no winners yet. Are you sure you want to end it?", view=ConfirmEndView(giveaway_id), ephemeral=True)

class ConfirmEndView(discord.ui.View):
    def __init__(self, giveaway_id: int):
        self.giveaway_id = giveaway_id
        super().__init__()

    @discord.ui.button(label="End Giveaway", style=discord.ButtonStyle.danger)
    async def end_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with aiosqlite.connect("bunny.db") as db:
            await db.execute("update giveaways set ended = 1 where giveaway_id = ?", (self.giveaway_id, ))
            await db.commit()
            await interaction.response.edit_message(content=f"Giveaway ended.", view=None)

class GiveawayCreateModal(discord.ui.Modal, title="Create Giveaway"):
    def __init__(self, channel: discord.TextChannel):
        self.channel = channel
        super().__init__()

    name = discord.ui.TextInput(label="Giveaway Name")
    thumbnail = discord.ui.TextInput(label="Thumbnail URL", required=False)
    image = discord.ui.TextInput(label="Image URL", required=False)
    description = discord.ui.TextInput(label="Giveaway Description", style=discord.TextStyle.long)

    async def on_submit(self, interaction: discord.Interaction):
        async with aiosqlite.connect("bunny.db") as db:
            db.row_factory = aiosqlite.Row
            await db.execute("create table if not exists giveaways (giveaway_id integer primary key, name text, ended integer)")
            await db.execute("create table if not exists giveaway_entries (entry_id integer primary key, giveaway_id integer, user_id integer, won integer, unique(giveaway_id, user_id))")
            data = await db.execute("insert into giveaways (name, ended) values (?, ?) returning giveaway_id, name", (self.name.value, 0))
            giveaway = await data.fetchone()
            await db.commit()
        embed = discord.Embed(title=self.name.value, description=self.description.value, timestamp=discord.utils.utcnow(), color=discord.Color.blue())
        embed.set_thumbnail(url=self.thumbnail.value)
        embed.set_image(url=self.image.value)
        embed.add_field(name="Entries", value=0)
        embed.set_footer(text=f"ID: {giveaway['giveaway_id']}")
        giveaway_view = GiveawayView(giveaway["giveaway_id"])
        msg: discord.Message = await self.channel.send(embed=embed, view=giveaway_view)
        giveaway_view.msg = msg
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Jump to Message!", url=msg.jump_url))
        await interaction.response.send_message(f"Giveaway created, published in {self.channel.mention}!", view=view, ephemeral=True)

class GiveawayView(discord.ui.View):
    def __init__(self, giveaway_id):
        self.giveaway_id = giveaway_id
        self.entries = 0
        super().__init__(timeout=None)

    @discord.ui.button(label="Enter giveaway!", style=discord.ButtonStyle.primary, emoji="🐰")
    async def enter_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with aiosqlite.connect("bunny.db") as db:
            db.row_factory = aiosqlite.Row
            data = await db.execute("select * from giveaways where giveaway_id = ?", (self.giveaway_id,))
            giveaway = await data.fetchone()
            if giveaway["ended"]:
                button.disabled = True
                await interaction.response.edit_message(view=self)
                return await interaction.followup.send("This giveaway has already ended.", ephemeral=True)
            try:
                await db.execute("insert into giveaway_entries (giveaway_id, user_id, won) values (?, ?, ?)", (self.giveaway_id, interaction.user.id, 0))
                await db.commit()
            except aiosqlite.IntegrityError:
                await interaction.response.send_message("You have already entered this giveaway!", ephemeral=True)
            else:
                self.entries +=1
                embed = self.msg.embeds[0]
                embed.clear_fields().add_field(name="Entries", value=self.entries)
                await interaction.response.edit_message(embed=embed)
                await interaction.followup.send("You've entered the giveaway! Best of luck!", ephemeral=True)
    
class WinnerSelectView(discord.ui.View):
    def __init__(self, giveaway_id: int, user: discord.Member, channel: discord.TextChannel):
        self.giveaway_id = giveaway_id
        self.user = user
        self.channel = channel
        super().__init__()

    @discord.ui.button(label="Publish Winner", style=discord.ButtonStyle.gray)
    async def publish_winner(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with aiosqlite.connect("bunny.db") as db:
            db.row_factory = aiosqlite.Row
            data = await db.execute("select name from giveaways where giveaway_id = ?", (self.giveaway_id,))
            giveaway = await data.fetchone()
            embed = discord.Embed(title="Winner! Winner! Winner!", color=discord.Color.blurple())
            embed.description = f"The winner of the {giveaway['name']} giveaway is!\n\n{self.user.mention}!\n\n Congratulations! A mod will contact you shortly to give you your prize!"
            msg = await self.channel.send(content=self.user.mention, embed=embed)
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Jump to Message!", url=msg.jump_url))
            await interaction.response.edit_message(content="Winner published!", view=None)
            await db.execute("update giveaway_entries set won = 1 where giveaway_id = ? and user_id = ?", (self.giveaway_id, self.user.id))
            await db.commit()

    @discord.ui.button(label="Re-pick", style=discord.ButtonStyle.danger)
    async def repick_winner(self, interaction: discord.Interaction, button: discord.ui.Button):
        winner_data = await winner_select(self.giveaway_id)
        winner = interaction.guild.get_member(winner_data["user_id"])
        self.user = winner
        await interaction.response.edit_message(content=f"New winner selected: {winner.mention}", view=self)

async def winner_select(id: int):
    async with aiosqlite.connect("bunny.db") as db:
        db.row_factory = aiosqlite.Row
        data = await db.execute("select entry_id, user_id from giveaway_entries where giveaway_id = ? and won = ?", (id, 0))
        entries = await data.fetchall()
        return random.choice(entries)

async def setup(bot):
    await bot.add_cog(Giveaway(bot))
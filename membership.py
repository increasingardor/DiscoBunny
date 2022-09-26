import discord

# Modal to get info from new people to Bunny's membership
class MembershipInfo(discord.ui.Modal, title="Additional User Information"):
    # Defines a text field
    snap = discord.ui.TextInput(label="Email Address", required=True)

    # The submit action of the modal. Takes info entered, creates embed and
    # and sends it to a channel. Sends ephemeral response to submitting user.
    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(color=discord.Color.brand_green(), title="Email Address Information")
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="Tier", value=interaction.user.top_role.name)
        embed.add_field(name="Email Address", value=self.snap.value, inline=False)
        channel = interaction.guild.get_channel(1012456365278638110)
        await channel.send(embed=embed)
        await interaction.response.send_message("Thanks! We'll send you your Fansly link soon.", ephemeral=True)

# Button to launch the modal. Sent in a message by another command.
class GetMemberInfo(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Submit Info", style=discord.ButtonStyle.blurple, custom_id="member_view")
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MembershipInfo())

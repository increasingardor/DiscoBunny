from datetime import datetime
import typing
import zoneinfo
import discord
from discord import app_commands
from discord.ext import tasks, commands
import aiosqlite
import sqlite3
from jishaku.paginators import PaginatorInterface

class Reminders(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    async def cog_load(self):
        await self.remind_loop.start()

    async def cog_unload(self):
        self.remind_loop.stop()

    @tasks.loop()
    async def remind_loop(self):
        async with aiosqlite.connect("bunny.db", detect_types=sqlite3.PARSE_DECLTYPES) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("create table if not exists reminders (reminder_id integer primary key, user_id integer, reminder_text text, start_time text, end_time text, completed integer)")
            data = await db.execute("select reminder_id, user_id, reminder_text, start_time, end_time, completed from reminders where completed = 0 order by end_time limit 1")
            next = await data.fetchall()
        
        if not next:
            print("next is None")
            self.remind_loop.cancel()
        else:
            next_reminder = next[0]
            try:
                date = datetime.strptime(next_reminder["end_time"], "%Y-%m-%d %H:%M:%S.%f%z")
            except ValueError as e:
                date = datetime.strptime(next_reminder["end_time"], "%Y-%m-%d %H:%M:%S%z")

            await discord.utils.sleep_until(date)

            user = self.bot.guilds[0].get_member(next_reminder["user_id"])
            channel = self.bot.guilds[0].get_channel(int(self.bot.settings.reminder_channel))
            embed = discord.Embed(title=f"Reminder for {user.display_name}", description=next_reminder["reminder_text"], color=discord.Color.green())
            embed.set_footer(text=f"Reminder set at")
            embed.timestamp = datetime.strptime(next_reminder["start_time"], "%Y-%m-%d %H:%M:%S.%f%z")
            await channel.send(user.mention, embed=embed)

            async with aiosqlite.connect("bunny.db") as db:
                await db.execute("update reminders set completed = 1 where reminder_id = ?", (next_reminder["reminder_id"],))
                await db.commit()

    @remind_loop.before_loop
    async def before_remind_loop(self):
        await self.bot.wait_until_ready()

    reminder = app_commands.Group(name="reminders", description="Reminders")

    @reminder.command(name="set")
    async def set_reminder(self, interaction: discord.Interaction):
        """
        Set a reminder
        """
        date = datetime.now(tz=zoneinfo.ZoneInfo("US/Central"))
        modal = ReminderModal(date)
        await interaction.response.send_modal(modal)
        await modal.wait()

        if self.remind_loop.is_running():
            await self.remind_loop.restart()
        else:
            await self.remind_loop.start()
        
    @reminder.command(name="list")
    async def list_reminders(self, interaction: discord.Interaction, which: typing.Literal["upcoming", "past", "all"]="upcoming"):
        """
        List your reminders
        """
        if which != "all":
            completed = 0 if which == "upcoming" else 1
            async with aiosqlite.connect("bunny.db") as db:
                db.row_factory = aiosqlite.Row
                data = await db.execute("select reminder_id, user_id, reminder_text, start_time, end_time, completed from reminders where user_id = ? and completed = ?", (interaction.user.id, completed))
                reminders = await data.fetchall()
        else:
            async with aiosqlite.connect("bunny.db") as db:
                db.row_factory = aiosqlite.Row
                data = await db.execute("select reminder_id, user_id, reminder_text, start_time, end_time, completed from reminders where user_id = ?", (interaction.user.id, completed))
                reminders = await data.fetchall()
        embed = discord.Embed(title=f"Reminders List")
        if reminders:
            description = f"For {interaction.user.mention}\n\n" + "\n\n".join([f"**{reminder['end_time'].split('.')[0]} Central**\n*Set on {reminder['start_time'].split('.')[0]}*\n{reminder['reminder_text']}" for reminder in reminders])
        else:
            description = f"For {interaction.user.mention}\n\n*No reminders found*"
        embed.description = description
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ReminderModal(discord.ui.Modal, title="Reminder! Fill date, or hours/minutes."):
    def __init__(self, date):
        self.curr_date = date
        self.date.label = f"Date and time-currently {self.curr_date.strftime('%Y-%m-%d %H:%M')}"
        super().__init__()

    date = discord.ui.TextInput(label=f"Date and time (YYYY-MM-DD HH:MM)", required=False)
    hours = discord.ui.TextInput(label="Hour", required=False)
    minutes = discord.ui.TextInput(label="Minutes", required=False)
    text = discord.ui.TextInput(label="Reminder Text", required=True, style=discord.TextStyle.long)

    async def on_submit(self, interaction: discord.Interaction):
        if self.date.value and (self.hours.value or self.minutes.value):
            return await interaction.response.send_message("Please use either date, or a combination of hours and/or minutes.", ephemeral=True)
        else:
            new_date = datetime.now(tz=zoneinfo.ZoneInfo("US/Central")).replace(second=0, microsecond=0)
            if self.date.value:
                entered_date = datetime.strptime(self.date.value, "%Y-%m-%d %H:%M")
                new_date = new_date.replace(year=entered_date.year, month=entered_date.month, day=entered_date.day, hour=entered_date.hour, minute=entered_date.minute)
            if self.hours.value:
                new_date = new_date.replace(hour=new_date.hour + int(self.hours.value))
            if self.minutes.value:
                new_date = new_date.replace(minute=new_date.minute + int(self.minutes.value))
            async with aiosqlite.connect("bunny.db") as db:
                db.row_factory = aiosqlite.Row
                await db.execute("create table if not exists reminders (reminder_id integer primary key, user_id integer, reminder_text text, start_time text, end_time text, completed integer)")
                await db.execute("insert into reminders (user_id, reminder_text, start_time, end_time, completed) values (?, ?, ?, ?, ?)", (interaction.user.id, self.text.value, datetime.now(tz=zoneinfo.ZoneInfo("US/Central")), new_date, 0))
                await db.commit()
        
        await interaction.response.send_message(f"You will be reminded at {new_date.strftime('%Y-%m-%d %H:%M')} with the message:\n```\n{self.text.value}\n```", ephemeral=True)
        self.stop()
        
        

async def setup(bot):
    await bot.add_cog(Reminders(bot))
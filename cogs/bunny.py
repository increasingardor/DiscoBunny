import discord
from discord.ext import commands
from discord import app_commands
import gspread
import validators
import pytz
from dotenv import load_dotenv
import os
import asyncio
import asyncpraw
import random
import datetime
import time
import re
import checks
import aiosqlite
import typing
import traceback
import membership

class Bunny(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        load_dotenv()
        self.responses = ["We're hunting wabbit...", "Trying to find Bunny...", "Searching for Bunny...", "Picking a random Bunny post..."]
        self.found = ["Found a wabbit, found a wabbit, found a WABBIT!", "Found Bunny!", "Bunny located.", "Here's your random Bunny..."]
        self.numberwang = False
        self.gag = False
        self.bot = bot

    @commands.group(invoke_without_command=True, aliases=["b"])
    @checks.is_level_5()
    async def bunny(self, ctx, tag: typing.Optional[str]=None):
        """Get a random Bunny Reddit post

        Retrieves a random post from Bunny's Reddit profile. This could be a text post, a post from a NSFW subreddit, or a post from a SFW subreddit post. Sometimes this will include a preview image, and sometimes it will not, but will always include a link to the actual post. Optionally, a tag may be provided to narrow the results. Must be Level 5 or higher to use.
        """
        if ctx.invoked_subcommand is None:
            reddit = asyncpraw.Reddit(
                client_id=await self.bot.settings.get("client_id"),#self.CLIENT_ID,
                client_secret=await self.bot.settings.get("client_secret"),#,self.CLIENT_SECRET,
                user_agent="BunnitBot 1.1"
            )

            rand_response = random.randint(0, len(self.responses) - 1)
            await ctx.send(self.responses[rand_response])
            post_list = []
            if tag is None:
                result = await self.bot.db.execute("select reddit_id, post_id from posts")
                posts = await result.fetchall()
            else:
                result = await self.bot.db.execute("select tag_id from tags where name = ?", (tag,))
                tag_entry = await result.fetchone()
                if tag_entry:
                    result = await self.bot.db.execute("select p.reddit_id, p.post_id from posts p inner join post_tags pt on p.post_id = pt.post_id inner join tags t on pt.tag_id = t.tag_id where t.tag_id = ?", (tag_entry["tag_id"],))
                    posts = await result.fetchall()
                else:
                    await ctx.send(f"Tag `{tag}` does not exist, getting random post.")
                    result = await self.bot.db.execute("select reddit_id, post_id from posts")
                    posts = await result.fetchall()
            post_list = [post for post in posts]#[post["reddit_id"] for post in posts]
            random_post = random.choice(post_list)
            selected_post = await reddit.submission(id=random_post["reddit_id"])#f"{random_post['reddit_id']}")
            result = await self.bot.db.execute("select t.name from tags t inner join post_tags pt on t.tag_id = pt.tag_id where pt.post_id = ?", (random_post["post_id"],))
            post_tags = await result.fetchall()
            selected_post.tags = " ".join([f"`{post_tag['name']}`" for post_tag in post_tags])
            await ctx.send(self.found[rand_response])
            image_url = self.get_image_url(selected_post)
            embed = self.embed_from_post(ctx, selected_post, image_url)
            if not ctx.channel.is_nsfw() or ctx.channel.id == 940258352775192639:
                embed.set_image(url=None)
                await ctx.send(embed=embed)
                await ctx.send(f"||{image_url} ||")
            else:
                await ctx.send(embed=embed)
            await reddit.close()

#    async def get_posts(self, tag=0):
#        with self.bot.db:
#            if tag > 0:
#                posts = await self.bot.db.execute("select p.reddit_id from posts p inner join post_tags pt on p.post_id = pt.post_id inner join tags t on pt.tag_id = t.tag_id where t.tag_id = ?", (tag,)).fetchall()
#                return [post[0] for post in posts]
#            else:
#                posts = await self.bot.db.execute("select reddit_id from posts").fetchall()
#                return [post[0] for post in posts]

    def embed_from_post(self, ctx, selected_post, image_url):
        embed = discord.Embed(title=selected_post.title, url=f"http://old.reddit.com{selected_post.permalink}", color=2447966)
        embed.set_author(name="Bunny", url="http://reddit.com/u/heyitsjustbunny")
        if image_url != None:
            embed.set_image(url=image_url)
        embed.timestamp = datetime.datetime.utcfromtimestamp(selected_post.created_utc)
        embed.set_footer(text=f"Posted to {selected_post.subreddit.display_name} • Requested by {ctx.author.display_name} • id {selected_post.id}")
        embed.description = f"Tags: {selected_post.tags}"
        return embed

    async def add_to_sheet(self, spreadsheet_id, sheet_name, values):
        gc = gspread.service_account(await self.bot.settings.get("service_account"))
        spreadsheet = gc.open_by_key(spreadsheet_id)
        sheet = spreadsheet.worksheet(sheet_name)
        sheet.append_row(values)

    def get_image_url(self, post):
        if post.url.find("imgur") > -1:
            return post.url.replace("gifv", "jpg")
        elif post.title.find("Removed by Reddit") > -1:
            return "https://www.publicdomainpictures.net/pictures/280000/nahled/not-found-image-15383864787lu.jpg"
        elif post.url.find("gallery") > -1:
            for i in post.media_metadata.items():
                return i[1]["p"][0]["u"]
                break
        else:
            try:
                return post.preview["images"][0]["source"]["url"]
            except:
                return None    

    @bunny.error
    async def bunny_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send("You must be at least Level 5 to do that. Engage in chat and level up, and you'll be able to do that in no time!")
        else:
            raise error

    @bunny.command(name="untagged")
    @checks.is_mod()
    async def bunny_untagged(self, ctx):
        posts = await self.get_untagged_posts()
        if posts:
            return await self.get_tags(ctx, posts)
        else:
            return await ctx.send("No untagged posts!")

    async def get_untagged_posts(self):
        result = await self.bot.db.execute("select p.post_id, p.reddit_id from posts p left join post_tags pt on p.post_id = pt.post_id where pt.tag_id is null order by p.post_id")
        posts = await result.fetchall()
#        await self.bot.db.commit()
        return posts


    async def get_tags(self, ctx, posts):
        def is_author(msg):
            return msg.author.id == ctx.author.id and msg.channel == ctx.channel
        
        def is_yes(msg):
            return msg.lower() == "y" or msg.lower() == "yes"

        def is_no(msg):
            return msg.lower() == "n" or msg.lower() == "no"

        post = posts.pop()
        reddit = asyncpraw.Reddit(
            client_id=await self.bot.settings.get("client_id"),#self.CLIENT_ID,
            client_secret=await self.bot.settings.get("client_secret"),#self.CLIENT_SECRET,
            user_agent="BunnitBot 1.1",
        )
        print(post["reddit_id"])
        reddit_post = await reddit.submission(id=post["reddit_id"])
        await ctx.send(f"Please provide space separated tags for this post:\nhttp://old.reddit.com{reddit_post.permalink}") 
        reddit.close()
        
        try:
            msg = await self.bot.wait_for("message", check=is_author, timeout=300)
        except asyncio.TimeoutError:
            return await ctx.send("Tagging ended due to no response.")
        else:
            if msg.content.lower().startswith("done"):
                return await ctx.send(f"Ended tagging. Last post untagged. {len(posts)} posts still untagged.")
            elif msg.content.lower().startswith("skip"):
                if posts:
                    await ctx.send("Post skipped!")
                    await self.get_tags(ctx, posts)
            else:
                tags = []
                for tag in msg.content.lower().split():
                    tag = tag
                    tag_id = await self.process_tag(ctx, tag)
                    if tag_id:
                        await self.tag_post(tag_id, post[0])
                        tags.append(tag)
                await ctx.send(f"Post tagged with {' '.join(tags)}")
                if posts:
                    await ctx.send("Tag another post (y/n)?")
                    try:
                        msg = await self.bot.wait_for("message",check=is_author, timeout=120)
                    except asyncio.TimeoutError:
                        return await ctx.send(f"Tagging ended due to no response. {len(posts)} still untagged.")
                    else:
                        if is_yes(msg.content):
                            await self.get_tags(ctx, posts)
                        elif is_no(msg.content):
                            return await ctx.send(f"Tagging ended. {len(posts)} still untagged.")
                else:
                    posts_db = await self.get_untagged_posts()
                    if posts_db:
                        await ctx.send(f"No posts remain to tag, but there are {len(posts_db)} still untagged in the database, possibly skipped in this session. Review these posts for tagging (y/n)")
                        try:
                            msg = await self.bot.wait_for("message", check=is_author, timeout=15)
                        except asyncio.TimeoutError:
                            return await ctx.send("Tagging ended due to no response.")
                        else:
                            if is_yes(msg.content):
                                await self.get_tags(posts_db)
                            if is_no(msg.content):
                                return await ctx.send("Tagging ended.")
                    

    async def process_tag(self, ctx, tag):
        def is_yes(msg_content):
            return msg_content.lower() == "y" or msg_content.lower() == "yes"

        def is_no(msg_content):
            return msg_content.lower() == "n" or msg_content.lower() == "no"

        def is_author(msg):
            return msg.author.id == ctx.author.id and msg.channel == ctx.channel
        
#        with self.bot.db:
        row = await self.bot.db.execute("select tag_id from tags where name = ?", (tag,))
        result = await row.fetchone()
        if not result:
            await ctx.send(f"Tag {tag} does not exist in the database - create it (y/n)?")
            try:
                msg = await self.bot.wait_for("message", check=is_author, timeout=15.0)
            except asyncio.TimeoutError:
                await ctx.send(f"Tag {tag} not inserted due to no response.")
                return None
            else:
                if is_yes(msg.content):
                    await self.add_tag(ctx, tag)                    
                    row = await self.bot.db.execute("select tag_id from tags where name = ?", (tag,))
                    reslt = await row.fetchone()
                elif is_no(msg.content):
                    await ctx.send(f"Tag {tag} not inserted.")
                    return None
        return result["tag_id"]

    async def add_tag(self, ctx, tag):
        await self.bot.db.execute("insert into tags (name) values (?)", (tag,))
        await self.bot.db.commit()
        await ctx.send(f"Tag {tag} inserted.")

    async def tag_post(self, tag_id, post_id):
        await self.bot.db.execute("insert into post_tags (post_id, tag_id) values (?,?)", (post_id, tag_id))
        await self.bot.db.commit()

    @bunny.command(name="tag")
    @checks.is_mod()
    async def bunny_tag(self, ctx, reddit_id, *tags):
        if tags:
            row = await self.bot.db.execute("select post_id from posts where reddit_id = ?", (reddit_id,))
            post_db = await row.fetchone()
            if not post_db:
                return await ctx.send(f"A post with the id {reddit_post} cannot be found.")
            else:
                post_id = post_db["post_id"]
                rows = await self.bot.db.execute("select t.name from tags t inner join post_tags pt on t.tag_id = pt.tag_id where pt.post_id = ?", (post_id,))
                tags_db = await rows.fetchall()
                existing_tags = [tag["name"] for tag in tags_db]
                duplicates = [tag for tag in tags if tag in existing_tags]
                new_tags = [tag for tag in tags if tag not in existing_tags]
                if duplicates:
                    await ctx.send(f"Skipping the following tags, as this post already has them: {' '.join(duplicates)}")
                if new_tags:
                    added_tags = []
                    for tag in new_tags:
                        tag_id = await self.process_tag(ctx, tag)
                        if tag_id:
                            await self.tag_post(tag_id, post_id)
                            added_tags.append(tag)
                    return await ctx.send(f"Added tags {' '.join(added_tags)}")
                else:
                    await ctx.send("You provided no new tags. No changes made.") 

    @bunny.command(name="tags")
    async def bunny_tags(self, ctx):
        rows = await self.bot.db.execute("select t.name, count(pt.tag_id) as count from tags t inner join post_tags pt on t.tag_id = pt.tag_id group by t.name order by count(pt.tag_id) desc")
        tags = await rows.fetchall()
        tags_list = [f"{tag['name']}\t{tag['count']}" for tag in tags if tag[1] > 4]
        tags_msg = "\n".join(tags_list)
        await ctx.send(f"```Tag\tCount\n---------------\n{tags_msg}\n```")

    @bunny.command(name="del-post")
    @checks.is_mod()
    async def del_post(self, ctx, reddit_id):
        rows = await self.bot.db.execute("select post_id from posts where reddit_id = ?", (reddit_id,))
        post = await rows.fetchone()
        if post is not None:
            await self.bot.db.execute("delete from post_tags where post_id = ?", (post,))
            await self.bot.db.execute("delete from posts where post_id = ?", (post,))
            await self.bot.db.commit()
            return await ctx.send(f"Post with id {reddit_id} deleted.")
        else:
            return await ctx.send(f"Could not find post with id {reddit_id}.")

    @commands.command()
    async def suggest(self, ctx, url, *, comments=""):
        """
        Suggest a gift for Bunny

        Suggest a gift for Bunny to add to her Throne wish list. If she adds your gift she can mention you in a message on the server. Please note that, for safety reasons, suggestions from Etsy are automatically rejected.
        """

        spreadsheet = await self.bot.settings.get("suggest_sheet")
        sheetname = "Main List" if ctx.author.id != 991121986103279636 else "Dath"
        tz = pytz.timezone('US/Central')

        if not validators.url(url):
            await ctx.send("Please provide a valid URL.")
        else:
            if re.search("etsy", url.lower()):
                return await ctx.send("For safety reasons, Bunny cannot take suggestions from Etsy stores.")
            values = [url, ctx.author.display_name, ctx.author.mention, datetime.datetime.now(tz).strftime("%m/%d/%Y %H:%M:%S"), comments]
            await self.add_to_sheet(spreadsheet, sheetname, values)
            await ctx.send("Suggestion made!")


    @suggest.error
    async def suggest_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"You must supply a URL to suggest a gift. Try `!help suggest` for more information.")
        else:
            raise error

    @commands.command(hidden=True)
    async def prize(self, ctx, url):
        channel = ctx.bot.get_channel(948272967178149948) 
        if not validators.url(url):
            await ctx.send("Please provide a valid URL.")
        else:
            await channel.send(url)
            await ctx.send(f"Prize link posted in {channel.mention}!")

    @commands.group(invoke_without_command=True)
    @checks.is_mod()
    async def reddit(self, ctx):
        if ctx.invoked_subcommand is None:
#            file_exists = os.path.isfile(os.getenv("REDDIT_OFF"))
#            on_off = "off" if file_exists else "on"
            reddit_off = bool(int(await self.bot.settings.get("reddit_off")))
            on_off = "off" if reddit_off else "on"
            return await ctx.send(f"Reddit posts are currently {on_off}.")

    @reddit.command(name="off")
    @checks.is_mod()
    async def reddit_off(self, ctx):
#        path = os.getenv("REDDIT_OFF")
        reddit_off = bool(int(self.bot.settings.get("reddit_off")))
        if reddit_off:
            return await ctx.send("Reddit posts are already off")
        else:
#            open(path, "a").close()
            self.bot.settings.set("reddit_off", 1)
            return await ctx.send("Reddit posts turned off.")

    @reddit.command(name="on")
    @checks.is_mod()
    async def reddit_on(self, ctx):
#        path = os.getenv("REDDIT_OFF")
        reddit_off = bool(int(self.bot.settings.get("reddit_off")))
        if not reddit_off:
            return await ctx.send("Reddit posts are already on.")
        else:
#            os.remove(path)
            self.bot.settings.set("reddit_off", 0)
            return await ctx.send("Reddit posts turned on.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if isinstance(message.channel, discord.DMChannel):
            return
        if message.channel.name == "are-you-pooping" and message.content.lower() != "yes":
            if message.author.top_role < discord.utils.get(message.guild.roles, name=await self.bot.settings.get("mod_role")):
#            if not len([role for role in message.author.roles if role.name in os.environ["MOD_ROLES"].split(",")]): 
                try: 
                    await asyncio.sleep(1)
                    msg = await message.channel.fetch_message(message.id)
                    await message.delete()
                except discord.NotFound:
                    return
                except Exception as e:
                    error_msg = f"ERROR: {type(e).__name__}: {e}"
                    print(error_msg)
                    owner = message.guild.get_member(self.bot.settings.get("owner_id"))
                    await owner.send(error_msg)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if isinstance(after.channel, discord.DMChannel):
            return
        if after.channel.name == "are-you-pooping" and after.content.lower() != "yes":
            try:                
                msg = await after.channel.fetch_message(after.id)
                await after.delete()
            except discord.NotFound:
                return
            except Exception as e:
                error_msg = f"ERROR: {type(e).__name__}: {e}"
                print(error_msg)
                owner = message.guild.get_member(self.bot.settings.owner_id)
                await owner.send(error_msg)

    @commands.command(name="lock-emoji", hidden=True)
    async def lock_emoji(self, ctx):
        emoji = discord.utils.get(ctx.guild.emojis, name="shiny_black_hearts")
        king = discord.utils.get(ctx.guild.roles, name="King")
        await emoji.edit(name="shiny_black_hearts", roles=[king], reason="Lock to Bunny")
        await ctx.send("Emoji locked.")

    @commands.command()
    @checks.is_mod()
    async def quote(self, ctx, author: discord.Member, *, quote):
        embed = discord.Embed(title="Quote", description=f'"{quote}"')
        embed.set_author(name=author.nick, icon_url=author.avatar_url).set_footer(text=ctx.author.nick, icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @commands.command()
    @checks.is_mod()
    async def numberwang(self, ctx):
        if not self.numberwang:
            await ctx.send(f"It's Numberwang! Numberwang is now turned on.")
            self.numberwang = not self.numberwang
        else:
            self.numberwang = not self.numberwang
            await ctx.send(f"It's Numberwang! Numberwang is now turned off.")

    @commands.Cog.listener(name="on_message")
    async def number_listener(self, message):
#940258352775192639
        if self.numberwang and message.channel.id == 940258352775192639 and message.author.top_role < discord.utils.get(message.guild.roles, name=await self.bot.settings.get("mod_role")):
            if not message.content.isdigit():
                await message.delete()

    @commands.command(hidden=True)
    @checks.is_mod()
    async def gag(self, ctx):
        if self.gag == True:
            new_state = "ungagged"
        else:
            new_state = "gagged"
        self.gag = not self.gag
        await ctx.send(f"Bunny is now {new_state}.")

    @commands.Cog.listener("on_message")
    async def bunny_gag(self, message):
        if message.author.id == 940257449502466138 and self.gag:
            await message.delete()

    @commands.command(name="get-posts", hidden=True)
    async def get_posts(self, ctx):
        reddit = asyncpraw.Reddit(
            client_id=self.CLIENT_ID,
            client_secret=self.CLIENT_SECRET,
            user_agent="BunnitBot 1.1",
        )
        bunny = await reddit.redditor("heyitsjustbunny")
        async for post in bunny.submissions.hot(limit=1000):
            print(f"{post.id} {datetime.datetime.utcfromtimestamp(post.created_utc)}")
            if not post.is_self and post.title.find("Removed by Reddit") == -1:
                with open("/home/aricept/DiscoBunny/new_posts.txt", "a") as file:
                    file.write(f"{post.id}\n")
        reddit.close()

#    @commands.command()
#    async def twitch(self, ctx):
#        tz = pytz.timezone("US/Central")
#        today = datetime.datetime.now(tz)
#        day = today.weekday()
#        if day <= 2:
#          next_day = datetime.timedelta(days=1)
#        elif day <= 4:
#          next_day = datetime.timedelta(days=3)
#        else:
#          next_day = datetime.timedelta(days=8)
#        next_date = today.replace(hour=19, minute=0) + next_day
#        utc_next = next_date.astimezone(pytz.utc)
#        now = datetime.datetime.utcnow()
#        await ctx.send(f"Bunny is a streamer! Catch her on Tuesdays and Thursdays (Wednesdays and Fridays for our European friends) on Twitch!\nThe next stream is on <t:{int(utc_next.timestamp())}> at https://twitch.tv/heyitsjustbunny")


#    @commands.command()
#    async def prune(self, ctx):
#        role = ctx.guild.get_role(945922913423482891)
#        seven_days = discord.utils.utcnow() - datetime.timedelta(days=7)
#        members = [member for member in ctx.guild.members if role not in member.roles and not member.bot and member.joined_at < seven_days]
#        await ctx.send(f"Beginning prune. {len(members)} have joined the server more than seven days ago but have not accepted the rules. Beginning kicks...")
#        for member in members:
#            print(member.name)
#            await member.kick(reason="The Great Purging: has not accepted the rules within seven days of joining the server.")
#        await ctx.send("Purge complete. Deadweight removed. The Community is Pure once again.")
#        count = await ctx.guild.estimate_pruned_members(days=1)
#        await ctx.send(f"Pruning {count} members who haven't accepted the rules.")
#        pruned = await ctx.guild.prune_members(days=1)
#        await ctx.send(f"Prune completed, {pruned} members kicked.")
       

    @commands.command(name="prune-count")
    @checks.is_mod()
    async def prune_count(self, ctx):
#        role = ctx.guild.get_role(945922913423482891)
#        seven_days = discord.utils.utcnow() - datetime.timedelta(days=7)
#        members = [member for member in ctx.guild.members if role not in member.roles and not member.bot and member.joined_at < seven_days]
#        await ctx.send(f"{len(members)} members to be pruned.")
        count = await ctx.guild.estimate_pruned_members(days=1)
        await ctx.send(f"{count} to be pruned")



    @commands.command(name="create-view")
    @checks.is_mod()
    async def create_view(self, ctx):
        channel = ctx.guild.get_channel(1012168519019921489)
        embed = discord.Embed(title="Email Needed!", color=discord.Color.brand_green(), description="As Bunny transitions to Fansly, we need some information to match you up between Discord and the Stripe payment info to figure out how long you subscribed for. Just click the button below and enter the email address you used when signing up for the membership, and we'll get you a link to Fansly for your membership!")
        msg = await channel.send(embed=embed, view=membership.GetMemberInfo())
        print(msg.id)
        await self.bot.settings.set("member_view", msg.id)

class Suggestion(discord.ui.Modal, title="Wishlist Suggestion!"):
    url = discord.ui.TextInput(label="URL")
    comments = discord.ui.TextInput(label="Comment", placeholder="Comment for Bunny", style=discord.TextStyle.long)
    

    async def add_to_sheet(self, spreadsheet_id, sheet_name, values):
        gc = gspread.service_account(await self.client.settings.get("service_account"))
        spreadsheet = gc.open_by_key(spreadsheet_id)
        sheet = spreadsheet.worksheet(sheet_name)
        sheet.append_row(values)

    async def on_submit(self, interaction: discord.Interaction):
        self.client = interaction.client
        spreadsheet = await interaction.client.settings.get("suggest_sheet")
        sheetname = "Main List" if interaction.id != 991121986103279636 else "Dath"
        tz = pytz.timezone('US/Central')

        if not validators.url(self.url.value):
            return await interaction.response.send_message("Please provide a valid URL.")
        else:
            if re.search("etsy", self.url.value.lower()):
                return await interaction.response.send("For safety reasons, Bunny cannot take suggestions from Etsy stores.")
            values = [self.url.value, interaction.user.display_name, interaction.user.mention, datetime.datetime.now(tz).strftime("%m/%d/%Y %H:%M:%S"), self.comments.value]
            await self.add_to_sheet(spreadsheet, sheetname, values)
#            await ctx.send("Suggestion made!")
        await interaction.response.send_message(f"Thanks for suggesting {self.url.value}!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Bunny(bot))

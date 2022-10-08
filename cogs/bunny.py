import aiosqlite
import discord
from discord.ext import commands
import gspread
import validators
import pytz
from dotenv import load_dotenv
import asyncio
import asyncpraw
import random
import datetime
import re
import checks
import typing
import membership

class Bunny(commands.Cog):
    # Various commands related to Bunny
    # `ctx` parameter in commands is Discord Context, includes info about the sender, the message, 
    # the Discord server (called a guild), and methods to interact with them

    def __init__(self, bot):
        # Set bot vars, load environment variables
        self.bot = bot
        load_dotenv()
        # Response list for !bunny command
        self.responses = ["We're hunting wabbit...", "Trying to find Bunny...", "Searching for Bunny...", "Picking a random Bunny post..."]
        self.found = ["Found a wabbit, found a wabbit, found a WABBIT!", "Found Bunny!", "Bunny located.", "Here's your random Bunny..."]
        # Bot var for !numberwang command, so only numbers can be used in general
        self.numberwang = False

    @commands.group(invoke_without_command=True, aliases=["b"])
    @checks.is_level_5()
    async def bunny(self, ctx, tag: typing.Optional[str]=None):
        """Get a random Bunny Reddit post

        Retrieves a random post from Bunny's Reddit profile. This could be a text post, a post from a NSFW subreddit, or a post from a SFW subreddit post. Sometimes this will include a preview image, and sometimes it will not, but will always include a link to the actual post. Optionally, a tag may be provided to narrow the results. Must be Level 5 or higher to use.
        """
        # If no subcommand is used, connects to Reddit
        if ctx.invoked_subcommand is None:
            reddit = asyncpraw.Reddit(
                client_id=await self.bot.settings.get("client_id"),
                client_secret=await self.bot.settings.get("client_secret"),
                user_agent="BunnitBot 1.1"
            )

            # Pulls random response
            rand_response = random.randint(0, len(self.responses) - 1)
            original = await ctx.send(self.responses[rand_response])
            post_list = []

            async with aiosqlite.connect("bunny.db") as db:
                db.row_factory = aiosqlite.Row
                # If no tag was provided, pulls list of all posts from database
                if tag is None:
                    result = await db.execute("select reddit_id, post_id from posts")
                    posts = await result.fetchall()
                else:
                    # Checks to see if the provided tag exists; if it does, pulls posts with that tag
                    result = await db.execute("select tag_id from tags where name = ?", (tag,))
                    tag_entry = await result.fetchone()
                    if tag_entry:
                        result = await db.execute("select p.reddit_id, p.post_id from posts p inner join post_tags pt on p.post_id = pt.post_id inner join tags t on pt.tag_id = t.tag_id where t.tag_id = ?", (tag_entry["tag_id"],))
                        posts = await result.fetchall()
                    else:
                        # Pulls all posts if the tag doesn't exist
                        await ctx.send(f"Tag `{tag}` does not exist, getting random post.")
                        result = await db.execute("select reddit_id, post_id from posts")
                        posts = await result.fetchall()

                # Pulls random post from list
                post_list = [post for post in posts]
                random_post = random.choice(post_list)
                selected_post = await reddit.submission(id=random_post["reddit_id"])

                # Grabs all tags for the selected post to add to embed
                result = await db.execute("select t.name from tags t inner join post_tags pt on t.tag_id = pt.tag_id where pt.post_id = ?", (random_post["post_id"],)) #self.bot.db.execute("select t.name from tags t inner join post_tags pt on t.tag_id = pt.tag_id where pt.post_id = ?", (random_post["post_id"],))
                post_tags = await result.fetchall()
                selected_post.tags = " ".join([f"`{post_tag['name']}`" for post_tag in post_tags])
                await ctx.send(self.found[rand_response])

                # Parses image URL from Reddit data, creates embed
                image_url = self.get_image_url(selected_post)
                embed = self.embed_from_post(ctx, selected_post, image_url)

                # Checks if channel is marked NSFW for image masking, sends embed, closes Reddit
                if not ctx.channel.is_nsfw() or ctx.channel.id == 940258352775192639:
                    embed.set_image(url=None)
                    if embed.video:
                        embed.video.url = None
                    await ctx.send(embed=embed)
                    await ctx.send(f"||{image_url} ||")
                else:
                    await ctx.send(embed=embed)
                await reddit.close()

    def embed_from_post(self, ctx, selected_post, image_url):
        # Builds embed
        embed = discord.Embed(title=selected_post.title, url=f"http://old.reddit.com{selected_post.permalink}", color=2447966)
        embed.set_author(name="Bunny", url="http://reddit.com/u/heyitsjustbunny")
        if image_url != None:
            embed.set_image(url=image_url)
        embed.timestamp = datetime.datetime.utcfromtimestamp(selected_post.created_utc)
        embed.set_footer(text=f"Posted to {selected_post.subreddit.display_name} • Requested by {ctx.author.display_name} • id {selected_post.id}")
        embed.description = f"Tags: {selected_post.tags}"
        return embed

    def get_image_url(self, post):
        # Parses image URL
        # Discord can't display Imgur's .gifv so we repalce with a jpg
        if post.url.find("imgur") > -1:
            return post.url.replace("gifv", "jpg")
        # If post was removed by Reddit we return a placeholder image because the image is not available.
        elif post.title.find("Removed by Reddit") > -1:
            return "https://www.publicdomainpictures.net/pictures/280000/nahled/not-found-image-15383864787lu.jpg"
        # For Reddit galleries we get the first preview image.
        elif post.url.find("gallery") > -1:
            for i in post.media_metadata.items():
                return i[1]["p"][0]["u"]
        # For individual Reddit images we just return the URL
        else:
            try:
                return post.preview["images"][0]["source"]["url"]
            except:
                return None    

    # Error handler for below minimum level
    @bunny.error
    async def bunny_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send("You must be at least Level 5 to do that. Engage in chat and level up, and you'll be able to do that in no time!")
        else:
            raise error

    @bunny.command(name="untagged")
    @checks.is_mod()
    async def bunny_untagged(self, ctx):
        # Gets untagged posts and presents them for tagging, one at a time.
        posts = await self.get_untagged_posts()
        if posts:
            return await self.get_tags(ctx, posts)
        else:
            return await ctx.send("No untagged posts!")

    async def get_untagged_posts(self):
        # Gets list of untagged posts from database
        async with aiosqlite.connect("bunny.db") as db:
            db.row_factory = aiosqlite.Row
            result = await db.execute("select p.post_id, p.reddit_id from posts p left join post_tags pt on p.post_id = pt.post_id where pt.tag_id is null order by p.post_id")
            posts = await result.fetchall()
        return posts


    async def get_tags(self, ctx, posts):
        # Gets input from user to tag posts
        # Checks if input was from the original command author
        def is_author(msg):
            return msg.author.id == ctx.author.id and msg.channel == ctx.channel
        
        # Checks if the response is yes
        def is_yes(msg):
            return msg.lower() == "y" or msg.lower() == "yes"

        # Checks if repsonse is no
        def is_no(msg):
            return msg.lower() == "n" or msg.lower() == "no"

        # Pulls post from end of list and gets the post from Reddit, sends message to Discord
        post = posts.pop()
        reddit = asyncpraw.Reddit(
            client_id=await self.bot.settings.get("client_id"),#self.CLIENT_ID,
            client_secret=await self.bot.settings.get("client_secret"),#self.CLIENT_SECRET,
            user_agent="BunnitBot 1.1",
        )
        reddit_post = await reddit.submission(id=post["reddit_id"])
        await ctx.send(f"Please provide space separated tags for this post:\nhttp://old.reddit.com{reddit_post.permalink}") 
        await reddit.close()
        
        # Waits for response from original author for five minutes.
        try:
            msg = await self.bot.wait_for("message", check=is_author, timeout=300)
        except asyncio.TimeoutError:
            return await ctx.send("Tagging ended due to no response.")
        else:
            # If author responds "done" ends tagging
            if msg.content.lower().startswith("done"):
                return await ctx.send(f"Ended tagging. Last post untagged. {len(posts)} posts still untagged.")
            # If author responds "skip" moves to next untagged post
            elif msg.content.lower().startswith("skip"):
                if posts:
                    await ctx.send("Post skipped!")
                    await self.get_tags(ctx, posts)
            else:
                # Splits response into space separated words/tags
                tags = []
                for tag in msg.content.lower().split():
                    tag = tag

                    # Checks if tag exists. See process_tag for more info
                    tag_id = await self.process_tag(ctx, tag)
                    if tag_id:
                        await self.tag_post(tag_id, post[0])
                        tags.append(tag)
                await ctx.send(f"Post tagged with {' '.join(tags)}")
                # Prompt if wants to continue tagging if the posts are still in the list
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
                    # If posts list was empty, checks if there are still untagged posts in the database.
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
        # Processes actual tags to database
        def is_yes(msg_content):
            return msg_content.lower() == "y" or msg_content.lower() == "yes"

        def is_no(msg_content):
            return msg_content.lower() == "n" or msg_content.lower() == "no"

        def is_author(msg):
            return msg.author.id == ctx.author.id and msg.channel == ctx.channel
        
        # Gets tag by name from database
        async with aiosqlite.connect("bunny.db") as db:
            db.row_factory = aiosqlite.Row
            row = await db.execute("select tag_id from tags where name = ?", (tag,))
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
                        row = await db.execute("select tag_id from tags where name = ?", (tag,))
                        result = await row.fetchone()
                    elif is_no(msg.content):
                        await ctx.send(f"Tag {tag} not inserted.")
                        return None
        return result["tag_id"]

    async def add_tag(self, ctx, tag):
        # Adds new tag to database
        async with aiosqlite.connect("bunny.db") as db:
            await db.execute("insert into tags (name) values (?)", (tag,))
            await db.commit()
        await ctx.send(f"Tag {tag} inserted.")

    async def tag_post(self, tag_id, post_id):
        # Tags a post in the database
        async with aiosqlite.connect("bunny.db") as db:
            await db.execute("insert into post_tags (post_id, tag_id) values (?,?)", (post_id, tag_id))
            await db.commit()

    @bunny.command(name="tag")
    @checks.is_mod()
    async def bunny_tag(self, ctx, reddit_id, *tags):
        # Manually tag a post by Reddit ID
        async with aiosqlite.connect("bunny.db") as db:
            db.row_factory = aiosqlite.Row
            if tags:
                row = await db.execute("select post_id from posts where reddit_id = ?", (reddit_id,))
                post_db = await row.fetchone()
                if not post_db:
                    return await ctx.send(f"A post with the id {reddit_id} cannot be found.")
                else:
                    post_id = post_db["post_id"]
                    rows = await db.execute("select t.name from tags t inner join post_tags pt on t.tag_id = pt.tag_id where pt.post_id = ?", (post_id,))
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
        # Get list of all tags (more than five posts) and count
        async with aiosqlite.connect("bunny.db") as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute("select t.name, count(pt.tag_id) as count from tags t inner join post_tags pt on t.tag_id = pt.tag_id group by t.name order by count(pt.tag_id) desc")
            tags = await rows.fetchall()
        tags_list = [f"{tag['name']}\t{tag['count']}" for tag in tags if tag[1] > 4]
        tags_msg = "\n".join(tags_list)
        await ctx.send(f"```Tag\tCount\n---------------\n{tags_msg}\n```")

    @bunny.command(name="del-post")
    @checks.is_mod()
    async def del_post(self, ctx, reddit_id):
        # Delete a post from the database
        async with aiosqlite.connect("bunny.db") as db:
            rows = await db.execute("select post_id from posts where reddit_id = ?", (reddit_id,))
            post = await rows.fetchone()
        if post is not None:
            await self.bot.db.execute("delete from post_tags where post_id = ?", (post,))
            await self.bot.db.execute("delete from posts where post_id = ?", (post,))
            await self.bot.db.commit()
            return await ctx.send(f"Post with id {reddit_id} deleted.")
        else:
            return await ctx.send(f"Could not find post with id {reddit_id}.")

    @commands.group(invoke_without_command=True)
    @checks.is_mod()
    async def reddit(self, ctx):
        # Group of commands that controls Reddit posts being posted to Discord
        # This command by itself without a subcommand returns the current setting
        if ctx.invoked_subcommand is None:
            reddit_off = bool(int(await self.bot.settings.get("reddit_off")))
            on_off = "off" if reddit_off else "on"
            return await ctx.send(f"Reddit posts are currently {on_off}.")

    @reddit.command(name="off")
    @checks.is_mod()
    async def reddit_off(self, ctx):
        # Turns Reddit posting to off
        reddit_off = bool(int(self.bot.settings.get("reddit_off")))
        if reddit_off:
            return await ctx.send("Reddit posts are already off")
        else:
            await self.bot.settings.set("reddit_off", 1)
            return await ctx.send("Reddit posts turned off.")

    @reddit.command(name="on")
    @checks.is_mod()
    async def reddit_on(self, ctx):
        # Turns Reddit posting to on
        reddit_off = bool(int(self.bot.settings.get("reddit_off")))
        if not reddit_off:
            return await ctx.send("Reddit posts are already on.")
        else:
            await self.bot.settings.set("reddit_off", 0)
            return await ctx.send("Reddit posts turned on.")

    @commands.Cog.listener()
    async def on_message(self, message):
        # Adds listener for all messages, but is watching specifically for #are-you-pooping posts

        # Skips if is a DM
        if isinstance(message.channel, discord.DMChannel):
            return

        # If we're in the right channel and the message is not exactly equal to yes/YES/YeS etc.
        if message.channel.name == "are-you-pooping" and message.content.lower() != "yes":
            # Excludes mods from being deleted.
            if message.author.top_role < discord.utils.get(message.guild.roles, name=await self.bot.settings.get("mod_role")):
                try: 
                    # Deletes message after 1s delay
                    await asyncio.sleep(1)
                    msg = await message.channel.fetch_message(message.id)
                    await message.delete()
                except discord.NotFound:
                    # If we can't find the message, it was deleted, so we return
                    return
                except Exception as e:
                    error_msg = f"ERROR: {type(e).__name__}: {e}"
                    print(error_msg)
                    owner = message.guild.get_member(await self.bot.settings.get("owner_id"))
                    await owner.send(error_msg)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        # Same as above, but for message edits, which the original bot does not cover
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
                owner = before.guild.get_member(await self.bot.settings.get("owner_id"))
                await owner.send(error_msg)

    @commands.command()
    @checks.is_mod()
    async def numberwang(self, ctx):
        # Turns numberwang on or off
        if not self.numberwang:
            await ctx.send(f"It's Numberwang! Numberwang is now turned on.")
            self.numberwang = not self.numberwang
        else:
            self.numberwang = not self.numberwang
            await ctx.send(f"It's Numberwang! Numberwang is now turned off.")

    @commands.Cog.listener(name="on_message")
    async def number_listener(self, message):
        # If numberwang is on, checks channel of message, whether user is a mod, and if the message is a digit.
        # Deletes if is in general, not a mod, and number is not a digit.
        if self.numberwang and message.channel.id == 940258352775192639 and message.author.top_role < discord.utils.get(message.guild.roles, name=await self.bot.settings.get("mod_role")):
            if not message.content.isdigit():
                await message.delete()

    @commands.command(name="get-posts", hidden=True)
    async def get_posts(self, ctx):
        # Retrieves list of all Bunny's posts from Reddit. Used if needed to rebuild the post list.
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

    @commands.command(name="create-view")
    @checks.is_mod()
    async def create_view(self, ctx):
        # Used to create the buttons to get the additional user info needed for matching to Fansly.
        channel = ctx.guild.get_channel(1012168519019921489)
        embed = discord.Embed(title="Email Needed!", color=discord.Color.brand_green(), description="As Bunny transitions to Fansly, we need some information to match you up between Discord and the Stripe payment info to figure out how long you subscribed for. Just click the button below and enter the email address you used when signing up for the membership, and we'll get you a link to Fansly for your membership!")
        msg = await channel.send(embed=embed, view=membership.GetMemberInfo())
        print(msg.id)
        await self.bot.settings.set("member_view", msg.id)

async def setup(bot):
    await bot.add_cog(Bunny(bot))

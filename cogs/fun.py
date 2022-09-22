import discord
from discord.ext import commands
import typing
from pprint import pprint
from jishaku.paginators import PaginatorEmbedInterface

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

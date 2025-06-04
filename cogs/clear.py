import discord
from discord.ext import commands
class ClearCommandCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="clear", description="")
    @discord.default_permissions(
        administrator=True,
    )
    @discord.option(
        "number",
        int,
        required=True
    )
    async def clear(self, ctx: discord.ApplicationContext):
        number = ctx.options.get("number", 0)
        if number < 1:
            await ctx.respond("Please specify a positive number.", ephemeral=True)
            return

        await ctx.defer(ephemeral=True)
        deleted = await ctx.channel.purge(limit=number)
        embed = discord.Embed(
            title="Messages Deleted",
            description=f"Deleted {len(deleted)} messages.",
            color=discord.Color.red()
        )
        await ctx.respond(embed=embed, ephemeral=True)

def setup(bot: discord.Bot):
    bot.add_cog(ClearCommandCog(bot))
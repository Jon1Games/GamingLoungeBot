import discord
from discord.ext import commands
class PingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="ping", description="reply with pong and the latency")
    async def ping(self, ctx: discord.ApplicationContext):
        await ctx.respond(f"Pong! Latency is {self.bot.latency}", ephemeral=True)

def setup(bot: discord.Bot):
    bot.add_cog(PingCog(bot))
import discord
from dotenv import load_dotenv
import os

intents = discord.Intents.default()

bot = discord.Bot(intents=intents)

load_dotenv()

@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")

# Load cogs
def load_cogs():
    for file in os.listdir("./cogs"):
        if file.endswith(".py"):
            try:
                bot.load_extension(f"cogs.{file[:-3]}")
                print(f"Loaded {file}")
            except Exception as e:
                print(f"Failed to load {file}: {e}")

load_cogs()
bot.run(os.getenv('TOKEN'))

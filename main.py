import discord
import os
from dotenv import load_dotenv
import mariadb
import sys

# Connect to MariaDB Platform
try:
    conn = mariadb.connect(
        user="",
        password="",
        host="192.168.178.0",
        port=3306,
        database=""
    )
except mariadb.Error as e:
    print(f"Error connecting to MariaDB Platform: {e}")
    sys.exit(1)

# Get Cursor
cur = conn.cursor()

# Create Table
try: 
    cur.execute("CREATE TABLE IF NOT EXISTS `warnings`(`id` INTEGER AUTO_INCREMENT PRIMARY KEY NOT NULL, `guild` LONG NOT NULL, `user` LONG NOT NULL, `mod` LONG NOT NULL, `reason` VARCHAR(256)) ENGINE = InnoDB;") 
except mariadb.Error as e: 
    print(f"Error: {e}")

def getWarnings(guild_id, user_id):
    cur.execute("SELECT `id`,`guild`,`user`,`mod`,`reason` FROM `warnings` WHERE (guild=? AND user=?);", (guild_id, user_id))
    i = 0
    for id,guild,user,mod,reason in cur:
        i += 1
    return i

async def warningRoles(ctx, user: discord.User, warnings: int):
    if discord.utils.get(ctx.guild.roles, name="warned"):
        pass
    else:
        await ctx.guild.create_role(name="warned")
    role = discord.utils.get(ctx.guild.roles, name="warned")
    await user.add_roles(role)

    if discord.utils.get(ctx.guild.roles, name="warnings: " + str(warnings)):
        pass
    else:
        await ctx.guild.create_role(name="warnings: " + str(warnings))
    role = discord.utils.get(ctx.guild.roles, name="warnings: " + str(warnings))
    await user.add_roles(role)

load_dotenv()
bot = discord.Bot()

@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")

@bot.slash_command(name="ping", description="reply with pong")
async def ping(ctx: discord.ApplicationContext):
    await ctx.respond("pong")

@bot.slash_command(name="warn")
@discord.default_permissions(
    administrator=True,
)
@discord.option(
    "user",
    discord.User,
    required=True,
    default=''
)
@discord.option(
    "reason", 
    required=False,
    default=''
)
async def warn(ctx: discord.ApplicationContext, user, reason: str):
    try: 
        warns = getWarnings(ctx.guild_id, user.id)
        cur.execute("INSERT INTO `warnings` (`guild`,`user`,`mod`,`reason`) VALUES (?, ?, ?, ?)", (ctx.guild_id, user.id, ctx.author.id, reason)) 
        conn.commit()
        await ctx.respond("User " + user.name + " warned succesfully.")

        if not warns == 0:
            if discord.utils.get(user.roles, name="warnings: " + str(warns)):
                await user.remove_roles(discord.utils.get(user.roles, name="warnings: " + str(warns)))

        await warningRoles(ctx, user, getWarnings(ctx.guild_id, user.id))
    except mariadb.Error as e: 
        print(f"Error: {e}")
        await ctx.respond("and error occured, pls contact Jon1Games")

@bot.slash_command(name="list_warns")
@discord.default_permissions(
    administrator=True,
)
@discord.option(
    "user",
    discord.User,
    required=False,
    default=''
)
@discord.option(
    "page",
    required=False,
    default='1'
)
async def list_warns(ctx: discord.ApplicationContext, user, page):
    wait_embed = discord.Embed(title=f"__**Generating Warning list ...**__", color=0x03f8fc)
    msg = await ctx.respond(embed=wait_embed)
    guildmode = False
    if user == "":
        cur.execute("SELECT `id`,`guild`,`user`,`mod`,`reason` FROM `warnings` WHERE guild=?;", (ctx.guild_id,))
        guildmode = True
    else: 
        cur.execute("SELECT `id`,`guild`,`user`,`mod`,`reason` FROM `warnings` WHERE (guild=? AND user=?);", (ctx.guild_id, user.id)) 

    if guildmode == True:
        u = ctx.guild.name
    else: 
        u = user
    embed = discord.Embed(title=f"__**Warning list of {u}**__", color=0x03f8fc)

    offset = int(page) * 10

    i = 1
    for id,guild,user,mod,reason in cur:
        if i <= offset - 10:
            i += 1
        elif i <= offset:
            i += 1
            n = await bot.fetch_user(mod)
            embed.add_field(name=f'**ID: {id}**', value=f'> Moderator: {n}\n> Reason: {reason}',inline=False)

    await msg.edit(embed=embed)

@bot.slash_command(name="remove_warn")
@discord.default_permissions(
    administrator=True,
)
@discord.option(
    "warn_id", 
    required=True,
    default=''
)
async def remove_warn(ctx: discord.ApplicationContext, warn_id):
    try: 
        cur.execute("SELECT `user`,`mod` FROM `warnings` WHERE `id` = ? AND `guild` = ?;", (warn_id,ctx.guild_id))
        u = None
        for user,mod in cur:
            u = await ctx.guild.query_members(user_ids=[user]) 
            u = u[0]
        warns = getWarnings(ctx.guild_id, u.id)
        cur.execute("DELETE FROM `warnings` WHERE `id` = ? AND `guild` = ?;", (warn_id,ctx.guild_id)) 
        conn.commit()
        await ctx.respond("The warning with the ID " + warn_id + " was removed.")

        if warns - 1 == 0:
            await u.remove_roles(discord.utils.get(u.roles, name="warned"))
            await u.remove_roles(discord.utils.get(u.roles, name="warnings: " + str(warns)))
        else:
            await u.remove_roles(discord.utils.get(u.roles, name="warnings: " + str(warns)))
            await warningRoles(ctx, u, warns - 1)
    except mariadb.Error as e: 
        print(f"Error: {e}")
        await ctx.respond("and error occured, pls contact Jon1Games")
    
bot.run(os.getenv('TOKEN'))

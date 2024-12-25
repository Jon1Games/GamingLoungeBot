import discord
import os
from dotenv import load_dotenv
import mariadb
import sys
from datetime import datetime, timedelta, date
import threading
import asyncio
from discord.ext import tasks

intents = discord.Intents.default()
intents.members = True

bot = discord.Bot(intents=intents)

load_dotenv()

def dbConnect():
    # Connect to MariaDB Platform
    try:
        conn = mariadb.connect(
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT')),
            database=os.getenv('DB_DATABASE')
        )
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Platform: {e}")
        sys.exit(1)

    # Get Cursor
    return conn

def createTables():
    conn = dbConnect()
    cur = conn.cursor()
    # Create Table
    try: 
        cur.execute("CREATE TABLE IF NOT EXISTS `warnings`(`id` INTEGER AUTO_INCREMENT PRIMARY KEY NOT NULL, `guild` LONG NOT NULL, `user` LONG NOT NULL, `mod` LONG NOT NULL, `exipire` LONG,`reason` VARCHAR(256)) ENGINE = InnoDB;") 
    except mariadb.Error as e: 
        print(f"Error: {e}")
    conn.close()

def getAllWarnings(guild_id, user_id, cur):
    cur.execute("SELECT `id`,`guild`,`user`,`mod`,`reason` FROM `warnings` WHERE (guild=? AND user=?);", (guild_id, user_id))
    i = 0
    for id,guild,user,mod,reason in cur:
        i += 1
    return i

def getWarnings(guild_id, user_id, cur):
    now = datetime.now()
    cur.execute("SELECT `id`,`guild`,`user`,`mod`,`reason` FROM `warnings` WHERE (guild=? AND user=? AND (exipire>? or exipire IS NULL));", (guild_id, user_id, int(now.strftime("%Y%m%d%H"))))
    i = 0
    for id,guild,user,mod,reason in cur:
        i += 1
    return i

async def warningRoles(guild: discord.Guild, user: discord.User, cur):
    all_warnings = getAllWarnings(guild.id, user.id, cur) 
    warnings = getWarnings(guild.id, user.id, cur)

    if discord.utils.get(guild.roles, name="warned"):
        pass
    else:
        await guild.create_role(name="warned")
    role = discord.utils.get(guild.roles, name="warned")
    if warnings == 0:
        await user.remove_roles(role)
    else:
        await user.add_roles(role)

    for a in range(1, all_warnings):
        if discord.utils.get(guild.roles, name="warnings: " + str(a)):
            role = discord.utils.get(guild.roles, name="warnings: " + str(a))
            if role in user.roles and a != warnings:
                await user.remove_roles(role)

    if discord.utils.get(guild.roles, name="warnings: " + str(warnings)):
        pass
    else:
        await guild.create_role(name="warnings: " + str(warnings))
    role = discord.utils.get(guild.roles, name="warnings: " + str(warnings))
    if warnings == 0:
        await user.remove_roles(role)
    else:
        await user.add_roles(role)

@tasks.loop(seconds=3600)
async def recalcRoleWarnCound():
    conn = dbConnect()
    cur = conn.cursor()
    for guild in bot.guilds:
        role = discord.utils.get(guild.roles, name="warned")
        for user in guild.members:
            if role in user.roles:
                await warningRoles(guild, user, cur)
    conn.close()

recalcRoleWarnCound.start()

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
@discord.option(
    "hours", 
    required=False,
    default='0'
)
@discord.option(
    "days", 
    required=False,
    default='0'
)
@discord.option(
    "weeks", 
    required=False,
    default='0'
)
async def warn(ctx: discord.ApplicationContext, user, reason: str, hours: int, days: int, weeks: int):
    try: 
        if hours == "0" and days == "0" and weeks == "0":
            time = None
        else:
            now = datetime.now()
            now = now + timedelta(hours=int(hours), days=int(days), weeks=int(weeks))
            time = int(now.strftime("%Y%m%d%H"))
        conn = dbConnect()
        cur = conn.cursor()
        cur.execute("INSERT INTO `warnings` (`guild`,`user`,`mod`,`reason`, `exipire`) VALUES (?, ?, ?, ?, ?)", (ctx.guild_id, user.id, ctx.author.id, reason, time)) 
        conn.commit()

        embed = discord.Embed(title=f"__**Der Nutzer {user.name} wurde erfolgreicht Verwarnt.**__", color=0xAAFF00)
        if time == None:
            embed.add_field(name=f'**Informationen:**', value=f'> Reason: {reason}\n> Auslauf Datum:',inline=False)
        else:
            time = str(time)
            embed.add_field(name=f'**Informationen:**', value=f'> Reason: {reason}\n> Auslauf Datum: {time[0]}{time[1]}{time[2]}{time[3]}/{time[4]}{time[5]}/{time[6]}{time[7]}, {time[8]}{time[9]}:00',inline=False)

        await ctx.respond(embed=embed)

        await warningRoles(ctx.guild, user, cur)
        conn.close()
    except mariadb.Error as e: 
        print(f"Error: {e}")
        embed = discord.Embed(title=f"__**EIn Fehler ist aufgetreten, bitte Kontaktiere Jon1Games*__", color=0xFF0000)
        await ctx.respond(embed=embed)

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
    await recalcRoleWarnCound()
    wait_embed = discord.Embed(title=f"__**Generating Warning list ...**__", color=0x03f8fc)
    msg = await ctx.respond(embed=wait_embed)
    guildmode = False
    now = datetime.now()
    conn = dbConnect()
    cur = conn.cursor()
    if user == "":
        cur.execute("SELECT `id`,`guild`,`user`,`mod`,`reason`, `exipire` FROM `warnings` WHERE (guild=? AND (exipire>? or exipire IS NULL));", (ctx.guild_id, int(now.strftime("%Y%m%d%H"))))
        guildmode = True
    else: 
        cur.execute("SELECT `id`,`guild`,`user`,`mod`,`reason`, `exipire` FROM `warnings` WHERE (guild=? AND user=? AND (exipire>? or exipire IS NULL));", (ctx.guild_id, user.id, int(now.strftime("%Y%m%d%H")))) 
    conn.close()

    if guildmode == True:
        u = ctx.guild.name
    else: 
        u = user
    embed = discord.Embed(title=f"__**Warning list of {u}**__", color=0x03f8fc)

    offset = int(page) * 10

    i = 1
    for id,guild,user,mod,reason,exipire in cur:
        if i <= offset - 10:
            i += 1
        elif i <= offset:
            i += 1
            n = await bot.fetch_user(mod)
            if guildmode:
                if exipire == None:
                    u = await bot.fetch_user(user)
                    embed.add_field(name=f'**ID: {id}**', value=f'> {u}\n> Moderator: {n}\n> Reason: {reason}',inline=False)
                else:
                    time = str(exipire)
                    embed.add_field(name=f'**ID: {id}**', value=f'> {u}\n> Moderator: {n}\n> Reason: {reason}\n> Expire: {time[0]}{time[1]}{time[2]}{time[3]}/{time[4]}{time[5]}/{time[6]}{time[7]}, {time[8]}{time[9]}:00',inline=False)
            else:
                if exipire == None:
                    embed.add_field(name=f'**ID: {id}**', value=f'> Moderator: {n}\n> Reason: {reason}',inline=False)
                else:
                    time = str(exipire)
                    embed.add_field(name=f'**ID: {id}**', value=f'> Moderator: {n}\n> Reason: {reason}\n> Expire: {time[0]}{time[1]}{time[2]}{time[3]}/{time[4]}{time[5]}/{time[6]}{time[7]}, {time[8]}{time[9]}:00',inline=False)

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
        conn = dbConnect()
        cur = conn.cursor()
        cur.execute("SELECT `user`,`mod` FROM `warnings` WHERE `id` = ? AND `guild` = ?;", (warn_id,ctx.guild_id))
        u = None
        for user,mod in cur:
            u = await ctx.guild.query_members(user_ids=[user]) 
            u = u[0]
        cur.execute("UPDATE `warnings` SET `exipire` = ? WHERE `id` = ? AND `guild` = ?;", (0,warn_id,ctx.guild_id)) 
        conn.commit()
        embed = discord.Embed(title=f"__**Die Verwarnung mit der ID {warn_id} wurde entfernt**__", color=0xAAFF00)
        await ctx.respond(embed=embed)

        await warningRoles(ctx.guild, u, cur)
        conn.close()
    except mariadb.Error as e: 
        print(f"Error: {e}")
        embed = discord.Embed(title=f"__**EIn Fehler ist aufgetreten, bitte Kontaktiere Jon1Games*__", color=0xFF0000)
        await ctx.respond(embed=embed)

bot.run(os.getenv('TOKEN'))

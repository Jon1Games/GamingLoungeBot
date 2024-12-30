import discord
import os
from dotenv import load_dotenv
import mariadb
import sys
from datetime import datetime, timedelta
from discord.ext import tasks
import json
from threading import Timer
from random import randrange, randint
from typing import Union

configEdit = True
config = json.load("config.json")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

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

@bot.slash_command(name="ping", description="Antwortet mit \"Pong!\"")
async def ping(ctx: discord.ApplicationContext):
    await ctx.respond("Pong!", ephemeral=True)

@bot.slash_command(name="warn", description="Verwarnt ein Benutzer.")
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
            embed.add_field(name=f'**Informationen:**', value=f'> Nutzer: {user.mention}\n> Grund: {reason}\n> Auslauf Datum:',inline=False)
        else:
            time = str(time)
            embed.add_field(name=f'**Informationen:**', value=f'> Nutzer: {user.mention}\n> Grund: {reason}\n> Auslauf Datum: {time[0]}{time[1]}{time[2]}{time[3]}/{time[4]}{time[5]}/{time[6]}{time[7]}, {time[8]}{time[9]}:00',inline=False)

        await ctx.respond(embed=embed)

        await warningRoles(ctx.guild, user, cur)
        conn.close()
    except mariadb.Error as e: 
        print(f"Error: {e}")
        embed = discord.Embed(title=f"__**EIn Fehler ist aufgetreten, bitte Kontaktiere Jon1Games*__", color=0xFF0000)
        await ctx.respond(embed=embed)

@bot.slash_command(name="warn list", description="Erstellt eine Liste mit Verwarnungen.")
@discord.default_permissions(
    administrator=True,
)
@discord.option(
    "nutzer",
    discord.User,
    required=False,
    default=''
)
@discord.option(
    "seite",
    required=False,
    default='1'
)
async def warn_list(ctx: discord.ApplicationContext, nutzer, seite):
    await recalcRoleWarnCound()
    wait_embed = discord.Embed(title=f"__**Generating Warning list ...**__", color=0x03f8fc)
    msg = await ctx.respond(embed=wait_embed)
    guildmode = False
    now = datetime.now()
    conn = dbConnect()
    cur = conn.cursor()
    if nutzer == "":
        cur.execute("SELECT `id`,`guild`,`user`,`mod`,`reason`, `exipire` FROM `warnings` WHERE (guild=? AND (exipire>? or exipire IS NULL));", (ctx.guild_id, int(now.strftime("%Y%m%d%H"))))
        guildmode = True
    else: 
        cur.execute("SELECT `id`,`guild`,`user`,`mod`,`reason`, `exipire` FROM `warnings` WHERE (guild=? AND user=? AND (exipire>? or exipire IS NULL));", (ctx.guild_id, user.id, int(now.strftime("%Y%m%d%H")))) 
    conn.close()

    if guildmode == True:
        u = ctx.guild.name
    else: 
        u = nutzer
    embed = discord.Embed(title=f"__**Warning list of {u}**__", color=0x03f8fc)

    offset = int(seite) * 10
    
    i = 1
    for id,guild,user,mod,reason,exipire in cur:
        if i <= offset - 10:
            i += 1
        elif i <= offset:
            i += 1
            n = await bot.fetch_user(mod)
            if guildmode:
                if exipire == None:
                    u = await bot.fetch_user(nutzer)
                    embed.add_field(name=f'**ID: {id}**', value=f'> Nutzer: {u.mention}\n> Moderator: {n}\n> Grund: {reason}',inline=False)
                else:
                    time = str(exipire)
                    u = await bot.fetch_user(nutzer)
                    embed.add_field(name=f'**ID: {id}**', value=f'> Nutzer: {u.mention}\n> Moderator: {n}\n> Grund: {reason}\n> Auslauf Datum: {time[0]}{time[1]}{time[2]}{time[3]}/{time[4]}{time[5]}/{time[6]}{time[7]}, {time[8]}{time[9]}:00',inline=False)
            else:
                if exipire == None:
                    embed.add_field(name=f'**ID: {id}**', value=f'> Moderator: {n}\n> Grund: {reason}',inline=False)
                else:
                    time = str(exipire)
                    embed.add_field(name=f'**ID: {id}**', value=f'> Moderator: {n}\n> Grund: {reason}\n> Auslauf Datum: {time[0]}{time[1]}{time[2]}{time[3]}/{time[4]}{time[5]}/{time[6]}{time[7]}, {time[8]}{time[9]}:00',inline=False)

    await msg.edit(embed=embed)

@bot.slash_command(name="warn remove", description="Endfernt eine Verwarnun.")
@discord.default_permissions(
    administrator=True,
)
@discord.option(
    "warn_id", 
    required=True,
    default=''
)
async def warn_remove(ctx: discord.ApplicationContext, warn_id):
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
        embed = discord.Embed(title=f"__**Ein Fehler ist aufgetreten, bitte Kontaktiere Jon1Games*__", color=0xFF0000)
        await ctx.respond(embed=embed)

@bot.slash_command(name="clear", description="Löscht eine Anzahl von Nachrichtem in dem Aktuellem Kanal.")
@discord.default_permissions(
    administrator=True,
)
@discord.option(
    "count", 
    required=True,
    default=1
)
@discord.option(
    "user", 
    discord.User,
    required=False,
    default=None
)
async def clear(ctx: discord.ApplicationContext, count, user):
    embed = discord.Embed(title=f"__**Bereite Löschen von {str(count)} Nachrichten vor...*__", color=0xAAFF00)
    msg = ctx.respond(embed=embed)
    
    channel = ctx.channel()
    messages = await channel.history(limit=count + 1)
    if user is not None:
        for a in messages:
            if a.author.id == user.id:
                messages.remove(a)
    
    for a in messages:
        a.delete()
    embed2 = discord.Embed(title=f"__**{str(len(messages))} Nachrichten wurden gelöscht.*__", color=0xAAFF00)
    msg.edit(embed=embed2)
    
@bot.slash_command(name="lock", description="Schließt einen Kanal für eine Rolle.")
@discord.default_permissions(
    administrator=True,
)
@discord.option(
    "role", 
    discord.Role,
    required=False,
    default=None
)
async def lock(ctx: discord.ApplicationContext, role):
    channel = ctx.channel()
    if role is None:
        role = ctx.guild.default_role
    
    perms = ctx.channel.overwrites_for(role)
    perms.send_messages=False
    
    embed = discord.Embed(title=f"__**Kanal {channel.mention} wurde für {role.mention} gespert.**__", color=0xAAFF00)
    msg = ctx.respond(embed=embed)
    
@bot.slash_command(name="unlock", description="Eröffnet einen Kanal für eine Rolle.")
@discord.default_permissions(
    administrator=True,
)
@discord.option(
    "role", 
    discord.Role,
    required=False,
    default=None
)
async def unlock(ctx: discord.ApplicationContext, role):
    channel = ctx.channel()
    if role is None:
        role = ctx.guild.default_role
    
    perms = ctx.channel.overwrites_for(role)
    perms.send_messages=True
    
    embed = discord.Embed(title=f"__**Kanal {channel.mention} wurde für {role.mention} entgespert.**__", color=0xAAFF00)
    msg = ctx.respond(embed=embed)

@bot.slash_command(name="random number", description="Generiert eine Nummer zwischen zwei Werten.")
@discord.option(
    "number1", 
    required=False,
    default=0
)
@discord.option(
    "number2", 
    required=False,
    default=2147483647
)
async def random_number(ctx: discord.ApplicationContext, number1, number2):
    embed = discord.Embed(title=f"__**Generiere Zahl Zwischen {str(number1)} und {str(number2)}...*__", color=0xAAFF00)
    msg = ctx.respond(embed=embed)
    
    rand = randrange(number1, number2)
    
    embed = discord.Embed(title=f"__** {str(rand)} **__", color=0xAAFF00)
    msg.edit(embed=embed)

@bot.slash_command(name="dice", description="Würfelt in der angegebenem Formel und gibt das Ergebnis aus. (<Anzahl>D<Seiten>,<Anzahl>D<Seiten>,...)")
@discord.option(
    "formular", 
    required=False,
    default="1D6"
)
async def dice(ctx: discord.ApplicationContext, formular):
    embed = discord.Embed(title=f"__**Generiere deinen Wurf...**__", color=0xAAFF00)
    msg = await ctx.respond(embed=embed)
    
    def dice(formula):
        formula = formula.split("D")
        
        count = 0
        for a in formula:
            formula[count] = int(formula[count])
            count += 1
        
        dices = []
        result = 0
        for a in range(formula[0]):
            rand = randrange(1, formula[1])
            dices.append(rand)
            result += rand
        return dices, result

    def multiDice(formula):
        formula = formula.split(",")
        
        dices = []
        result = 0
        for a in formula:
            dices.append(str(a))
            d, r = dice(a)
            dices.append(str(d))
            result += r
        return dices, result

    dices, result = multiDice(formula=formular)
    embed = discord.Embed(title=f"__**Wurf von {ctx.author.mention}**__", color=0xAAFF00)
    form = None
    for a in dices:
        if form is None:
            form = a
        else:
            embed.add_field(name=f'**{form}**', value=f'{str(a)}', inline=False)
            form = None
    embed.add_field(name=f'**Gesamt Ergebnis:**', value=f'{str(result)}', inline=False)
    
    msg.edit(embed=embed)

@bot.slash_command(name="disconnect", description="Wift einen Nutzer aus seiem Aktuellem Sprachkannal.")
@discord.default_permissions(
    administrator=True,
)
@discord.option(
    "user",
    discord.User, 
    required=True,
    default=None
)
@discord.option(
    "reason", 
    required=True,
    default=None
)
async def disconnect(ctx: discord.ApplicationContext, user, reason):
    if user is None:
            embed = discord.Embed(title=f"__**Gebe einen Nutzer an um diesen auf seinem Sprachkanal zu werfen!**__", color=0xFF0000)
    elif user.voice is None:
        embed = discord.Embed(title=f"__**Der Nutzer {user.mention} befindet sich nicht in einem Sprachkanal!**__", color=0xFF0000)
    else:
        duration = datetime.timedelta(seconds=1)
        reason = f"/disconnect - by {ctx.author.mention} | GamingLoungeBot\n{reason}"
        embed = discord.Embed(title=f"__**Der Nutzer {user.mention} wurde aus seinem Sprachkanal geworfen.**__", color=0xAAFF00)
        await user.timeout(duration, reason=reason)
        
    msg = ctx.respond(embed=embed, ephemeral=True)
    
@bot.slash_command(name="message remove", description="Löscht eine Nachricht durch ID")
@discord.default_permissions(
    administrator=True,
)
@discord.option(
    "messageId",
    required=True,
    default=None
)
async def modMessageDeletion(ctx: discord.ApplicationContext, messageId):
    if messageId is None:
        embed = discord.Embed(title=f"__**Du must Eine Nachrichten ID angeben um diese nachricht zu löschen!**__", color=0xFF0000)
        ctx.respond(embed=embed, ephemeral=True)
    else:
        message = ctx.fetch_message(messageId)
        # embed =
        if ctx.guild.id in bot.get_channel(config['modMessageDeletion']):
            channel = bot.get_channel(config['modMessageDeletion'][ctx.guild.id])
            modEmbed = discord.Embed(title=f"__**Der Nutzer {ctx.author.mention} hat eine nachricht gelöscht**__")
            modEmbed.add_field(name=f'**Nutzer**', value=f'{message.author.mention}', inline=False)
            modEmbed.add_field(name=f'**Inhalt**', value=f'{message.content}', inline=False)
            channel.sendMessage(embed=modEmbed)
        else: 
            embed = discord.Embed(title=f"__**Es wurde kein Mod  Nachrichten lösch Log eingestellt, nutze /setup modMessageDeletion <channel>**__", color=0xAAFF00)
        await ctx.respond(embed=embed, ephemeral=True)
    
@bot.slash_command(name="setup modMessageDeletion")
@discord.default_permissions(
    administrator=True,
)
@discord.option(
    "channel",
    Union[discord.TextChannel],
    required=True,
    default=None
)
async def setup_modMessageDeletion(ctx: discord.ApplicationContext, channel):
    config.update({"modMessageDeletion":{ctx.guild.id:channel.id}})
    embed = discord.Embed(name=f'__**Mod Nachrichten lösch Log**__', value=f'Neuer Kanal: {channel.mention}')
    await ctx.respond(embed=embed, ephemeral=True)

def saveConfig():
    global configEdit, config
    if configEdit:
        configEdit = False
        with open("configs/config.json", 'w') as json_file:
            json.dump(config, json_file, 
                            indent=4,  
                            separators=(',',': '))
        configEdit = True
    else:
        print("coudn´t save config")

Timer(300, saveConfig).start()


bot.run(os.getenv('TOKEN'))

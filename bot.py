import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
from datetime import datetime, timezone
from database import tempmute_col, tempban_col

load_dotenv()

# Regeneration automatique des cogs depuis setup_files.py
try:
    exec(open("setup_files.py").read())
    print("Cogs regeneres avec succes")
except Exception as e:
    print(f"setup_files erreur : {e}")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="+", intents=intents)
bot.remove_command("help")
bot._cogs_loaded = False

COGS = [
    "cogs.utilitaire",
    "cogs.controle_bot",
    "cogs.antiraid",
    "cogs.gestion_serveur",
    "cogs.config_serveur",
    "cogs.logs_config",
    "cogs.params_moderation",
    "cogs.moderation",
    "cogs.welcome_tickets",
]

async def restore_tempmutes():
    now = datetime.now(timezone.utc).timestamp()
    async for doc in tempmute_col.find({}):
        guild = bot.get_guild(doc["guild_id"])
        if not guild:
            continue
        member = guild.get_member(doc["user_id"])
        role = guild.get_role(doc["role_id"])
        if not member or not role:
            await tempmute_col.delete_one({"_id": doc["_id"]})
            continue
        remaining = doc["expire_at"] - now
        if remaining <= 0:
            if role in member.roles:
                await member.remove_roles(role)
            await tempmute_col.delete_one({"_id": doc["_id"]})
            print(f"  🔊 Tempmute expiré (downtime) : {member}")
        else:
            async def unmute_task(m=member, r=role, t=remaining, d=doc):
                await asyncio.sleep(t)
                try:
                    if r in m.roles:
                        await m.remove_roles(r)
                        print(f"  🔊 Tempmute terminé (reprise) : {m}")
                except Exception:
                    pass
                await tempmute_col.delete_one({"_id": d["_id"]})
            asyncio.create_task(unmute_task())
            print(f"  🔇 Tempmute repris : {member} ({int(remaining)}s restantes)")

async def restore_tempbans():
    now = datetime.now(timezone.utc).timestamp()
    async for doc in tempban_col.find({}):
        guild = bot.get_guild(doc["guild_id"])
        if not guild:
            continue
        remaining = doc["expire_at"] - now
        user_id = doc["user_id"]
        if remaining <= 0:
            try:
                user = await bot.fetch_user(user_id)
                await guild.unban(user)
                print(f"  ✅ Tempban expiré (downtime) : {user}")
            except Exception:
                pass
            await tempban_col.delete_one({"_id": doc["_id"]})
        else:
            async def unban_task(gid=guild, uid=user_id, t=remaining, d=doc):
                await asyncio.sleep(t)
                try:
                    user = await bot.fetch_user(uid)
                    await gid.unban(user)
                    print(f"  ✅ Tempban terminé (reprise) : {user}")
                except Exception:
                    pass
                await tempban_col.delete_one({"_id": d["_id"]})
            asyncio.create_task(unban_task())
            print(f"  🔨 Tempban repris : user_id={user_id} ({int(remaining)}s restantes)")

@bot.event
async def on_ready():
    if bot._cogs_loaded:
        return
    bot._cogs_loaded = True
    print(f"✅ Connecté en tant que {bot.user}")
    for cog in COGS:
        try:
            await bot.load_extension(cog)
            print(f"  ✔ {cog} chargé")
        except Exception as e:
            print(f"  ✘ Erreur sur {cog} : {e}")
    print("🔄 Reprise des tempmutes/tempbans...")
    await restore_tempmutes()
    await restore_tempbans()
    print("✅ Bot prêt !")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.CheckFailure):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Tu n'as pas la permission d'utiliser cette commande.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Membre introuvable.")
    elif isinstance(error, commands.RoleNotFound):
        await ctx.send("❌ Rôle introuvable.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Argument invalide. Vérifie ta commande.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Argument manquant : `{error.param.name}`")
    elif isinstance(error, commands.NotOwner):
        await ctx.send("❌ Cette commande est réservée au propriétaire du bot.")
    elif isinstance(error, commands.CommandInvokeError):
        await ctx.send(f"❌ Une erreur s'est produite : `{error.original}`")
        print(f"[ERREUR] {ctx.command} : {error.original}")

@bot.command()
async def help(ctx, categorie: str = None):
    menus = {
        "moderation": {
            "title": "🔨 Modération",
            "color": discord.Color.red(),
            "commands": [
                ("+warn @membre [raison]", "Avertit un membre"),
                ("+mute @membre [raison]", "Mute un membre"),
                ("+tempmute @membre <durée> [raison]", "Mute temporaire (10m, 2h, 1j)"),
                ("+unmute @membre", "Unmute un membre"),
                ("+unmuteall", "Supprime tous les mutes"),
                ("+mutelist", "Liste des membres mutés"),
                ("+kick @membre [raison]", "Expulse un membre"),
                ("+ban @membre [raison]", "Bannit un membre"),
                ("+tempban @membre <durée> [raison]", "Ban temporaire"),
                ("+unban <ID>", "Débannit par ID"),
                ("+banlist", "Liste des bans"),
                ("+unbanall", "Supprime tous les bans"),
                ("+clear [nombre] [@membre]", "Supprime des messages"),
                ("+lock [#salon]", "Verrouille un salon"),
                ("+unlock [#salon]", "Déverrouille un salon"),
                ("+lockall / +unlockall", "Verrouille/déverrouille tout"),
                ("+hide [#salon]", "Cache un salon"),
                ("+unhide [#salon]", "Affiche un salon"),
                ("+hideall / +unhideall", "Cache/affiche tout"),
                ("+addrole @membre <rôle>", "Ajoute un rôle"),
                ("+delrole @membre <rôle>", "Retire un rôle"),
                ("+derank @membre", "Supprime tous les rôles"),
                ("+sanctions @membre", "Affiche les sanctions"),
                ("+delsanction @membre <n°>", "Supprime une sanction"),
                ("+clearsanctions @membre", "Supprime les sanctions"),
            ]
        },
        "utilitaire": {
            "title": "📦 Utilitaire",
            "color": discord.Color.blurple(),
            "commands": [
                ("+serverinfo", "Infos du serveur"),
                ("+vocinfo", "Activité vocale"),
                ("+user [@membre]", "Infos utilisateur"),
                ("+member [@membre]", "Infos membre"),
                ("+role <rôle>", "Infos sur un rôle"),
                ("+channel [#salon]", "Infos sur un salon"),
                ("+pic [@membre]", "Photo de profil"),
                ("+banner [@membre]", "Bannière"),
                ("+serverpic", "Icône du serveur"),
                ("+serverbanner", "Bannière du serveur"),
                ("+allbots", "Liste des bots"),
                ("+alladmins", "Liste des admins"),
                ("+boosters", "Liste des boosters"),
                ("+rolemembers <rôle>", "Membres avec un rôle"),
                ("+snipe", "Dernier message supprimé"),
                ("+suggestion <message>", "Poste une suggestion"),
                ("+wiki <mot-clé>", "Recherche Wikipedia"),
                ("+calc <calcul>", "Calculatrice"),
            ]
        },
        "antiraid": {
            "title": "🛡️ Antiraid",
            "color": discord.Color.orange(),
            "commands": [
                ("+antitoken on/off/lock", "Active/désactive l'antitoken"),
                ("+antitoken <nb>/<durée>", "Configure la sensibilité"),
                ("+secur", "Paramètres antiraid"),
                ("+raidping <rôle>", "Rôle pingé en cas de raid"),
                ("+wl [@membre]", "Whitelist antiraid"),
                ("+unwl @membre", "Retire de la whitelist"),
                ("+clearwl", "Vide la whitelist"),
            ]
        },
        "modparams": {
            "title": "🔒 Paramètres de modération",
            "color": discord.Color.dark_gray(),
            "commands": [
                ("+muterole", "Crée/met à jour le rôle Muted"),
                ("+antispam on/off", "Active/désactive l'antispam"),
                ("+antispam <nb>/<durée>", "Configure l'antispam"),
                ("+antilink on/off", "Active/désactive l'antilink"),
                ("+antilink invite/all", "Mode antilink"),
                ("+badwords on/off", "Active/désactive le filtre"),
                ("+badwords add <mot>", "Ajoute un mot interdit"),
                ("+badwords del <mot>", "Retire un mot interdit"),
                ("+badwords list", "Liste des mots interdits"),
                ("+clearbadwords", "Vide la liste"),
            ]
        },
        "gestion": {
            "title": "⚙️ Gestion du serveur",
            "color": discord.Color.green(),
            "commands": [
                ("+giveaway", "Crée un giveaway"),
                ("+slowmode <sec> [#salon]", "Change le slowmode"),
                ("+renew [#salon]", "Recrée un salon"),
                ("+voicemove <#src> <#dest>", "Déplace les membres vocaux"),
                ("+voicekick @membre", "Déconnecte du vocal"),
                ("+bringall <#salon>", "Amène tous en vocal"),
                ("+massiverole <rôle>", "Ajoute un rôle à tous"),
                ("+unmassiverole <rôle>", "Retire un rôle à tous"),
            ]
        },
        "logs": {
            "title": "📋 Logs",
            "color": discord.Color.teal(),
            "commands": [
                ("+modlog on #salon", "Active les logs de modération"),
                ("+modlog off", "Désactive les logs"),
                ("+settings", "Affiche tous les paramètres"),
            ]
        },
        "config": {
            "title": "🔧 Configuration",
            "color": discord.Color.gold(),
            "commands": [
                ("+sync [all]", "Synchronise les permissions"),
                ("+perms", "Permissions du bot"),
                ("+setperm <perm> [rôle]", "Donne une permission"),
                ("+delperm <rôle>", "Retire les permissions"),
            ]
        },
        "controle": {
            "title": "🤖 Contrôle du bot",
            "color": discord.Color.purple(),
            "commands": [
                ("+say <message>", "Fait parler le bot"),
                ("+setname <nom>", "Change le nom du bot"),
                ("+prefix <préfixe>", "Change le préfixe"),
                ("+serverlist", "Liste des serveurs"),
                ("+owner [@membre]", "Grade Owner"),
                ("+unowner @membre", "Retire le grade Owner"),
                ("+bl [@membre] [raison]", "Blacklist"),
                ("+unbl @membre", "Retire de la blacklist"),
                ("+blinfo @membre", "Infos blacklist"),
                ("+clearbl", "Vide la blacklist"),
            ]
        },
    }

    if not categorie:
        embed = discord.Embed(
            title="📖 Menu d'aide",
            description="Utilise `+help <catégorie>` pour voir les commandes.\n",
            color=discord.Color.blurple()
        )
        embed.add_field(name="🔨 moderation", value="Ban, kick, mute, lock...", inline=True)
        embed.add_field(name="📦 utilitaire", value="Infos, wiki, calc...", inline=True)
        embed.add_field(name="🛡️ antiraid", value="Antitoken, whitelist...", inline=True)
        embed.add_field(name="🔒 modparams", value="Antispam, antilink...", inline=True)
        embed.add_field(name="⚙️ gestion", value="Giveaway, rôles...", inline=True)
        embed.add_field(name="📋 logs", value="Modlog, settings...", inline=True)
        embed.add_field(name="🔧 config", value="Permissions, sync...", inline=True)
        embed.add_field(name="🤖 controle", value="Owners, blacklist...", inline=True)
        embed.set_footer(text="Préfixe : +  |  Exemple : +help moderation")
        await ctx.send(embed=embed)
    elif categorie.lower() in menus:
        menu = menus[categorie.lower()]
        embed = discord.Embed(title=menu["title"], color=menu["color"])
        for cmd, desc in menu["commands"]:
            embed.add_field(name=cmd, value=desc, inline=False)
        embed.set_footer(text="[ ] = optionnel  |  < > = obligatoire")
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Catégorie inconnue. Utilise `+help` pour voir la liste.")

bot.run(os.getenv("DISCORD_TOKEN"))

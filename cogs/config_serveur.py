import discord
from discord.ext import commands
from database import get_config, set_config, config_col

# Niveau de permission par defaut pour chaque commande
DEFAULT_PERMS = {
    # Niveau 1 - Tout le monde
    "help": 1, "serverinfo": 1, "vocinfo": 1, "user": 1, "member": 1,
    "pic": 1, "banner": 1, "serverpic": 1, "serverbanner": 1,
    "role": 1, "channel": 1, "boosters": 1, "allbots": 1,
    "alladmins": 1, "botadmins": 1, "rolemembers": 1,
    "snipe": 1, "wiki": 1, "search": 1, "calc": 1,
    "suggestion": 1, "changelogs": 1, "emoji": 1,
    # Niveau 2 - Membres de confiance
    "warn": 2, "sanctions": 2,
    # Niveau 3 - Moderateurs
    "mute": 3, "unmute": 3, "tempmute": 3, "mutelist": 3,
    "clear": 3, "kick": 3,
    # Niveau 4 - Moderateurs superieurs
    "ban": 4, "unban": 4, "tempban": 4, "banlist": 4,
    "lock": 4, "unlock": 4, "hide": 4, "unhide": 4,
    "addrole": 4, "delrole": 4,
    # Niveau 5 - Admins
    "lockall": 5, "unlockall": 5, "hideall": 5, "unhideall": 5,
    "derank": 5, "unmuteall": 5, "unbanall": 5,
    "clearsanctions": 5, "delsanction": 5,
    "antispam": 5, "antilink": 5, "badwords": 5, "clearbadwords": 5,
    "muterole": 5, "slowmode": 5, "renew": 5,
    "modlog": 5, "settings": 5, "perms": 5,
    # Niveau 6 - Admins superieurs
    "wl": 6, "unwl": 6, "clearwl": 6, "raidping": 6,
    "antitoken": 6, "secur": 6,
    "massiverole": 6, "unmassiverole": 6,
    "voicemove": 6, "voicekick": 6, "bringall": 6,
    "giveaway": 6, "sync": 6, "setperm": 6, "delperm": 6,
    "clearallsanctions": 6,
    # Niveau 7 - Co-proprietaires
    "say": 7, "prefix": 7, "clearperms": 7,
    # Niveau 8 - Proprietaires
    "owner": 8, "unowner": 8, "serverlist": 8,
    "setname": 8,
    # Niveau 9 - Owner du bot uniquement
    "bl": 9, "unbl": 9, "blinfo": 9, "clearbl": 9,
}

LEVEL_NAMES = {
    1: "Tout le monde",
    2: "Membres de confiance",
    3: "Moderateurs",
    4: "Moderateurs superieurs",
    5: "Administrateurs",
    6: "Administrateurs superieurs",
    7: "Co-proprietaires",
    8: "Proprietaires du serveur",
    9: "Owner du bot uniquement",
}

LEVEL_COLORS = {
    1: discord.Color.light_grey(),
    2: discord.Color.green(),
    3: discord.Color.blue(),
    4: discord.Color.gold(),
    5: discord.Color.orange(),
    6: discord.Color.red(),
    7: discord.Color.purple(),
    8: discord.Color.dark_red(),
    9: discord.Color.from_rgb(0, 0, 0),
}

async def get_user_level(member: discord.Member, guild_id: int) -> int:
    """Retourne le niveau de permission d'un membre"""
    cfg = await get_config(guild_id)
    # Niveau 9 : owner du bot (defini dans controle_bot)
    # Niveau 8 : proprietaire du serveur
    if member.guild.owner_id == member.id:
        return 8
    # Verifier les niveaux 7 a 2 via les roles configures
    for level in range(7, 1, -1):
        role_id = cfg.get(f"perm_level_{level}")
        if role_id:
            role = member.guild.get_role(role_id)
            if role and role in member.roles:
                return level
    # Verifier les permissions Discord natives comme fallback
    if member.guild_permissions.administrator:
        return 5
    if member.guild_permissions.ban_members:
        return 4
    if member.guild_permissions.kick_members:
        return 3
    return 1

async def check_perm(ctx, command_name: str) -> bool:
    """Verifie si l'auteur a la permission d'utiliser la commande"""
    cfg = await get_config(ctx.guild.id)
    # Recuperer le niveau requis (custom ou defaut)
    required = cfg.get(f"cmd_perm_{command_name}", DEFAULT_PERMS.get(command_name, 5))
    user_level = await get_user_level(ctx.author, ctx.guild.id)
    # Owner du serveur = niveau 8 minimum
    if ctx.author.id == ctx.guild.owner_id:
        return True
    return user_level >= required

class ConfigServeur(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def perms(self, ctx, niveau: int = None):
        """Affiche le systeme de permissions (+perms ou +perms 3)"""
        if not await check_perm(ctx, "perms"):
            await ctx.send("Vous n'avez pas la permission.")
            return

        cfg = await get_config(ctx.guild.id)

        if niveau is None:
            # Afficher tous les niveaux avec les roles associes
            embed = discord.Embed(
                title="Systeme de permissions",
                description="Utilise `+perms <niveau>` pour voir les commandes d'un niveau.\nUtilise `+setperm <niveau> <@role>` pour assigner un role a un niveau.",
                color=discord.Color.blurple()
            )
            for lvl in range(1, 10):
                role_id = cfg.get(f"perm_level_{lvl}")
                role_mention = f"<@&{role_id}>" if role_id else "Non configure"
                if lvl == 1:
                    role_mention = "Tout le monde"
                elif lvl == 8:
                    role_mention = "Proprietaire du serveur"
                elif lvl == 9:
                    role_mention = "Owner du bot"
                embed.add_field(
                    name=f"Niveau {lvl} - {LEVEL_NAMES[lvl]}",
                    value=role_mention,
                    inline=False
                )
            await ctx.send(embed=embed)

        elif 1 <= niveau <= 9:
            # Afficher toutes les commandes de ce niveau
            custom_perms = {k.replace("cmd_perm_", ""): v for k, v in cfg.items() if k.startswith("cmd_perm_")}
            all_perms = {**DEFAULT_PERMS, **custom_perms}

            cmds = [cmd for cmd, lvl in all_perms.items() if int(lvl) == niveau]
            cmds.sort()

            role_id = cfg.get(f"perm_level_{niveau}")
            role_mention = f"<@&{role_id}>" if role_id else ("Tout le monde" if niveau == 1 else "Non configure")
            if niveau == 8:
                role_mention = "Proprietaire du serveur"
            if niveau == 9:
                role_mention = "Owner du bot"

            embed = discord.Embed(
                title=f"Niveau {niveau} - {LEVEL_NAMES[niveau]}",
                description=f"Role associe : {role_mention}\n\n**Commandes ({len(cmds)}) :**\n" +
                            (", ".join([f"`+{c}`" for c in cmds]) if cmds else "Aucune commande"),
                color=LEVEL_COLORS[niveau]
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("Le niveau doit etre entre 1 et 9.")

    @commands.command()
    async def setperm(self, ctx, cible: str, valeur: str = None):
        """Change la permission d'une commande ou assigne un role a un niveau
        Exemples:
        +setperm 3 @Moderateur  -> assigne le role Moderateur au niveau 3
        +setperm ban 4          -> met la commande ban au niveau 4
        """
        if not await check_perm(ctx, "setperm"):
            await ctx.send("Vous n'avez pas la permission.")
            return

        # Cas 1 : assigner un role a un niveau (+setperm 3 @Role)
        if cible.isdigit():
            niveau = int(cible)
            if not 2 <= niveau <= 7:
                await ctx.send("Le niveau doit etre entre 2 et 7 pour l'assignation de roles.")
                return
            if not ctx.message.role_mentions:
                await ctx.send("Mentionne un role. Exemple : `+setperm 3 @Moderateur`")
                return
            role = ctx.message.role_mentions[0]
            await set_config(ctx.guild.id, {f"perm_level_{niveau}": role.id})
            embed = discord.Embed(
                title="Permission mise a jour",
                description=f"Le role {role.mention} a ete assigne au niveau **{niveau} - {LEVEL_NAMES[niveau]}**",
                color=LEVEL_COLORS[niveau]
            )
            await ctx.send(embed=embed)

        # Cas 2 : changer le niveau d'une commande (+setperm ban 4)
        else:
            cmd_name = cible.lower().lstrip("+")
            if cmd_name not in DEFAULT_PERMS:
                await ctx.send(f"Commande `{cmd_name}` introuvable. Utilise `+perms` pour voir toutes les commandes.")
                return
            if valeur is None or not valeur.isdigit():
                await ctx.send(f"Precise un niveau. Exemple : `+setperm {cmd_name} 4`")
                return
            niveau = int(valeur)
            if not 1 <= niveau <= 9:
                await ctx.send("Le niveau doit etre entre 1 et 9.")
                return
            await set_config(ctx.guild.id, {f"cmd_perm_{cmd_name}": niveau})
            embed = discord.Embed(
                title="Permission mise a jour",
                description=f"La commande `+{cmd_name}` est maintenant au niveau **{niveau} - {LEVEL_NAMES[niveau]}**",
                color=LEVEL_COLORS[niveau]
            )
            await ctx.send(embed=embed)

    @commands.command()
    async def delperm(self, ctx, cible: str):
        """Remet une commande ou un niveau a sa valeur par defaut
        +delperm ban        -> remet +ban a son niveau par defaut
        +delperm 3          -> supprime le role du niveau 3
        """
        if not await check_perm(ctx, "delperm"):
            await ctx.send("Vous n'avez pas la permission.")
            return

        if cible.isdigit():
            niveau = int(cible)
            await config_col.update_one(
                {"guild_id": ctx.guild.id},
                {"$unset": {f"perm_level_{niveau}": ""}},
                upsert=True
            )
            await ctx.send(f"Role du niveau {niveau} supprime.")
        else:
            cmd_name = cible.lower().lstrip("+")
            await config_col.update_one(
                {"guild_id": ctx.guild.id},
                {"$unset": {f"cmd_perm_{cmd_name}": ""}},
                upsert=True
            )
            default = DEFAULT_PERMS.get(cmd_name, "?")
            await ctx.send(f"Commande `+{cmd_name}` remise au niveau par defaut ({default}).")

    @commands.command(name="clearperms")
    async def clear_perms(self, ctx):
        """Remet toutes les permissions a leurs valeurs par defaut"""
        if not await check_perm(ctx, "clearperms"):
            await ctx.send("Vous n'avez pas la permission.")
            return
        cfg = await get_config(ctx.guild.id)
        unset = {}
        for key in cfg:
            if key.startswith("perm_level_") or key.startswith("cmd_perm_"):
                unset[key] = ""
        if unset:
            await config_col.update_one({"guild_id": ctx.guild.id}, {"$unset": unset})
        await ctx.send("Toutes les permissions ont ete remises par defaut.")

    @commands.command()
    async def sync(self, ctx, target: str = "all"):
        """Synchronise les permissions avec la categorie"""
        if not await check_perm(ctx, "sync"):
            await ctx.send("Vous n'avez pas la permission.")
            return
        if target == "all":
            count = 0
            for ch in ctx.guild.channels:
                if ch.category:
                    await ch.edit(sync_permissions=True)
                    count += 1
            await ctx.send(f"{count} salon(s) synchronise(s).")
        else:
            ch = discord.utils.get(ctx.guild.channels, name=target)
            if ch and ch.category:
                await ch.edit(sync_permissions=True)
                await ctx.send(f"{ch.mention} synchronise.")
            else:
                await ctx.send("Salon ou categorie introuvable.")

async def setup(bot):
    await bot.add_cog(ConfigServeur(bot))

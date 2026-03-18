import discord
from discord.ext import commands
from collections import defaultdict
from database import get_config, set_config, whitelist_col
import time

class Antiraid(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.join_log = defaultdict(list)  # cache RAM pour la détection de raid

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def antitoken(self, ctx, *args):
        """Configure l'antitoken"""
        if not args:
            await ctx.send("Usage : `+antitoken on`, `+antitoken off`, `+antitoken lock`, `+antitoken 5/10`")
            return
        action = args[0].lower()
        if action == "on":
            await set_config(ctx.guild.id, {"antitoken_enabled": True})
            await ctx.send("✅ Antitoken activé.")
        elif action == "off":
            await set_config(ctx.guild.id, {"antitoken_enabled": False})
            await ctx.send("✅ Antitoken désactivé.")
        elif action == "lock":
            await ctx.guild.edit(verification_level=discord.VerificationLevel.highest)
            await ctx.send("🔒 Serveur verrouillé (niveau de vérification max).")
        elif "/" in action:
            try:
                nb, dur = action.split("/")
                await set_config(ctx.guild.id, {"antitoken_nb": int(nb), "antitoken_dur": int(dur)})
                await ctx.send(f"✅ Antitoken : {nb} join(s) en {dur}s.")
            except Exception:
                await ctx.send("❌ Format invalide. Exemple : `+antitoken 5/10`")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def wl(self, ctx, member: discord.Member = None):
        """Whitelist antiraid : ajoute ou affiche"""
        if member:
            await whitelist_col.update_one(
                {"guild_id": ctx.guild.id},
                {"$addToSet": {"users": member.id}},
                upsert=True
            )
            await ctx.send(f"✅ {member.mention} ajouté à la whitelist.")
        else:
            doc = await whitelist_col.find_one({"guild_id": ctx.guild.id})
            ids = doc["users"] if doc else []
            desc = "\n".join([f"<@{uid}>" for uid in ids]) or "Whitelist vide."
            embed = discord.Embed(title="✅ Whitelist antiraid", description=desc, color=discord.Color.green())
            await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def unwl(self, ctx, member: discord.Member):
        """Retire de la whitelist"""
        await whitelist_col.update_one(
            {"guild_id": ctx.guild.id},
            {"$pull": {"users": member.id}}
        )
        await ctx.send(f"✅ {member.mention} retiré de la whitelist.")

    @commands.command(name="clearwl")
    @commands.has_permissions(administrator=True)
    async def clear_wl(self, ctx):
        """Vide la whitelist"""
        await whitelist_col.delete_one({"guild_id": ctx.guild.id})
        await ctx.send("✅ Whitelist vidée.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def raidping(self, ctx, role: discord.Role):
        """Définit le rôle pingé en cas de raid"""
        await set_config(ctx.guild.id, {"raidping_role_id": role.id})
        await ctx.send(f"✅ Rôle de raid ping défini : {role.mention}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def secur(self, ctx, action: str = None):
        """Affiche/modifie les paramètres antiraid"""
        cfg = await get_config(ctx.guild.id)
        if not action:
            doc = await whitelist_col.find_one({"guild_id": ctx.guild.id})
            wl_count = len(doc["users"]) if doc else 0
            embed = discord.Embed(title="🛡️ Paramètres Antiraid", color=discord.Color.red())
            embed.add_field(name="Antitoken", value="✅" if cfg.get("antitoken_enabled") else "❌")
            nb = cfg.get("antitoken_nb", 10)
            dur = cfg.get("antitoken_dur", 10)
            embed.add_field(name="Sensibilité", value=f"{nb} joins en {dur}s")
            embed.add_field(name="Whitelist", value=f"{wl_count} membre(s)")
            await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        cfg = await get_config(member.guild.id)
        if not cfg.get("antitoken_enabled"):
            return
        doc = await whitelist_col.find_one({"guild_id": member.guild.id})
        wl = doc["users"] if doc else []
        if member.id in wl:
            return
        nb = cfg.get("antitoken_nb", 10)
        dur = cfg.get("antitoken_dur", 10)
        guild_id = member.guild.id
        now = time.time()
        self.join_log[guild_id] = [t for t in self.join_log[guild_id] if now - t < dur]
        self.join_log[guild_id].append(now)
        if len(self.join_log[guild_id]) >= nb:
            self.join_log[guild_id].clear()
            await member.guild.edit(verification_level=discord.VerificationLevel.highest)
            rp_id = cfg.get("raidping_role_id")
            ping = f"<@&{rp_id}>" if rp_id else ""
            log_channel = member.guild.system_channel
            if log_channel:
                await log_channel.send(f"🚨 {ping} **RAID DÉTECTÉ** - Niveau de vérification mis au maximum !")

async def setup(bot):
    await bot.add_cog(Antiraid(bot))

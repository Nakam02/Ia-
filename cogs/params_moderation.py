import discord
from discord.ext import commands
from collections import defaultdict
from datetime import datetime, timezone
import re
import time
from database import get_config, set_config, badwords_col

class ParamsModeration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.msg_timestamps = defaultdict(list)  # cache RAM pour l'antispam (performance)

    # ── Muterole ──────────────────────────────────────────────────

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def muterole(self, ctx):
        """Crée/met à jour le rôle Muted"""
        role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not role:
            role = await ctx.guild.create_role(name="Muted", reason="Création rôle muet")
        errors = []
        for ch in ctx.guild.channels:
            try:
                await ch.set_permissions(role, send_messages=False, speak=False, add_reactions=False)
            except Exception:
                errors.append(ch.name)
        msg = "✅ Rôle Muted mis à jour."
        if errors:
            msg += f"\n⚠️ Erreurs sur : {', '.join(errors)}"
        await ctx.send(msg)

    # ── Antispam ──────────────────────────────────────────────────

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def antispam(self, ctx, *args):
        """Active/désactive ou configure l'antispam"""
        cfg = await get_config(ctx.guild.id)
        if not args:
            status = "activé" if cfg.get("antispam_enabled") else "désactivé"
            nb = cfg.get("antispam_nb", 5)
            dur = cfg.get("antispam_dur", 5)
            await ctx.send(f"ℹ️ Antispam : **{status}** - Config : {nb} msg en {dur}s\nUsage : `+antispam on/off` ou `+antispam 5/3`")
            return
        action = args[0].lower()
        if action in ("on", "off"):
            await set_config(ctx.guild.id, {"antispam_enabled": action == "on"})
            await ctx.send(f"✅ Antispam {'activé' if action == 'on' else 'désactivé'}.")
        elif "/" in action:
            try:
                nb, dur = action.split("/")
                await set_config(ctx.guild.id, {"antispam_nb": int(nb), "antispam_dur": int(dur)})
                await ctx.send(f"✅ Antispam : {nb} message(s) en {dur}s max.")
            except Exception:
                await ctx.send("❌ Format invalide. Exemple : `+antispam 5/3`")

    # ── Antilink ──────────────────────────────────────────────────

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def antilink(self, ctx, *args):
        """Active/désactive l'antilink"""
        cfg = await get_config(ctx.guild.id)
        if not args:
            status = "activé" if cfg.get("antilink_enabled") else "désactivé"
            mode = cfg.get("antilink_mode", "all")
            await ctx.send(f"ℹ️ Antilink : **{status}** - Mode : {mode}\nUsage : `+antilink on/off` ou `+antilink invite/all`")
            return
        action = args[0].lower()
        if action in ("on", "off"):
            await set_config(ctx.guild.id, {"antilink_enabled": action == "on"})
            await ctx.send(f"✅ Antilink {'activé' if action == 'on' else 'désactivé'}.")
        elif action in ("invite", "all"):
            await set_config(ctx.guild.id, {"antilink_mode": action})
            await ctx.send(f"✅ Antilink réglé sur : **{action}**")

    # ── Badwords ──────────────────────────────────────────────────

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def badwords(self, ctx, action: str = None, *, word: str = None):
        """Gère la liste des mots interdits"""
        doc = await badwords_col.find_one({"guild_id": ctx.guild.id})
        words = set(doc["words"]) if doc else set()

        if not action or action == "list":
            await ctx.send(f"🚫 Mots interdits ({len(words)}) : {', '.join(words) or 'Aucun'}")
        elif action == "on":
            await set_config(ctx.guild.id, {"badwords_enabled": True})
            await ctx.send("✅ Filtre de mots activé.")
        elif action == "off":
            await set_config(ctx.guild.id, {"badwords_enabled": False})
            await ctx.send("✅ Filtre de mots désactivé.")
        elif action == "add" and word:
            words.add(word.lower())
            await badwords_col.update_one(
                {"guild_id": ctx.guild.id},
                {"$set": {"words": list(words)}},
                upsert=True
            )
            await ctx.send(f"✅ `{word}` ajouté aux mots interdits.")
        elif action == "del" and word:
            words.discard(word.lower())
            await badwords_col.update_one(
                {"guild_id": ctx.guild.id},
                {"$set": {"words": list(words)}},
                upsert=True
            )
            await ctx.send(f"✅ `{word}` retiré des mots interdits.")
        else:
            await ctx.send("Usage : `+badwords on/off/list/add <mot>/del <mot>`")

    @commands.command(name="clearbadwords")
    @commands.has_permissions(administrator=True)
    async def clear_badwords(self, ctx):
        """Supprime tous les mots interdits"""
        await badwords_col.delete_one({"guild_id": ctx.guild.id})
        await ctx.send("✅ Liste des mots interdits vidée.")

    # ── Listener on_message ───────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        guild_id = message.guild.id
        cfg = await get_config(guild_id)

        # Filtre mots interdits
        if cfg.get("badwords_enabled"):
            doc = await badwords_col.find_one({"guild_id": guild_id})
            words = doc["words"] if doc else []
            if any(w in message.content.lower() for w in words):
                try:
                    await message.delete()
                    await message.channel.send(f"⚠️ {message.author.mention}, ce mot est interdit !", delete_after=5)
                except Exception:
                    pass
                return

        # Antilink
        if cfg.get("antilink_enabled"):
            mode = cfg.get("antilink_mode", "all")
            blocked = False
            if mode == "all" and re.search(r"https?://", message.content):
                blocked = True
            elif mode == "invite" and re.search(r"discord\.gg/", message.content):
                blocked = True
            if blocked:
                try:
                    await message.delete()
                    await message.channel.send(f"🔗 {message.author.mention}, les liens sont interdits !", delete_after=5)
                except Exception:
                    pass
                return

        # Antispam
        if cfg.get("antispam_enabled"):
            nb = cfg.get("antispam_nb", 5)
            dur = cfg.get("antispam_dur", 5)
            key = (guild_id, message.author.id)
            now = time.time()
            self.msg_timestamps[key] = [t for t in self.msg_timestamps[key] if now - t < dur]
            self.msg_timestamps[key].append(now)
            if len(self.msg_timestamps[key]) >= nb:
                self.msg_timestamps[key].clear()
                try:
                    await message.delete()
                    await message.channel.send(
                        f"🚫 {message.author.mention}, tu envoies des messages trop vite !", delete_after=5
                    )
                except Exception:
                    pass

async def setup(bot):
    await bot.add_cog(ParamsModeration(bot))

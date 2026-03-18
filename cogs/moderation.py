import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timezone
from database import (
    add_sanction, get_sanctions, clear_sanctions,
    clear_all_sanctions, get_config, tempmute_col, tempban_col,
    sanctions_col
)

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _log(self, ctx, action, target, reason):
        self.bot.dispatch("mod_action", ctx, action, target, reason)

    async def _resolve_member(self, ctx, member):
        """Résout le membre depuis une mention ou une réponse"""
        if member is None:
            if ctx.message.reference and ctx.message.reference.resolved:
                ref = ctx.message.reference.resolved
                if isinstance(ref, discord.Message):
                    return ref.author
        return member

    # ── Sanctions ─────────────────────────────────────────────────

    @commands.command()
    async def sanctions(self, ctx, member: discord.Member):
        """Affiche les sanctions d'un membre"""
        data = await get_sanctions(ctx.guild.id, member.id)
        if not data:
            await ctx.send(f"✅ {member.mention} n'a aucune sanction.")
            return
        # Discord limite à 25 fields par embed - on pagine si besoin
        chunks = [data[i:i+10] for i in range(0, len(data), 10)]
        for page, chunk in enumerate(chunks, 1):
            embed = discord.Embed(
                title=f"📋 Sanctions de {member.display_name} (page {page}/{len(chunks)})",
                color=discord.Color.orange()
            )
            for i, s in enumerate(chunk, (page-1)*10+1):
                embed.add_field(
                    name=f"#{i} - {s['type']}",
                    value=f"📝 {s['reason'][:200]}\n🔧 <@{s['mod_id']}>\n📅 {s['date']}",
                    inline=False
                )
            await ctx.send(embed=embed)

    @commands.command(name="delsanction")
    @commands.has_permissions(kick_members=True)
    async def del_sanction(self, ctx, member: discord.Member, numero: int):
        """Supprime une sanction d'un membre par son numéro"""
        data = await get_sanctions(ctx.guild.id, member.id)
        if not data or numero < 1 or numero > len(data):
            await ctx.send("❌ Numéro de sanction invalide.")
            return
        data.pop(numero - 1)
        await sanctions_col.update_one(
            {"guild_id": ctx.guild.id, "user_id": member.id},
            {"$set": {"sanctions": data}}
        )
        await ctx.send(f"✅ Sanction #{numero} de {member.mention} supprimée.")

    @commands.command(name="clearsanctions")
    @commands.has_permissions(kick_members=True)
    async def clear_sanctions_cmd(self, ctx, member: discord.Member):
        """Supprime toutes les sanctions d'un membre"""
        await clear_sanctions(ctx.guild.id, member.id)
        await ctx.send(f"✅ Toutes les sanctions de {member.mention} ont été supprimées.")

    @commands.command(name="clearallsanctions")
    @commands.has_permissions(administrator=True)
    async def clear_all_sanctions_cmd(self, ctx):
        """Supprime toutes les sanctions de tous les membres"""
        await clear_all_sanctions(ctx.guild.id)
        await ctx.send("✅ Toutes les sanctions du serveur ont été supprimées.")

    # ── Modération ────────────────────────────────────────────────

    @commands.command(name="clear", aliases=["purge", "sup"])
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def clear(self, ctx, nombre: int = 10, member: discord.Member = None):
        """Supprime des messages (+clear 10 ou +clear 10 @membre)"""
        if nombre < 1 or nombre > 1000:
            await ctx.send("❌ Le nombre doit être entre 1 et 1000.")
            return
        try:
            await ctx.message.delete()
        except Exception:
            pass
        def check(m):
            return member is None or m.author == member
        try:
            deleted = await ctx.channel.purge(limit=nombre, check=check)
            confirmation = await ctx.send(f"🗑️ {len(deleted)} message(s) supprimé(s).")
            await confirmation.delete(delay=3)
        except discord.Forbidden:
            await ctx.send("❌ Le bot n'a pas la permission **Gérer les messages** dans ce salon.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Erreur Discord : `{e}`")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def warn(self, ctx, member: discord.Member = None, *, reason="Aucune raison"):
        """Avertit un membre - fonctionne aussi en répondant à un message"""
        member = await self._resolve_member(ctx, member)
        if not member:
            await ctx.send("❌ Mentionne un membre ou réponds à son message.")
            return
        sanction = {
            "type": "WARN", "reason": reason,
            "mod_id": ctx.author.id,
            "date": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
        }
        await add_sanction(ctx.guild.id, member.id, sanction)
        await ctx.send(f"⚠️ {member.mention} a reçu un avertissement. Raison : **{reason}**")
        self._log(ctx, "WARN", member, reason)

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member = None, *, reason="Aucune raison"):
        """Mute un membre - fonctionne aussi en répondant à un message"""
        # Si pas de mention, chercher dans le message auquel on répond
        if member is None:
            if ctx.message.reference and ctx.message.reference.resolved:
                ref = ctx.message.reference.resolved
                if isinstance(ref, discord.Message):
                    member = ref.author
            if member is None:
                await ctx.send("❌ Mentionne un membre ou réponds à son message. Exemple : `+mute @membre` ou réponds à son message avec `+mute`")
                return
        # Empêcher de muter un bot ou soi-même
        if member.bot:
            await ctx.send("❌ Impossible de muter un bot.")
            return
        if member == ctx.author:
            await ctx.send("❌ Tu ne peux pas te muter toi-même.")
            return
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            mute_role = await ctx.guild.create_role(name="Muted")
            for ch in ctx.guild.channels:
                try:
                    await ch.set_permissions(mute_role, send_messages=False, speak=False)
                except Exception:
                    pass
        if mute_role in member.roles:
            await ctx.send(f"❌ {member.mention} est déjà muté.")
            return
        await member.add_roles(mute_role)
        sanction = {
            "type": "MUTE", "reason": reason,
            "mod_id": ctx.author.id,
            "date": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
        }
        await add_sanction(ctx.guild.id, member.id, sanction)
        await ctx.send(f"🔇 {member.mention} est muté. Raison : **{reason}**")
        self._log(ctx, "MUTE", member, reason)

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def tempmute(self, ctx, member: discord.Member = None, duree: str = None, *, reason="Aucune raison"):
        """Mute temporaire - fonctionne aussi en répondant à un message"""
        member = await self._resolve_member(ctx, member)
        if not member:
            await ctx.send("❌ Mentionne un membre ou réponds à son message.")
            return
        if duree is None:
            await ctx.send("❌ Précise une durée. Exemple : `+tempmute @membre 10m`")
            return
        multiplicateurs = {"s": 1, "m": 60, "h": 3600, "j": 86400}
        try:
            temps = int(duree[:-1]) * multiplicateurs.get(duree[-1], 1)
        except Exception:
            await ctx.send("❌ Format invalide. Exemple : `10m`, `2h`, `1j`")
            return
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            mute_role = await ctx.guild.create_role(name="Muted")
            for ch in ctx.guild.channels:
                try:
                    await ch.set_permissions(mute_role, send_messages=False, speak=False)
                except Exception:
                    pass
        await member.add_roles(mute_role)
        expire_at = datetime.now(timezone.utc).timestamp() + temps
        await tempmute_col.update_one(
            {"guild_id": ctx.guild.id, "user_id": member.id},
            {"$set": {"expire_at": expire_at, "role_id": mute_role.id}},
            upsert=True
        )
        sanction = {
            "type": "TEMPMUTE", "reason": reason,
            "mod_id": ctx.author.id, "duree": duree,
            "date": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
        }
        await add_sanction(ctx.guild.id, member.id, sanction)
        await ctx.send(f"🔇 {member.mention} est muté pour **{duree}**. Raison : **{reason}**")
        self._log(ctx, "TEMPMUTE", member, reason)

        async def unmute_after():
            await asyncio.sleep(temps)
            if mute_role in member.roles:
                try:
                    await member.remove_roles(mute_role)
                    await ctx.send(f"🔊 {member.mention} a été automatiquement démuté.")
                except Exception:
                    pass
            await tempmute_col.delete_one({"guild_id": ctx.guild.id, "user_id": member.id})
        asyncio.create_task(unmute_after())

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member):
        """Unmute un membre"""
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if mute_role and mute_role in member.roles:
            await member.remove_roles(mute_role)
            await tempmute_col.delete_one({"guild_id": ctx.guild.id, "user_id": member.id})
            await ctx.send(f"🔊 {member.mention} est démuté.")
            self._log(ctx, "UNMUTE", member, "-")
        else:
            await ctx.send(f"❌ {member.mention} n'est pas muté.")

    @commands.command()
    async def mutelist(self, ctx):
        """Liste des membres mutés"""
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            await ctx.send("❌ Aucun rôle Muted trouvé.")
            return
        muted = mute_role.members
        desc = "\n".join([f"• {m.mention}" for m in muted]) or "Aucun membre muté."
        embed = discord.Embed(title=f"🔇 Membres mutés ({len(muted)})", description=desc, color=discord.Color.dark_gray())
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def unmuteall(self, ctx):
        """Supprime tous les mutes"""
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            await ctx.send("❌ Aucun rôle Muted trouvé.")
            return
        count = 0
        for member in mute_role.members:
            await member.remove_roles(mute_role)
            count += 1
        await tempmute_col.delete_many({"guild_id": ctx.guild.id})
        await ctx.send(f"✅ {count} membre(s) démuté(s).")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member = None, *, reason="Aucune raison"):
        """Expulse un membre - fonctionne aussi en répondant à un message"""
        member = await self._resolve_member(ctx, member)
        if not member:
            await ctx.send("❌ Mentionne un membre ou réponds à son message.")
            return
        if member.bot:
            await ctx.send("❌ Impossible d'expulser un bot.")
            return
        sanction = {
            "type": "KICK", "reason": reason,
            "mod_id": ctx.author.id,
            "date": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
        }
        await add_sanction(ctx.guild.id, member.id, sanction)
        await member.kick(reason=reason)
        await ctx.send(f"👢 {member.mention} a été expulsé. Raison : **{reason}**")
        self._log(ctx, "KICK", member, reason)

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member = None, *, reason="Aucune raison"):
        """Bannit un membre - fonctionne aussi en répondant à un message"""
        member = await self._resolve_member(ctx, member)
        if not member:
            await ctx.send("❌ Mentionne un membre ou réponds à son message.")
            return
        if member.bot:
            await ctx.send("❌ Impossible de bannir un bot.")
            return
        sanction = {
            "type": "BAN", "reason": reason,
            "mod_id": ctx.author.id,
            "date": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
        }
        await add_sanction(ctx.guild.id, member.id, sanction)
        await member.ban(reason=reason)
        await ctx.send(f"🔨 {member.mention} a été banni. Raison : **{reason}**")
        self._log(ctx, "BAN", member, reason)

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def tempban(self, ctx, member: discord.Member, duree: str, *, reason="Aucune raison"):
        """Ban temporaire"""
        multiplicateurs = {"s": 1, "m": 60, "h": 3600, "j": 86400}
        try:
            temps = int(duree[:-1]) * multiplicateurs.get(duree[-1], 1)
        except Exception:
            await ctx.send("❌ Format invalide. Exemple : `1j`, `12h`")
            return
        expire_at = datetime.now(timezone.utc).timestamp() + temps
        await tempban_col.update_one(
            {"guild_id": ctx.guild.id, "user_id": member.id},
            {"$set": {"expire_at": expire_at}},
            upsert=True
        )
        sanction = {
            "type": "TEMPBAN", "reason": reason,
            "mod_id": ctx.author.id, "duree": duree,
            "date": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
        }
        await add_sanction(ctx.guild.id, member.id, sanction)
        await member.ban(reason=reason)
        await ctx.send(f"🔨 {member.mention} banni pour **{duree}**. Raison : **{reason}**")
        self._log(ctx, "TEMPBAN", member, reason)
        member_id = member.id

        async def unban_after():
            await asyncio.sleep(temps)
            try:
                user = await ctx.bot.fetch_user(member_id)
                await ctx.guild.unban(user)
                await ctx.send(f"✅ {user} a été automatiquement débanni.")
            except Exception:
                pass
            await tempban_col.delete_one({"guild_id": ctx.guild.id, "user_id": member_id})
        asyncio.create_task(unban_after())

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, *, user_id: int):
        """Débannit un membre (par ID)"""
        user = await self.bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await tempban_col.delete_one({"guild_id": ctx.guild.id, "user_id": user_id})
        await ctx.send(f"✅ {user} a été débanni.")
        self._log(ctx, "UNBAN", user, "-")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def banlist(self, ctx):
        """Liste des bans en cours"""
        bans = [entry async for entry in ctx.guild.bans()]
        desc = "\n".join([f"• {b.user} - {b.reason or 'Aucune raison'}" for b in bans]) or "Aucun ban."
        embed = discord.Embed(title=f"🔨 Bans ({len(bans)})", description=desc, color=discord.Color.red())
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unbanall(self, ctx):
        """Supprime tous les bannissements"""
        count = 0
        async for entry in ctx.guild.bans():
            await ctx.guild.unban(entry.user)
            count += 1
        await tempban_col.delete_many({"guild_id": ctx.guild.id})
        await ctx.send(f"✅ {count} bannissement(s) supprimé(s).")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send(f"🔒 {channel.mention} est verrouillé.")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send(f"🔓 {channel.mention} est déverrouillé.")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def lockall(self, ctx):
        for ch in ctx.guild.text_channels:
            await ch.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send("🔒 Tous les salons ont été verrouillés.")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def unlockall(self, ctx):
        for ch in ctx.guild.text_channels:
            await ch.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send("🔓 Tous les salons ont été déverrouillés.")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def hide(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, view_channel=False)
        await ctx.send(f"👁️ {channel.mention} est caché.")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def unhide(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, view_channel=True)
        await ctx.send(f"👁️ {channel.mention} est visible.")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def hideall(self, ctx):
        for ch in ctx.guild.text_channels:
            await ch.set_permissions(ctx.guild.default_role, view_channel=False)
        await ctx.send("👁️ Tous les salons sont cachés.")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def unhideall(self, ctx):
        for ch in ctx.guild.text_channels:
            await ch.set_permissions(ctx.guild.default_role, view_channel=True)
        await ctx.send("👁️ Tous les salons sont visibles.")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def addrole(self, ctx, member: discord.Member, *, role: discord.Role):
        await member.add_roles(role)
        await ctx.send(f"✅ Rôle **{role.name}** ajouté à {member.mention}.")
        self._log(ctx, "ADD_ROLE", member, role.name)

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def delrole(self, ctx, member: discord.Member, *, role: discord.Role):
        await member.remove_roles(role)
        await ctx.send(f"✅ Rôle **{role.name}** retiré à {member.mention}.")
        self._log(ctx, "DEL_ROLE", member, role.name)

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def derank(self, ctx, member: discord.Member):
        roles = [r for r in member.roles if r != ctx.guild.default_role]
        await member.remove_roles(*roles)
        await ctx.send(f"✅ Tous les rôles de {member.mention} ont été supprimés.")
        self._log(ctx, "DERANK", member, "-")

async def setup(bot):
    await bot.add_cog(Moderation(bot))

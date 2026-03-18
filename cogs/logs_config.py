import discord
from discord.ext import commands
from datetime import datetime, timezone
from database import get_config, set_config, config_col

class LogsConfig(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_log_channel(self, guild_id):
        cfg = await get_config(guild_id)
        cid = cfg.get("log_channel_id")
        return self.bot.get_channel(cid) if cid else None

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def modlog(self, ctx, action: str, channel: discord.TextChannel = None):
        """Active/désactive les logs de modération"""
        if action == "on" and channel:
            await set_config(ctx.guild.id, {"log_channel_id": channel.id})
            await ctx.send(f"✅ Logs de modération activés dans {channel.mention}.")
        elif action == "off":
            await config_col.update_one({"guild_id": ctx.guild.id}, {"$unset": {"log_channel_id": ""}}, upsert=True)
            await ctx.send("✅ Logs de modération désactivés.")
        else:
            await ctx.send("Usage : `+modlog on #salon` ou `+modlog off`")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def settings(self, ctx):
        """Affiche les paramètres du bot sur le serveur"""
        cfg = await get_config(ctx.guild.id)
        cid = cfg.get("log_channel_id")
        ch = f"<#{cid}>" if cid else "Non configuré"
        embed = discord.Embed(title="⚙️ Paramètres du bot", color=discord.Color.blurple())
        embed.add_field(name="📋 Salon de logs", value=ch)
        embed.add_field(name="Préfixe", value=cfg.get("prefix", "+"))
        embed.add_field(name="Antispam", value="✅" if cfg.get("antispam_enabled") else "❌")
        embed.add_field(name="Antilink", value="✅" if cfg.get("antilink_enabled") else "❌")
        embed.add_field(name="Badwords", value="✅" if cfg.get("badwords_enabled") else "❌")
        embed.add_field(name="Antitoken", value="✅" if cfg.get("antitoken_enabled") else "❌")
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_mod_action(self, ctx, action: str, target, reason: str):
        channel = await self.get_log_channel(ctx.guild.id)
        if not channel:
            return
        colors = {
            "KICK": discord.Color.orange(), "BAN": discord.Color.red(),
            "TEMPBAN": discord.Color.dark_red(), "MUTE": discord.Color.dark_gray(),
            "TEMPMUTE": discord.Color.greyple(), "UNMUTE": discord.Color.green(),
            "WARN": discord.Color.yellow(), "UNBAN": discord.Color.teal(),
            "ADD_ROLE": discord.Color.blue(), "DEL_ROLE": discord.Color.purple(),
            "DERANK": discord.Color.magenta(),
        }
        embed = discord.Embed(
            title=f"🛡️ {action}",
            color=colors.get(action, discord.Color.blurple()),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="👤 Cible", value=getattr(target, "mention", str(target)), inline=True)
        embed.add_field(name="🔧 Modérateur", value=ctx.author.mention, inline=True)
        embed.add_field(name="📝 Raison", value=reason, inline=False)
        embed.set_footer(text=ctx.guild.name)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild:
            return
        channel = await self.get_log_channel(message.guild.id)
        if not channel:
            return
        embed = discord.Embed(title="🗑️ Message supprimé", color=discord.Color.red(), timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Auteur", value=message.author.mention)
        embed.add_field(name="Salon", value=message.channel.mention)
        embed.add_field(name="Contenu", value=message.content[:1024] or "*[vide]*", inline=False)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or before.content == after.content or not before.guild:
            return
        channel = await self.get_log_channel(before.guild.id)
        if not channel:
            return
        embed = discord.Embed(title="✏️ Message édité", color=discord.Color.orange(), timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Auteur", value=before.author.mention)
        embed.add_field(name="Salon", value=before.channel.mention)
        embed.add_field(name="Avant", value=before.content[:512] or "*[vide]*", inline=False)
        embed.add_field(name="Après", value=after.content[:512] or "*[vide]*", inline=False)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = await self.get_log_channel(member.guild.id)
        if not channel:
            return
        embed = discord.Embed(title="📥 Membre rejoint", color=discord.Color.green(), timestamp=datetime.now(timezone.utc))
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Membre", value=member.mention)
        embed.add_field(name="Compte créé le", value=member.created_at.strftime("%d/%m/%Y"))
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        channel = await self.get_log_channel(member.guild.id)
        if not channel:
            return
        embed = discord.Embed(title="📤 Membre parti", color=discord.Color.red(), timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Membre", value=str(member))
        await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(LogsConfig(bot))
